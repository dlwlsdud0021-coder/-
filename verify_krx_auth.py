# verify_krx_auth.py — KRX 인증 + 수급 데이터 조회 검증
# 실행: python verify_krx_auth.py
#
# 사전 준비:
#   Windows PowerShell:
#     $env:KRX_ID = "내아이디"
#     $env:KRX_PW = "내비밀번호"
#   또는 .env 파일 없이 직접 환경변수 설정 후 실행

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("krx_verify")

print("=" * 60)
print("KRX 인증 + 수급 데이터 검증 스크립트")
print("=" * 60)

# ── [1] 환경변수 확인 ─────────────────────────────────────
print()
print("[1] 환경변수 확인")

KRX_ID = os.environ.get("KRX_ID", "")
KRX_PW = os.environ.get("KRX_PW", "")

if not KRX_ID or not KRX_PW:
    print()
    print("  ❌ KRX_ID 또는 KRX_PW 환경변수가 설정되어 있지 않습니다.")
    print()
    print("  설정 방법 (PowerShell):")
    print('    $env:KRX_ID = "내아이디"')
    print('    $env:KRX_PW = "내비밀번호"')
    print()
    print("  설정 방법 (CMD):")
    print('    set KRX_ID=내아이디')
    print('    set KRX_PW=내비밀번호')
    print()
    print("  환경변수 설정 후 다시 실행해주세요.")
    sys.exit(1)

log.info("KRX_ID 설정 확인: %s (길이: %d)", KRX_ID[:2] + "***", len(KRX_ID))
log.info("KRX_PW 설정 확인: *** (길이: %d)", len(KRX_PW))
print("  ✅ 환경변수 확인 완료")

# ── [2] pykrx import (환경변수 설정된 상태에서) ────────────
print()
print("[2] pykrx 인증 시도")
try:
    from pykrx import stock as krx
    log.info("pykrx import 완료")
except Exception as e:
    log.error("pykrx import 실패: %s", e)
    traceback.print_exc()
    sys.exit(1)

# ── [3] krxs 세션 인증 상태 직접 확인 ─────────────────────
print()
print("[3] KRX 세션(krxs) 상태 확인")
try:
    from pykrx.website.comm.webio import krxs
    headers = krxs.get_headers()
    log.info("krxs 헤더 키 목록: %s", list(headers.keys()))

    # 세션 쿠키 확인
    cookies = dict(krxs.session.cookies)
    if cookies:
        log.info("세션 쿠키 있음: %s", list(cookies.keys()))
        print("  ✅ KRX 세션 쿠키 확인됨")
    else:
        log.warning("세션 쿠키 없음 — 인증 실패 가능성")
        print("  ⚠️ 세션 쿠키 없음")

except Exception as e:
    log.warning("krxs 세션 확인 불가: %s", e)
    print(f"  ⚠️ krxs 세션 직접 확인 불가 ({type(e).__name__})")

# ── [4] MDCSTAT02302 직접 POST로 인증 상태 검증 ────────────
print()
print("[4] MDCSTAT02302 엔드포인트 인증 상태 검증")
try:
    import requests
    from pykrx.website.comm.webio import krxs

    URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
    PAYLOAD = {
        "bld":       "dbms/MDC/STAT/standard/MDCSTAT02302",
        "strtDd":    "20260526",
        "endDd":     "20260615",
        "isuCd":     "KR7005930003",
        "inqTpCd":   "2",
        "trdVolVal": "1",
        "askBid":    "3",
    }

    headers = krxs.get_headers()
    resp = krxs.session.post(URL, headers=headers, data=PAYLOAD, timeout=15)

    log.info("status_code: %d", resp.status_code)
    log.info("응답 길이: %d bytes", len(resp.text))
    log.info("응답 앞 200자: %s", resp.text[:200])

    if resp.text.strip() == "LOGOUT":
        print("  ❌ 응답: LOGOUT — KRX 인증 실패")
        print("     KRX_ID/KRX_PW를 확인하거나 data.krx.co.kr 로그인 상태를 확인하세요.")
    elif resp.status_code == 200:
        try:
            j = resp.json()
            output = j.get("output", [])
            log.info("output 개수: %d", len(output))
            if output:
                log.info("output[0] 키: %s", list(output[0].keys()))
                print(f"  ✅ 인증 성공 — output {len(output)}건 반환")
            else:
                print("  ⚠️ 인증은 성공했으나 output이 비어있음 (조회 기간 데이터 없음)")
        except Exception as je:
            print(f"  ⚠️ JSON 파싱 실패: {je}")
            print(f"     응답 본문: {resp.text[:300]}")
    else:
        print(f"  ❌ HTTP {resp.status_code} — 응답: {resp.text[:200]}")

except Exception as e:
    log.error("직접 요청 실패: %s", e)
    traceback.print_exc()

# ── [5] pykrx 공식 함수로 005930 수급 데이터 조회 ─────────
print()
print("[5] krx.get_market_trading_volume_by_date('005930') 조회")
try:
    END   = datetime.today().strftime("%Y%m%d")
    START = (datetime.today() - timedelta(days=40)).strftime("%Y%m%d")

    log.info("조회 기간: %s ~ %s", START, END)
    df = krx.get_market_trading_volume_by_date(START, END, "005930", on="순매수")

    log.info("shape: %s", df.shape)
    log.info("columns: %s", list(df.columns))
    log.info("empty: %s", df.empty)

    if not df.empty:
        print(f"  ✅ 수급 데이터 조회 성공!")
        print(f"     shape: {df.shape}")
        print(f"     columns: {list(df.columns)}")
        print()
        print(df.tail(5).to_string())
    else:
        print("  ❌ 빈 DataFrame 반환 — 인증 실패 또는 데이터 없음")

except Exception as e:
    log.error("수급 조회 실패: %s", e)
    traceback.print_exc()

print()
print("=" * 60)
print("검증 완료")
print("=" * 60)
