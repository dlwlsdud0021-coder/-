# diagnose_krx_response.py — KRX HTTP 응답 원인 분석
# 실행: python diagnose_krx_response.py
import sys
import json
import requests
import platform

print("=" * 60)
print("[환경 정보]")
print(f"  Python 버전: {sys.version}")
print(f"  OS: {platform.system()} {platform.release()}")
try:
    import pykrx
    print(f"  pykrx 버전: {pykrx.__version__}")
except:
    print("  pykrx: 확인 불가")
try:
    print(f"  requests 버전: {requests.__version__}")
except:
    print("  requests: 확인 불가")
print("=" * 60)

# ── pykrx 내부 세션/헤더 확인 ──────────────────────────────
print()
print("[1] pykrx 내부 requests 헤더 확인")
try:
    from pykrx.website.comm.webio import Post
    import inspect
    src = inspect.getsource(Post)
    # headers 관련 라인만 추출
    for line in src.splitlines():
        if "header" in line.lower() or "user" in line.lower() or "agent" in line.lower():
            print(" ", line.rstrip())
except Exception as e:
    print("  확인 불가:", e)

# ── 실제 KRX API 직접 호출 ──────────────────────────────────
print()
print("[2] KRX MDCSTAT02302 엔드포인트 직접 POST 호출")

URL     = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://data.krx.co.kr/",
    "Content-Type": "application/x-www-form-urlencoded",
}
PAYLOAD = {
    "bld":       "dbms/MDC/STAT/standard/MDCSTAT02302",
    "strtDd":    "20260506",
    "endDd":     "20260615",
    "isuCd":     "KR7005930003",
    "inqTpCd":   "2",
    "trdVolVal": "1",
    "askBid":    "3",
}

try:
    resp = requests.post(URL, headers=HEADERS, data=PAYLOAD, timeout=15)
    print(f"  status_code: {resp.status_code}")
    print(f"  최종 URL:    {resp.url}")
    print(f"  응답 길이:   {len(resp.text)} bytes")
    print(f"  Content-Type: {resp.headers.get('Content-Type', '없음')}")
    print()
    print(f"  응답 본문 앞 500자:")
    print("  " + "-" * 50)
    print(resp.text[:500] if resp.text else "(빈 응답)")
    print("  " + "-" * 50)

    # JSON 파싱 시도
    print()
    try:
        j = resp.json()
        print(f"  JSON 파싱: 성공 | 최상위 키: {list(j.keys())}")
        output = j.get("output", [])
        print(f"  output 개수: {len(output)}")
        if output:
            print(f"  output[0] 키: {list(output[0].keys())}")
    except Exception as je:
        print(f"  JSON 파싱 실패: {type(je).__name__}: {je}")

except Exception as e:
    import traceback
    print(f"  요청 자체 실패: {type(e).__name__}: {e}")
    traceback.print_exc()

# ── pykrx 내장 세션으로 동일 요청 ──────────────────────────
print()
print("[3] pykrx 내장 세션(webio.Post)으로 동일 요청")
try:
    from pykrx.website.comm.webio import Post

    class TestPost(Post):
        @property
        def url(self):
            return "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

    tp = TestPost()
    resp2 = tp.read(**PAYLOAD)
    print(f"  type(resp2): {type(resp2)}")
    print(f"  status_code: {resp2.status_code}")
    print(f"  응답 길이: {len(resp2.text)} bytes")
    print(f"  응답 앞 300자: {resp2.text[:300]}")
except Exception as e:
    import traceback
    print(f"  실패: {type(e).__name__}: {e}")
    traceback.print_exc()

# ── Python 3.14 호환성 확인 ─────────────────────────────────
print()
print("[4] Python 3.14 + requests 호환성 확인")
try:
    major, minor = sys.version_info[:2]
    if major == 3 and minor >= 14:
        print("  ※ Python 3.14 이상 사용 중")
        print("  pykrx 1.2.8은 Python 3.14 공식 지원 여부 미확인")
        print("  requests ssl/urllib3 변경사항 영향 가능성 있음")
    else:
        print(f"  Python {major}.{minor} — 호환성 문제 없음")
except Exception as e:
    print("  확인 불가:", e)

print()
print("=" * 60)
print("진단 완료")
print("=" * 60)
