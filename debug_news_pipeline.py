"""
debug_news_pipeline.py — 뉴스 파이프라인 전체 진단
실행: python debug_news_pipeline.py   (프로젝트 폴더에서)
"""

import sys, os, json, traceback

# ─── Streamlit 모킹 (st 없이 실행) ─────────────────────────
import types
_fake_st = types.ModuleType("streamlit")
_fake_st.cache_data = lambda *a, **kw: (lambda fn: fn)
_fake_st.secrets = {}
try:
    _secrets = {}
    _sec_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    with open(_sec_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line: continue
            k, _, v = line.partition("=")
            _secrets[k.strip()] = v.strip().strip('"').strip("'")
    _fake_st.secrets = _secrets
    print(f"[OK] secrets 로드: {list(_secrets.keys())}")
except Exception as e:
    print(f"[WARN] secrets.toml 로드 실패: {e}")
sys.modules["streamlit"] = _fake_st

os.environ.setdefault("KRX_ID", str(_fake_st.secrets.get("KRX_ID", "")))
os.environ.setdefault("KRX_PW", str(_fake_st.secrets.get("KRX_PW", "")))

# ─── import news ───────────────────────────────────────────
print("\n[1] news.py import...")
try:
    import news
    print(f"[OK] import 성공")
    print(f"[OK] FEEDPARSER_OK = {news.FEEDPARSER_OK}")
    print(f"[OK] fetch_category_news 존재: {hasattr(news, 'fetch_category_news')}")
    print(f"[OK] add_action_signals 존재: {hasattr(news, 'add_action_signals')}")
except Exception as e:
    print(f"[FAIL] import 오류:")
    traceback.print_exc()
    sys.exit(1)

# ─── feedparser 직접 테스트 ────────────────────────────────
print("\n[2] feedparser 직접 네트워크 테스트...")
if not news.FEEDPARSER_OK:
    print("[FAIL] feedparser 미설치 — pip install feedparser 실행 필요")
    sys.exit(1)

import feedparser
test_url = "https://news.google.com/rss/search?q=코스피+주식&hl=ko&gl=KR&ceid=KR:ko"
try:
    feed = feedparser.parse(test_url)
    print(f"[OK] bozo={feed.bozo}, entries={len(feed.entries)}")
    if feed.entries:
        e = feed.entries[0]
        print(f"[OK] 첫 항목: {e.get('title','')[:80]}")
    else:
        print("[WARN] entries가 비어있음 — Google News 접근 차단 또는 네트워크 문제")
except Exception as e:
    print(f"[FAIL] feedparser.parse 예외: {e}")
    traceback.print_exc()

# ─── fetch_category_news 테스트 ────────────────────────────
print("\n[3] fetch_category_news('전체', max_items=3)...")
try:
    raw = news.fetch_category_news("전체", max_items=3)
    print(f"[OK] 반환 개수: {len(raw)}")
    if not raw:
        print("[WARN] 빈 리스트 반환 — feedparser 네트워크 문제 또는 모든 항목 파싱 실패")
except Exception as e:
    print(f"[FAIL] fetch_category_news 예외:")
    traceback.print_exc()
    raw = []

# ─── 첫 뉴스 full dump ─────────────────────────────────────
if raw:
    print("\n[4] 첫 뉴스 객체 full dump:")
    print(json.dumps(raw[0], ensure_ascii=False, indent=2, default=str))

# ─── enrich + action_signal 테스트 ────────────────────────
if raw:
    print("\n[5] enrich_news_with_portfolio(raw, [], [])...")
    try:
        enriched = news.enrich_news_with_portfolio(raw, [], [])
        print(f"[OK] enriched 개수: {len(enriched)}")
    except Exception as e:
        print(f"[FAIL]:")
        traceback.print_exc()
        enriched = raw

    print("\n[6] add_action_signals(enriched)...")
    try:
        signaled = news.add_action_signals(enriched)
        print(f"[OK] signaled 개수: {len(signaled)}")
    except Exception as e:
        print(f"[FAIL]:")
        traceback.print_exc()
        signaled = enriched

    # ─── 프론트 기대 필드 체크 ─────────────────────────────
    REQUIRED = ["title", "sentiment", "label", "category", "badge_type",
                "source", "published", "summary", "ai_summary", "strategy", "strat_cls"]
    print("\n[7] 프론트 필드 체크:")
    if signaled:
        f = signaled[0]
        all_ok = True
        for field in REQUIRED:
            ok = field in f
            val = str(f.get(field, ""))[:60]
            if not ok: all_ok = False
            print(f"  {'[OK]  ' if ok else '[MISS]'} {field:12s} = {val}")

        if all_ok:
            print("\n결론: 백엔드 정상 → 프론트/캐시 문제 확인 필요")
        else:
            print("\n결론: 누락 필드 있음 → 백엔드 수정 필요")

        print("\n[8] 최종 뉴스 객체 (signaled 첫 번째):")
        print(json.dumps(signaled[0], ensure_ascii=False, indent=2, default=str))
    else:
        print("[WARN] signaled 비어있음")
else:
    print("\n[결론] fetch_category_news가 빈 리스트 반환")
    print("       → feedparser가 Google News에서 데이터를 못 가져오는 상태")
    print("       → 네트워크 확인 또는 잠시 후 재시도")

print("\n=== 진단 완료 ===")
