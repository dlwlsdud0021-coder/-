# diagnose_investor.py — 수급 데이터 원인 분석 스크립트
# 실행: python diagnose_investor.py
from pykrx.website.krx.market.ticker import StockTicker, get_stock_ticker_isin
from pykrx.website.krx.market.core import 투자자별_거래실적_개별종목_일별추이_일반
from pykrx import stock as krx
from datetime import datetime, timedelta
import traceback

CODE  = "005930"
END   = datetime.today().strftime("%Y%m%d")
START = (datetime.today() - timedelta(days=40)).strftime("%Y%m%d")

print("=" * 60)
print(f"진단 대상 종목: {CODE}")
print(f"조회 기간: {START} ~ {END}")
print("=" * 60)

print()
print("[1] StockTicker().get('005930') 결과")
try:
    s = StockTicker().get(CODE)
    print("  반환값 타입:", type(s))
    print("  반환값:", s)
except Exception as e:
    print("  예외:", type(e).__name__, e)
    traceback.print_exc()

print()
print("[2] get_stock_ticker_isin('005930') 결과")
try:
    isin = get_stock_ticker_isin(CODE)
    print("  반환값 타입:", type(isin))
    print("  반환값:", isin)
except Exception as e:
    print("  예외:", type(e).__name__, e)
    traceback.print_exc()

print()
print("[3] StockTicker().listed 상태")
try:
    st = StockTicker()
    print("  listed shape:", st.listed.shape)
    print("  listed columns:", list(st.listed.columns))
    print("  '005930' in index:", CODE in st.listed.index)
    if CODE in st.listed.index:
        print("  005930 행:", st.listed.loc[CODE])
    else:
        print("  ※ '005930'이 listed index에 없음")
        print("  delisted shape:", st.delisted.shape)
        print("  '005930' in delisted:", CODE in st.delisted.index)
except Exception as e:
    print("  예외:", type(e).__name__, e)
    traceback.print_exc()

print()
print("[4] 투자자별_거래실적_개별종목_일별추이_일반().fetch() 직접 호출")
try:
    isin = get_stock_ticker_isin(CODE)
    print("  전달 ISIN:", repr(isin), "| 타입:", type(isin))
    df_raw = 투자자별_거래실적_개별종목_일별추이_일반().fetch(
        START, END, isin, 1, 3   # 1=거래량, 3=순매수
    )
    print("  shape:", df_raw.shape)
    print("  columns:", list(df_raw.columns))
    print("  empty?:", df_raw.empty)
    if not df_raw.empty:
        print(df_raw.head(3).to_string())
    else:
        print("  ※ fetch() 결과가 빈 DataFrame")
except Exception as e:
    print("  예외:", type(e).__name__, e)
    traceback.print_exc()

print()
print("[5] krx.get_market_trading_volume_by_date() 최종 결과")
try:
    df_final = krx.get_market_trading_volume_by_date(START, END, CODE, on="순매수")
    print("  shape:", df_final.shape)
    print("  columns:", list(df_final.columns))
    print("  empty?:", df_final.empty)
    if not df_final.empty:
        print(df_final.tail(3).to_string())
    else:
        print("  ※ 최종 결과가 빈 DataFrame")
except Exception as e:
    print("  예외:", type(e).__name__, e)
    traceback.print_exc()

print()
print("=" * 60)
print("진단 완료")
print("=" * 60)
