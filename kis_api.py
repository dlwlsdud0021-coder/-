"""
한국투자증권 API 연동 모듈 (Phase 3)

사전 준비:
1. https://apiportal.koreainvestment.com 에서 앱 등록
2. APP_KEY, APP_SECRET 발급
3. .env 파일에 키 저장

pip install python-dotenv requests
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG  (환경변수 또는 직접 입력)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _get_secret(key: str, default: str = "") -> str:
    """환경변수 → Streamlit Secrets 순으로 조회"""
    val = os.getenv(key, "")
    if val:
        return val.strip()
    try:
        import streamlit as st
        val = st.secrets.get(key, default)
        return str(val).strip() if val else default
    except Exception:
        return default

APP_KEY      = _get_secret("KIS_APP_KEY")
APP_SECRET   = _get_secret("KIS_APP_SECRET")
CANO         = _get_secret("KIS_CANO")
ACNT_PRDT_CD = _get_secret("KIS_ACNT_PRDT_CD", "01")

# 실전: https://openapi.koreainvestment.com:9443
# 모의: https://openapivts.koreainvestment.com:29443
BASE_URL = _get_secret("KIS_BASE_URL", "https://openapivts.koreainvestment.com:29443")

_token_cache: dict = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_access_token() -> str:
    """OAuth 토큰 발급 (캐시 포함)"""
    now = time.time()
    if _token_cache.get("token") and now < _token_cache.get("expires", 0) - 60:
        return _token_cache["token"]

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
    }
    resp = requests.post(url, json=body)
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expires_in = data.get("expires_in", 86400)
    _token_cache["token"] = token
    _token_cache["expires"] = now + expires_in
    return token


def _headers(tr_id: str) -> dict:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token()}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 현재가 조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_current_price(code: str) -> Optional[dict]:
    """
    종목 현재가 조회
    Returns:
        {current_price, change, change_pct, high, low, volume, ...}
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {
        "fid_cond_mrkt_div_code": "J",  # J=주식
        "fid_input_iscd": code,
    }
    try:
        resp = requests.get(url, headers=_headers("FHKST01010100"), params=params)
        resp.raise_for_status()
        d = resp.json()["output"]
        return {
            "current_price": int(d["stck_prpr"]),
            "change": int(d["prdy_vrss"]),
            "change_pct": float(d["prdy_ctrt"]),
            "high": int(d["stck_hgpr"]),
            "low": int(d["stck_lwpr"]),
            "vol": int(d["acml_vol"]),
            "open": int(d["stck_oprc"]),
        }
    except Exception as e:
        print(f"[KIS] get_current_price({code}) 오류: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OHLCV (일봉)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_ohlcv(code: str, period: str = "D", count: int = 60) -> list[dict]:
    """
    일봉/주봉/월봉 조회
    period: D=일, W=주, M=월
    Returns: list of {date, open, high, low, close, volume}
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=count * 2)).strftime("%Y%m%d")

    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code,
        "fid_input_date_1": start_date,
        "fid_input_date_2": end_date,
        "fid_period_div_code": period,
        "fid_org_adj_prc": "0",
    }
    try:
        resp = requests.get(url, headers=_headers("FHKST03010100"), params=params)
        resp.raise_for_status()
        rows = resp.json().get("output2", [])
        result = []
        for r in rows[:count]:
            result.append({
                "date": r["stck_bsop_date"],
                "open": int(r["stck_oprc"]),
                "high": int(r["stck_hgpr"]),
                "low": int(r["stck_lwpr"]),
                "close": int(r["stck_clpr"]),
                "volume": int(r["acml_vol"]),
            })
        return result
    except Exception as e:
        print(f"[KIS] get_ohlcv({code}) 오류: {e}")
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 외국인·기관 수급
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# KOSPI 시장 전체 수급 추정에 사용할 대형주 (시총 상위 10개)
# 삼성전자 단독 proxy 대신 시총 가중 평균으로 더 대표성 있는 KOSPI 수급 추정
_KOSPI_TOP10 = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "207940",  # 삼성바이오로직스
    "005380",  # 현대차
    "000270",  # 기아
    "068270",  # 셀트리온
    "105560",  # KB금융
    "055550",  # 신한지주
    "035420",  # NAVER
    "051910",  # LG화학
]


def get_kospi_market_investor(days: int = 25) -> list[dict]:
    """
    KOSPI 시장 전체 외국인·기관 순매수 거래대금 (단위: 백만원).

    1순위: KIS '시장별 투자자 매매동향' 직접 조회 (TR: FHKUP03500100)
    2순위: 시총 상위 10개 종목 합산 (삼성전자 단독 proxy보다 대표성 높음)

    Returns: list of {date, foreign_net, institution_net}  (최신순)
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=days + 15)).strftime("%Y%m%d")

    # 1순위: KIS 시장별 투자자 매매동향 (KOSPI 전체)
    try:
        url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-market-investor-trend-by-date"
        params = {
            "fid_cond_mrkt_div_code": "J",   # J=KOSPI
            "fid_input_date_1": start_date,
            "fid_input_date_2": end_date,
        }
        resp = requests.get(url, headers=_headers("FHKUP03500100"), params=params, timeout=8)
        resp.raise_for_status()
        rows = resp.json().get("output", [])
        if rows and any(abs(int(r.get("frgn_ntby_tr_pbmn", 0))) > 0 for r in rows):
            result = []
            for r in rows[:days]:
                result.append({
                    "date": r["stck_bsop_date"],
                    "foreign_net":     int(r.get("frgn_ntby_tr_pbmn", 0)),
                    "institution_net": int(r.get("orgn_ntby_tr_pbmn", 0)),
                    "_source": "market_direct",
                })
            return result
    except Exception as e:
        print(f"[KIS] KOSPI 시장 직접 수급 실패: {e}")

    # 2순위: 시총 상위 10종목 합산
    from collections import defaultdict
    daily_totals: dict = defaultdict(lambda: {"foreign_net": 0, "institution_net": 0})
    success_count = 0
    for code in _KOSPI_TOP10:
        try:
            url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": code,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
            }
            resp = requests.get(url, headers=_headers("FHKST01010900"), params=params, timeout=6)
            resp.raise_for_status()
            rows = resp.json().get("output", [])
            for r in rows[:days]:
                d = r["stck_bsop_date"]
                daily_totals[d]["foreign_net"]     += int(r.get("frgn_ntby_tr_pbmn", 0))
                daily_totals[d]["institution_net"] += int(r.get("orgn_ntby_tr_pbmn", 0))
            success_count += 1
        except Exception:
            continue  # 개별 종목 실패는 건너뜀

    if success_count >= 3 and daily_totals:
        result = []
        for date in sorted(daily_totals.keys(), reverse=True)[:days]:
            result.append({
                "date": date,
                "foreign_net":     daily_totals[date]["foreign_net"],
                "institution_net": daily_totals[date]["institution_net"],
                "_source": f"top{success_count}_aggregate",
            })
        return result

    return []


def get_investor_trading_value(code: str, days: int = 25) -> list[dict]:
    """외국인·기관 일별 순매수 거래대금 (단위: 백만원)"""
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=days + 10)).strftime("%Y%m%d")
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code,
        "fid_input_date_1": start_date,
        "fid_input_date_2": end_date,
    }
    try:
        resp = requests.get(url, headers=_headers("FHKST01010900"), params=params)
        resp.raise_for_status()
        rows = resp.json().get("output", [])
        result = []
        for r in rows[:days]:
            result.append({
                "date": r["stck_bsop_date"],
                "foreign_net": int(r.get("frgn_ntby_tr_pbmn", 0)),   # 백만원
                "institution_net": int(r.get("orgn_ntby_tr_pbmn", 0)),
            })
        return result
    except Exception as e:
        print(f"[KIS] get_investor_trading_value({code}) 오류: {e}")
        return []


def get_investor_trading(code: str, days: int = 25) -> list[dict]:
    """
    외국인·기관 일별 순매수 조회
    Returns: list of {date, foreign_net, institution_net}
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=days + 10)).strftime("%Y%m%d")

    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code,
        "fid_input_date_1": start_date,
        "fid_input_date_2": end_date,
    }
    try:
        resp = requests.get(url, headers=_headers("FHKST01010900"), params=params)
        resp.raise_for_status()
        rows = resp.json().get("output", [])
        result = []
        for r in rows[:days]:
            result.append({
                "date": r["stck_bsop_date"],
                "foreign_net": int(r.get("frgn_ntby_qty", 0)),
                "institution_net": int(r.get("orgn_ntby_qty", 0)),
            })
        return result
    except Exception as e:
        print(f"[KIS] get_investor_trading({code}) 오류: {e}")
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 시가총액 상위 종목 (KRX IP 차단 없이 Streamlit Cloud에서도 동작)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_top_stocks_by_cap(market: str = "J", n: int = 100) -> list[dict]:
    """
    시가총액 상위 종목 조회 (KIS API)
    market: J=코스피, Q=코스닥
    Returns: [{"code", "name", "market", "market_cap"}, ...]
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/ranking/market-cap"
    params = {
        "fid_cond_mrkt_div_code": market,
        "fid_cond_scr_div_code": "20174",
        "fid_div_cls_code": "0",
        "fid_blng_cls_code": "0",
        "fid_trgt_cls_code": "0",
        "fid_trgt_exls_cls_code": "0",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_input_iscd": "0000",
    }
    market_name = "KOSPI" if market == "J" else "KOSDAQ"
    try:
        resp = requests.get(url, headers=_headers("FHPST01740000"), params=params, timeout=10)
        resp.raise_for_status()
        rows = resp.json().get("output", [])
        result = []
        for r in rows[:n]:
            result.append({
                "code":       r.get("stck_shrn_iscd", ""),
                "name":       r.get("hts_kor_isnm", ""),
                "market":     market_name,
                "market_cap": int(r.get("stck_avls", 0)),
            })
        return result
    except Exception as e:
        print(f"[KIS] get_top_stocks_by_cap({market}) 오류: {e}")
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 지수 현재가 (KOSPI/KOSDAQ)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_index_price(index_code: str = "0001") -> Optional[dict]:
    """
    지수 현재가 조회
    index_code: 0001=KOSPI, 1001=KOSDAQ
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-index-price"
    params = {
        "fid_cond_mrkt_div_code": "U",
        "fid_input_iscd": index_code,
    }
    try:
        resp = requests.get(url, headers=_headers("FHPUP02100000"), params=params)
        resp.raise_for_status()
        d = resp.json()["output"]
        return {
            "current": float(d["bstp_nmix_prpr"]),
            "change": float(d["bstp_nmix_prdy_vrss"]),
            "change_pct": float(d["bstp_nmix_prdy_ctrt"]),
        }
    except Exception as e:
        print(f"[KIS] get_index_price({index_code}) 오류: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 기술적 지표 계산 (pykrx 불필요, 직접 계산)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_rsi(closes: list[float], period: int = 14) -> float:
    """RSI 계산"""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas[-period:]]
    losses = [abs(min(d, 0)) for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 1)


def calc_ma(closes: list[float], period: int) -> float:
    """이동평균 계산"""
    if len(closes) < period:
        return closes[-1] if closes else 0
    return round(sum(closes[-period:]) / period, 0)


def calc_gap(current: float, ma: float) -> float:
    """이격도 계산"""
    if ma == 0:
        return 100.0
    return round(current / ma * 100, 1)


def calc_bollinger(closes: list[float], period: int = 20, std_mult: float = 2.0) -> dict:
    """볼린저밴드 계산"""
    if len(closes) < period:
        return {"mid": closes[-1], "top": closes[-1], "bot": closes[-1]}
    recent = closes[-period:]
    mid = sum(recent) / period
    variance = sum((x - mid) ** 2 for x in recent) / period
    std = variance ** 0.5
    return {
        "mid": round(mid, 0),
        "top": round(mid + std_mult * std, 0),
        "bot": round(mid - std_mult * std, 0),
    }


def calc_obv(closes: list[float], volumes: list[int]) -> list[int]:
    """OBV 계산"""
    obv = [0]
    for i in range(1, min(len(closes), len(volumes))):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 종합 종목 분석 (Phase 3 메인 함수)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def analyze_stock(code: str, avg_price: float = 0, qty: int = 0) -> dict:
    """
    종목 종합 분석 반환
    - 현재가, RSI, 이격도, 볼린저밴드, 외국인/기관 수급
    - avg_price/qty: 보유종목인 경우 입력
    """
    price_info = get_current_price(code) or {}
    ohlcv = get_ohlcv(code, "D", 120)
    investor = get_investor_trading(code, 5)

    closes = [d["close"] for d in ohlcv][::-1]  # 오래된 순으로
    vols = [d["volume"] for d in ohlcv][::-1]

    current = price_info.get("current_price", 0)
    ma20 = calc_ma(closes, 20)
    ma60 = calc_ma(closes, 60)
    rsi = calc_rsi(closes)
    gap = calc_gap(current, ma20)
    bb = calc_bollinger(closes)
    obv = calc_obv(closes, vols)
    obv_rising = len(obv) >= 5 and obv[-1] > obv[-5]

    # 수급 시그널
    f_consecutive = 0
    for d in investor:
        if d["foreign_net"] > 0:
            f_consecutive += 1
        else:
            break

    pnl = (current - avg_price) * qty if avg_price and qty else 0
    pnl_pct = (current / avg_price - 1) * 100 if avg_price else 0

    return {
        "code": code,
        "current_price": current,
        "change": price_info.get("change", 0),
        "change_pct": price_info.get("change_pct", 0),
        "high": price_info.get("high", 0),
        "low": price_info.get("low", 0),
        "vol": price_info.get("vol", 0),
        "rsi": rsi,
        "gap": gap,
        "ma20": ma20,
        "ma60": ma60,
        "bb_top": bb["top"],
        "bb_bot": bb["bot"],
        "obv_rising": obv_rising,
        "foreign_consecutive": f_consecutive,
        "pnl": pnl,
        "pnl_pct": round(pnl_pct, 2),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 매집신호 스캐너
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def scan_accumulation(codes: list[str]) -> list[dict]:
    """
    여러 종목에 대해 매집신호 점수 계산
    score 4~5: 신뢰도 높음, 3: 보통
    """
    results = []
    for code in codes:
        info = analyze_stock(code)
        if not info["current_price"]:
            continue

        ohlcv = get_ohlcv(code, "D", 30)
        closes = [d["close"] for d in ohlcv][::-1]
        vols = [d["volume"] for d in ohlcv][::-1]

        # 5개 시그널 체크
        avg_vol = sum(vols[-20:]) / 20 if len(vols) >= 20 else 0
        cur_vol = vols[-1] if vols else 0
        vol_surge = cur_vol > avg_vol * 2  # 거래량 2배 이상

        obv_list = calc_obv(closes, vols)
        obv_rising = len(obv_list) >= 5 and obv_list[-1] > obv_list[-5]

        investor = get_investor_trading(code, 5)
        foreign_buy = sum(1 for d in investor if d["foreign_net"] > 0) >= 3
        inst_buy = sum(1 for d in investor if d["institution_net"] > 0) >= 3

        # 횡보 (5일 등락 범위 < 5%)
        if len(closes) >= 5:
            price_range = (max(closes[-5:]) - min(closes[-5:])) / closes[-5] * 100
            sideways = price_range < 5
        else:
            sideways = False

        signals = [vol_surge, obv_rising, foreign_buy, inst_buy, sideways]
        score = sum(signals)

        if score >= 3:
            vol_pct = round((cur_vol / avg_vol - 1) * 100) if avg_vol else 0
            results.append({
                "code": code,
                "score": f"{score}/5",
                "score_num": score,
                "signals": signals,
                "vol_pct": vol_pct,
                **info,
            })

    results.sort(key=lambda x: x["score_num"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


if __name__ == "__main__":
    # 테스트
    print("KIS API 모듈 로드 완료")
    print(f"BASE_URL: {BASE_URL}")
    print("APP_KEY 설정 여부:", APP_KEY != "YOUR_APP_KEY_HERE")
