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
APP_KEY    = os.getenv("KIS_APP_KEY", "YOUR_APP_KEY_HERE")
APP_SECRET = os.getenv("KIS_APP_SECRET", "YOUR_APP_SECRET_HERE")
CANO       = os.getenv("KIS_CANO", "YOUR_ACCOUNT_NUMBER")  # 계좌번호 앞 8자리
ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD", "01")         # 계좌상품코드

# 실전: https://openapi.koreainvestment.com:9443
# 모의: https://openapivts.koreainvestment.com:29443
BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

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
