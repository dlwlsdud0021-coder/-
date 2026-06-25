"""
main.py — 포켓주식 FastAPI 백엔드
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

import database as db
from market_data import (get_index_data, get_us_indices, search_stock_by_name,
    get_all_tickers, get_top_stocks, get_ohlcv, get_investor_trading, get_current_price,
    get_index_ohlcv_history, get_kospi_investor, get_sector_performance)
from news import (fetch_market_news, fetch_stock_news, enrich_top10_summaries,
    rank_by_importance, generate_ai_summary, generate_strategy,
    classify_sentiment, classify_category, extract_related_stocks)
from home_analysis import analyze_us_impact, generate_forecast, calc_ma_status, _extra_metrics, market_phase, is_market_open
from analysis import analyze_stock, watchlist_timing
from database import get_recent_predictions, get_prediction_accuracy, save_prediction, update_prediction_result
import requests as _requests

# ─────────────────────────────────────────────────────────
# DART 공시 API
# ─────────────────────────────────────────────────────────
_DART_KEY = os.environ.get("DART_API_KEY", "")
_dart_corp_cache: dict = {}

def _dart_corp_code(stock_code: str) -> str:
    if stock_code in _dart_corp_cache:
        return _dart_corp_cache[stock_code]
    try:
        r = _requests.get(
            "https://opendart.fss.or.kr/api/company.json",
            params={"crtfc_key": _DART_KEY, "stock_code": stock_code},
            timeout=5,
        )
        d = r.json()
        if d.get("status") == "000":
            code = d.get("corp_code", "")
            _dart_corp_cache[stock_code] = code
            return code
    except Exception:
        pass
    return ""

def _dart_disclosures(stock_code: str, days: int = 30) -> list:
    if not _DART_KEY:
        return []
    corp_code = _dart_corp_code(stock_code)
    if not corp_code:
        return []
    try:
        end_dt = datetime.now()
        bgn_dt = end_dt - timedelta(days=days)
        r = _requests.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": _DART_KEY,
                "corp_code": corp_code,
                "bgn_de": bgn_dt.strftime("%Y%m%d"),
                "end_de": end_dt.strftime("%Y%m%d"),
                "page_count": 6,
            },
            timeout=6,
        )
        data = r.json()
        if data.get("status") == "000":
            items = data.get("list", [])
            result = []
            for it in items[:6]:
                rpt = it.get("report_nm", "")
                meaning, impact, badge = _analyze_disclosure(rpt)
                result.append({
                    "title":   rpt,
                    "date":    it.get("rcept_dt", "")[:10].replace("-", "."),
                    "type":    it.get("pblntf_ty_nm") or "기타공시",
                    "url":     f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it.get('rcept_no','')}",
                    "meaning": meaning,
                    "impact":  impact,
                    "badge":   badge,
                })
            return result
    except Exception:
        pass
    return []

def _analyze_disclosure(title: str) -> tuple:
    """공시 제목 기반 투자자 해석 (rule-based)"""
    t = title.lower()
    # 내부자 거래
    if "소유상황" in title or "임원" in title or "주요주주" in title:
        return (
            f"'{title}' 공시예요. 임원·주요주주가 주식을 사거나 팔 때 제출하는 공시로, "
            "지분 변동 방향이 중요한 신호가 됩니다. DART에서 원문을 확인해 매수인지 매도인지 파악하세요.",
            ["공시 당일: 매수면 긍정, 매도면 부정 신호로 해석", "단기(1~2주): 지분 변동 규모가 클수록 영향 커짐",
             "주의사항: 소규모 변동은 세금·재무 목적일 수 있어 맹신 금지"],
            "기타공시"
        )
    # 실적 보고
    if any(k in title for k in ["사업보고서", "반기보고서", "분기보고서"]):
        return (
            f"'{title}' 공시예요. 회사의 공식 실적·재무 현황을 담은 정기 보고서입니다. "
            "매출·영업이익 증감과 가이던스(향후 전망)가 주가에 직접 영향을 줍니다.",
            ["공시 당일: 어닝 서프라이즈/쇼크 여부 확인 필수", "단기(1~2주): 애널리스트 목표가 변화 체크",
             "중기(1개월): 실적 추세 방향이 주가 흐름 결정", "주의사항: 영업이익보다 순이익 왜곡 여부 확인"],
            "정기공시"
        )
    # 주요 경영사항
    if any(k in title for k in ["주요사항", "공급계약", "수주", "MOU", "협약", "투자"]):
        return (
            f"'{title}' 공시예요. 주가에 영향을 줄 수 있는 주요 경영 이슈를 공시한 것으로, "
            "계약 규모와 상대방이 핵심 확인 포인트입니다.",
            ["공시 당일: 계약 규모가 매출 대비 10% 이상이면 중요 호재", "단기(1~2주): 계약 이행 가능성 모니터링",
             "중기(1개월): 실제 매출 반영 시점 확인", "주의사항: 조건부 계약은 불확실성 존재"],
            "주요공시"
        )
    # 유상증자/CB
    if any(k in title for k in ["유상증자", "전환사채", "신주", "CB", "BW"]):
        return (
            f"'{title}' 공시예요. 주식 발행을 통한 자금 조달로, 기존 주주의 지분이 희석될 수 있습니다. "
            "조달 목적(성장투자 vs 부채상환)이 핵심 판단 기준입니다.",
            ["공시 당일: 희석률과 조달 목적 즉시 확인", "단기(1~2주): 주가 하락 압력 가능성 높음",
             "중기(1개월): 자금 사용 목적이 성장이라면 회복 가능", "주의사항: 부채상환 목적이면 재무 악화 신호"],
            "주의공시"
        )
    # 배당
    if any(k in title for k in ["배당", "결산"]):
        return (
            f"'{title}' 공시예요. 주주에게 이익을 배분하는 배당 관련 공시로, "
            "배당 수익률과 지급 일정이 주가에 영향을 줍니다.",
            ["공시 당일: 배당금액과 전년 대비 증감 확인", "단기: 배당락일 전후 매수·매도 전략 검토",
             "주의사항: 배당락일 이후 주가 하락은 일반적인 현상"],
            "배당공시"
        )
    # 기본 fallback
    return (
        f"'{title}' 공시예요. DART(dart.fss.or.kr)에서 원문을 직접 확인하면 더 자세한 내용을 볼 수 있어요.",
        ["공시 당일: 시장 반응 확인 필요", "단기(1~2주): 공시 내용의 실현 가능성 모니터링",
         "중기(1개월): 실제 영향 반영 여부 확인", "주의사항: 공시 하나만으로 매매 결정하지 마세요"],
        "기타공시"
    )

# ─────────────────────────────────────────────────────────
# JWT 설정
# ─────────────────────────────────────────────────────────
_JWT_SECRET = os.environ.get("JWT_SECRET")
if not _JWT_SECRET:
    raise RuntimeError("JWT_SECRET 환경변수가 설정되지 않았습니다. Render 환경변수를 확인하세요.")
_JWT_ALGO = "HS256"
_JWT_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def _make_token(user_id: int, username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "name": username, "exp": exp}, _JWT_SECRET, algorithm=_JWT_ALGO)

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except JWTError:
        return {}

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="인증이 만료되었습니다")
    return {"user_id": int(payload["sub"]), "username": payload["name"]}

# ─────────────────────────────────────────────────────────
# FastAPI 앱
# ─────────────────────────────────────────────────────────
app = FastAPI(title="포켓주식 API")

@app.on_event("startup")
def _migrate():
    """watchlist.group_name 컬럼 없으면 추가"""
    try:
        from database import _db as _get_db
        _get_db().rpc("exec_sql", {"sql": "ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS group_name TEXT DEFAULT '기본'"}).execute()
    except Exception:
        pass  # rpc 없으면 Supabase SQL 에디터에서 직접 실행 필요

_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS or ["*"],  # 환경변수 설정 시 제한, 없으면 개발용 전체 허용
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ─────────────────────────────────────────────────────────
# Pydantic 모델
# ─────────────────────────────────────────────────────────
class LoginBody(BaseModel):
    username: str
    password: str

class RegisterBody(BaseModel):
    username: str
    password: str

class HoldingBody(BaseModel):
    code: str
    name: str
    avg_price: float
    qty: int

class WatchlistBody(BaseModel):
    code: str
    name: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    group_name: Optional[str] = "기본"

class WatchlistGroupBody(BaseModel):
    group_name: str

class StockSearchBody(BaseModel):
    query: str

# ─────────────────────────────────────────────────────────
# 로그인 브루트포스 방어 (IP당 5회 실패 → 60초 잠금)
# ─────────────────────────────────────────────────────────
import time as _time
_login_fail: dict = {}  # {ip: {"count": n, "until": timestamp}}
_MAX_FAIL = 5
_LOCKOUT_SEC = 60

def _check_brute(ip: str):
    now = _time.time()
    rec = _login_fail.get(ip)
    if rec and rec["until"] > now:
        remaining = int(rec["until"] - now)
        raise HTTPException(status_code=429, detail=f"로그인 시도 초과. {remaining}초 후 다시 시도하세요.")

def _record_fail(ip: str):
    now = _time.time()
    rec = _login_fail.get(ip, {"count": 0, "until": 0})
    rec["count"] += 1
    if rec["count"] >= _MAX_FAIL:
        rec["until"] = now + _LOCKOUT_SEC
        rec["count"] = 0
    _login_fail[ip] = rec

def _clear_fail(ip: str):
    _login_fail.pop(ip, None)

# ─────────────────────────────────────────────────────────
# 인증 API
# ─────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(body: LoginBody, request: Request):
    ip = request.client.host
    _check_brute(ip)
    ok, user_id = db.verify_user(body.username, body.password)
    if not ok:
        _record_fail(ip)
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다")
    _clear_fail(ip)
    token = _make_token(user_id, body.username)
    return {"token": token, "username": body.username, "user_id": user_id}

@app.post("/api/auth/register")
def register(body: RegisterBody):
    ok, msg = db.create_user(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    ok2, user_id = db.verify_user(body.username, body.password)
    token = _make_token(user_id, body.username)
    return {"token": token, "username": body.username, "user_id": user_id, "message": msg}

@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return user

# ─────────────────────────────────────────────────────────
# 홈 API
# ─────────────────────────────────────────────────────────
@app.get("/api/home")
def home_data():
    try:
        idx = get_index_data()
        us_raw = get_us_indices()
        kp = idx.get("KOSPI", {})
        kd = idx.get("KOSDAQ", {})
        sp = us_raw.get("S&P500", {})
        nd = us_raw.get("나스닥", {})
        indices = {
            "kospi": kp.get("current", 0),
            "kospi_change_pct": kp.get("change_pct", 0),
            "kosdaq": kd.get("current", 0),
            "kosdaq_change_pct": kd.get("change_pct", 0),
            "sp500": sp.get("current", 0),
            "sp500_change_pct": sp.get("change_pct", 0),
            "nasdaq": nd.get("current", 0),
            "nasdaq_change_pct": nd.get("change_pct", 0),
        }
        # KOSPI 이동평균선 계산 (분석 품질 향상용)
        try:
            kp_hist = get_index_ohlcv_history("1001", days=120)
            ma = calc_ma_status(kp_hist)
        except Exception:
            kp_hist = None
            ma = {}

        # 외국인/기관 수급 최근 5일
        investor = []
        try:
            inv_df = get_kospi_investor(days=30)
            if inv_df is not None and not inv_df.empty:
                unit = inv_df["_unit"].iloc[0] if "_unit" in inv_df.columns else "qty"
                for dt, row in inv_df.tail(5).iterrows():
                    f_raw = float(row.get("외국인", 0))
                    i_raw = float(row.get("기관", 0))
                    if unit == "won":
                        # 원 단위 → 억원
                        f_val = round(f_raw / 1e8, 0)
                        i_val = round(i_raw / 1e8, 0)
                        disp_unit = "억"
                    elif unit == "百만" or (abs(f_raw) > 0 and abs(f_raw) < 1e6):
                        # 백만원 → 억원
                        f_val = round(f_raw / 100, 0)
                        i_val = round(i_raw / 100, 0)
                        disp_unit = "억"
                    else:
                        # 주(qty) → 만주
                        f_val = round(f_raw / 10000, 1)
                        i_val = round(i_raw / 10000, 1)
                        disp_unit = "만주"
                    investor.append({
                        "date": str(dt)[:10],
                        "foreign": f_val,
                        "inst":    i_val,
                        "unit":    disp_unit,
                    })
        except Exception:
            pass

        # MA 포함해서 analyze_us_impact 호출 → Gemini 상세 분석 가능
        analysis_raw = analyze_us_impact(us_raw, idx, ma, kp_hist)
        analysis = []
        for item in (analysis_raw or []):
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                analysis.append({"dot": item[0], "label": item[1], "text": item[2], "checkpoints": item[3] if len(item) > 3 else []})
            elif isinstance(item, dict):
                analysis.append(item)
        forecast = generate_forecast(us_raw, idx, ma)
        return {
            "indices": indices,
            "analysis": analysis,
            "forecast": forecast,
            "investor": investor,
            "market_phase": market_phase(),
            "is_open": is_market_open(),
        }
    except Exception as e:
        return {"error": str(e), "indices": {}, "analysis": [], "forecast": {}, "investor": [], "market_phase": "close", "is_open": False}

# ─────────────────────────────────────────────────────────
# 예측 상세 API (예측 히스토리 포함)
# ─────────────────────────────────────────────────────────
@app.get("/api/forecast/detail")
def forecast_detail():
    from datetime import date, timedelta
    try:
        idx = get_index_data()
        us_raw = get_us_indices()
        try:
            kp_hist = get_index_ohlcv_history("1001", days=120)
            ma = calc_ma_status(kp_hist)
        except Exception:
            kp_hist = None
            ma = {}
        forecast = generate_forecast(us_raw, idx, ma)

        # 주말(토=5, 일=6) 제외하고 예측 저장
        today = date.today()
        if today.weekday() < 5:
            try:
                today_str = today.isoformat()
                save_prediction(
                    date=today_str,
                    index_name="KOSPI",
                    predicted_direction=forecast.get("direction", "sideways"),
                    predicted_change=forecast.get("predicted_pct", 0.0),
                    confidence=forecast.get("confidence", 50),
                    prediction_basis=forecast.get("basis", {}),
                    gemini_text=forecast.get("full_gemini_text", ""),
                )
                # 전 거래일 예측 결과 업데이트 (직전 평일)
                prev = today - timedelta(days=1)
                while prev.weekday() >= 5:
                    prev -= timedelta(days=1)
                prev_str = prev.isoformat()
                preds_check = get_recent_predictions(limit=5)
                for p in preds_check:
                    if p["date"] == prev_str and p.get("actual_direction") is None:
                        kp_now = idx.get("KOSPI", {})
                        actual_pct = kp_now.get("change_pct", 0.0)
                        actual_dir = "up" if actual_pct > 0.3 else ("down" if actual_pct < -0.3 else "sideways")
                        update_prediction_result(prev_str, "KOSPI", actual_dir, actual_pct)
                        break
            except Exception:
                pass

        preds = get_recent_predictions(limit=7)
        stats = get_prediction_accuracy()
        return {
            "forecast": forecast,
            "history": preds,
            "stats": stats,
        }
    except Exception as e:
        return {"error": str(e), "forecast": {}, "history": [], "stats": {}}

# ─────────────────────────────────────────────────────────
# 지수 상세 API (KOSPI / KOSDAQ)
# ─────────────────────────────────────────────────────────
@app.get("/api/index/{name}")
def index_detail(name: str):
    """name: KOSPI 또는 KOSDAQ"""
    try:
        idx = get_index_data()
        us_raw = get_us_indices()
        info = idx.get(name.upper(), {})

        # 이동평균선 (KOSPI=1001, KOSDAQ=2001)
        index_code = "1001" if name.upper() == "KOSPI" else "2001"
        hist_df = get_index_ohlcv_history(index_code, days=120)
        ma = calc_ma_status(hist_df)

        # extra_metrics (RSI, 이격도, 5일 수익률, 거래량비)
        ex = _extra_metrics(hist_df, ma)

        # 외국인/기관 수급 (KOSPI만)
        investor_data = []
        if name.upper() == "KOSPI":
            try:
                inv_df = get_kospi_investor(days=10)
                if inv_df is not None and not inv_df.empty:
                    unit = inv_df["_unit"].iloc[0] if "_unit" in inv_df.columns else "qty"
                    for dt, row in inv_df.tail(5).iterrows():
                        f_raw = float(row.get("외국인", 0))
                        i_raw = float(row.get("기관", 0))
                        if unit == "won":
                            f_val, i_val, disp_unit = round(f_raw/1e8,0), round(i_raw/1e8,0), "억"
                        elif abs(f_raw) > 0 and abs(f_raw) < 1e6:
                            f_val, i_val, disp_unit = round(f_raw/100,0), round(i_raw/100,0), "억"
                        else:
                            f_val, i_val, disp_unit = round(f_raw/10000,1), round(i_raw/10000,1), "만주"
                        investor_data.append({"date": str(dt)[:10], "foreign": f_val, "inst": i_val, "unit": disp_unit})
            except Exception:
                pass

        # 섹터 퍼포먼스
        try:
            sectors = get_sector_performance()
        except Exception:
            sectors = []

        # AI 분석 (generate_forecast 재활용)
        try:
            analysis = analyze_us_impact(us_raw, idx, ma)
            analysis_out = []
            for item in (analysis or []):
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    analysis_out.append({"dot": item[0], "label": item[1], "text": item[2], "checkpoints": item[3] if len(item) > 3 else []})
                elif isinstance(item, dict):
                    analysis_out.append(item)
        except Exception:
            analysis_out = []

        return {
            "name": name.upper(),
            "info": info,
            "ma": ma,
            "ex": ex,
            "investor": investor_data,
            "sectors": sectors,
            "analysis": analysis_out,
        }
    except Exception as e:
        return {"error": str(e), "name": name, "info": {}, "ma": {}, "investor": [], "sectors": [], "analysis": []}

# ─────────────────────────────────────────────────────────
# 외국인·기관 수급 25일 상세 API
# ─────────────────────────────────────────────────────────
@app.get("/api/supply")
def supply_detail():
    """KOSPI 외국인·기관 수급 25일 상세 (홈화면 클릭 시 진입)"""
    try:
        inv_df = get_kospi_investor(days=35)
        rows = []
        disp_unit = "억"
        if inv_df is not None and not inv_df.empty:
            unit = inv_df["_unit"].iloc[0] if "_unit" in inv_df.columns else "qty"
            for dt, row in inv_df.tail(25).iterrows():
                f_raw = float(row.get("외국인", 0))
                i_raw = float(row.get("기관", 0))
                if unit == "won":
                    f_val, i_val, disp_unit = round(f_raw/1e8, 0), round(i_raw/1e8, 0), "억"
                elif abs(f_raw) > 0 and abs(f_raw) < 1e6:
                    f_val, i_val, disp_unit = round(f_raw/100, 0), round(i_raw/100, 0), "억"
                else:
                    f_val, i_val, disp_unit = round(f_raw/10000, 1), round(i_raw/10000, 1), "만주"
                rows.append({
                    "date": str(dt)[:10],
                    "foreign": f_val,
                    "inst":    i_val,
                })

        # 집계 계산
        total_f = sum(r["foreign"] for r in rows)
        total_i = sum(r["inst"] for r in rows)
        buy_days_f = sum(1 for r in rows if r["foreign"] > 0)
        buy_days_i = sum(1 for r in rows if r["inst"] > 0)
        both_buy  = sum(1 for r in rows if r["foreign"] > 0 and r["inst"] > 0)
        both_sell = sum(1 for r in rows if r["foreign"] < 0 and r["inst"] < 0)

        # 연속 순매수/매도일 (최근부터 역산)
        streak_f, streak_i = 0, 0
        for r in reversed(rows):
            if r["foreign"] > 0 and streak_f >= 0: streak_f += 1
            elif r["foreign"] < 0 and streak_f <= 0: streak_f -= 1
            else: break
        for r in reversed(rows):
            if r["inst"] > 0 and streak_i >= 0: streak_i += 1
            elif r["inst"] < 0 and streak_i <= 0: streak_i -= 1
            else: break

        # 시스템 판단 문구
        f_trend = "순매수" if total_f > 0 else "순매도"
        i_trend = "순매수" if total_i > 0 else "순매도"
        streak_txt = ""
        if streak_f > 2:
            streak_txt = f"외국인 {streak_f}일 연속 순매수로 매집 흐름이 이어지고 있어요. "
        elif streak_f < -2:
            streak_txt = f"외국인 {abs(streak_f)}일 연속 순매도로 이탈 흐름이 감지돼요. "
        unit_label = disp_unit
        advice = f"{streak_txt}25일 누적 외국인 {total_f:+.1f}{unit_label}, 기관 {total_i:+.1f}{unit_label}. " + (
            "외국인·기관 동반 매수 흐름으로 수급 기반이 탄탄해요." if both_buy > 10 else
            "외국인·기관 엇갈린 흐름이 이어지고 있어요. 방향 확인이 필요해요." if both_sell < 3 else
            "외국인·기관이 함께 매도하는 날이 많아요. 조심이 필요한 시점이에요."
        )

        return {
            "rows": rows,
            "unit": disp_unit,
            "total_foreign": round(total_f, 1),
            "total_inst": round(total_i, 1),
            "buy_days_foreign": buy_days_f,
            "buy_days_inst": buy_days_i,
            "both_buy": both_buy,
            "both_sell": both_sell,
            "streak_foreign": streak_f,
            "streak_inst": streak_i,
            "advice": advice,
            "days": len(rows),
        }
    except Exception as e:
        return {"error": str(e), "rows": []}

# ─────────────────────────────────────────────────────────
# 시장 지수 API
# ─────────────────────────────────────────────────────────
@app.get("/api/market")
def market_data():
    try:
        idx = get_index_data()
        us = get_us_indices()
        return {"kr": idx, "us": us}
    except Exception as e:
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────
# 시황 API — 투자심리지수(8요소) + 시장 오버뷰
# ─────────────────────────────────────────────────────────
def _calc_sentiment_index() -> dict:
    """
    한국 시장 투자심리지수 (CNN Fear & Greed 방식)
    각 지표를 0~100으로 정규화 → 가중평균 → 최종 점수
    """
    import numpy as np
    from market_data import PYKRX_OK, _last_trading_date, _parse_naver_num

    def clamp(v, lo=0, hi=100): return max(lo, min(hi, v))
    def norm(v, v_min, v_max):  # v → 0~100 선형 정규화
        if v_max == v_min: return 50
        return clamp((v - v_min) / (v_max - v_min) * 100)

    factor_details = []
    sub_scores = []   # (weight, sub_score)

    # ── 공통 데이터 미리 로드 ──────────────────────────
    ohlcv_kospi = None
    inv_data    = None
    df_today    = None  # 당일 전 종목 OHLCV (pykrx)

    try: ohlcv_kospi = get_index_ohlcv_history("KOSPI", days=125)  # 6개월
    except: pass
    try: inv_data = get_kospi_investor(days=15)
    except: pass
    try:
        if PYKRX_OK:
            import pykrx.stock as _krx
            tdate = _last_trading_date()
            df_today = _krx.get_market_ohlcv_by_ticker(tdate, market="KOSPI")
    except: pass

    # ── 1. VKOSPI 공포지수 (가중 20%) ─────────────────
    # VKOSPI: 낮을수록 안정(탐욕), 높을수록 공포. 기준 10~40
    try:
        url = "https://m.stock.naver.com/api/stock/VKOSPI/basic"
        r = _requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            d = r.json()
            vk = float(_parse_naver_num(d.get("closePrice", 0)))
            if vk > 0:
                sub = norm(vk, 10, 40)          # 10→100점(공포낮음), 40→0점(공포높음)
                sub = 100 - sub                  # 반전: 높은 VKOSPI = 낮은 심리점수
                chg_vk = float(_parse_naver_num(d.get("compareToPreviousClosePrice", 0)))
                direction = "down" if chg_vk > 0 else "up" if chg_vk < 0 else "neutral"
                factor_details.append({"name": "VKOSPI (공포지수)", "value": f"{vk:.2f}",
                    "sub_score": round(sub), "direction": direction,
                    "desc": "낮을수록 시장 안정"})
                sub_scores.append((0.20, sub))
    except: pass

    # ── 2. KOSPI 등락률 (가중 15%) ─────────────────────
    # -3% 이하 → 0점, +3% 이상 → 100점
    try:
        idx = get_index_data()
        kospi = next((x for x in (idx or []) if x.get("name") == "KOSPI"), None)
        if kospi:
            chg = float(kospi.get("change_pct", 0) or 0)
            sub = norm(chg, -3.0, 3.0)
            factor_details.append({"name": "KOSPI 등락률", "value": f"{chg:+.2f}%",
                "sub_score": round(sub), "direction": "up" if chg > 0 else "down" if chg < 0 else "neutral",
                "desc": "당일 KOSPI 등락"})
            sub_scores.append((0.15, sub))
    except: pass

    # ── 3. 외국인 3일 순매수 (가중 15%) ─────────────────
    # -1조 이하 → 0점, +1조 이상 → 100점 (규모 반영)
    try:
        if inv_data is not None and not inv_data.empty and "외국인" in inv_data.columns:
            f_net = float(inv_data["외국인"].tail(3).sum())
            sub = norm(f_net, -1e12, 1e12)
            val = f"{f_net/1e8:+.0f}억" if abs(f_net) >= 1e8 else f"{f_net/1e4:+.0f}만"
            factor_details.append({"name": "외국인 3일 순매수", "value": val,
                "sub_score": round(sub), "direction": "up" if f_net > 0 else "down",
                "desc": "외국인 3일 누적 순매수 금액"})
            sub_scores.append((0.15, sub))
    except: pass

    # ── 4. 기관 3일 순매수 (가중 12%) ──────────────────
    # -5000억~+5000억 정규화
    try:
        if inv_data is not None and not inv_data.empty:
            col = "기관합계" if "기관합계" in inv_data.columns else "기관" if "기관" in inv_data.columns else None
            if col:
                i_net = float(inv_data[col].tail(3).sum())
                sub = norm(i_net, -5e11, 5e11)
                val = f"{i_net/1e8:+.0f}억" if abs(i_net) >= 1e8 else f"{i_net/1e4:+.0f}만"
                factor_details.append({"name": "기관 3일 순매수", "value": val,
                    "sub_score": round(sub), "direction": "up" if i_net > 0 else "down",
                    "desc": "기관 3일 누적 순매수 금액"})
                sub_scores.append((0.12, sub))
    except: pass

    # ── 5. 등락비율 ADR (가중 13%) ──────────────────────
    # 상승종목 수 / 전체. 30%→0점, 70%→100점
    try:
        if df_today is not None and not df_today.empty:
            chg_col = next((c for c in df_today.columns if "등락률" in str(c)), None)
            if chg_col:
                up_cnt = int((df_today[chg_col] > 0).sum())
                dn_cnt = int((df_today[chg_col] < 0).sum())
                total  = up_cnt + dn_cnt
                if total > 0:
                    adr = up_cnt / total * 100
                    sub = norm(adr, 30, 70)
                    factor_details.append({"name": "등락비율 ADR", "value": f"상승 {up_cnt} / 하락 {dn_cnt}",
                        "sub_score": round(sub), "direction": "up" if adr > 50 else "down",
                        "desc": "KOSPI 상승 종목 비율"})
                    sub_scores.append((0.13, sub))
    except: pass

    # ── 6. KOSPI 60일 고점 대비 위치 (가중 10%) ────────
    # KOSPI 현재가가 60일 범위 어디에 있는지 (신고가에 가까울수록 탐욕)
    try:
        if ohlcv_kospi is not None and not ohlcv_kospi.empty and len(ohlcv_kospi) >= 60:
            closes = ohlcv_kospi["close"].values if "close" in ohlcv_kospi.columns else ohlcv_kospi.iloc[:,3].values
            hi60 = float(closes[-60:].max())
            lo60 = float(closes[-60:].min())
            cur  = float(closes[-1])
            sub  = norm(cur, lo60, hi60)
            pct  = (cur - lo60) / (hi60 - lo60) * 100 if hi60 > lo60 else 50
            factor_details.append({"name": "60일 고점 대비 위치", "value": f"{pct:.0f}%",
                "sub_score": round(sub), "direction": "up" if sub > 50 else "down",
                "desc": "60일 범위 내 현재 위치 (높을수록 고점 근접)"})
            sub_scores.append((0.10, sub))
    except: pass

    # ── 7. 거래대금 vs 20일 평균 (가중 8%) ──────────────
    # 거래대금 폭증 = 관심 상승 = 약한 탐욕 신호
    # 0.5배 미만 → 0점, 2배 초과 → 100점
    try:
        if ohlcv_kospi is not None and not ohlcv_kospi.empty and len(ohlcv_kospi) >= 21:
            for vc in ohlcv_kospi.columns:
                if "거래" in str(vc) or "vol" in str(vc).lower():
                    vols = ohlcv_kospi[vc].values
                    avg20 = float(np.mean(vols[-21:-1]))
                    today_v = float(vols[-1])
                    if avg20 > 0:
                        ratio = today_v / avg20
                        sub = norm(ratio, 0.5, 2.0)
                        factor_details.append({"name": "거래대금 vs 20일평균", "value": f"{ratio:.2f}배",
                            "sub_score": round(sub), "direction": "up" if ratio > 1 else "down",
                            "desc": "거래대금 활성도 (1배=평균 수준)"})
                        sub_scores.append((0.08, sub))
                    break
    except: pass

    # ── 8. 시장 변동성 — KOSPI 10일 표준편차 (가중 7%) ──
    # 변동성 낮을수록 안정(탐욕). 0.3%→100점, 2.5%→0점
    try:
        if ohlcv_kospi is not None and not ohlcv_kospi.empty and len(ohlcv_kospi) >= 11:
            closes = ohlcv_kospi["close"].values if "close" in ohlcv_kospi.columns else ohlcv_kospi.iloc[:,3].values
            returns = np.diff(closes[-11:]) / closes[-11:-1] * 100
            vol = float(np.std(returns))
            sub = 100 - norm(vol, 0.3, 2.5)   # 반전: 높은 변동성 = 낮은 점수
            factor_details.append({"name": "시장 변동성 (10일)", "value": f"{vol:.2f}%",
                "sub_score": round(sub), "direction": "up" if vol < 1.0 else "down",
                "desc": "낮을수록 시장 안정 (탐욕)"})
            sub_scores.append((0.07, sub))
    except: pass

    # ── 가중평균 계산 ──────────────────────────────────
    if sub_scores:
        total_w = sum(w for w, _ in sub_scores)
        score = sum(w * s for w, s in sub_scores) / total_w
    else:
        score = 50.0
    score = int(clamp(round(score)))

    if score >= 75:   label, color = "극단적 탐욕", "#E24B4A"
    elif score >= 60: label, color = "탐욕",       "#F5A623"
    elif score >= 40: label, color = "중립",       "#8E8E9A"
    elif score >= 25: label, color = "공포",       "#5B5BD6"
    else:             label, color = "극단적 공포","#27500A"

    factors_summary = [f["name"] + " " + f["value"] for f in factor_details[:4]]
    return {
        "score": score, "label": label, "color": color,
        "factors": factors_summary,
        "factor_details": factor_details,
    }


def _get_exchange_rates() -> list:
    """환율 정보 — yfinance 기반 (달러/원, 100엔/원, 위안/원)"""
    import yfinance as yf
    pairs = [
        {"symbol": "KRW=X",    "name": "달러/원",  "mult": 1},
        {"symbol": "JPYKRW=X", "name": "100엔/원", "mult": 100},  # yfinance는 1엔 기준 → ×100
        {"symbol": "CNYKRW=X", "name": "위안/원",  "mult": 1},
    ]
    result = []
    for p in pairs:
        try:
            df = yf.Ticker(p["symbol"]).history(period="5d", auto_adjust=False)
            if df is None or len(df) < 2:
                continue
            price_raw = float(df["Close"].iloc[-1])
            prev_raw  = float(df["Close"].iloc[-2])
            price = round(price_raw * p["mult"], 2)
            prev  = prev_raw * p["mult"]
            chg   = round(price - prev, 2)
            chg_pct = round(chg / prev * 100, 2)
            result.append({"name": p["name"], "price": price, "change": chg, "change_pct": chg_pct})
        except: pass
    return result


def _get_us_futures() -> list:
    """미국 선물 (S&P500, 나스닥, 다우)"""
    futures = [
        {"symbol": "ES=F", "name": "S&P500 선물"},
        {"symbol": "NQ=F", "name": "나스닥 선물"},
        {"symbol": "YM=F", "name": "다우 선물"},
    ]
    result = []
    for f in futures:
        try:
            import yfinance as yf
            t = yf.Ticker(f["symbol"])
            info = t.fast_info
            price = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
            prev  = getattr(info, "previous_close", None)
            if price and prev and prev > 0:
                chg = price - prev
                chg_pct = chg / prev * 100
                result.append({"name": f["name"], "symbol": f["symbol"],
                               "price": round(price, 2), "change": round(chg, 2),
                               "change_pct": round(chg_pct, 2)})
        except: pass
    return result


def _get_top_net_buy(n: int = 5) -> dict:
    """외국인·기관 당일 순매수 TOP N"""
    from market_data import PYKRX_OK, _last_trading_date, get_stock_name
    if not PYKRX_OK:
        return {"foreign": [], "institution": []}
    try:
        import pykrx.stock as krx_s
        tdate = _last_trading_date()
        df = krx_s.get_market_trading_value_by_ticker(tdate, tdate, "KOSPI")
        if df is None or df.empty:
            return {"foreign": [], "institution": []}
        foreign_col = next((c for c in df.columns if "외국인" in str(c)), None)
        inst_col    = next((c for c in df.columns if "기관합계" in str(c) or ("기관" in str(c) and "합계" in str(c))), None)
        if not inst_col:
            inst_col = next((c for c in df.columns if "기관" in str(c)), None)

        def top_n(col):
            if not col or col not in df.columns: return []
            s = df[col].dropna()
            top = s.nlargest(n)
            out = []
            for code, val in top.items():
                name = get_stock_name(str(code)) or str(code)
                out.append({"code": str(code), "name": name,
                            "value": int(val), "value_str": f"{int(val)/1e8:.0f}억"})
            return out

        return {"foreign": top_n(foreign_col), "institution": top_n(inst_col)}
    except Exception as e:
        print(f"[시황] 순매수 TOP 실패: {e}")
        return {"foreign": [], "institution": []}


def _get_top_volume(n: int = 5) -> list:
    """거래대금 상위 종목"""
    from market_data import PYKRX_OK, _last_trading_date, get_stock_name
    if not PYKRX_OK:
        return []
    try:
        import pykrx.stock as krx_s
        tdate = _last_trading_date()
        df = krx_s.get_market_ohlcv_by_ticker(tdate, market="KOSPI")
        if df is None or df.empty:
            return []
        val_col = next((c for c in df.columns if "거래대금" in str(c)), None)
        chg_col = next((c for c in df.columns if "등락률" in str(c)), None)
        close_col = next((c for c in df.columns if "종가" in str(c)), None)
        if not val_col: return []
        top = df[val_col].nlargest(n)
        result = []
        for code, val in top.items():
            name = get_stock_name(str(code)) or str(code)
            chg  = float(df.loc[code, chg_col]) if chg_col and code in df.index else 0
            price = int(df.loc[code, close_col]) if close_col and code in df.index else 0
            result.append({"code": str(code), "name": name, "price": price,
                           "change_pct": round(chg, 2), "value": int(val),
                           "value_str": f"{int(val)/1e8:.0f}억"})
        return result
    except Exception as e:
        print(f"[시황] 거래대금 TOP 실패: {e}")
        return []


_sentiment_cache: dict = {"data": None, "ts": 0}
_SENTIMENT_TTL = 300  # 5분 캐시

@app.get("/api/sentiment")
def get_sentiment(force: bool = False):
    import concurrent.futures, time
    now = time.time()
    if not force and _sentiment_cache["data"] and (now - _sentiment_cache["ts"]) < _SENTIMENT_TTL:
        print("[시황] 캐시 반환")
        return _sentiment_cache["data"]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
            f_sent   = pool.submit(_calc_sentiment_index)
            f_fx     = pool.submit(_get_exchange_rates)
            f_fut    = pool.submit(_get_us_futures)
            f_us     = pool.submit(get_us_indices)
            f_sector = pool.submit(get_sector_performance)
            f_netbuy = pool.submit(_get_top_net_buy, 5)
            f_vol    = pool.submit(_get_top_volume, 5)
            sentiment  = f_sent.result(timeout=30)
            fx         = f_fx.result(timeout=15)
            futures    = f_fut.result(timeout=15)
            us_indices = f_us.result(timeout=15)
            sectors    = f_sector.result(timeout=25)
            net_buy    = f_netbuy.result(timeout=25)
            top_volume = f_vol.result(timeout=25)

        # 주말/장외 여부
        from home_analysis import is_market_open
        from market_data import _last_trading_date
        import datetime as _dt
        now_kst = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
        is_weekend = now_kst.weekday() >= 5
        is_after_hours = not is_market_open()
        base_date = _last_trading_date()
        base_date_str = f"{base_date[:4]}.{base_date[4:6]}.{base_date[6:]} 기준"
        market_note = "주말 — 최근 거래일" if is_weekend else ("장 마감 후" if is_after_hours else "실시간")

        result = _to_python({
            "sentiment":    sentiment,
            "fx":           fx,
            "us_futures":   futures,
            "us_indices":   us_indices,
            "sectors":      sectors,
            "net_buy":      net_buy,
            "top_volume":   top_volume,
            "updated_at":   now_kst.strftime("%m/%d %H:%M"),
            "base_date":    base_date_str,
            "market_note":  market_note,
        })
        _sentiment_cache["data"] = result
        _sentiment_cache["ts"]   = now
        return result
    except Exception as e:
        print(f"[시황] API 오류: {e}")
        return {"sentiment": {"score": 50, "label": "중립", "color": "#8E8E9A", "factors": [], "factor_details": []},
                "fx": [], "us_futures": [], "sectors": [], "net_buy": {"foreign":[],"institution":[]}, "top_volume": [],
                "updated_at": "", "base_date": "", "market_note": ""}

# ─────────────────────────────────────────────────────────
# 뉴스 API
# ─────────────────────────────────────────────────────────
@app.get("/api/news")
def market_news():
    try:
        raw = fetch_market_news(max_items=8)
        ranked = rank_by_importance(raw)[:5]
        # Gemini 제거 — 감성분류(빠름)만 수행
        result = []
        for item in ranked:
            title   = item.get("title", "")
            summary = item.get("summary", "")
            sentiment_info = classify_sentiment(title + " " + summary)
            category = item.get("category") or classify_category(title, summary)
            result.append({
                **item,
                "category":        category,
                "sentiment":       sentiment_info["sentiment"],
                "sentiment_label": sentiment_info["label"],
                "label":           sentiment_info["label"],
                "badge_type":      sentiment_info["badge_type"],
            })
        return {"news": result}
    except Exception as e:
        return {"news": [], "error": str(e)}

class NewsAnalyzeBody(BaseModel):
    title: str = ""
    summary: str = ""
    sentiment: str = "neutral"
    category: str = "전체"

@app.get("/api/news/fetch-body")
def fetch_news_body(url: str):
    """뉴스 기사 URL에서 본문 추출"""
    try:
        import requests as req
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
        resp = req.get(url, headers=headers, timeout=8, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "figure"]):
            tag.decompose()

        # 네이버 뉴스 본문 선택자 우선 시도
        body = ""
        for selector in [
            "#dic_area",           # 네이버 뉴스
            "#articleBodyContents", # 네이버 구버전
            ".article-body",
            ".news-article-body",
            "article",
            ".article_view",
            "#article-view-content-div",
            ".article_txt",
        ]:
            el = soup.select_one(selector)
            if el:
                body = el.get_text(separator="\n", strip=True)
                break

        # 셀렉터 실패 시 <p> 태그 모음
        if not body:
            paragraphs = soup.find_all("p")
            body = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)

        # 빈 줄 정리
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        body = "\n".join(lines[:80])  # 최대 80줄

        return {"body": body}
    except Exception as e:
        return {"body": "", "error": str(e)}

@app.post("/api/news/analyze")
def analyze_news_article(body: NewsAnalyzeBody):
    """단일 뉴스 기사에 대한 AI 분석 온디맨드 생성"""
    try:
        title = body.title
        summary = body.summary
        # sentiment/category 재분류 (더 정확하게)
        sentiment_info = classify_sentiment(title + " " + summary)
        sentiment = body.sentiment or sentiment_info.get("sentiment", "neutral")
        category = body.category or classify_category(title, summary)
        ai_summary = generate_ai_summary(title, summary, sentiment, category)
        strategy, _ = generate_strategy(sentiment, category, title, summary)
        related = extract_related_stocks(title, summary, category)
        return {
            "ai_summary": ai_summary,
            "strategy": strategy,
            "related_stocks": related,
            "sentiment": sentiment,
            "category": category,
        }
    except Exception as e:
        return {"error": str(e), "ai_summary": None, "strategy": None}

@app.get("/api/news/{code}")
def stock_news(code: str):
    try:
        tickers = get_all_tickers()
        name = tickers.get(code, code)
        return {"news": fetch_stock_news(name), "name": name}
    except Exception as e:
        return {"news": [], "error": str(e)}

# ─────────────────────────────────────────────────────────
# 보유종목 API
# ─────────────────────────────────────────────────────────
@app.get("/api/holdings")
def get_holdings_list(user=Depends(get_current_user)):
    holdings = db.get_holdings(user["user_id"])
    if not holdings:
        return {"holdings": [], "total_value": 0, "total_pnl": 0, "total_pnl_pct": 0}
    result = []
    total_value = 0
    total_cost = 0
    for h in holdings:
        code = h["code"]
        try:
            pd2 = get_current_price(code)
            cur_price = pd2.get("current_price", h["avg_price"]) or h["avg_price"]
            change_pct = pd2.get("change_pct", 0)
        except Exception:
            cur_price = h["avg_price"]
            change_pct = 0
        value = cur_price * h["qty"]
        cost = h["avg_price"] * h["qty"]
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0
        total_value += value
        total_cost += cost
        # 미니 분석 (카드에 RSI/이격도/지지선 표시용)
        try:
            ohlcv = get_ohlcv(code, days=60)
            inv   = get_investor_trading(code, days=5)
            a     = analyze_stock(ohlcv, inv, h["avg_price"], h["qty"])
            rsi       = round(a.get("rsi", 50), 1)
            gap20     = round(a.get("gap20", 100), 1)
            ma20      = a.get("ma20")
            ma60      = a.get("ma60")
            boll      = a.get("bollinger", {})
            badges    = a.get("badges", [])
        except Exception:
            rsi = 50; gap20 = 100; ma20 = None; ma60 = None; boll = {}; badges = []
        result.append({
            **h,
            "cur_price": cur_price,
            "change_pct": round(change_pct, 2),
            "value": value,
            "pnl": pnl,
            "pnl_pct": round(pnl_pct, 2),
            "rsi": rsi,
            "gap20": gap20,
            "ma20": ma20,
            "ma60": ma60,
            "boll_lower": boll.get("lower"),
            "badges": badges,
        })
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    return {
        "holdings": result,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl_pct, 2),
    }

@app.post("/api/holdings")
def add_holding(body: HoldingBody, user=Depends(get_current_user)):
    ok, msg = db.add_holding(user["user_id"], body.code, body.name, body.avg_price, body.qty)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.put("/api/holdings/{code}")
def update_holding(code: str, body: HoldingBody, user=Depends(get_current_user)):
    db.update_holding(user["user_id"], code, body.avg_price, body.qty)
    return {"message": "수정 완료"}

@app.delete("/api/holdings/{code}")
def delete_holding(code: str, user=Depends(get_current_user)):
    db.delete_holding(user["user_id"], code)
    return {"message": "삭제 완료"}

def _calc_ai_targets(cur: float, analysis: dict, ohlcv) -> dict:
    """볼린저/MA/고점 기반 AI 추천 목표가·손절가 계산"""
    if not cur or cur <= 0:
        return {}
    try:
        boll = analysis.get("bollinger") or {}
        ma20 = analysis.get("ma20")
        boll_upper = boll.get("upper")
        boll_lower = boll.get("lower")
        ohlcv_ok = ohlcv is not None and not ohlcv.empty
        tp, tb = None, ""
        if boll_upper and boll_upper > cur:
            tp = round(boll_upper / 100) * 100; tb = "볼린저 상단"
        elif ohlcv_ok:
            hcol = "high" if "high" in ohlcv.columns else "고가"
            if hcol in ohlcv.columns:
                high60 = float(ohlcv[hcol].tail(60).max())
                if high60 > cur * 1.03:
                    tp = round(high60 / 100) * 100; tb = "60일 고점"
        if not tp:
            tp = round(cur * 1.08 / 100) * 100; tb = "현재가 +8%"
        sp, sb = None, ""
        if boll_lower and boll_lower < cur:
            sp = round(boll_lower / 100) * 100; sb = "볼린저 하단"
        elif ma20 and ma20 * 0.97 < cur:
            sp = round(ma20 * 0.97 / 100) * 100; sb = "20일선 -3%"
        if not sp:
            sp = round(cur * 0.95 / 100) * 100; sb = "현재가 -5%"
        tu = round((tp - cur) / cur * 100, 1) if cur else 0
        sd = round((sp - cur) / cur * 100, 1) if cur else 0
        rr = round(abs(tu / sd), 1) if sd else 0
        return {"target_price": tp, "target_basis": tb, "target_upside": tu,
                "stop_price": sp, "stop_basis": sb, "stop_downside": sd, "risk_reward": rr}
    except Exception:
        return {}


def _to_python(obj):
    """numpy/pandas 타입 → Python 기본 타입 변환 (JSON 직렬화용)"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _to_python(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_python(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

@app.get("/api/holdings/{code}/detail")
def holding_detail(code: str, user=Depends(get_current_user)):
    holdings = db.get_holdings(user["user_id"])
    h = next((x for x in holdings if x["code"] == code), None)
    if not h:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    # ── 단계별 독립 실행: 하나 실패해도 나머지는 계속 ──
    analysis: dict = {"cur_price": h["avg_price"]}

    # 1) OHLCV + 기술 지표
    ohlcv = None
    try:
        ohlcv = get_ohlcv(code, days=60)
        inv   = get_investor_trading(code, days=25)
        result = analyze_stock(ohlcv, inv, h["avg_price"], h["qty"])
        analysis.update(result)
    except Exception as e:
        print(f"[HoldingDetail] analyze_stock 실패({code}): {e}")

    # 2) 현재가
    try:
        pd2 = get_current_price(code)
        cur = pd2.get("current_price", h["avg_price"]) or h["avg_price"]
        analysis["cur_price"]      = cur
        analysis["cur_change"]     = pd2.get("change", 0)
        analysis["cur_change_pct"] = pd2.get("change_pct", 0)
        analysis["cur_high"]       = pd2.get("high", 0)
        analysis["cur_low"]        = pd2.get("low", 0)
        analysis["cur_volume"]     = pd2.get("volume", 0)
    except Exception as e:
        print(f"[HoldingDetail] get_current_price 실패({code}): {e}")
        cur = h["avg_price"]

    # 3) 목표가/손절가
    try:
        avg_p = h["avg_price"]
        boll  = analysis.get("bollinger", {})
        ma20  = analysis.get("ma20")
        boll_upper = boll.get("upper")
        boll_lower = boll.get("lower")
        tp, tb = None, ""
        if boll_upper and boll_upper > cur:
            tp = round(boll_upper / 100) * 100; tb = "볼린저 상단"
        elif ohlcv is not None and not ohlcv.empty:
            hcol = "high" if "high" in ohlcv.columns else "고가"
            if hcol in ohlcv.columns:
                high60 = float(ohlcv[hcol].tail(60).max())
                if high60 > cur * 1.03:
                    tp = round(high60 / 100) * 100; tb = "60일 고점"
        avg_tp = round(avg_p * 1.10 / 100) * 100
        if not tp or avg_tp > tp: tp = avg_tp; tb = "평단가 +10%"
        if not tp: tp = round(cur * 1.08 / 100) * 100; tb = "현재가 +8%"
        sp, sb = None, ""
        if boll_lower and boll_lower < cur:
            sp = round(boll_lower / 100) * 100; sb = "볼린저 하단"
        elif ma20 and ma20 * 0.97 < cur:
            sp = round(ma20 * 0.97 / 100) * 100; sb = "20일선 -3%"
        avg_sp = round(avg_p * 0.93 / 100) * 100
        if not sp or avg_sp > sp: sp = avg_sp; sb = "평단가 -7%"
        if not sp: sp = round(cur * 0.95 / 100) * 100; sb = "현재가 -5%"
        tu = (tp - cur) / cur * 100 if cur else 0
        sd = (sp - cur) / cur * 100 if cur else 0
        avs = (sp - avg_p) / avg_p * 100 if avg_p and sp else None
        rr  = abs(tu / sd) if sd else 0
        analysis["targets"] = {
            "target_price": tp, "target_basis": tb, "target_upside": round(tu, 1),
            "stop_price": sp, "stop_basis": sb, "stop_downside": round(sd, 1),
            "avg_vs_stop": round(avs, 1) if avs is not None else None,
            "risk_reward": round(rr, 1),
        }
    except Exception as e:
        print(f"[HoldingDetail] targets 계산 실패({code}): {e}")
        analysis.setdefault("targets", {})

    # 4) 수급 일별 데이터 + 거래량 리스트
    try:
        inv_list = []
        if ohlcv is not None:
            inv2 = get_investor_trading(code, days=5)
            if inv2 is not None and not inv2.empty:
                for dt, row in inv2.tail(5).iterrows():
                    inv_list.append({
                        "date": str(dt)[:10],
                        "foreign": int(row.get("외국인", 0)),
                        "inst":    int(row.get("기관", 0)),
                    })
        analysis["inv_list"] = inv_list
        # 5일 거래량 리스트
        vol_list = []
        if ohlcv is not None and not ohlcv.empty:
            for dt, row in ohlcv.tail(5).iterrows():
                vol_list.append({"date": str(dt)[:10], "volume": int(row.get("volume", 0))})
        analysis["vol_list"] = vol_list
    except Exception as e:
        analysis["inv_list"] = []
        analysis["vol_list"] = []

    # 5) OHLCV 차트 데이터
    try:
        ohlcv_data = []
        if ohlcv is not None and not ohlcv.empty:
            for dt, row in ohlcv.tail(60).iterrows():
                ohlcv_data.append({
                    "date":   str(dt)[:10],
                    "open":   int(row.get("open",   row.get("시가",  0))),
                    "high":   int(row.get("high",   row.get("고가",  0))),
                    "low":    int(row.get("low",    row.get("저가",  0))),
                    "close":  int(row.get("close",  row.get("종가",  0))),
                    "volume": int(row.get("volume", row.get("거래량",0))),
                })
        analysis["ohlcv"] = ohlcv_data
    except Exception as e:
        analysis["ohlcv"] = []

    # 6) 종목 뉴스 — 비동기 분리 (/api/stock/{code}/news 별도 호출)
    analysis["news"] = []

    # 7) DART 공시
    try:
        analysis["disclosures"] = _dart_disclosures(code, days=30)
    except Exception:
        analysis["disclosures"] = []

    return _to_python({"holding": h, "analysis": analysis})

# ─────────────────────────────────────────────────────────
# 관심종목 API
# ─────────────────────────────────────────────────────────
@app.get("/api/watchlist")
def get_watchlist(user=Depends(get_current_user)):
    items = db.get_watchlist(user["user_id"])
    # 각 종목에 미니 분석 추가 (현재가, RSI, 타이밍)
    enriched = []
    for item in items:
        entry = dict(item)
        try:
            ohlcv = get_ohlcv(item["code"], days=60)
            inv   = get_investor_trading(item["code"], days=5)
            a     = analyze_stock(ohlcv, inv)
            pd2   = get_current_price(item["code"])
            cur   = pd2.get("current_price", 0) or 0
            # 장 마감/주말이면 OHLCV 마지막 종가로 폴백
            if (not cur) and ohlcv is not None and not ohlcv.empty:
                cur = float(ohlcv["close"].iloc[-1])
            chg_pct = pd2.get("change_pct", 0) or 0
            timing  = watchlist_timing(a, item.get("target_price"), item.get("stop_loss"))
            entry["cur_price"]    = float(cur)
            entry["change_pct"]   = float(round(chg_pct, 2))
            entry["rsi"]          = float(round(a.get("rsi", 50), 1))
            entry["gap20"]        = float(round(a.get("gap20", 100), 1))
            entry["badges"]       = _to_python(a.get("badges", []))
            entry["timing"]       = _to_python(timing)
            entry["targets"]      = _to_python(_calc_ai_targets(cur, a, ohlcv))
        except Exception as e:
            entry["_err"] = str(e)
        # 필수 필드 기본값 보장
        entry.setdefault("cur_price", 0)
        entry.setdefault("change_pct", 0)
        entry.setdefault("rsi", None)
        entry.setdefault("timing", {})
        entry.setdefault("badges", [])
        entry.setdefault("targets", {})
        enriched.append(entry)
    # 알림 배지: 매수검토 종목 카운트
    alert_count = sum(1 for e in enriched if (e.get("timing") or {}).get("status") == "buy_ok")
    groups = db.get_watchlist_groups(user["user_id"])
    return _to_python({"watchlist": enriched, "alert_count": alert_count, "groups": groups})

@app.post("/api/watchlist")
def add_watchlist(body: WatchlistBody, user=Depends(get_current_user)):
    ok, msg = db.add_watchlist(user["user_id"], body.code, body.name,
                               body.target_price, body.stop_loss, body.group_name)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.put("/api/watchlist/{code}/group")
def update_watchlist_group(code: str, body: WatchlistGroupBody, user=Depends(get_current_user)):
    db.update_watchlist_group(user["user_id"], code, body.group_name)
    return {"message": "그룹 변경 완료"}

@app.delete("/api/watchlist/{code}")
def delete_watchlist(code: str, user=Depends(get_current_user)):
    db.delete_watchlist(user["user_id"], code)
    return {"message": "삭제 완료"}

@app.get("/api/watchlist/{code}/detail")
def watchlist_detail(code: str, user=Depends(get_current_user)):
    items = db.get_watchlist(user["user_id"])
    item = next((x for x in items if x["code"] == code), None)
    if not item:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    try:
        ohlcv = get_ohlcv(code, days=60)
        inv = get_investor_trading(code, days=25)
        analysis = analyze_stock(ohlcv, inv)
        pd2 = get_current_price(code)
        cur = pd2.get("current_price", 0) or 0
        ohlcv_ok = ohlcv is not None and not ohlcv.empty
        last = ohlcv.iloc[-1] if ohlcv_ok else None
        # 장 마감/주말이면 OHLCV 마지막 행으로 폴백
        if not cur and last is not None:
            cur = float(last["close"])
        analysis["cur_price"]     = cur
        analysis["cur_change"]    = pd2.get("change", 0) or 0
        analysis["cur_change_pct"]= pd2.get("change_pct", 0) or 0
        analysis["cur_high"]      = pd2.get("high", 0) or (float(last["high"])   if last is not None else 0)
        analysis["cur_low"]       = pd2.get("low", 0)  or (float(last["low"])    if last is not None else 0)
        analysis["cur_volume"]    = pd2.get("volume", 0) or (int(last["volume"]) if last is not None else 0)
        timing = watchlist_timing(analysis, item.get("target_price"), item.get("stop_loss"))
        analysis["timing"] = timing
        # AI 추천 목표가/손절가 계산
        analysis["targets"] = _calc_ai_targets(cur, analysis, ohlcv)
        # 수급 일별
        inv_list = []
        if inv is not None and not inv.empty:
            for dt, row in inv.tail(5).iterrows():
                inv_list.append({
                    "date": str(dt)[:10],
                    "foreign": int(row.get("외국인", 0)),
                    "inst": int(row.get("기관", 0)),
                })
        analysis["inv_list"] = inv_list
        analysis["news"] = []  # 뉴스는 /api/stock/{code}/news 별도 호출
        # OHLCV 차트 데이터
        ohlcv_data = []
        if ohlcv is not None and not ohlcv.empty:
            for dt, row in ohlcv.tail(60).iterrows():
                ohlcv_data.append({
                    "date":   str(dt)[:10],
                    "open":   int(row.get("open",   row.get("시가",  0))),
                    "high":   int(row.get("high",   row.get("고가",  0))),
                    "low":    int(row.get("low",    row.get("저가",  0))),
                    "close":  int(row.get("close",  row.get("종가",  0))),
                    "volume": int(row.get("volume", row.get("거래량",0))),
                })
        analysis["ohlcv"] = ohlcv_data
    except Exception as e:
        import traceback
        analysis = {"error": str(e), "traceback": traceback.format_exc()}
    analysis.setdefault("targets", {})
    analysis.setdefault("timing", {})
    analysis.setdefault("inv_list", [])
    analysis.setdefault("vol_list", [])
    analysis.setdefault("ohlcv", [])
    analysis.setdefault("news", [])
    return _to_python({"item": item, "analysis": analysis})

# ─────────────────────────────────────────────────────────
# 종목 검색 API
# ─────────────────────────────────────────────────────────
@app.get("/api/stock/search")
def search_stock(q: str = ""):
    if not q:
        return {"results": []}
    results = search_stock_by_name(q, max_results=10)
    return {"results": [{"name": r[0], "code": r[1]} for r in results]}

@app.get("/api/stock/{code}/investor")
def stock_investor(code: str, days: int = 5):
    """수급 데이터만 반환 (5/10/20일 탭 전환용)"""
    try:
        days = min(max(days, 5), 20)
        inv = get_investor_trading(code, days=days)
        inv_list = []
        if inv is not None and not inv.empty:
            for dt, row in inv.tail(days).iterrows():
                inv_list.append({
                    "date": str(dt)[:10],
                    "foreign": float(row.get("외국인", 0)),
                    "inst": float(row.get("기관", 0)),
                })
        return {"inv_list": inv_list, "days": days}
    except Exception as e:
        return {"inv_list": [], "days": days}

@app.get("/api/stock/{code}")
def stock_detail(code: str):
    try:
        tickers = get_all_tickers()
        name = tickers.get(code, code)
        ohlcv = get_ohlcv(code, days=60)
        inv = get_investor_trading(code, days=5)
        analysis = analyze_stock(ohlcv, inv)
        pd2 = get_current_price(code)
        analysis["cur_price"] = pd2.get("current_price", 0)
        news = fetch_stock_news(name)
        return {"code": code, "name": name, "analysis": analysis, "news": news}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────
# 매집 스캐너 API — 백그라운드 계산, 캐시 즉시 반환
# ─────────────────────────────────────────────────────────
import threading as _threading
_scanner_cache = {"data": None, "ts": 0, "running": False}

def _run_scanner():
    """백그라운드 스레드에서 스캐너 계산 실행"""
    import time
    if _scanner_cache["running"]:
        return
    _scanner_cache["running"] = True
    import logging as _log
    _slog = _log.getLogger("scanner")
    try:
        stocks = [s for s in get_top_stocks(100) if s.get("code") and len(s["code"]) == 6]
        _slog.info(f"[스캐너] 종목 수: {len(stocks)}")
        results = []
        for s in stocks[:100]:
            try:
                ohlcv = get_ohlcv(s["code"], days=60)
                inv = get_investor_trading(s["code"], days=5)
                a = analyze_stock(ohlcv, inv)
                no_investor = (a.get("foreign_net_3d", 0) == 0 and a.get("institution_net_3d", 0) == 0)
                min_score = 3 if no_investor else 4
                if a["score"] >= min_score:
                    pd2 = get_current_price(s["code"])
                    price = pd2.get("current_price", 0) or 0
                    if not price and ohlcv is not None and not ohlcv.empty:
                        price = float(ohlcv["close"].iloc[-1])
                    change_pct = pd2.get("change_pct", 0) or 0
                    ohlcv_data = []
                    if ohlcv is not None and not ohlcv.empty:
                        for dt, row in ohlcv.tail(60).iterrows():
                            ohlcv_data.append({
                                "date":   str(dt)[:10],
                                "open":   int(row.get("open",   row.get("시가",  0))),
                                "high":   int(row.get("high",   row.get("고가",  0))),
                                "low":    int(row.get("low",    row.get("저가",  0))),
                                "close":  int(row.get("close",  row.get("종가",  0))),
                                "volume": int(row.get("volume", row.get("거래량",0))),
                            })
                    results.append(_to_python({
                        "code": s["code"], "name": s["name"],
                        "price": price, "change_pct": change_pct, **a,
                        "ohlcv": ohlcv_data,
                    }))
            except Exception as _e:
                _slog.warning(f"[스캐너] {s.get('code')} 오류: {_e}")
                continue
        _slog.info(f"[스캐너] 완료: {len(results)}개 신호 종목")
        results.sort(key=lambda x: (x["score"], x.get("volume_ratio", 0)), reverse=True)
        _scanner_cache["data"] = {"results": results[:20]}
        _scanner_cache["ts"] = time.time()
    except Exception as e:
        _slog.error(f"[스캐너] 치명적 오류: {e}")
        if not _scanner_cache["data"]:
            _scanner_cache["data"] = {"results": [], "error": str(e)}
    finally:
        _scanner_cache["running"] = False

@app.get("/api/scanner")
def get_scanner():
    import time
    now = time.time()
    cache_age = now - _scanner_cache["ts"]
    import datetime as _dt
    def _with_ts(data):
        ts = _scanner_cache["ts"]
        scanned_at = _dt.datetime.fromtimestamp(ts).strftime("%m.%d %H:%M") if ts else None
        age_min = int(cache_age // 60) if ts else None
        return {**data, "scanned_at": scanned_at, "cache_age_min": age_min}

    # 캐시 유효(1시간)하면 즉시 반환
    if _scanner_cache["data"] and cache_age < 3600:
        return _with_ts(_scanner_cache["data"])
    # 캐시 없거나 만료 → 백그라운드 계산 시작
    if not _scanner_cache["running"]:
        t = _threading.Thread(target=_run_scanner, daemon=True)
        t.start()
    # 계산 중이면 stale 캐시 또는 로딩 상태 반환
    if _scanner_cache["data"]:
        return _with_ts(_scanner_cache["data"])
    return {"results": [], "loading": True, "scanned_at": None, "cache_age_min": None}

# ─────────────────────────────────────────────────────────
# 정적 파일 서빙 (프론트엔드)
# ─────────────────────────────────────────────────────────
app.mount("/icons", StaticFiles(directory="frontend/icons"), name="icons")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/api/debug/html-hex")
def debug_html_hex():
    with open("frontend/index.html", "rb") as f:
        data = f.read()
    idx = data.find(b'login-title">')
    return {"bom": data[:3].hex(), "login_title_hex": data[idx:idx+20].hex(), "size": len(data)}

@app.get("/manifest.json")
def manifest():
    return FileResponse("frontend/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("frontend/service-worker.js", media_type="application/javascript")

@app.get("/")
@app.head("/")
def root():
    return FileResponse("frontend/index.html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache", "Expires": "0"
    })

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    return FileResponse("frontend/index.html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache", "Expires": "0"
    })
