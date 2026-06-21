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
from database import get_recent_predictions, get_prediction_accuracy
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
_JWT_SECRET = os.environ.get("JWT_SECRET", "pocket-stock-secret-2026")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

class StockSearchBody(BaseModel):
    query: str

# ─────────────────────────────────────────────────────────
# 인증 API
# ─────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(body: LoginBody):
    ok, user_id = db.verify_user(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다")
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
                analysis.append({"dot": item[0], "label": item[1], "text": item[2]})
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
                    analysis_out.append({"dot": item[0], "label": item[1], "text": item[2]})
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

@app.delete("/api/holdings/{code}")
def delete_holding(code: str, user=Depends(get_current_user)):
    db.delete_holding(user["user_id"], code)
    return {"message": "삭제 완료"}

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

    # 4) 수급 일별 데이터
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
    except Exception as e:
        analysis["inv_list"] = []

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

    # 6) 종목 뉴스
    try:
        news = fetch_stock_news(h["name"])
        analysis["news"] = news[:3]
    except Exception:
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
        except Exception as e:
            entry["_err"] = str(e)
        enriched.append(entry)
    return _to_python({"watchlist": enriched})

@app.post("/api/watchlist")
def add_watchlist(body: WatchlistBody, user=Depends(get_current_user)):
    ok, msg = db.add_watchlist(user["user_id"], body.code, body.name, body.target_price, body.stop_loss)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

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
        news = fetch_stock_news(item.get("name", code))
        analysis["news"] = news[:3]
    except Exception as e:
        import traceback
        analysis = {"error": str(e), "traceback": traceback.format_exc()}
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
# 매집 스캐너 API
# ─────────────────────────────────────────────────────────
_scanner_cache = {"data": None, "ts": 0}

@app.get("/api/scanner")
def scanner():
    import time
    now = time.time()
    if _scanner_cache["data"] and now - _scanner_cache["ts"] < 3600:
        return _scanner_cache["data"]
    try:
        stocks = get_top_stocks(100)
        results = []
        for s in stocks[:100]:
            try:
                ohlcv = get_ohlcv(s["code"], days=60)
                inv = get_investor_trading(s["code"], days=5)
                a = analyze_stock(ohlcv, inv)
                if a["score"] >= 3:
                    pd2 = get_current_price(s["code"])
                    price = pd2.get("current_price", 0) or 0
                    # 주말/장마감 시 OHLCV 마지막 종가 폴백
                    if not price and ohlcv is not None and not ohlcv.empty:
                        price = float(ohlcv["close"].iloc[-1])
                    change_pct = pd2.get("change_pct", 0) or 0
                    results.append(_to_python({
                        "code": s["code"], "name": s["name"],
                        "price": price,
                        "change_pct": change_pct,
                        **a
                    }))
            except Exception:
                continue
        results.sort(key=lambda x: (x["score"], x.get("volume_ratio", 0)), reverse=True)
        data = {"results": results[:20]}
        _scanner_cache["data"] = data
        _scanner_cache["ts"] = now
        return data
    except Exception as e:
        return {"results": [], "error": str(e)}

# ─────────────────────────────────────────────────────────
# 정적 파일 서빙 (프론트엔드)
# ─────────────────────────────────────────────────────────
app.mount("/icons", StaticFiles(directory="frontend/icons"), name="icons")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/manifest.json")
def manifest():
    return FileResponse("frontend/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("frontend/service-worker.js", media_type="application/javascript")

@app.get("/")
@app.head("/")
def root():
    return FileResponse("frontend/index.html")

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    return FileResponse("frontend/index.html")
