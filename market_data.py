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
except ImportError:
    import types, sys
    pkg = types.ModuleType("pkg_resources")
    pkg.get_distribution = lambda name: None
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
@st.cache_data(ttl=86400)
def get_stock_name(code: str) -> str:
    """종목코드 → 종목명"""
    if PYKRX_OK:
        try:
            name = krx.get_market_ticker_name(code)
            return name if name else code
        except:
            pass
    if FDR_OK:
        try:
            listing = fdr.StockListing("KRX")
            row = listing[listing["Code"] == code]
            if not row.empty:
                return row.iloc[0]["Name"]
        except:
            pass
    return code


@st.cache_data(ttl=86400)
def get_all_tickers() -> dict:
    """코스피+코스닥 전 종목 {code: name}"""
    if PYKRX_OK:
        try:
            tdate = _last_trading_date()
            kospi = krx.get_market_ticker_list(tdate, market="KOSPI")
            kosdaq = krx.get_market_ticker_list(tdate, market="KOSDAQ")
            result = {}
            for c in kospi + kosdaq:
                result[c] = krx.get_market_ticker_name(c)
            return result
        except:
            pass
    if FDR_OK:
        try:
            listing = fdr.StockListing("KRX")
            return dict(zip(listing["Code"].astype(str), listing["Name"]))
        except:
            pass
    return {}


# ─────────────────────────────────────────────────────────
# 국내 지수 (KOSPI / KOSDAQ) — yfinance 기반
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=180)  # 3분 캐시 (장중 실시간 반영)
def get_index_data() -> dict:
    """
    Returns:
        {
          "KOSPI": {current, change, change_pct, volume_billion},
          "KOSDAQ": {...},
        }
    yfinance ^KS11(KOSPI) / ^KQ11(KOSDAQ) 사용.
    """
    # 1차: pykrx
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
                prev = float(df["종가"].iloc[-2])
                chg  = cur - prev
                chg_pct = chg / prev * 100
                vol  = float(df["거래량"].iloc[-1]) if "거래량" in df.columns else 0
                result[name] = {
                    "current":        round(cur, 2),
                    "change":         round(chg, 2),
                    "change_pct":     round(chg_pct, 2),
                    "volume_billion": round(vol / 1e8, 1),
                }
            if len(result) == 2:
                return result
        except Exception as e:
            _logger.warning(f"[지수] pykrx 실패, yfinance로 전환: {e}")

    # 2차: yfinance 폴백
    try:
        import yfinance as yf
        result = {}
        for name, ticker in [("KOSPI", "^KS11"), ("KOSDAQ", "^KQ11")]:
            df = yf.download(ticker, period="5d", interval="1d",
                             progress=False, auto_adjust=True)
            if df is None or df.empty:
                result[name] = _dummy_index()[name]
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            if len(df) < 2:
                result[name] = _dummy_index()[name]
                continue
            cur  = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg  = cur - prev
            chg_pct = chg / prev * 100
            result[name] = {
                "current":        round(cur, 2),
                "change":         round(chg, 2),
                "change_pct":     round(chg_pct, 2),
                "volume_billion": 0,
            }
        return result
    except Exception as e:
        _logger.warning(f"[지수] yfinance 실패: {e}")
        return _dummy_index()


def _dummy_index():
    return {
        "KOSPI":  {"current": 0, "change": 0, "change_pct": 0, "volume_billion": 0},
        "KOSDAQ": {"current": 0, "change": 0, "change_pct": 0, "volume_billion": 0},
    }


# ─────────────────────────────────────────────────────────
# 미국 지수 (S&P500, 나스닥, 다우)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600)  # 10분 캐시
def get_us_indices() -> dict:
    try:
        import yfinance as yf
        from datetime import datetime, timezone, timedelta

        # 한국 시간 기준 23:30 이후면 미국 장 열림 → 실시간, 이전이면 전일 종가
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        us_market_open = now_kst.replace(hour=23, minute=30, second=0, microsecond=0)
        is_us_open = now_kst >= us_market_open

        result = {}
        symbols = {"S&P500": "^GSPC", "나스닥": "^IXIC", "다우": "^DJI"}
        for name, sym in symbols.items():
            t = yf.Ticker(sym)
            if is_us_open:
                # 장중: 1분봉으로 현재가
                hist_intra = t.history(period="1d", interval="1m")
                hist_daily = t.history(period="5d", interval="1d")
                if hist_intra.empty or len(hist_daily) < 2:
                    result[name] = {"current": 0, "change_pct": 0}
                    continue
                cur = float(hist_intra["Close"].iloc[-1])
                prev = float(hist_daily["Close"].iloc[-2])
            else:
                # 장마감: 최근 2일 일봉 (전일 종가 기준)
                hist = t.history(period="5d", interval="1d")
                if len(hist) < 2:
                    result[name] = {"current": 0, "change_pct": 0}
                    continue
                cur = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
            pct = (cur - prev) / prev * 100
            result[name] = {"current": round(cur, 2), "change_pct": round(pct, 2)}
        return result
    except:
        return {"S&P500": {"current": 0, "change_pct": 0},
                "나스닥":  {"current": 0, "change_pct": 0},
                "다우":    {"current": 0, "change_pct": 0}}


# ─────────────────────────────────────────────────────────
# 종목 OHLCV
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_ohlcv(code: str, days: int = 120) -> pd.DataFrame:
    """
    Returns DataFrame with columns: open, high, low, close, volume
    최신 날짜가 마지막 행
    """
    # 1차: pykrx
    if PYKRX_OK:
        try:
            end = _today()
            start = _ndays_ago(days + 30)
            df = krx.get_market_ohlcv(start, end, code)
            if df is not None and not df.empty:
                df = df.rename(columns={"시가": "open", "고가": "high", "저가": "low",
                                        "종가": "close", "거래량": "volume"})
                df.index = pd.to_datetime(df.index)
                return df.tail(days)
        except:
            pass
    # 2차: FinanceDataReader
    if FDR_OK:
        try:
            start = (datetime.today() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
            df = fdr.DataReader(code, start)
            if df is not None and not df.empty:
                df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                        "Close": "close", "Volume": "volume"})
                df.index = pd.to_datetime(df.index)
                return df[["open", "high", "low", "close", "volume"]].tail(days)
        except:
            pass
    return pd.DataFrame()


@st.cache_data(ttl=300)
def get_current_price(code: str) -> dict:
    """
    현재가 정보 반환
    Returns: {current_price, change, change_pct, high, low, volume}
    """
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
            "change": chg,
            "change_pct": round(chg_pct, 2),
            "high": int(last["high"]),
            "low": int(last["low"]),
            "volume": int(last["volume"]),
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


@st.cache_data(ttl=600)
def get_investor_trading(code: str, days: int = 25) -> pd.DataFrame:
    """
    종목별 투자자 순매수량 (일별)
    Returns DataFrame: index=날짜, columns=[외국인, 기관, 개인]
    양수=순매수, 음수=순매도 (단위: 주)
    실패 시 빈 DataFrame 반환 + 로그/화면 디버그 출력
    """
    _logger.info("[수급] 조회 시작 | code=%s days=%d", code, days)

    if not PYKRX_OK:
        _logger.error("[수급] pykrx 미설치 — import 실패")
        return pd.DataFrame()

    end   = _today()
    start = _ndays_ago(days + 15)
    _logger.info("[수급] 조회 기간: %s ~ %s", start, end)
    _logger.info("[수급] 데이터 소스: pykrx get_market_trading_volume_by_date")
    _logger.info("[수급] URL: https://data.krx.co.kr (KRX 공식)")

    try:
        df = krx.get_market_trading_volume_by_date(
            start, end, code, on="순매수"
        )
    except Exception as exc:
        err_msg = traceback.format_exc()
        _logger.error("[수급] API 호출 실패 | code=%s | %s", code, exc)
        _logger.debug("[수급] 상세 traceback:\n%s", err_msg)
        with st.expander(f"🔴 수급 데이터 조회 실패 — {code}", expanded=False):
            st.markdown(f"""
**데이터 소스:** pykrx `get_market_trading_volume_by_date`
**조회 URL:** `https://data.krx.co.kr`
**조회 기간:** `{start}` ~ `{end}`
**실패 원인:** `{type(exc).__name__}: {exc}`
""")
            st.code(err_msg, language="text")
        return pd.DataFrame()

    # ── 빈 응답 처리 ──
    if df is None or df.empty:
        _logger.warning("[수급] 응답 비어있음 | code=%s start=%s end=%s", code, start, end)
        with st.expander(f"⚠️ 수급 데이터 없음 — {code}", expanded=False):
            st.markdown(f"""
**데이터 소스:** pykrx `get_market_trading_volume_by_date`
**조회 기간:** `{start}` ~ `{end}`
**결과:** 빈 DataFrame (해당 기간 데이터 없음)
""")
        return pd.DataFrame()

    # ── 컬럼 확인 ──
    _logger.info("[수급] 응답 컬럼: %s | shape: %s", list(df.columns), df.shape)
    missing = [c for c in _INVESTOR_NEEDED if c not in df.columns]
    if missing:
        _logger.warning("[수급] 필요 컬럼 누락: %s | 실제 컬럼: %s", missing, list(df.columns))
        with st.expander(f"⚠️ 수급 컬럼 불일치 — {code}", expanded=False):
            st.markdown(f"""
**필요한 컬럼:** `{_INVESTOR_NEEDED}`
**실제 반환 컬럼:** `{list(df.columns)}`
**누락 컬럼:** `{missing}`
""")
            st.dataframe(df.tail(3))

    # ── 존재하는 컬럼만 선택 ──
    available = [c for c in _INVESTOR_NEEDED if c in df.columns]
    if not available:
        _logger.error("[수급] 사용 가능한 컬럼 없음 | code=%s", code)
        return pd.DataFrame()

    result = df[available].rename(columns=_INVESTOR_COL_MAP)
    result.index = pd.to_datetime(result.index)
    result = result.tail(days)

    _logger.info("[수급] 조회 성공 | code=%s | rows=%d | cols=%s",
                 code, len(result), list(result.columns))
    return result


@st.cache_data(ttl=600)
def get_kospi_investor_value(days: int = 25) -> pd.DataFrame:
    """
    KOSPI 외국인·기관 일별 순매수 거래대금 (원 단위).
    pykrx get_market_trading_value_by_date('KOSPI') 사용.
    Returns: DataFrame, index=날짜, columns=[외국인, 기관]  (단위: 원)
    """
    if not PYKRX_OK:
        _logger.error("[수급] pykrx 미설치")
        return pd.DataFrame()

    end   = _today()
    start = _ndays_ago(days + 15)

    try:
        df = krx.get_market_trading_value_by_date(start, end, "KOSPI")
    except Exception as exc:
        _logger.error("[수급] API 호출 실패 | %s", exc)
        return pd.DataFrame()

    if df is None or df.empty:
        _logger.warning("[수급] 빈 응답")
        return pd.DataFrame()

    # 외국인합계 / 기관합계 컬럼 추출
    col_map = {}
    for c in df.columns:
        if "외국인" in c:
            col_map["외국인"] = c
        elif "기관" in c:
            col_map["기관"] = c

    if len(col_map) < 2:
        _logger.warning("[수급] 컬럼 없음: %s", df.columns.tolist())
        return pd.DataFrame()

    out = df[[col_map["외국인"], col_map["기관"]]].copy()
    out.columns = ["외국인", "기관"]
    out.index = pd.to_datetime(out.index)
    _logger.info("[수급] 성공 | rows=%d", len(out))
    return out.tail(days)


@st.cache_data(ttl=600)
def get_kospi_investor(days: int = 25) -> pd.DataFrame:
    """KOSPI 전체 외국인/기관/개인 순매수 (홈 수급 탭용)"""
    _logger.info("[수급-KOSPI] 조회 시작 | days=%d", days)

    if not PYKRX_OK:
        _logger.error("[수급-KOSPI] pykrx 미설치")
        return pd.DataFrame()

    end   = _today()
    start = _ndays_ago(days + 15)

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
    _logger.info("[수급-KOSPI] 성공 | rows=%d", len(result))
    return result.tail(days)


# ─────────────────────────────────────────────────────────
# 스캐너: 시가총액 상위 종목 목록
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)  # 1시간 캐시 (자주 안 바뀜)
def get_top_stocks(n: int = 200) -> list:
    """
    시가총액 상위 N개 종목 리스트
    Returns: [{"code": ..., "name": ..., "market": ..., "market_cap": ...}, ...]
    """
    if not PYKRX_OK:
        return []
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
        result.sort(key=lambda x: x["market_cap"], reverse=True)
        return result[:n]
    except:
        return []


# ─────────────────────────────────────────────────────────
# 지수 OHLCV 히스토리 (이동평균선 계산용)
# yfinance 기반: ^KS11=KOSPI, ^KQ11=KOSDAQ
# ─────────────────────────────────────────────────────────
_INDEX_TICKER = {"1001": "^KS11", "2001": "^KQ11"}

@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=600)
def get_sector_performance() -> list:
    """
    주요 섹터 대표 종목들로 섹터 등락률 계산.
    Returns: [{"name": str, "pct": float}, ...] 내림차순 정렬
    """
    sectors = {
        "반도체": ["005930", "000660"],   # 삼성전자, SK하이닉스
        "방산":   ["012450", "047810"],   # 한화에어로, 한국항공우주
        "로봇":   ["215600", "166090"],   # 로보스타, 하나머티리얼즈
        "2차전지":["373220", "051910"],   # LG에너지솔루션, LG화학
        "바이오": ["207940", "068270"],   # 삼성바이오, 셀트리온
        "금융":   ["105560", "055550"],   # KB금융, 신한지주
    }
    result = []
    try:
        from datetime import date, timedelta
        end   = date.today().strftime("%Y%m%d")
        start = (date.today() - timedelta(days=5)).strftime("%Y%m%d")
        for sector_name, codes in sectors.items():
            pcts = []
            for code in codes:
                try:
                    df = krx.get_market_ohlcv_by_date(start, end, code)
                    if df is None or df.empty or len(df) < 2:
                        continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [c[0] for c in df.columns]
                    close_col = "종가" if "종가" in df.columns else "Close"
                    cur  = float(df[close_col].iloc[-1])
                    prev = float(df[close_col].iloc[-2])
                    pcts.append((cur - prev) / prev * 100)
                except Exception:
                    pass
            if pcts:
                result.append({"name": sector_name, "pct": round(sum(pcts) / len(pcts), 2)})
    except Exception:
        pass
    result.sort(key=lambda x: x["pct"], reverse=True)
    return result


# ─────────────────────────────────────────────────────────
# 전체 시장 당일 데이터 (스캐너 빠른 조회용)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
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
