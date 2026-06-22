"""
market_data.py — 실제 시장 데이터 수집
- pykrx: 국내 주식 OHLCV, 지수, 외국인/기관 수급, 종목 목록
- yfinance: 미국 지수 (S&P500, 나스닥, 다우)
- KIS API: 실시간 현재가 (kis_api.py)
"""

import os
import time
import logging
import traceback
from datetime import datetime, timedelta

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pandas as pd
import streamlit as st

# 수급 데이터 전용 로거
_logger = logging.getLogger("market_data.investor")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ─────────────────────────────────────────────────────────
# KRX 인증 초기화 (pykrx 1.2.8 — 수급 API 필수)
# 환경변수 우선, 없으면 Streamlit Secrets에서 시도
# ─────────────────────────────────────────────────────────
def _init_krx_auth() -> bool:
    """
    KRX_ID / KRX_PW를 환경변수 또는 Streamlit Secrets에서 읽어
    os.environ에 설정한다. pykrx는 import 시점이 아닌 API 호출 시
    환경변수를 참조하므로, 호출 전 설정해두면 된다.
    Returns: True(성공) / False(자격증명 없음)
    """
    krx_id = os.environ.get("KRX_ID", "")
    krx_pw = os.environ.get("KRX_PW", "")

    # 환경변수 없으면 Streamlit Secrets에서 시도
    if not krx_id or not krx_pw:
        try:
            krx_id = st.secrets.get("KRX_ID", "")
            krx_pw = st.secrets.get("KRX_PW", "")
            if krx_id and krx_pw:
                os.environ["KRX_ID"] = krx_id
                os.environ["KRX_PW"] = krx_pw
                _logger.info("[KRX 인증] Streamlit Secrets에서 자격증명 로드")
        except Exception:
            pass  # Secrets 없는 환경 (로컬 스크립트 등) — 무시

    if krx_id and krx_pw:
        _logger.info("[KRX 인증] 자격증명 확인 완료 | ID: %s***", krx_id[:2])
        return True
    else:
        _logger.warning("[KRX 인증] KRX_ID / KRX_PW 환경변수 없음 — 수급 API 사용 불가")
        return False


KRX_AUTH_OK = _init_krx_auth()

# ─────────────────────────────────────────────────────────
# 날짜 헬퍼
# ─────────────────────────────────────────────────────────
def _today() -> str:
    return datetime.today().strftime("%Y%m%d")

def _ndays_ago(n: int) -> str:
    return (datetime.today() - timedelta(days=n)).strftime("%Y%m%d")

def _last_trading_date() -> str:
    """최근 영업일 (주말 제외)"""
    d = datetime.today()
    # 장 마감 전(오전)이면 전날 데이터 사용
    if d.hour < 16:
        d -= timedelta(days=1)
    while d.weekday() >= 5:  # 토/일
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


# ─────────────────────────────────────────────────────────
# pykrx 안전 임포트 (pkg_resources 없으면 직접 패치)
# ─────────────────────────────────────────────────────────
try:
    import pkg_resources
    # 필요한 속성이 없으면 더미로 채우기
    if not hasattr(pkg_resources, 'resource_filename'):
        pkg_resources.resource_filename = lambda *a, **k: ""
    if not hasattr(pkg_resources, 'get_distribution'):
        pkg_resources.get_distribution = lambda name: None
except ImportError:
    import types, sys
    pkg = types.ModuleType("pkg_resources")
    pkg.get_distribution = lambda name: None
    pkg.resource_filename = lambda *a, **k: ""
    pkg.resource_string = lambda *a, **k: b""
    pkg.resource_stream = lambda *a, **k: None
    pkg.working_set = []
    pkg.require = lambda *a, **k: None
    sys.modules["pkg_resources"] = pkg

try:
    from pykrx import stock as krx
    PYKRX_OK = True
    _logger.info("[pykrx] import 성공")
except Exception as e:
    PYKRX_OK = False
    _logger.error("[pykrx] import 실패: %s", e)

# ─────────────────────────────────────────────────────────
# FinanceDataReader 안전 임포트 (pykrx 폴백)
# ─────────────────────────────────────────────────────────
try:
    import FinanceDataReader as fdr
    FDR_OK = True
    _logger.info("[FDR] import 성공")
except Exception as e:
    FDR_OK = False
    _logger.warning("[FDR] import 실패: %s", e)


# ─────────────────────────────────────────────────────────
# 종목명 조회 (캐시)
# ─────────────────────────────────────────────────────────
def get_stock_name(code: str) -> str:
    """종목코드 → 종목명. KIS API → pykrx → FDR 순"""
    # 1순위: KIS API (get_top_stocks 캐시에서 찾기)
    try:
        stocks = get_top_stocks(200)
        for s in stocks:
            if s["code"] == code:
                return s["name"]
    except:
        pass
    # 2순위: pykrx
    if PYKRX_OK:
        try:
            name = krx.get_market_ticker_name(code)
            if name:
                return name
        except:
            pass
    # 3순위: FDR
    if FDR_OK:
        try:
            listing = fdr.StockListing("KRX")
            row = listing[listing["Code"] == code]
            if not row.empty:
                return row.iloc[0]["Name"]
        except:
            pass
    return code


def get_all_tickers() -> dict:
    """코스피+코스닥 전 종목 {code: name}. pykrx → FDR → KIS 순 (KIS는 200종목 제한)"""
    # 1순위: pykrx (전 종목)
    if PYKRX_OK:
        try:
            tdate = _last_trading_date()
            kospi = krx.get_market_ticker_list(tdate, market="KOSPI")
            kosdaq = krx.get_market_ticker_list(tdate, market="KOSDAQ")
            result = {}
            for c in kospi + kosdaq:
                result[c] = krx.get_market_ticker_name(c)
            if result:
                return result
        except:
            pass
    # 2순위: FDR
    if FDR_OK:
        try:
            listing = fdr.StockListing("KRX")
            result = dict(zip(listing["Code"].astype(str), listing["Name"]))
            if result:
                return result
        except:
            pass
    # 3순위: KIS (상위 200종목만)
    try:
        stocks = get_top_stocks(200)
        if stocks:
            return {s["code"]: s["name"] for s in stocks}
    except:
        pass
    return {}


def search_stock_by_name(query: str, max_results: int = 10) -> list:
    """종목명 검색 → [(name, code), ...]. get_all_tickers() 기반 부분 일치."""
    if not query:
        return []
    q = query.strip().lower()
    tickers = get_all_tickers()
    matches = [(name, code) for code, name in tickers.items() if q in name.lower()]
    matches.sort(key=lambda x: (not x[0].lower().startswith(q), x[0]))
    return matches[:max_results]


# ─────────────────────────────────────────────────────────
# 국내 지수 (KOSPI / KOSDAQ) — yfinance 기반
# ─────────────────────────────────────────────────────────
def get_index_data() -> dict:
    # 1순위: KIS API (가장 정확한 실시간 데이터)
    try:
        from kis_api import get_index_price
        kospi = get_index_price("0001")
        kosdaq = get_index_price("1001")
        if kospi and kosdaq:
            return {
                "KOSPI":  {"current": kospi["current"], "change": kospi["change"],
                           "change_pct": kospi["change_pct"], "volume_billion": 0},
                "KOSDAQ": {"current": kosdaq["current"], "change": kosdaq["change"],
                           "change_pct": kosdaq["change_pct"], "volume_billion": 0},
            }
    except Exception as e:
        _logger.warning(f"[지수] KIS API 실패: {e}")

    # 2순위: yfinance 실시간 (장중 15분 지연)
    try:
        import yfinance as yf
        result = {}
        for name, sym in [("KOSPI", "^KS11"), ("KOSDAQ", "^KQ11")]:
            t = yf.Ticker(sym)
            fi = t.fast_info
            cur  = fi.last_price
            prev = fi.previous_close
            if not cur or not prev:
                continue
            chg     = cur - prev
            chg_pct = chg / prev * 100
            result[name] = {
                "current":        round(cur, 2),
                "change":         round(chg, 2),
                "change_pct":     round(chg_pct, 2),
                "volume_billion": 0,
            }
            _logger.info(f"[지수] yfinance {name} = {cur} ({chg_pct:+.2f}%)")
        if len(result) == 2:
            return result
    except Exception as e:
        _logger.warning(f"[지수] yfinance 실패: {e}")

    # 3순위: FDR — KS11(KOSPI), KQ11(KOSDAQ)
    if FDR_OK:
        try:
            from datetime import timezone, timedelta
            kst = timezone(timedelta(hours=9))
            start = (datetime.now(kst) - timedelta(days=10)).strftime("%Y-%m-%d")
            result = {}
            for name, sym in [("KOSPI", "KS11"), ("KOSDAQ", "KQ11")]:
                df = fdr.DataReader(sym, start)
                if df is None or df.empty or len(df) < 2:
                    continue
                cur  = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2])
                chg  = cur - prev
                chg_pct = chg / prev * 100
                if "Change" in df.columns:
                    chg_pct = float(df["Change"].iloc[-1]) * 100
                    chg = round(cur - cur / (1 + float(df["Change"].iloc[-1])), 2)
                result[name] = {
                    "current":        round(cur, 2),
                    "change":         round(chg, 2),
                    "change_pct":     round(chg_pct, 2),
                    "volume_billion": 0,
                }
                _logger.info(f"[지수] {name} = {cur} ({chg_pct:+.2f}%)")
            if len(result) == 2:
                return result
        except Exception as e:
            _logger.warning(f"[지수] FDR 실패: {e}")

    # 폴백: pykrx
    if PYKRX_OK:
        try:
            result = {}
            end = _today()
            start = _ndays_ago(10)
            for name, idx_code in [("KOSPI", "1001"), ("KOSDAQ", "2001")]:
                df = krx.get_index_ohlcv_by_date(start, end, idx_code)
                if df is None or df.empty or len(df) < 2:
                    continue
                cur  = float(df["종가"].iloc[-1])
                if "등락률" in df.columns:
                    chg_pct = float(df["등락률"].iloc[-1])
                    chg = round(cur - cur / (1 + chg_pct / 100), 2)
                else:
                    prev = float(df["종가"].iloc[-2])
                    chg = cur - prev
                    chg_pct = chg / prev * 100
                result[name] = {
                    "current":        round(cur, 2),
                    "change":         round(chg, 2),
                    "change_pct":     round(chg_pct, 2),
                    "volume_billion": 0,
                }
            if len(result) == 2:
                return result
        except Exception as e:
            _logger.warning(f"[지수] pykrx 실패: {e}")

    return _dummy_index()


def _dummy_index():
    return {
        "KOSPI":  {"current": 0, "change": 0, "change_pct": 0, "volume_billion": 0},
        "KOSDAQ": {"current": 0, "change": 0, "change_pct": 0, "volume_billion": 0},
    }


# ─────────────────────────────────────────────────────────
# 미국 지수 (S&P500, 나스닥, 다우)
# ─────────────────────────────────────────────────────────
def get_us_indices() -> dict:
    # 1순위: yfinance history — 정규장 종가 기준 (fast_info.last_price는 장외가 포함)
    try:
        import yfinance as yf
        result = {}
        for name, sym in [("S&P500", "^GSPC"), ("나스닥", "^IXIC"), ("다우", "^DJI")]:
            df = yf.Ticker(sym).history(period="5d", auto_adjust=False)
            if df is not None and len(df) >= 2:
                cur  = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2])
                pct  = (cur - prev) / prev * 100
                result[name] = {"current": round(cur, 2), "change_pct": round(pct, 2)}
            else:
                result[name] = {"current": 0, "change_pct": 0}
        if any(v["current"] > 0 for v in result.values()):
            return result
    except Exception as e:
        _logger.warning(f"[미국지수] yfinance 실패: {e}")

    # 2순위: FDR
    if FDR_OK:
        try:
            start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            result = {}
            for name, sym in [("S&P500", "US500"), ("나스닥", "IXIC"), ("다우", "DJI")]:
                df = fdr.DataReader(sym, start)
                if df is None or df.empty or len(df) < 2:
                    result[name] = {"current": 0, "change_pct": 0}
                    continue
                cur  = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2])
                pct  = (cur - prev) / prev * 100
                if "Change" in df.columns:
                    pct = float(df["Change"].iloc[-1]) * 100
                result[name] = {"current": round(cur, 2), "change_pct": round(pct, 2)}
            return result
        except Exception as e:
            _logger.warning(f"[미국지수] FDR 실패: {e}")

    return {"S&P500": {"current": 0, "change_pct": 0},
            "나스닥":  {"current": 0, "change_pct": 0},
            "다우":    {"current": 0, "change_pct": 0}}


# ─────────────────────────────────────────────────────────
# 종목 OHLCV
# ─────────────────────────────────────────────────────────
def get_ohlcv(code: str, days: int = 120) -> pd.DataFrame:
    """
    Returns DataFrame with columns: open, high, low, close, volume
    최신 날짜가 마지막 행
    KIS VTS는 OHLCV 미지원 → pykrx/FDR 우선
    """
    # 1순위: pykrx (KIS VTS가 OHLCV 미지원이므로 pykrx 우선)
    if PYKRX_OK:
        try:
            end = _today()
            start = _ndays_ago(days + 30)
            df = krx.get_market_ohlcv(start, end, code)
            if df is not None and not df.empty:
                df = df.rename(columns={"시가": "open", "고가": "high", "저가": "low",
                                        "종가": "close", "거래량": "volume"})
                df.index = pd.to_datetime(df.index)
                _logger.info(f"[OHLCV] pykrx 성공({code}): {len(df)}행")
                return df[["open", "high", "low", "close", "volume"]].tail(days)
        except Exception as e:
            _logger.warning(f"[OHLCV] pykrx 실패({code}): {e}")

    # 2순위: FinanceDataReader
    if FDR_OK:
        try:
            start = (datetime.today() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
            df = fdr.DataReader(code, start)
            if df is not None and not df.empty:
                df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                        "Close": "close", "Volume": "volume"})
                df.index = pd.to_datetime(df.index)
                _logger.info(f"[OHLCV] FDR 성공({code}): {len(df)}행")
                return df[["open", "high", "low", "close", "volume"]].tail(days)
        except Exception as e:
            _logger.warning(f"[OHLCV] FDR 실패({code}): {e}")

    # 3순위: KIS API (실전 계정에서만 동작)
    try:
        from kis_api import get_ohlcv as kis_ohlcv
        rows = kis_ohlcv(code, "D", days)
        if rows:
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            return df[["open", "high", "low", "close", "volume"]].tail(days)
    except Exception as e:
        _logger.warning(f"[OHLCV] KIS 실패({code}): {e}")

    return pd.DataFrame()


def _parse_naver_num(val) -> float:
    if not val:
        return 0.0
    return float(str(val).replace(",", "") or 0)

def _naver_current_price(code: str) -> dict:
    """네이버 모바일 주식 API — 시간외 단일가 우선, 없으면 정규장 종가"""
    try:
        import requests as _req
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"
        r = _req.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return {}
        d = r.json()
        regular_price = int(_parse_naver_num(d.get("closePrice")))
        regular_chg   = int(_parse_naver_num(d.get("compareToPreviousClosePrice")))
        regular_pct   = float(d.get("fluctuationsRatio") or 0)
        high = int(_parse_naver_num(d.get("highPrice")))
        low  = int(_parse_naver_num(d.get("lowPrice")))
        vol  = int(_parse_naver_num(d.get("accumulatedTradingVolume")))
        if regular_price <= 0:
            return {}
        # 시간외 단일가 확인
        over = d.get("overMarketPriceInfo") or {}
        over_price = int(_parse_naver_num(over.get("overPrice"))) if over else 0
        over_chg   = int(_parse_naver_num(over.get("compareToPreviousClosePrice"))) if over else 0
        over_pct   = float(over.get("fluctuationsRatio") or 0) if over else 0
        over_status = over.get("overMarketStatus", "") if over else ""
        # 시간외 가격 있으면 우선 사용 (PREOPEN=장전, OPEN=진행중, CLOSE=종료)
        if over_price > 0 and over_status in ("PREOPEN", "OPEN", "CLOSE"):
            _logger.info(f"[현재가] 네이버 시간외 성공({code}): {over_price} (정규장: {regular_price})")
            return {
                "current_price": over_price,
                "change":        over_chg,
                "change_pct":    over_pct,
                "high":          high,
                "low":           low,
                "volume":        vol,
            }
        _logger.info(f"[현재가] 네이버 정규장({code}): {regular_price}")
        return {
            "current_price": regular_price,
            "change":        regular_chg,
            "change_pct":    regular_pct,
            "high":          high,
            "low":           low,
            "volume":        vol,
        }
    except Exception as e:
        _logger.warning(f"[현재가] 네이버 실패({code}): {e}")
    return {}


def get_current_price(code: str) -> dict:
    """
    현재가 정보 반환
    1순위: 네이버 모바일 API (시간외 단일가 포함)
    2순위: KIS API (실시간)
    3순위: yfinance
    4순위: pykrx/FDR (종가 기반)
    """
    # 1순위: 네이버 모바일 API (시간외 포함)
    result = _naver_current_price(code)
    if result:
        return result

    # 2순위: KIS API 실시간
    try:
        from kis_api import get_current_price as kis_price
        result = kis_price(code)
        if result and result.get("current_price", 0) > 0:
            _logger.info(f"[현재가] KIS API 성공({code}): {result['current_price']}")
            return {
                "current_price": result["current_price"],
                "change":        result.get("change", 0),
                "change_pct":    result.get("change_pct", 0),
                "high":          result.get("high", 0),
                "low":           result.get("low", 0),
                "volume":        result.get("vol", 0),
            }
    except Exception as e:
        _logger.warning(f"[현재가] KIS API 실패({code}): {e}")

    # 2순위: yfinance (시간외 포함 최신가)
    try:
        import yfinance as yf
        t = yf.Ticker(f"{code}.KS")
        # prepost=True로 시간외 단일가(애프터) 포함한 최신 가격 조회
        hist = t.history(period="2d", prepost=True)
        fi = t.fast_info
        prev_close = fi.previous_close
        if hist is not None and not hist.empty and prev_close and prev_close > 0:
            cur = float(hist["Close"].iloc[-1])
            if cur > 0:
                chg = cur - prev_close
                chg_pct = chg / prev_close * 100
                high = float(hist["High"].iloc[-1])
                low  = float(hist["Low"].iloc[-1])
                vol  = int(hist["Volume"].iloc[-1])
                _logger.info(f"[현재가] yfinance 성공({code}): {int(cur)} (시간외 포함)")
                return {
                    "current_price": int(cur),
                    "change":        int(chg),
                    "change_pct":    round(chg_pct, 2),
                    "high":          int(high),
                    "low":           int(low),
                    "volume":        vol,
                }
    except Exception as e:
        _logger.warning(f"[현재가] yfinance 실패({code}): {e}")

    # 3순위: pykrx / FDR (종가 기반)
    df = get_ohlcv(code, days=5)
    if df is None or df.empty:
        return {}
    try:
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last
        cur = int(last["close"])
        chg = cur - int(prev["close"])
        chg_pct = chg / int(prev["close"]) * 100 if prev["close"] else 0
        return {
            "current_price": cur,
            "change":        chg,
            "change_pct":    round(chg_pct, 2),
            "high":          int(last["high"]),
            "low":           int(last["low"]),
            "volume":        int(last["volume"]),
        }
    except:
        return {}


# ─────────────────────────────────────────────────────────
# 외국인 / 기관 / 개인 수급
# ─────────────────────────────────────────────────────────
# pykrx get_market_trading_volume_by_date 반환 컬럼:
#   기관합계, 기타법인, 개인, 외국인합계, 전체  (단위: 주, 순매수=양수)
_INVESTOR_COL_MAP = {"외국인합계": "외국인", "기관합계": "기관"}
_INVESTOR_NEEDED  = ["외국인합계", "기관합계", "개인"]


def get_investor_trading(code: str, days: int = 25) -> pd.DataFrame:
    """
    종목별 투자자 순매수량 (일별).
    1순위: KIS API (Streamlit Cloud에서도 동작)
    2순위: pykrx (로컬/한국 IP 전용)
    """
    # 1순위: KIS API
    try:
        from kis_api import get_investor_trading as kis_investor
        rows = kis_investor(code, days)
        if rows:
            records = []
            for r in rows:
                records.append({
                    "날짜":    pd.to_datetime(r["date"], format="%Y%m%d"),
                    "외국인":  r.get("foreign_net", 0),
                    "기관":    r.get("institution_net", 0),
                })
            df = pd.DataFrame(records).set_index("날짜").sort_index()
            _logger.info(f"[수급] KIS API 성공({code}): {len(df)}행, 최신={df.index[-1].date()}")
            return df.tail(days)
    except Exception as e:
        _logger.warning(f"[수급] KIS API 실패({code}): {e}")

    # 2순위: pykrx (한국 IP에서만 동작)
    if not PYKRX_OK:
        return pd.DataFrame()
    try:
        end   = _last_trading_date()   # 주말이면 마지막 거래일 사용
        start = _ndays_ago(days + 15)
        df = krx.get_market_trading_volume_by_date(start, end, code, on="순매수")
        if df is None or df.empty:
            return pd.DataFrame()
        available = [c for c in _INVESTOR_NEEDED if c in df.columns]
        if not available:
            return pd.DataFrame()
        result = df[available].rename(columns=_INVESTOR_COL_MAP)
        result.index = pd.to_datetime(result.index)
        return result.tail(days)
    except Exception as e:
        _logger.warning("[수급] pykrx 실패 | code=%s | %s", code, e)
        return pd.DataFrame()


def get_kospi_investor_value(days: int = 25) -> pd.DataFrame:
    """
    KOSPI 외국인·기관 일별 순매수 거래대금.
    1순위: get_kospi_investor() 재사용, 2순위: pykrx
    """
    # 1순위: get_kospi_investor 결과 재활용
    try:
        df = get_kospi_investor(days)
        if df is not None and not df.empty:
            cols = [c for c in ["외국인", "기관"] if c in df.columns]
            if cols:
                return df[cols]
    except:
        pass

    # 2순위: pykrx
    if not PYKRX_OK:
        return pd.DataFrame()
    end   = _last_trading_date()
    start = _ndays_ago(days + 15)
    try:
        df = krx.get_market_trading_value_by_date(start, end, "KOSPI")
        if df is None or df.empty:
            return pd.DataFrame()
        col_map = {}
        for c in df.columns:
            if "외국인" in c: col_map["외국인"] = c
            elif "기관" in c: col_map["기관"] = c
        if len(col_map) < 2:
            return pd.DataFrame()
        out = df[[col_map["외국인"], col_map["기관"]]].copy()
        out.columns = ["외국인", "기관"]
        out.index = pd.to_datetime(out.index)
        return out.tail(days)
    except Exception as exc:
        _logger.error("[수급] pykrx 실패 | %s", exc)
        return pd.DataFrame()


def get_kospi_investor(days: int = 25) -> pd.DataFrame:
    """KOSPI 전체 외국인/기관/개인 순매수 (홈 수급 탭용)
    1순위: KIS API, 2순위: pykrx
    """
    # 1순위: KIS API — 거래대금(백만원) 기준으로 KOSPI 수급 추정
    try:
        from kis_api import get_investor_trading_value as kis_inv_val
        rows = kis_inv_val("005930", days)  # 삼성전자 거래대금 기준
        # 값이 모두 0이면 필드 미지원 → pykrx로 폴백
        if rows and any(abs(r.get("foreign_net", 0)) > 0 for r in rows):
            records = [{"날짜": pd.to_datetime(r["date"], format="%Y%m%d"),
                        "외국인": r.get("foreign_net", 0),   # 백만원 단위
                        "기관":   r.get("institution_net", 0)} for r in rows]
            df = pd.DataFrame(records).set_index("날짜").sort_index()
            _logger.info(f"[수급-KOSPI] KIS 금액 성공: {len(df)}행, 최신날짜={df.index[-1].date()}")
            return df.tail(days)
        else:
            raise ValueError("KIS 수급 금액 필드 0 또는 미지원 → pykrx 폴백")
    except Exception as e:
        _logger.warning(f"[수급-KOSPI] KIS API 실패: {e}")

    # 2순위: KIS 수량(주) 기반 — 거래대금 필드 미지원 시 수량으로 폴백
    try:
        from kis_api import get_investor_trading as kis_inv_qty
        rows = kis_inv_qty("005930", days)
        if rows and any(abs(r.get("foreign_net", 0)) > 0 for r in rows):
            records = [{"날짜": pd.to_datetime(r["date"], format="%Y%m%d"),
                        "외국인": r.get("foreign_net", 0),
                        "기관":   r.get("institution_net", 0),
                        "_unit": "qty"} for r in rows]
            df = pd.DataFrame(records).set_index("날짜").sort_index()
            _logger.info(f"[수급-KOSPI] KIS 수량 폴백 성공: {len(df)}행, 최신날짜={df.index[-1].date()}")
            return df.tail(days)
    except Exception as e:
        _logger.warning(f"[수급-KOSPI] KIS 수량 폴백 실패: {e}")

    if not PYKRX_OK:
        _logger.error("[수급-KOSPI] pykrx 미설치")
        return pd.DataFrame()

    end   = _last_trading_date()
    start = _ndays_ago(days + 15)

    # pykrx 거래대금(원) 버전 우선
    try:
        df = krx.get_market_trading_value_by_date(start, end, "KOSPI")
        if df is not None and not df.empty:
            col_map = {}
            for c in df.columns:
                if "외국인" in c: col_map["외국인"] = c
                elif "기관" in c: col_map["기관"] = c
            if len(col_map) >= 2:
                result = df[[col_map["외국인"], col_map["기관"]]].copy()
                result.columns = ["외국인", "기관"]
                result.index = pd.to_datetime(result.index)
                result = result.sort_index()
                result["_unit"] = "won"
                _logger.info("[수급-KOSPI] pykrx 거래대금 성공, 최신=%s", result.index[-1].date())
                return result.tail(days)
    except Exception as exc:
        _logger.warning("[수급-KOSPI] pykrx 거래대금 실패 | %s", exc)

    # pykrx 거래량(주) 버전 폴백
    try:
        df = krx.get_market_trading_volume_by_date(
            start, end, "KOSPI", on="순매수"
        )
    except Exception as exc:
        _logger.error("[수급-KOSPI] API 호출 실패 | %s", exc)
        _logger.debug(traceback.format_exc())
        return pd.DataFrame()

    if df is None or df.empty:
        _logger.warning("[수급-KOSPI] 빈 응답")
        return pd.DataFrame()

    _logger.info("[수급-KOSPI] 응답 컬럼: %s", list(df.columns))
    available = [c for c in _INVESTOR_NEEDED if c in df.columns]
    if not available:
        return pd.DataFrame()

    result = df[available].rename(columns=_INVESTOR_COL_MAP)
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()
    result["_unit"] = "qty"
    _logger.info("[수급-KOSPI] 성공 | rows=%d, 최신=%s", len(result), result.index[-1].date())
    return result.tail(days)


# ─────────────────────────────────────────────────────────
# 스캐너: 시가총액 상위 종목 목록
# ─────────────────────────────────────────────────────────
def get_top_stocks(n: int = 200) -> list:
    """
    시가총액 상위 N개 종목 리스트
    1순위: KIS API (Streamlit Cloud도 가능)
    2순위: pykrx (한국 IP)
    3순위: FDR
    4순위: 하드코딩 50개
    """
    # 1순위: KIS API (해외 IP 차단 없음)
    try:
        from kis_api import get_top_stocks_by_cap
        kospi  = get_top_stocks_by_cap("J", n // 2)
        kosdaq = get_top_stocks_by_cap("Q", n // 2)
        result = kospi + kosdaq
        if result:
            result.sort(key=lambda x: x["market_cap"], reverse=True)
            _logger.info(f"[종목목록] KIS API 성공: {len(result)}개")
            return _supplement_with_fallback(result, n)
    except Exception as e:
        _logger.warning(f"[종목목록] KIS API 실패: {e}")

    # 2순위: pykrx
    if PYKRX_OK:
        try:
            tdate = _last_trading_date()
            result = []
            for market in ["KOSPI", "KOSDAQ"]:
                df = krx.get_market_cap_by_ticker(tdate, market=market)
                if df is None or df.empty:
                    continue
                df = df.sort_values("시가총액", ascending=False).head(n // 2)
                for code, row in df.iterrows():
                    result.append({
                        "code": str(code),
                        "name": krx.get_market_ticker_name(str(code)),
                        "market": market,
                        "market_cap": int(row["시가총액"]),
                    })
            if result:
                result.sort(key=lambda x: x["market_cap"], reverse=True)
                return _supplement_with_fallback(result, n)
        except:
            pass

    # 3순위: FDR (Streamlit Cloud에서도 동작)
    if FDR_OK:
        try:
            listing = fdr.StockListing("KRX")
            if listing is not None and not listing.empty:
                cap_col = next((c for c in listing.columns if "cap" in c.lower() or "시가총액" in c), None)
                if cap_col:
                    listing = listing.sort_values(cap_col, ascending=False)
                result = []
                for _, row in listing.head(n).iterrows():
                    code = str(row.get("Code", row.get("Symbol", ""))).zfill(6)
                    name = str(row.get("Name", code))
                    market = str(row.get("Market", "KOSPI"))
                    result.append({"code": code, "name": name, "market": market, "market_cap": 0})
                if result:
                    return _supplement_with_fallback(result, n)
        except Exception as e:
            _logger.warning(f"[종목목록] FDR 실패: {e}")

    # 최종: 시총 상위 종목 하드코딩 (해외 IP 차단 대비 — 항상 보충)
    _TOP_STOCKS_FALLBACK = [
        ("005930","삼성전자","KOSPI"),("000660","SK하이닉스","KOSPI"),
        ("373220","LG에너지솔루션","KOSPI"),("207940","삼성바이오로직스","KOSPI"),
        ("005380","현대차","KOSPI"),("000270","기아","KOSPI"),
        ("068270","셀트리온","KOSPI"),("105560","KB금융","KOSPI"),
        ("055550","신한지주","KOSPI"),("012330","현대모비스","KOSPI"),
        ("035420","NAVER","KOSPI"),("051910","LG화학","KOSPI"),
        ("006400","삼성SDI","KOSPI"),("003550","LG","KOSPI"),
        ("096770","SK이노베이션","KOSPI"),("034730","SK","KOSPI"),
        ("028260","삼성물산","KOSPI"),("017670","SK텔레콤","KOSPI"),
        ("030200","KT","KOSPI"),("032830","삼성생명","KOSPI"),
        ("012450","한화에어로스페이스","KOSPI"),("047810","한국항공우주","KOSPI"),
        ("042660","한화오션","KOSPI"),("009830","한화솔루션","KOSPI"),
        ("011200","HMM","KOSPI"),("066570","LG전자","KOSPI"),
        ("003490","대한항공","KOSPI"),("086790","하나금융지주","KOSPI"),
        ("138040","메리츠금융지주","KOSPI"),("009150","삼성전기","KOSPI"),
        ("018260","삼성에스디에스","KOSPI"),("010950","S-Oil","KOSPI"),
        ("000810","삼성화재","KOSPI"),("024110","기업은행","KOSPI"),
        ("316140","우리금융지주","KOSPI"),("039490","키움증권","KOSPI"),
        ("035720","카카오","KOSPI"),("259960","크래프톤","KOSPI"),
        ("036570","엔씨소프트","KOSPI"),("251270","넷마블","KOSPI"),
        ("041510","에스엠","KOSPI"),("352820","하이브","KOSPI"),
        # 코스닥 상위
        ("247540","에코프로비엠","KOSDAQ"),("086520","에코프로","KOSDAQ"),
        ("006280","녹십자","KOSDAQ"),("091990","셀트리온헬스케어","KOSDAQ"),
        ("196170","알테오젠","KOSDAQ"),("263750","펄어비스","KOSDAQ"),
        ("112040","위메이드","KOSDAQ"),("214150","클래시스","KOSDAQ"),
        ("028300","HLB","KOSDAQ"),("145020","휴젤","KOSDAQ"),
    ]
    fallback = [{"code": c, "name": nm, "market": m, "market_cap": 0}
                for c, nm, m in _TOP_STOCKS_FALLBACK]
    return fallback[:n]


def _supplement_with_fallback(result: list, n: int) -> list:
    """result가 n개 미만이면 하드코딩 fallback으로 보충"""
    if len(result) >= n:
        return result[:n]
    existing_codes = {s["code"] for s in result}
    _FALLBACK = [
        ("005930","삼성전자","KOSPI"),("000660","SK하이닉스","KOSPI"),
        ("373220","LG에너지솔루션","KOSPI"),("207940","삼성바이오로직스","KOSPI"),
        ("005380","현대차","KOSPI"),("000270","기아","KOSPI"),
        ("068270","셀트리온","KOSPI"),("105560","KB금융","KOSPI"),
        ("055550","신한지주","KOSPI"),("012330","현대모비스","KOSPI"),
        ("035420","NAVER","KOSPI"),("051910","LG화학","KOSPI"),
        ("006400","삼성SDI","KOSPI"),("003550","LG","KOSPI"),
        ("096770","SK이노베이션","KOSPI"),("034730","SK","KOSPI"),
        ("028260","삼성물산","KOSPI"),("017670","SK텔레콤","KOSPI"),
        ("030200","KT","KOSPI"),("032830","삼성생명","KOSPI"),
        ("012450","한화에어로스페이스","KOSPI"),("047810","한국항공우주","KOSPI"),
        ("042660","한화오션","KOSPI"),("009830","한화솔루션","KOSPI"),
        ("066570","LG전자","KOSPI"),("003490","대한항공","KOSPI"),
        ("086790","하나금융지주","KOSPI"),("138040","메리츠금융지주","KOSPI"),
        ("035720","카카오","KOSPI"),("259960","크래프톤","KOSPI"),
        ("247540","에코프로비엠","KOSDAQ"),("086520","에코프로","KOSDAQ"),
        ("196170","알테오젠","KOSDAQ"),("263750","펄어비스","KOSDAQ"),
        ("028300","HLB","KOSDAQ"),("145020","휴젤","KOSDAQ"),
        ("214150","클래시스","KOSDAQ"),("091990","셀트리온헬스케어","KOSDAQ"),
        ("352820","하이브","KOSPI"),("041510","에스엠","KOSPI"),
    ]
    for c, nm, m in _FALLBACK:
        if c not in existing_codes and len(result) < n:
            result.append({"code": c, "name": nm, "market": m, "market_cap": 0})
            existing_codes.add(c)
    return result[:n]


# ─────────────────────────────────────────────────────────
# 지수 OHLCV 히스토리 (이동평균선 계산용)
# yfinance 기반: ^KS11=KOSPI, ^KQ11=KOSDAQ
# ─────────────────────────────────────────────────────────
_INDEX_TICKER = {"1001": "^KS11", "2001": "^KQ11"}

def get_index_ohlcv_history(index_code: str = "1001", days: int = 120) -> pd.DataFrame:
    """
    지수 OHLCV 히스토리 반환 (이동평균선 계산용).
    index_code: "1001"=KOSPI, "2001"=KOSDAQ
    Returns: DataFrame with '종가' column, datetime index
    """
    ticker = _INDEX_TICKER.get(index_code, "^KS11")
    try:
        import yfinance as yf
        # 충분한 기간 확보 (주말·공휴일 제외 120 영업일 = 약 6개월)
        df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        # yfinance MultiIndex 컬럼 평탄화
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        # '종가' 컬럼으로 통일
        if "Close" in df.columns:
            df = df.rename(columns={"Close": "종가", "Open": "시가",
                                    "High": "고가", "Low": "저가",
                                    "Volume": "거래량"})
        df.index = pd.to_datetime(df.index)
        return df.tail(days)
    except Exception as e:
        _logger.warning(f"[지수 히스토리] yfinance 실패({ticker}): {e}")
        return pd.DataFrame()


def get_sector_performance() -> list:
    """
    주요 섹터 대표 종목들로 섹터 등락률 계산.
    1순위: KIS API / yfinance (Streamlit Cloud 가능)
    2순위: pykrx
    """
    sectors = {
        "반도체": ["005930", "000660"],
        "방산":   ["012450", "047810"],
        "로봇":   ["215600", "166090"],
        "2차전지":["373220", "051910"],
        "바이오": ["207940", "068270"],
        "금융":   ["105560", "055550"],
    }
    result = []
    for sector_name, codes in sectors.items():
        pcts = []
        for code in codes:
            try:
                # get_current_price는 KIS→yfinance→pykrx 순으로 이미 처리
                info = get_current_price(code)
                if info and info.get("change_pct") is not None:
                    pcts.append(info["change_pct"])
            except Exception:
                pass
        if pcts:
            result.append({"name": sector_name, "pct": round(sum(pcts) / len(pcts), 2)})
    result.sort(key=lambda x: x["pct"], reverse=True)
    return result


# ─────────────────────────────────────────────────────────
# 전체 시장 당일 데이터 (스캐너 빠른 조회용)
# ─────────────────────────────────────────────────────────
def get_market_snapshot(market: str = "KOSPI") -> pd.DataFrame:
    """
    당일 전 종목 OHLCV + 거래량 한번에 조회
    Returns: DataFrame indexed by ticker
    """
    if not PYKRX_OK:
        return pd.DataFrame()
    try:
        tdate = _last_trading_date()
        df = krx.get_market_ohlcv_by_ticker(tdate, market=market)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

