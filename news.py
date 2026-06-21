"""
news.py — 뉴스 수집 + 카테고리 분류 + AI 요약 + 대응 전략
- 네이버 뉴스 검색 API (1순위)
- feedparser RSS 폴백 (네이버 실패 시)
- 키워드 기반 카테고리 분류: 반도체 / 바이오 / 2차전지 / 금융 / 글로벌
- Gemini AI 분석 (실패 시 rule-based 폴백)
- 감성 × 카테고리 조합 대응 전략
"""

import re
import time
import os
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────────────────
# Gemini AI 설정
# ─────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
_gemini_model = None

# ─── Supabase 영구 캐시 ───────────────────────────────────
def _db_cache_get(key: str) -> str:
    """Supabase news_cache 테이블에서 결과 조회."""
    try:
        from database import _db
        row = _db().table("news_cache").select("result").eq("cache_key", key).maybe_single().execute()
        return row.data["result"] if row.data else ""
    except Exception:
        return ""

def _db_cache_set(key: str, value: str):
    """Supabase news_cache 테이블에 결과 저장 (upsert)."""
    try:
        from database import _db
        _db().table("news_cache").upsert({"cache_key": key, "result": value}).execute()
    except Exception:
        pass

def _get_gemini():
    global _gemini_model
    if _gemini_model is None and _GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=_GEMINI_KEY)
            _gemini_model = genai.GenerativeModel(
                "gemini-2.0-flash",
                generation_config={"temperature": 0.4, "max_output_tokens": 1500},
            )
        except Exception:
            _gemini_model = None
    return _gemini_model

_gemini_cache: dict[str, str] = {}

def _call_gemini(prompt: str, cache_key: str, retry: int = 1) -> str:
    """Gemini 호출. 메모리→DB→Gemini API 순으로 캐시 확인. rate limit 시 1회 재시도."""
    # 1순위: 메모리 캐시
    if cache_key in _gemini_cache:
        return _gemini_cache[cache_key]
    # 2순위: Supabase DB 캐시 (서버 재시작 후에도 유지)
    db_result = _db_cache_get(cache_key)
    if db_result:
        _gemini_cache[cache_key] = db_result
        return db_result
    # 3순위: Gemini API 호출
    model = _get_gemini()
    if not model:
        return ""
    for attempt in range(retry + 1):
        try:
            resp = model.generate_content(prompt)
            if not resp.candidates:
                print(f"[Gemini] No candidates - possibly blocked by safety filter")
                return ""
            if resp.candidates[0].finish_reason and str(resp.candidates[0].finish_reason) == "SAFETY":
                print(f"[Gemini] Blocked by safety filter")
                return ""
            result = resp.text.strip()
            _gemini_cache[cache_key] = result
            _db_cache_set(cache_key, result)  # Supabase에 영구 저장
            return result
        except Exception as e:
            err_str = str(e)
            # rate limit (429) → 재시도
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                if attempt < retry:
                    import time
                    print(f"[Gemini] Rate limit, 32초 대기 후 재시도...")
                    time.sleep(32)
                    continue
                print(f"[Gemini] Rate limit 재시도 실패: {err_str[:120]}")
            else:
                import traceback
                print(f"[Gemini ERROR] {e}")
                traceback.print_exc()
            return ""

# ─────────────────────────────────────────────────────────
# feedparser 안전 임포트
# ─────────────────────────────────────────────────────────
try:
    import feedparser
    FEEDPARSER_OK = True
except ImportError:
    FEEDPARSER_OK = False


# ─────────────────────────────────────────────────────────
# 카테고리 설정
# ─────────────────────────────────────────────────────────

CATEGORY_CONFIG = {
    "전체": {
        "query": "코스피 코스닥 증시 주식",
        "keywords": [],
        "icon": "ti-news",
        "color": "#5B5BD6",
    },
    "반도체": {
        "query": "반도체 HBM 메모리 SK하이닉스 삼성전자 엔비디아",
        "keywords": [
            "반도체", "HBM", "메모리", "DRAM", "낸드", "NAND", "파운드리",
            "TSMC", "엔비디아", "AI칩", "시스템반도체", "D램", "웨이퍼",
            "팹리스", "비메모리", "삼성전자", "SK하이닉스", "하이닉스",
        ],
        "icon": "ti-cpu",
        "color": "#0A84FF",
    },
    "바이오": {
        "query": "바이오 제약 신약 임상 헬스케어",
        "keywords": [
            "바이오", "제약", "신약", "임상", "식약처", "의약품", "헬스케어",
            "셀트리온", "삼성바이오", "한미약품", "유한양행", "녹십자",
            "임상시험", "FDA", "항체", "mRNA", "바이오시밀러",
        ],
        "icon": "ti-dna",
        "color": "#30D158",
    },
    "2차전지": {
        "query": "배터리 2차전지 전기차 LG에너지 삼성SDI",
        "keywords": [
            "배터리", "2차전지", "전기차", "EV", "리튬", "음극재", "양극재",
            "LG에너지", "삼성SDI", "SK온", "CATL", "에코프로", "포스코퓨처엠",
            "전고체", "충전", "ESS", "에너지저장",
        ],
        "icon": "ti-battery-charging",
        "color": "#FF9F0A",
    },
    "금융": {
        "query": "금리 환율 한국은행 기준금리 증권 은행",
        "keywords": [
            "금리", "기준금리", "한국은행", "금통위", "채권", "국채",
            "CPI", "물가", "인플레이션", "환율", "원달러", "외환",
            "금리인상", "금리인하", "긴축", "양적완화",
            "증권사", "은행", "보험사", "KB금융", "신한금융", "하나금융",
            "우리금융", "미래에셋", "삼성증권", "키움증권",
        ],
        "icon": "ti-chart-line",
        "color": "#FF6B6B",
    },
    "글로벌": {
        "query": "미국 증시 나스닥 Fed 연준 중국 S&P",
        "keywords": [
            "미국", "중국", "일본", "나스닥", "S&P", "S&P500", "다우",
            "Fed", "연준", "FOMC", "파월", "뉴욕증시", "월스트리트",
            "달러", "엔화", "위안", "관세", "무역", "지정학", "경기침체",
        ],
        "icon": "ti-world",
        "color": "#BF5AF2",
    },
}

CATEGORY_NAMES = list(CATEGORY_CONFIG.keys())


# ─────────────────────────────────────────────────────────
# 감성 키워드
# ─────────────────────────────────────────────────────────

POSITIVE_KEYWORDS = [
    # 주가 직접 상승 신호
    "상한가", "신고가", "주가 상승", "증시 상승", "주식 상승", "급등세", "급등했",
    # 실적/사업 호조
    "호재", "흑자", "실적개선", "실적 호조", "영업이익 증가", "매출 증가",
    "수주", "기술수출", "기대감", "돌파", "청신호",
    # 수급 긍정
    "외국인 매수", "기관 매수", "목표가 상향", "강세", "반등", "호조",
    "순매수", "성공", "승인", "수출 증가",
    # 통화정책 완화
    "금리 인하", "기준금리 인하", "완화", "양적완화",
]

NEGATIVE_KEYWORDS = [
    # 주가 직접 하락 신호
    "급락", "급등락", "폭락", "폭등락", "하락", "하한가", "신저가", "주가 하락", "증시 하락", "지수 하락",
    # 실적/사업 부진
    "악재", "적자", "실적부진", "실적 부진", "영업손실", "감소", "취소", "손실",
    "불안", "매도", "하회", "외국인 매도", "기관 매도",
    "목표가 하향", "경고", "악화", "위기",
    "약세", "붕괴", "순매도", "부진", "우려", "침체",
    "규제", "제재", "벌금", "소송", "불확실", "리스크", "충격",
    # 통화정책 긴축
    "금리 인상", "기준금리 인상", "긴축", "금리 올릴", "금리를 올",
    # 매파/긴축 추가 표현
    "매파", "인상 전망", "올릴 것", "올릴 가능성", "꺾일", "꺾이",
    "상승세 꺾", "경기 둔화", "수요 둔화", "경기침체 우려", "부담 가중",
    "압박", "둔화 우려", "상승 꺾",
]

# 주식 관련 키워드 (비주식 뉴스 필터링용)
_STOCK_RELEVANCE_KW = [
    "코스피", "코스닥", "증시", "주가", "주식", "상장", "외국인", "기관",
    "급등", "급락", "금리", "환율", "달러", "Fed", "연준", "실적",
    "영업이익", "반도체", "바이오", "수출", "IPO", "공모", "배당",
    "시총", "PER", "PBR", "ETF", "펀드", "채권", "증권", "투자",
    "주주", "공시", "상한가", "하한가", "거래량", "매출", "순이익",
]

_NON_STOCK_KW = [
    "월드컵", "올림픽", "야구", "축구", "농구", "골프", "배구", "테니스",
    "연예", "아이돌", "드라마", "영화", "K팝", "날씨", "태풍", "지진",
    "선거", "대통령", "국회", "정치", "외교", "군사", "스포츠", "운동선수",
    "요리", "맛집", "여행", "관광", "패션", "뷰티", "건강",
]


# ─────────────────────────────────────────────────────────
# 감성 분류
# ─────────────────────────────────────────────────────────

def classify_sentiment(text: str) -> dict:
    """
    Returns: {
      sentiment: "positive" | "negative" | "mixed" | "neutral",
      label: str,
      badge_type: str,
      score: int,
    }
    """
    pos = sum(1 for k in POSITIVE_KEYWORDS if k in text)
    neg = sum(1 for k in NEGATIVE_KEYWORDS if k in text)
    score = pos - neg

    # score 절댓값이 크면 혼재라도 우세한 방향으로 판정 (금리인상/급등락 기사 오판 방지)
    if pos > 0 and neg > 0 and abs(score) <= 2:
        # neg 키워드 개수가 pos보다 훨씬 많으면 negative (예: 급등락 → 급등 1개지만 neg 많은 경우)
        if neg >= pos * 2:
            return {"sentiment": "negative", "label": "부정", "badge_type": "sell",    "score": score}
        else:
            return {"sentiment": "mixed",    "label": "혼조", "badge_type": "warn",    "score": score}
    elif score >= 2:
        return {"sentiment": "positive", "label": "긍정", "badge_type": "buy",     "score": score}
    elif score == 1:
        return {"sentiment": "positive", "label": "긍정", "badge_type": "ok",      "score": score}
    elif score <= -2:
        return {"sentiment": "negative", "label": "부정", "badge_type": "sell",    "score": score}
    elif score == -1:
        return {"sentiment": "negative", "label": "부정", "badge_type": "warn",    "score": score}
    else:
        return {"sentiment": "neutral",  "label": "중립", "badge_type": "neutral", "score": score}


# ─────────────────────────────────────────────────────────
# 카테고리 분류
# ─────────────────────────────────────────────────────────

def classify_category(title: str, summary: str = "") -> str:
    """
    제목 + 본문 키워드로 카테고리 분류
    Returns: "반도체" | "바이오" | "2차전지" | "금융" | "글로벌" | "전체"
    """
    text = (title + " " + summary).lower()
    scores = {}
    for cat, cfg in CATEGORY_CONFIG.items():
        if cat == "전체":
            continue
        score = sum(1 for kw in cfg["keywords"] if kw.lower() in text)
        if score > 0:
            scores[cat] = score
    if not scores:
        return "전체"
    return max(scores, key=scores.get)


# ─────────────────────────────────────────────────────────
# 수치 패턴
# ─────────────────────────────────────────────────────────

_NUMBER_PATTERN = re.compile(r"(\d[\d,.]*)(%|원|억|조|달러|위안|배|건|명|개)")


# ─────────────────────────────────────────────────────────
# 기업명 → KRX 티커 매핑
# ─────────────────────────────────────────────────────────

_COMPANY_TICKER_MAP: dict[str, str] = {
    # KOSPI 대형주
    "삼성전자":           "005930",
    "SK하이닉스":         "000660",
    "LG에너지솔루션":     "373220",
    "삼성SDI":            "006400",
    "현대차":             "005380",
    "기아":               "000270",
    "POSCO홀딩스":        "005490",
    "포스코":             "005490",
    "LG화학":             "051910",
    "한화":               "000880",
    "현대모비스":         "012330",
    "KB금융":             "105560",
    "신한금융":           "055550",
    "하나금융":           "086790",
    "우리금융":           "316140",
    "삼성바이오로직스":   "207940",
    "셀트리온":           "068270",
    "한미약품":           "128940",
    "유한양행":           "000100",
    "SK이노베이션":       "096770",
    # KOSDAQ 주요주
    "카카오":             "035720",
    "네이버":             "035420",
    "에코프로":           "086520",
    "에코프로비엠":       "247540",
    "포스코퓨처엠":       "003670",
    "SK온":               "285130",
    "엔씨소프트":         "036570",
    "크래프톤":           "259960",
    # 증권사
    "미래에셋":           "006800",
    "미래에셋증권":       "006800",
    "키움":               "039490",
    "키움증권":           "039490",
    "삼성증권":           "016360",
    "한국투자증권":       "071050",
    "NH투자증권":         "005940",
    "KB증권":             "030210",
    "신한투자증권":       "001230",
    "한화투자증권":       "003530",
    "대신증권":           "003540",
    "메리츠증권":         "008560",
    "신영증권":           "001720",
    # 추가 국내주
    "한화에어로스페이스": "012450",
    "한국항공우주":       "047810",
    "두산에너빌리티":     "034020",
    "두산밥캣":           "241560",
    "LS":                 "006260",
    "고려아연":           "010130",
    "롯데케미칼":         "011170",
    "OCI":                "010060",
    "HMM":                "011200",
    "팬오션":             "028670",
    "CJ대한통운":         "000120",
    "LG전자":             "066570",
    "삼성물산":           "028260",
    "현대건설":           "000720",
    "GS건설":             "006360",
    # 해외 (ticker 없음)
    "TSMC":               "",
    "엔비디아":           "",
    "애플":               "",
    "구글":               "",
    "마이크로소프트":     "",
    "스페이스X":          "",
    "테슬라":             "",
    "아마존":             "",
    "메타":               "",
    "오픈AI":             "",
}

_COMPANIES = list(_COMPANY_TICKER_MAP.keys())

# 기업 → 섹터 매핑 (관련종목 필터링용)
_COMPANY_SECTORS: dict[str, list[str]] = {
    "삼성전자":           ["반도체", "전자"],
    "SK하이닉스":         ["반도체"],
    "TSMC":               ["반도체"],
    "엔비디아":           ["반도체", "글로벌"],
    "삼성바이오로직스":   ["바이오"],
    "셀트리온":           ["바이오"],
    "한미약품":           ["바이오"],
    "유한양행":           ["바이오"],
    "LG에너지솔루션":     ["2차전지"],
    "삼성SDI":            ["2차전지"],
    "SK이노베이션":       ["2차전지"],
    "에코프로":           ["2차전지"],
    "에코프로비엠":       ["2차전지"],
    "포스코퓨처엠":       ["2차전지"],
    "SK온":               ["2차전지"],
    "KB금융":             ["금융"],
    "신한금융":           ["금융"],
    "하나금융":           ["금융"],
    "우리금융":           ["금융"],
    "미래에셋":           ["금융"],
    "미래에셋증권":       ["금융"],
    "키움":               ["금융"],
    "키움증권":           ["금융"],
    "삼성증권":           ["금융"],
    "현대차":             ["자동차", "글로벌"],
    "기아":               ["자동차"],
    "현대모비스":         ["자동차"],
    "LG전자":             ["전자"],
    "카카오":             ["전자"],
    "네이버":             ["전자"],
    "테슬라":             ["글로벌", "2차전지"],
    "애플":               ["글로벌"],
    "구글":               ["글로벌"],
    "마이크로소프트":     ["글로벌"],
    "아마존":             ["글로벌"],
    "메타":               ["글로벌"],
    "한화에어로스페이스": ["방산"],
    "한국항공우주":       ["방산"],
}

# 섹터별 대표종목 (관련종목 없을 때 폴백)
_SECTOR_FALLBACK: dict[str, list[tuple]] = {
    "반도체": [("삼성전자","005930"), ("SK하이닉스","000660"), ("한미반도체","042700")],
    "바이오": [("삼성바이오로직스","207940"), ("셀트리온","068270"), ("한미약품","128940")],
    "2차전지": [("LG에너지솔루션","373220"), ("삼성SDI","006400"), ("에코프로비엠","247540")],
    "금융": [("KB금융","105560"), ("신한금융","055550"), ("하나금융","086790")],
    "자동차": [("현대차","005380"), ("기아","000270"), ("현대모비스","012330")],
    "글로벌": [("삼성전자","005930"), ("현대차","005380"), ("LG에너지솔루션","373220")],
    "전체": [("삼성전자","005930"), ("SK하이닉스","000660"), ("LG에너지솔루션","373220")],
}


def get_ticker_by_name(name: str) -> str:
    return _COMPANY_TICKER_MAP.get(name, "")


_ACTION_MAP = {
    "상승": ("상승세", "긍정"),
    "급등": ("급등", "강한 긍정"),
    "하락": ("하락세", "부정"),
    "급락": ("급락", "강한 부정"),
    "수주": ("수주 계약", "긍정"),
    "승인": ("승인", "긍정"),
    "취소": ("취소", "부정"),
    "감소": ("감소", "부정"),
    "증가": ("증가", "긍정"),
    "흑자": ("흑자 전환", "긍정"),
    "적자": ("적자", "부정"),
    "돌파": ("돌파", "긍정"),
    "하회": ("기대치 하회", "부정"),
}

_CATEGORY_CONTEXT = {
    "반도체": {
        "positive": "HBM·AI 수요 확대 기조 속 반도체 섹터 전반에 긍정 영향 기대",
        "negative": "반도체 업황 둔화 우려로 관련주 단기 조정 가능성",
        "mixed":    "반도체 업황 방향성 불확실 — 단기 변동성 주의",
        "neutral":  "반도체 섹터 특이 동향 없음 — 외국인 수급 방향 모니터링",
    },
    "바이오": {
        "positive": "임상 결과·허가 기대감으로 바이오 섹터 상승 모멘텀 가능",
        "negative": "임상 실패·규제 리스크로 관련주 급락 가능성 — 분할 대응 권장",
        "mixed":    "바이오 이벤트 결과 불확실 — 결과 확인 전 비중 조절",
        "neutral":  "바이오 섹터 관망 국면 — 임상 일정 체크 권장",
    },
    "2차전지": {
        "positive": "전기차 수요 회복 신호로 2차전지 밸류체인 반등 가능",
        "negative": "EV 수요 둔화·경쟁 심화로 배터리 관련주 압박",
        "mixed":    "전기차 수요 vs 공급 과잉 우려 혼재 — 단기 관망",
        "neutral":  "2차전지 섹터 뚜렷한 방향성 없음 — 수주 동향 주시",
    },
    "금융": {
        "positive": "금리·환율 안정으로 시장 전반 리스크 완화 기대",
        "negative": "금리 상승·환율 불안으로 수출주·금융주 부담 증가",
        "mixed":    "통화정책 불확실성 지속 — 방어적 포트폴리오 유지",
        "neutral":  "금리·환율 보합 — 이벤트 대기 국면",
    },
    "글로벌": {
        "positive": "글로벌 위험 선호 개선으로 외국인 수급 유입 가능성",
        "negative": "글로벌 불확실성 확대 — 외국인 매도 압력 주의",
        "mixed":    "미국·중국 리스크 혼재 — 수출 비중 높은 종목 모니터링",
        "neutral":  "글로벌 시장 관망 — FOMC·중국 지표 체크",
    },
    "전체": {
        "positive": "시장 전반 긍정 분위기 — 코스피·코스닥 상승 모멘텀 기대",
        "negative": "시장 전반 약세 — 손절선 점검 및 현금 비중 확대 고려",
        "mixed":    "혼조 장세 — 섹터별 차별화 대응 권장",
        "neutral":  "특이 동향 없음 — 개별 종목 수급 중심으로 판단",
    },
}

_STRATEGY_MAP = {
    ("반도체", "positive"): (
        "HBM·AI 수혜주(SK하이닉스, 삼성전자) 비중을 유지하고, 단기 눌림목 구간에서 분할 매수를 검토하세요. "
        "초반 장세에서 외국인 순매수 지속 여부를 확인한 뒤 추가 비중을 늘리는 전략이 유효합니다. "
        "단, 고점 대비 5% 이상 조정이 나타나면 일부 차익 실현을 병행하는 것을 권장합니다.",
        "chip-buy"),
    ("반도체", "negative"): (
        "반도체 관련주의 현재 손절선(매수가 기준 -7~10%)을 재점검하고, 신규 매수는 보류하세요. "
        "업황 방향성이 확인되기 전까지 보유 비중을 단계적으로 줄이는 것이 안전합니다. "
        "주요 지수(SOX) 반등과 외국인 수급 전환 신호를 확인한 후 재진입 타이밍을 모색하세요.",
        "chip-sell"),
    ("반도체", "mixed"): (
        "장 초반 외국인 매매 방향을 먼저 확인한 뒤 대응하세요. 현재는 비중 조절이 우선입니다. "
        "긍정·부정 재료가 혼재된 구간에서는 분할 진입보다 관망이 리스크 관리에 유리합니다. "
        "실적 발표 또는 수급 방향성이 명확해지는 시점까지 신규 포지션 추가는 자제하세요.",
        "chip-warn"),
    ("반도체", "neutral"): (
        "반도체 섹터의 뚜렷한 방향성이 없는 구간입니다. 신규 진입보다 기존 포지션 유지가 적합합니다. "
        "다음 실적 발표 일정과 주요 고객사 수주 동향을 주시하며 대기하세요. "
        "외국인·기관 수급 변화가 포착되는 시점에 맞춰 방향을 정하는 것을 추천합니다.",
        "chip-neu"),

    ("바이오", "positive"): (
        "임상 성공·승인 기대감이 높아진 종목 중심으로 비중을 집중하되, 전량 베팅은 금물입니다. "
        "이벤트 결과 발표 전 30~50% 포지션 선진입 후 결과에 따라 추가 여부를 결정하세요. "
        "FDA·식약처 결과 발표 당일 변동성에 대비해 손절 기준선을 사전에 설정해 두는 것이 중요합니다.",
        "chip-buy"),
    ("바이오", "negative"): (
        "임상 실패 규제 리스크가 현실화된 경우 손절 후 재진입 타이밍을 냉정하게 판단하세요. "
        "급락 이후 단기 기술적 반등 구간에서 분할 매수 기회를 노릴 수 있지만, 추가 악재 여부를 먼저 확인하세요. "
        "해당 종목의 파이프라인(임상 단계별 일정)을 재검토하고 대안 종목으로 교체를 검토할 시점입니다.",
        "chip-sell"),
    ("바이오", "mixed"): (
        "이벤트 결과가 확인되기 전까지 신규 진입을 자제하고, 기존 보유분은 비중을 일부 줄여 리스크를 낮추세요. "
        "긍정 부정 신호가 혼재된 상황에서는 결과 발표 이후 방향성을 확인하는 것이 안전합니다. "
        "임상 단계별 주요 이정표 일정을 체크하고 대응 시나리오를 사전에 준비해 두세요.",
        "chip-warn"),
    ("바이오", "neutral"): (
        "바이오 섹터의 뚜렷한 모멘텀이 없는 구간으로, 관망이 최선입니다. "
        "임상 발표 예정 종목을 미리 리스트업하고 일정 관리에 집중하세요. "
        "FDA 결정일 국내 식약처 심사 일정 등을 달력에 표기해 이벤트 전 선제적 포지션을 준비할 수 있습니다.",
        "chip-neu"),
    ("2차전지", "positive"): (
        "전기차 수요 회복 신호에 따라 에코프로 포스코퓨처엠 등 밸류체인 반등 구간에서 분할 매수를 검토하세요. "
        "배터리 셀 소재 전반에 걸쳐 수혜 종목이 넓게 분포하므로 ETF 활용도 유효한 전략입니다. "
        "OEM 수주 공시와 글로벌 EV 판매량 지표가 연속으로 확인될 때 추가 비중 확대를 고려하세요.",
        "chip-buy"),
    ("2차전지", "negative"): (
        "전기차 수요 둔화 경쟁 심화 우려가 지속되는 구간에서는 배터리 관련주 비중을 단계적으로 축소하세요. "
        "수주 공백 기간에는 현금 비중을 높이고, 실적 발표 이후 업황 방향성을 재확인하는 것이 중요합니다. "
        "CATL 테슬라 등 선도 기업의 수요 전망 변화는 반전 신호가 될 수 있으니 모니터링을 유지하세요.",
        "chip-sell"),
    ("2차전지", "mixed"): (
        "전기차 판매 지표와 주요 OEM 수주 공시 확인 후 방향을 결정하세요. 현재 비중 유지가 적합합니다. "
        "공급 과잉 우려와 수요 회복 기대가 교차하는 구간으로, 단기 추격 매수보다 눌림목 대기 전략이 유리합니다. "
        "LG에너지 삼성SDI 등 대형주 중심으로 방어 포지션을 유지하며 시황을 지켜보세요.",
        "chip-warn"),
    ("2차전지", "neutral"): (
        "2차전지 섹터의 뚜렷한 방향성이 없는 구간으로, 신규 진입보다 관망이 적합합니다. "
        "주요 OEM 수주 뉴스와 글로벌 EV 시장 동향 모니터링에 집중하세요. "
        "에너지저장장치(ESS) 수요 등 배터리의 다변화 수요처도 함께 주시할 필요가 있습니다.",
        "chip-neu"),
    ("금융", "positive"): (
        "금리 안정기에는 성장주 비중 확대를 검토하고, 리츠 배당주에 대한 관심도 높아지는 시기입니다. "
        "코스피 금융주(은행 보험)는 순이자마진(NIM) 개선 가능성에 주목하며 저평가 여부를 확인하세요. "
        "환율 안정 흐름이 동반되면 수출 대형주에도 우호적인 환경이 조성될 수 있습니다.",
        "chip-buy"),
    ("금융", "negative"): (
        "금리 상승기에는 성장주 및 부채 비중이 높은 종목 비중을 축소하는 것이 우선입니다. "
        "통신 유틸리티 등 방어주로 포트폴리오 비중을 이동하고, 현금 비중을 30% 이상 유지하세요. "
        "원달러 환율 상승이 동반되면 수출주 일부는 방어할 수 있지만, 내수 부동산 관련주는 추가 조정에 주의하세요.",
        "chip-sell"),
    ("금융", "mixed"): (
        "통화정책 불확실성 구간에서는 현금 비중 30% 이상을 유지하며 방어적 포지션을 우선시하세요. "
        "FOMC 한국은행 금통위 결과를 확인하기 전까지 신규 포지션 확대는 자제하는 것이 안전합니다. "
        "금리 방향성이 결정되는 시점에 성장주와 가치주 비중을 조정하는 전략을 미리 준비해 두세요.",
        "chip-warn"),
    ("금융", "neutral"): (
        "금리 환율 이벤트 대기 국면으로, FOMC 결과 전까지 방어적 포지션 유지를 권장합니다. "
        "미국 고용 CPI 지표와 한국은행 기준금리 결정 일정을 미리 체크해 두세요. "
        "주요 매크로 이벤트 전후로 변동성이 커질 수 있으니 포지션 크기를 적정 수준으로 관리하세요.",
        "chip-neu"),
    ("글로벌", "positive"): (
        "글로벌 위험 선호 개선에 따라 외국인 수급 유입이 기대되며, 코스피 대형주 비중 확대를 검토하세요. "
        "원화 강세 흐름이 동반될 경우 내수주 금융주에도 긍정적으로 작용합니다. "
        "미국 나스닥 S&P500 흐름을 매일 확인하며 한국 시장 선행 지표로 활용하세요.",
        "chip-buy"),
    ("글로벌", "negative"): (
        "글로벌 불확실성 확대 시 외국인 매도 압력이 강해지므로 현금 비중을 높이세요. "
        "달러 강세 원화 약세 구간에서는 수입 비용 증가로 내수 기업이 타격받을 수 있습니다. "
        "미국 증시 하락폭이 2% 이상이면 다음 날 코스피도 동반 하락할 가능성이 높으니 주의하세요.",
        "chip-sell"),
    ("글로벌", "mixed"): (
        "글로벌 재료가 혼재된 구간에서는 포트폴리오 내 현금 비중을 20~30% 수준으로 확보하세요. "
        "미국 중국 지표 발표 전후 변동성이 커질 수 있으므로 레버리지 인버스 ETF 활용은 자제하세요. "
        "FOMC 의사록 중국 PMI 등 주요 지표 발표 일정을 미리 체크해 두세요.",
        "chip-warn"),
    ("글로벌", "neutral"): (
        "글로벌 시장이 방향성을 찾는 관망 국면입니다. 기존 포지션 유지가 적합합니다. "
        "미국 고용지표 CPI 등 다음 매크로 이벤트 일정을 체크하고 대응 시나리오를 준비해 두세요. "
        "원달러 환율과 외국인 수급 방향을 매일 확인하며 시장 분위기를 모니터링하세요.",
        "chip-neu"),
    ("전체", "positive"): (
        "시장 전반 긍정 분위기에서 코스피 대형주 중심으로 비중을 확대하는 전략이 유효합니다. "
        "외국인 순매수가 3일 이상 지속되면 추세 전환 신호로 볼 수 있으며 적극적 매수 타이밍입니다. "
        "단기 급등 후 차익 실현 매물이 나올 수 있으니 분할 매수 매도 원칙을 지키세요.",
        "chip-buy"),
    ("전체", "negative"): (
        "시장 전반 하락 시 손절선(-5~7%)을 철저히 지키고 현금 비중을 30% 이상 확보하세요. "
        "외국인이 대규모 매도 시 개인이 역매매로 대응하는 것은 위험합니다. "
        "낙폭 과대 우량주를 미리 리스트업해 두고, 시장이 안정될 때 분할 매수 기회를 노리세요.",
        "chip-sell"),
    ("전체", "mixed"): (
        "혼조 장세에서는 섹터별 차별화 대응이 중요합니다. 강한 섹터는 비중을 유지하고 약한 섹터는 줄이세요. "
        "거래량이 줄어드는 종목은 매도 신호이고, 거래량이 늘어나는 종목은 관심 종목으로 분류하세요. "
        "새로운 진입보다는 기존 포지션 점검과 손절선 재확인에 집중하세요.",
        "chip-warn"),
    ("전체", "neutral"): (
        "시장 특이 동향이 없는 구간에서는 새로 사거나 파는 것보다 기다리는 게 맞습니다. "
        "개별 종목의 실적 발표 공시 일정을 체크하고 이벤트 기반으로 대응하는 전략이 유효합니다. "
        "현금 보유 중이라면 관심 종목 리스트를 정리하며 다음 기회를 준비하세요.",
        "chip-neu"),
}

# ─────────────────────────────────────────────────────────
# RSS URL 상수
# ─────────────────────────────────────────────────────────
_YONHAP_ECONOMY_RSS  = "https://www.yna.co.kr/rss/economy.xml"
_HANKYUNG_RSS        = "https://www.hankyung.com/feed/all-news"
_MK_RSS              = "https://www.mk.co.kr/rss/30100041/"
_NAVER_FINANCE_RSS   = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"


def _google_news_url(query: str) -> str:
    from urllib.parse import quote_plus
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=ko&gl=KR&ceid=KR:ko"
    )


def _parse_feed(url: str, max_items: int = 15, source: str = "구글뉴스") -> list:
    """feedparser로 RSS 피드 파싱. 본문이 짧으면 원문 크롤링 시도."""
    if not FEEDPARSER_OK:
        return []
    try:
        import feedparser
        import html as html_mod
        import re as _re

        feed = feedparser.parse(url)
        results = []

        for entry in feed.entries[:max_items * 2]:
            title = html_mod.unescape(getattr(entry, "title", "") or "").strip()
            if not title:
                continue

            # 링크
            link = getattr(entry, "link", "") or ""

            # 본문 — summary > content > description 순서로 시도
            raw_sum = ""
            for attr in ("summary", "description", "content"):
                val = getattr(entry, attr, None)
                if val:
                    if isinstance(val, list):
                        val = val[0].get("value", "") if val else ""
                    raw_sum = val
                    break

            # HTML 태그 제거
            clean = _re.sub(r"<[^>]+>", " ", raw_sum)
            clean = html_mod.unescape(clean)
            clean = _re.sub(r"\s+", " ", clean).strip()

            # 본문이 너무 짧으면 (100자 미만) 원문 크롤링 시도
            if len(clean) < 100 and link:
                fetched = _fetch_article_text(link)
                if fetched:
                    clean = fetched

            # 날짜
            pub = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                import time as _time
                ts = _time.mktime(entry.published_parsed)
                from datetime import datetime, timezone, timedelta
                dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(
                    timezone(timedelta(hours=9))
                )
                pub = dt.strftime("%m/%d %H:%M")

            results.append({
                "title":   title,
                "summary": clean,
                "url":     link,
                "source":  source,
                "pub_date": pub,
            })

            if len(results) >= max_items:
                break

        return results
    except Exception:
        return []


def _merge_feeds(feed_quotas: list, max_items: int = 15) -> list:
    """여러 RSS를 quota 비율로 병합. 중복 제목 제거."""
    seen_titles = set()
    merged = []

    for url, quota, source in feed_quotas:
        items = _parse_feed(url, quota * 2, source)
        added = 0
        for item in items:
            key = item["title"][:30]
            if key not in seen_titles:
                seen_titles.add(key)
                merged.append(item)
                added += 1
            if added >= quota:
                break

    return merged[:max_items]


def _fetch_article_text(url: str, timeout: int = 5) -> str:
    """뉴스 원문 URL에서 본문 텍스트 크롤링 (짧은 RSS 요약 보완용)."""
    try:
        import requests
        import html as html_mod
        import re as _re

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        html_text = resp.text

        # 공통 본문 패턴 (연합·한경·MK·네이버)
        patterns = [
            r'<div[^>]+class="[^"]*article[_-]?body[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]+id="[^"]*article[_-]?body[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]+class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
        ]
        body = ""
        for pat in patterns:
            m = _re.search(pat, html_text, _re.DOTALL | _re.IGNORECASE)
            if m:
                body = m.group(1)
                break

        if not body:
            # 단락 태그 기반 폴백
            paras = _re.findall(r"<p[^>]*>(.*?)</p>", html_text, _re.DOTALL)
            body = " ".join(paras)

        # HTML 제거
        clean = _re.sub(r"<[^>]+>", " ", body)
        clean = html_mod.unescape(clean)
        clean = _re.sub(r"\s+", " ", clean).strip()
        # 광고/SNS 문구 제거
        clean = _re.sub(r"(무단.{0,10}금지|저작권|ⓒ|copyright|subscribe|SNS|공유하기|기자\s*$)", "", clean, flags=_re.IGNORECASE)
        clean = _re.sub(r"\s+", " ", clean).strip()

        return clean[:1500] if len(clean) > 50 else ""
    except Exception:
        return ""


def _calc_impact_score(title: str, summary: str, category: str) -> float:
    """뉴스 중요도 점수 계산 (0~100)."""
    score = 0.0
    text = title + " " + summary

    # 고임팩트 키워드
    HIGH_KW = ["급등", "급락", "상한가", "하한가", "실적", "어닝", "임상 성공",
               "FDA 승인", "수주", "계약", "합병", "인수", "기술수출",
               "FOMC", "금리", "기준금리", "외국인", "공매도", "IPO"]
    for kw in HIGH_KW:
        if kw in text:
            score += 8

    # 기업명 등장
    for co in _COMPANIES:
        if co in text:
            score += 5
            break

    # 숫자/수치 등장
    nums = _NUMBER_PATTERN.findall(text)
    score += min(len(nums) * 3, 15)

    # 카테고리 키워드
    cfg = CATEGORY_CONFIG.get(category, {})
    for kw in cfg.get("keywords", []):
        if kw in text:
            score += 2

    # 제목 길이 (짧은 제목 = 임팩트 있는 뉴스)
    if len(title) < 30:
        score += 5

    return min(score, 100.0)


def extract_related_stocks(title: str, summary: str, category: str) -> list:
    """뉴스 본문에서 언급된 기업 추출 → (name, ticker) 목록 반환."""
    text = title + " " + summary
    found = []
    seen = set()

    for co in _COMPANIES:
        if co in text and co not in seen:
            ticker = _COMPANY_TICKER_MAP.get(co, "")
            found.append({"name": co, "ticker": ticker})
            seen.add(co)

    # 언급 기업 없으면 섹터 폴백
    if not found:
        fallback_key = category if category in _SECTOR_FALLBACK else "전체"
        for name, ticker in _SECTOR_FALLBACK.get(fallback_key, []):
            found.append({"name": name, "ticker": ticker})

    return found[:5]




# ─────────────────────────────────────────────────────────
# AI 분석 생성 (Gemini + rule-based 폴백)
# ─────────────────────────────────────────────────────────

def _extract_term(text: str, term: str) -> str:
    """'단기(1~2주)' 또는 '중기(1~3개월)' 블록을 추출. 없으면 전체 반환."""
    other = "중기" if term == "단기" else "단기"
    # ▶ 단기 ... ▶ 중기 패턴
    pattern = rf"▶\s*{term}[^▶]*?(?=▶\s*{other}|$)"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        chunk = m.group(0)
        # 헤더 줄 제거 후 반환
        chunk = re.sub(rf"▶\s*{term}[^\n]*\n?", "", chunk, count=1).strip()
        return chunk if chunk else text
    # 패턴 없으면 전체 텍스트 반환 (Gemini가 포맷을 따르지 않은 경우)
    return text


def generate_ai_summary(title, summary, sentiment, category):
    cache_key = hashlib.md5(("v2:" + title[:80]).encode()).hexdigest()
    sentiment_kor = {"positive": "긍정", "negative": "부정", "mixed": "혼재", "neutral": "중립"}.get(sentiment, "중립")

    article_body = summary[:500] if summary else ""
    body_part = f"본문: {article_body}\n" if article_body else ""
    prompt = (
        "한국 주식 초보 투자자를 위한 뉴스 분석. 반드시 아래 기사 내용만 바탕으로 작성하세요.\n"
        "기사 제목: " + title + "\n"
        + body_part +
        "감성: " + sentiment_kor + "\n\n"
        "[분석] 이 기사의 핵심 사실을 2~3문장으로 요약. "
        "누가/무엇을/왜/어떤 숫자가 나왔는지 포함. 기사에 없는 내용 추론 금지. 완전한 문장으로.\n"
        "[영향] ▲수혜: 종목명 — 이유 한줄 / ▼피해: 종목명 — 이유 한줄 (특정 불가시 ETF 대체)\n"
    )
    raw = _call_gemini(prompt, cache_key)
    if raw:
        def _ext(tag, text):
            m = re.search(r"\[" + tag + r"\]\s*([\s\S]*?)(?=\[|$)", text)
            return m.group(1).strip() if m else ""
        analysis_txt = _ext("분석", raw)
        impact_txt   = _ext("영향", raw)
        if analysis_txt:
            result = "<b>📋 이 뉴스는?</b><br>" + analysis_txt.replace("\n", "<br>")
            if impact_txt:
                result += "<br><br><b>📌 영향 종목</b><br>" + impact_txt.replace("\n", "<br>")
            return result
        if len(raw) > 40:
            return "<b>📋 이 뉴스는?</b><br>" + raw.replace("\n", "<br>")

    # Rule-based 폴백 (Gemini 실패시)
    text = title + " " + summary
    companies = [c for c in _COMPANIES if c in text]
    numbers   = _NUMBER_PATTERN.findall(text)
    co_str    = "와 ".join(companies[:2]) if companies else ""
    num_str   = (numbers[0][0] + numbers[0][1]) if numbers else ""
    neg_hits  = [kw for kw in NEGATIVE_KEYWORDS if kw in text]
    pos_hits  = [kw for kw in POSITIVE_KEYWORDS if kw in text]

    sector_kr = {
        "반도체": "반도체·AI칩", "바이오": "바이오·제약",
        "2차전지": "2차전지·배터리", "금융": "금융·증권",
        "글로벌": "글로벌 시장", "전체": "국내 증시",
    }.get(category, category)

    # 섹션 1: 무슨 뉴스인가요? — 투자자 관점 해석
    # article_body 복사 금지: 위 기사 요약 박스와 중복됨
    # Gemini 미작동 시에도 카테고리+감성 기반 투자자 해석 문장 제공
    eff_what_sent = (sentiment if sentiment in ['positive', 'negative']
                     else 'negative' if neg_hits else 'positive' if pos_hits else 'neutral')

    if co_str and num_str:
        what = f"{co_str}와 관련해 {num_str} 규모의 이슈가 발생했습니다. "
        what += {
            'positive': f"{co_str} 주가에 단기 긍정적인 영향이 예상됩니다.",
            'negative': f"{co_str} 주가에 단기 하락 압력이 가해질 수 있습니다.",
        }.get(eff_what_sent, f"{sector_kr} 관련 이슈입니다.")
    elif co_str:
        what = {
            'positive': f"{co_str}에 긍정적인 뉴스가 나왔습니다. 실적 개선, 수주, 신사업 등 주가 상승의 직접적 트리거가 될 수 있습니다.",
            'negative': f"{co_str}에 부정적인 뉴스가 나왔습니다. 실적 부진, 계약 취소, 규제 이슈 등 주가 하락 압력으로 작용할 수 있습니다.",
            'mixed':    f"{co_str} 관련 뉴스로 긍정, 부정 요소가 혼재합니다. 장 초반 주가 반응을 먼저 확인하세요.",
            'neutral':  f"{co_str} 관련 공시, 참고 뉴스입니다. 중장기 방향성에 영향을 줄 수 있습니다.",
        }.get(eff_what_sent, f"{co_str} 관련 뉴스입니다.")
    else:
        cat_what = {
            ('전체', 'negative'): '국내 증시에 부정적인 이슈가 발생했습니다. 대외 악재나 수급 불균형으로 코스피, 코스닥 전반에 하락 압력이 가해질 수 있어 포트폴리오 점검이 필요합니다.',
            ('전체', 'positive'): '국내 증시에 긍정적인 이슈가 발생했습니다. 수급 개선이나 호재로 코스피, 코스닥이 상승 탄력을 받을 수 있습니다.',
            ('글로벌', 'negative'): '글로벌 시장에 불안 요인이 부각됐습니다. 해외 악재는 외국인 매도를 유발해 국내 증시에도 하락 압력을 전이시킬 수 있습니다.',
            ('글로벌', 'positive'): '글로벌 시장에 긍정적 신호가 나왔습니다. 미국 증시 호조는 다음 날 국내 증시 상승으로 이어지는 경향이 강하며 외국인 순매수 유입을 기대할 수 있습니다.',
            ('반도체', 'negative'): '반도체 업황에 우려 신호가 나왔습니다. 수요 감소, 가격 하락 이슈는 삼성전자, SK하이닉스 등 대형주 전반에 하락 압력을 주고 장비, 소재주에도 영향을 미칩니다.',
            ('반도체', 'positive'): '반도체 섹터에 긍정적 이슈가 발생했습니다. AI 수요 확대나 실적 호조 뉴스는 삼성전자, SK하이닉스 상승의 트리거이며 장비, 소재 중소형주로도 낙수 효과가 나타납니다.',
            ('금융', 'negative'): '금리 인상 또는 긴축 기조 신호가 나왔습니다. 금리가 오르면 고PER 성장주가 가장 먼저 타격을 받으며 주식에서 채권으로 자금이 이동합니다.',
            ('금융', 'positive'): '금리 인하 또는 완화 기조 신호가 나왔습니다. 금리가 내리면 주식 시장 전반에 호재이며 특히 고PER 성장주와 부동산 관련주가 큰 수혜를 받습니다.',
            ('바이오', 'negative'): '바이오, 제약 섹터에 부정적 이슈가 발생했습니다. 임상 실패나 허가 반려는 해당 종목의 급락을 유발하고 비슷한 파이프라인을 가진 다른 바이오주도 투자심리가 냉각될 수 있습니다.',
            ('바이오', 'positive'): '바이오, 제약 섹터에 긍정적 이슈가 발생했습니다. 임상 성공, FDA 승인, 기술수출 등은 해당 종목 급등의 트리거이며 섹터 전반 상승 랠리로 이어지기도 합니다.',
            ('2차전지', 'negative'): '2차전지, 배터리 섹터에 우려 뉴스가 나왔습니다. 전기차 수요 둔화나 중국 경쟁 심화 이슈는 배터리 셀, 소재, 장비 전 밸류체인에 매도 압력을 줍니다.',
            ('2차전지', 'positive'): '2차전지, 배터리 섹터에 긍정적 이슈가 발생했습니다. 전기차 수요 확대나 대규모 수주는 LG에너지솔루션, 삼성SDI와 에코프로, 포스코퓨처엠 등 소재주까지 함께 끌어올립니다.',
        }
        what = cat_what.get((category, eff_what_sent),
                cat_what.get(('전체', eff_what_sent),
                f"{sector_kr} 관련 이슈가 발생했습니다. 시장 반응을 주의 깊게 관찰하세요."))
    # Gemini 실패시 — 감지된 키워드 태그 + 짧은 해석만 표시
    badge_color = {'positive': '#3B6D11', 'negative': '#791F1F', 'mixed': '#633806', 'neutral': '#5B5BD6'}
    badge_bg    = {'positive': '#EAF3DE', 'negative': '#FCEBEB', 'mixed': '#FAEEDA', 'neutral': '#EEEDFE'}
    bc = badge_color.get(sentiment, '#5B5BD6')
    bb = badge_bg.get(sentiment, '#EEEDFE')

    hit_kws = (neg_hits[:4] if neg_hits else []) + (pos_hits[:2] if pos_hits else [])
    if hit_kws:
        kw_tags = " ".join(
            f"<span style='display:inline-block;margin:2px;padding:2px 8px;border-radius:6px;"
            f"font-size:11px;background:{('#FCEBEB' if kw in neg_hits else '#EAF3DE')};"
            f"color:{('#791F1F' if kw in neg_hits else '#3B6D11')};'>{kw}</span>"
            for kw in hit_kws
        )
        kw_section = "<b>🔍 감지된 키워드</b><br>" + kw_tags + "<br><br>"
    else:
        kw_section = ""

    return kw_section + "<b>📋 이 뉴스는?</b><br>" + what




def generate_strategy(sentiment, category, title="", summary=""):
    chip = {"positive": "chip-buy", "negative": "chip-sell", "mixed": "chip-warn"}.get(sentiment, "chip-neu")

    # generate_ai_summary와 동일한 캐시 키 사용 → Gemini 추가 호출 없음
    shared_key = hashlib.md5(("summary5:" + title[:80]).encode()).hexdigest()
    raw = _gemini_cache.get(shared_key, "")

    if raw:
        def _ext(tag, text):
            m = re.search(r"\[" + tag + r"\]\s*([\s\S]*?)(?=\[|$)", text)
            return m.group(1).strip() if m else ""
        mood   = _ext("시장분위기", raw)
        trade  = _ext("매매방법", raw)
        if mood and trade:
            short_trade = _extract_term(trade, "단기")
            mid_trade   = _extract_term(trade, "중기")
            trade_html  = (
                "<span style='color:#5B5BD6;font-weight:600;'>▶ 단기(1~2주)</span><br>" + short_trade.replace("\n","<br>")
                + "<br><br><span style='color:#FF9F0A;font-weight:600;'>▶ 중기(1~3개월)</span><br>" + mid_trade.replace("\n","<br>")
            ) if short_trade and short_trade != trade else trade.replace("\n","<br>")
            html = (
                "<b>🌡️ 지금 시장 분위기는?</b><br>" + mood.replace("\n","<br>") + "<br><br>"
                "<b>💰 어떻게 사고팔까요?</b><br>" + trade_html
            )
            return html, chip

    # ─── Rule-based 폴백 (Gemini 실패시) ─────────────────────────────
    MOOD = {
        ("반도체","positive"): (
            "반도체·AI 업황이 회복세로 접어들고 있는 강세 국면입니다. "
            "AI 수요 확대로 HBM·고성능 메모리 가격이 상승 중이며, 엔비디아 등 글로벌 빅테크의 설비투자(CAPEX) 확대가 한국 반도체 기업들에게 직접적인 수혜를 주고 있습니다. "
            "현재 투자자들의 심리는 '눌리면 사자'는 분위기로 반도체주에 대한 긍정적 기대감이 높습니다. "
            "단, 단기 급등 이후 차익 실현 매물이 나올 수 있어 모든 좋은 뉴스가 곧바로 상승으로 이어지지는 않습니다."
        ),
        ("반도체","negative"): (
            "반도체 업황이 둔화되는 약세 국면으로 접어들고 있습니다. "
            "메모리 반도체 가격 하락, AI 수요 일부 하향 조정, 재고 증가 등의 악재가 겹치면서 투자자들이 반도체주 비중을 줄이는 분위기입니다. "
            "외국인 투자자들도 삼성전자·SK하이닉스에서 자금을 빼는 흐름이 나타날 수 있어 코스피 전반도 영향을 받습니다. "
            "지금은 '공격'보다 '방어'에 초점을 맞추는 전략이 필요한 시기입니다."
        ),
        ("바이오","positive"): (
            "바이오·제약 섹터에 긍정적인 이벤트(임상 성공, 허가 승인, 기술 수출 등)가 나타나면서 투자 심리가 개선되고 있습니다. "
            "바이오주는 이런 이벤트 드리븐(사건 기반) 장세에서 단기에 큰 수익을 낼 수 있지만, 동시에 높은 변동성으로 손실도 클 수 있습니다. "
            "지금은 해당 종목뿐 아니라 비슷한 치료 영역의 다른 바이오주도 관심을 받는 시기입니다."
        ),
        ("바이오","negative"): (
            "임상 실패나 허가 반려 등 악재로 바이오 섹터 전반의 투자 심리가 크게 냉각된 상태입니다. "
            "바이오주는 한 회사의 실패 뉴스가 섹터 전체를 끌어내리는 경향이 있어 무관한 바이오주까지 하락할 수 있습니다. "
            "지금은 바이오 섹터 전반에 대한 신중한 접근이 필요한 시기입니다. 단기 반등을 노리는 것보다 충분히 소화된 뒤 재진입을 검토하는 것이 안전합니다."
        ),
        ("2차전지","positive"): (
            "전기차 수요 회복 또는 배터리 수주 확대 소식으로 2차전지 섹터 투자 심리가 개선되고 있습니다. "
            "배터리 업종은 전기차 판매량, 원자재(리튬·니켈·코발트) 가격, 중국 CATL 등 경쟁사 동향에 복합적으로 영향을 받습니다. "
            "LG에너지솔루션·삼성SDI 대형주와 에코프로 등 소재주 모두 상승 국면에 있으나, 소재주는 변동성이 훨씬 크다는 점을 기억하세요."
        ),
        ("2차전지","negative"): (
            "전기차 캐즘(일시적 수요 정체) 우려와 배터리 가격 하락으로 2차전지 섹터가 약세를 보이고 있습니다. "
            "중국 전기차·배터리 업체의 공격적인 가격 인하가 국내 업체들의 수익성을 압박하는 구조적 문제가 지속되고 있습니다. "
            "단기 반등이 있더라도 진짜 상승 추세 전환을 확인하기 전까지는 섣불리 비중을 늘리지 않는 것이 좋습니다."
        ),
        ("금융","positive"): (
            "금리 인하 기대감 또는 경기 회복 신호로 시장 전반에 위험자산 선호 분위기가 형성되고 있습니다. "
            "금리가 내려가면 주식의 매력도가 올라가고, 외국인 투자자들이 신흥국(한국 포함) 주식을 더 많이 삽니다. "
            "지금은 시장 전반의 상승 흐름에 올라타는 전략이 유효한 시기이나, 지나친 낙관주의는 금물입니다."
        ),
        ("금융","negative"): (
            "금리 인상 또는 긴축 우려로 시장 전반에 위험자산 회피 분위기가 형성되고 있습니다. "
            "금리가 오르면 성장주(PER이 높은 주식)의 밸류에이션이 낮아지고, 채권이 주식보다 매력적이 됩니다. "
            "지금은 공격적인 매수보다 현금 비중을 높이고 방어적인 포지션을 유지하는 것이 현명한 시기입니다."
        ),
        ("글로벌","positive"): (
            "미국 등 글로벌 주요 시장에서 긍정적인 신호가 나오며 한국 증시도 수혜를 받을 수 있는 환경입니다. "
            "미국 증시(나스닥·S&P500) 상승은 다음 날 한국 증시 시초가를 끌어올리는 강력한 동력이 됩니다. "
            "외국인 투자자들이 한국 주식을 사들이며 원화 강세(환율 하락)가 동반될 수 있어 수출주보다 내수주에 유리할 수 있습니다."
        ),
        ("글로벌","negative"): (
            "글로벌 시장의 불확실성이 높아지면서 안전자산 선호 분위기가 강화되고 있습니다. "
            "미국 증시 하락, 달러 강세, 지정학 리스크 등이 겹치면 외국인들이 한국 주식을 빠르게 팔고 빠져나갑니다. "
            "이런 시기에는 개별 종목의 좋은 뉴스도 시장 전체 하락에 묻히는 경우가 많으니 무리한 매수는 자제하세요."
        ),
    }

    _S = "<span style='color:#5B5BD6;font-weight:600;'>▶ 단기(1~2주)</span> "
    _M = "<br><span style='color:#FF9F0A;font-weight:600;'>▶ 중기(1~3개월)</span> "

    TRADE = {
        ("반도체","positive"): (
            _S +
            "<b>미보유자:</b> 갭 상승 +3% 이내 → 투자금의 30%를 1차 매수. +5% 이상 갭업이면 추격 금지, 2~3일 소화 후 눌림목(-3%) 진입. "
            "<b>보유자:</b> 1차 목표가 <b>+8%</b> 도달 시 절반 익절, 나머지는 <b>+15%</b>에서 정리. "
            "<b>손절선: 매수가 기준 -5%</b> (예: 80,000원 매수 → 76,000원 이탈 시 즉시 손절). 분할 매수: 1차 30% → 2차 30% → 3차 40%."
            + _M +
            "외국인 순매수가 2주 이상 지속 확인되면 비중을 포트폴리오의 30~40%까지 확대. "
            "중기 목표가 <b>+20~25%</b>. SOX 지수가 주간 기준 하락 전환되면 비중을 절반으로 줄이는 기준을 사전에 정해두세요."
        ),
        ("반도체","negative"): (
            _S +
            "<b>보유자:</b> 손실 -5% 이내 → 즉시 손절 검토. -5~10% 손실 → 반등 시 분할 매도로 비중 축소. -10% 초과 → 오늘 50% 매도 후 나머지는 -15% 도달 시 전량 정리. "
            "<b>미보유자:</b> 매수 금지. 외국인 순매수 전환 + 거래량 감소(매도 소진) 신호가 동시에 나타날 때까지 대기. "
            "<b>물타기 절대 금지</b> — 하락 추세 확인 전 추가 매수는 손실을 키웁니다."
            + _M +
            "업황 회복 신호(D램 현물가 반등 + 외국인 3일 연속 순매수)가 나타나면 투자금의 10~15% 소량으로 재진입. "
            "중기 재진입 후 손절선은 <b>-7%</b>로 평소보다 빡빡하게 설정하세요."
        ),
        ("바이오","positive"): (
            _S +
            "<b>이벤트 발표 전:</b> 이미 +20% 이상 올랐다면 '소문에 사고 뉴스에 팔라' — 결과 발표 전 보유량의 30~50% 익절 고려. "
            "<b>이벤트 발표 후 급등 시:</b> 당일 +10% 이상 급등이면 추격 매수 금지, 2~3일 소화 후 재진입. "
            "<b>손절선: 매수가 -8%</b> (예: 50,000원 매수 → 46,000원 이탈 시 즉시 손절). 1차 목표가: <b>+15%</b>."
            + _M +
            "임상 성공 후 추가 파이프라인(후속 신약 후보) 진행 상황을 확인하며 보유 여부 판단. "
            "FDA 승인 완료 + 매출 가시화 시점까지 비중을 포트폴리오의 <b>10% 이하</b>로 유지하세요. 중기 목표가: <b>+30~50%</b> (변동성 매우 큼)."
        ),
        ("바이오","negative"): (
            _S +
            "<b>보유자(급락 시):</b> 임상 실패·허가 반려 → 오늘 반등 구간에서 무조건 비중을 절반 이상 축소. 하한가(-30%) 연속 가능성 → '회복 기다리기'는 바이오 최악의 전략. "
            "<b>미보유자:</b> 최소 2주 경과 후 거래량이 정상화되고 주가 하락 속도가 줄면 소량(투자금 5%) 진입 검토. "
            "<b>손절선: -8%</b> — 바이오는 변동성이 크므로 일반 주식보다 손절선을 넓게 잡되, 반드시 지켜야 합니다."
            + _M +
            "해당 기업의 다른 파이프라인 가치를 재평가. 실패 파이프라인 외 유효한 신약 후보가 남아 있으면 중기 매수 기회. "
            "재진입 기준: 주가가 20일 이동평균선을 회복 + 외국인·기관 순매수 전환. 비중은 포트폴리오의 <b>5% 이하</b>로 제한."
        ),
        ("2차전지","positive"): (
            _S +
            "<b>분할 매수:</b> 1차 투자금의 25% → 2~3일 후 상승 확인 시 2차 25% 추가. 총 50% 초과 금지. "
            "<b>손절선:</b> 대형주(LG에너지·삼성SDI) <b>-5%</b>, 소재주(에코프로·포스코퓨처엠) <b>-7~8%</b>. "
            "1차 목표가: 대형주 <b>+8~10%</b>, 소재주 <b>+15~20%</b> (소재주는 변동성이 2~3배 큽니다)."
            + _M +
            "전기차 글로벌 판매량 데이터(월별)가 2개월 연속 증가 확인 시 비중을 30%까지 확대. "
            "중기 목표가: <b>+20~30%</b>. CATL 가격 인하 재개 or 국내 기업 수주 취소 뉴스가 나오면 즉시 비중 재검토."
        ),
        ("2차전지","negative"): (
            _S +
            "<b>보유자:</b> <b>-7%</b> 손절선이 지켜지지 않았다면 오늘 50% 매도로 손실 제한. 단기 반등 시 나머지도 정리. "
            "<b>미보유자:</b> 전기차 월별 판매량이 회복되는 시점까지 진입 금지. 저점 매수 시도는 추측성 매매. "
            "<b>대안:</b> 2차전지 비중을 줄이고 배당주·방산주 등 방어적 섹터로 교체 고려."
            + _M +
            "EV 캐즘이 구조적이라면 4~6개월 약세 가능. '언젠가 오를 것'이라는 기대로 버티기 금지. "
            "재진입 기준: 국내 배터리 기업 신규 수주 공시 + 외국인 순매수 전환 + 리튬 가격 반등. 3가지 중 2가지 이상 충족 시 투자금의 10% 소량 재진입."
        ),
        ("금융","positive"): (
            _S +
            "<b>성장주 비중 확대:</b> 금리 인하 국면에서 바이오·반도체·플랫폼 성장주가 가치주보다 더 오릅니다. 투자금의 10~20%를 성장주 ETF로 이동. "
            "<b>매수 주의:</b> 금리 인하 '기대감'이 이미 반영됐을 수 있습니다. 실제 발표 시 '소문에 사고 뉴스에 팔자' 하락이 나올 수 있으므로 인하 발표 직전 일부 익절. "
            "<b>손절선: -5%</b> (시장 전반이 좋을 때는 손절선을 일반 수준 유지)."
            + _M +
            "금리 인하 사이클 전체(보통 1~2년)에 걸쳐 성장주 비중을 점진적으로 확대하는 전략이 유효. "
            "중기 목표: 포트폴리오에서 성장주 비중을 40~50%까지 확대. 단, 경기 침체 신호(실업률 급등, GDP 마이너스)가 나오면 전략 수정 필요."
        ),
        ("금융","negative"): (
            _S +
            "<b>현금 비중 즉시 확대:</b> 투자금의 <b>30~40%</b>를 현금·단기채·MMF로 전환. "
            "<b>성장주 손절:</b> PER 30배 이상 성장주는 <b>-5%</b> 손절선 설정 후 지키기. 금리 상승기에 성장주 낙폭이 가장 큽니다. "
            "방어주(KT·SKT·배당주)로 포트폴리오 리밸런싱."
            + _M +
            "금리 고점 확인(중앙은행 인상 중단 선언) 후 성장주 재진입 준비. 고점 신호: 소비자물가(CPI)가 2개월 연속 하락. "
            "재진입 시 손절선은 <b>-7%</b>로 초기보다 빡빡하게. 금리 사이클 전환에 최소 3~6개월 소요됩니다."
        ),
        ("글로벌","positive"): (
            _S +
            "<b>외국인 수혜 종목 우선:</b> 당일 외국인 순매수 상위 종목(오후 3시 이후 확인) 중 삼성전자·SK하이닉스·현대차 위주로 진입. "
            "갭 상승 +3% 이내 → 투자금의 15~20% 1차 매수. 환율 확인: 원화 강세(환율 하락)면 내수주·성장주 유리. "
            "<b>손절선: -5%</b>. 글로벌 분위기가 하루 만에 급변할 수 있으니 단기 진입은 소량으로 시작."
            + _M +
            "외국인 순매수가 2주 이상 지속되면 코스피 대형주 비중을 30~40%까지 확대. "
            "중기 목표가: <b>+15~20%</b>. FOMC 금리 결정이나 중국 PMI 쇼크가 오면 즉시 비중 재검토."
        ),
        ("글로벌","negative"): (
            _S +
            "<b>손절선 강화: -3%</b> (평소 -5%에서 더 빡빡하게). 글로벌 불확실성 구간에서는 손실을 작게 끊는 것이 핵심. "
            "주식 비중을 <b>50% 이하</b>로 낮추고, 달러 예금·금 ETF(KODEX 골드선물)로 일부 헤지. "
            "<b>재진입 신호:</b> VIX 지수 30 이상에서 하락 전환 + 외국인 매도가 3~5일 후 순매수 전환 시."
            + _M +
            "글로벌 리스크(지정학·금리·경기침체) 해소 여부를 확인한 후 비중 정상화. "
            "재진입 시 손절선은 <b>-5%</b>로 복귀. 리스크 요인이 복수라면(예: 금리 인상 + 지정학 동시) 회복에 2~3개월 소요 가능하므로 서두르지 마세요."
        ),
    }

    RISK = {
        ("반도체","positive"): (
            "반도체 섹터는 글로벌 경기와 AI 투자 사이클에 민감하게 반응합니다. 포트폴리오에서 반도체 비중은 30~40%를 초과하지 않도록 하고, 삼성전자+SK하이닉스처럼 대형주 위주로 구성하면 변동성을 줄일 수 있습니다. "
            "SOX 지수(미국 반도체 ETF)가 -3% 이상 하락하면 국내 반도체주도 다음 날 큰 폭 하락이 예상되므로 뉴스를 항상 체크하세요. "
            "미국의 대중국 반도체 수출 규제 강화, 엔비디아 실적 발표, 한국 기업들의 분기 실적 발표 시즌에 변동성이 특히 커집니다."
        ),
        ("반도체","negative"): (
            "지금은 반도체 비중을 기존의 50% 수준으로 줄이는 것을 권장합니다. 손절선을 미리 설정하지 않으면 작은 손실이 큰 손실로 커집니다. "
            "단순히 '삼성전자는 망하지 않으니 기다리면 된다'는 생각은 단기 투자에서 손실을 키웁니다. 반도체 업황 회복 신호가 나올 때까지 비중 축소 후 재진입이 현명합니다. "
            "최악의 시나리오: AI 버블 붕괴로 HBM 수요가 급감할 경우 삼성전자·SK하이닉스 주가가 30~40% 하락할 수 있습니다. 이런 경우에도 포트폴리오 전체가 위험하지 않도록 분산 투자를 하세요."
        ),
        ("바이오","positive"): (
            "바이오주는 이벤트(임상 결과, 허가 심사) 발표 전후에 주가가 50% 이상 오르거나 내릴 수 있는 극단적 변동성 섹터입니다. "
            "포트폴리오에서 바이오 비중은 절대 10~15%를 초과하지 마세요. 한 번의 임상 실패가 투자금을 반토막 낼 수 있습니다. "
            "여러 바이오주에 분산(3~5개 종목)하더라도 임상 결과가 같은 시기에 집중되면 동반 하락할 수 있으므로 발표 일정을 반드시 확인하세요."
        ),
        ("바이오","negative"): (
            "임상 실패 시 -30~60% 급락이 하루에 발생할 수 있습니다. 이미 손실 중이라면 '회복을 기다리는' 전략은 바이오에서 가장 위험합니다. "
            "바이오주 매매의 원칙: ① 임상 결과 발표 전 반드시 일부 익절 ② 허가 결과 불확실한 종목은 소액만 투자 ③ 손절선 -8% 엄격 적용 ④ 전체 포트폴리오에서 10% 이하 유지. "
            "최악의 시나리오 대비: 임상 실패 뉴스가 장 시작 전 나오면 시초가가 하한가로 시작, 당일 매도 기회조차 없을 수 있습니다."
        ),
        ("2차전지","positive"): (
            "2차전지 소재주(에코프로·포스코퓨처엠 등)는 PER(주가수익비율)이 매우 높아 뉴스에 따른 주가 변동이 극단적입니다. "
            "대형주(LG에너지솔루션·삼성SDI) 위주로 포트폴리오를 구성하고, 소재주는 전체의 5~10%로 제한하는 것이 안전합니다. "
            "원자재(리튬·니켈) 가격 변동, 중국 CATL의 공격적 가격 인하, 전기차 판매량 월별 데이터를 지속적으로 모니터링하세요."
        ),
        ("2차전지","negative"): (
            "전기차 캐즘 장기화 시 2차전지 섹터 전체가 6~12개월 약세를 유지할 수 있습니다. '언젠가 오르겠지'라는 막연한 기대로 버티기보다 손실을 줄이고 다른 섹터를 찾는 것이 효율적입니다. "
            "분할 손절 전략: 현재 -10% 손실이라면 오늘 절반 손절, 나머지는 -15%에서 추가 손절. 한 번에 전량 손절이 심리적으로 어렵다면 이렇게 나눠서 손절하세요. "
            "최악 시나리오: 중국 전기차 저가 공세가 심화되고 미국 IRA 보조금이 축소될 경우 한국 배터리 기업들의 주가는 현재 대비 30~50% 추가 하락 가능성도 있습니다."
        ),
        ("금융","positive"): (
            "금리 인하 사이클이 시작되면 부동산 관련주(건설·리츠)도 수혜를 받지만, 경기 침체가 동반된 금리 인하라면 오히려 수익성이 악화될 수 있습니다. "
            "단순히 '금리가 내리면 주식이 오른다'는 공식은 맞지 않을 때도 있습니다. 금리 인하의 이유(경기 회복 vs. 경기 침체 대응)를 함께 확인하세요. "
            "포트폴리오 전체 주식 비중을 최대 70%로 제한하고, 나머지는 채권(안전자산)으로 유지하는 균형 잡힌 자산 배분을 권장합니다."
        ),
        ("금융","negative"): (
            "금리 인상이 장기화될 경우 성장주 전체가 30~50% 하락하는 '기술주 약세장'이 올 수 있습니다. 2022년 상황이 반복될 수 있음을 염두에 두세요. "
            "방어 전략: ① 주식 비중 50% 이하로 축소 ② 달러 예금·단기채 비중 확대 ③ 배당수익률 4% 이상 종목(통신·유틸리티)으로 리밸런싱 ④ 부동산 투자는 금리 안정화 이후로 미룰 것. "
            "금리 고점 확인 후 '금리 인하 기대감'이 형성되는 시점이 성장주 재진입 타이밍입니다."
        ),
        ("글로벌","positive"): (
            "글로벌 호재라도 미국 연준(Fed)의 금리 정책이나 지정학 리스크 변화로 분위기가 급변할 수 있습니다. "
            "포트폴리오에서 해외 ETF(미국 S&P500 ETF 등) 비중이 20~30% 있다면 달러 강세·약세에 따른 환차익/환차손도 함께 고려하세요. "
            "글로벌 시장은 美 연준 FOMC 회의(연 8회), 중국 경제 지표, 유가 변동 등에 민감합니다. 이 이벤트 전후에 변동성이 크게 높아집니다."
        ),
        ("글로벌","negative"): (
            "글로벌 불확실성 구간에서는 분산 투자가 최선의 방어입니다. 한국 주식에만 집중된 포트폴리오는 외국인 대규모 매도 시 큰 손실을 봅니다. "
            "달러 자산(달러 예금, 미국 국채 ETF) 보유 비중을 전체의 20~30%로 높이면 원화 약세 시 일부 손실을 상쇄할 수 있습니다. "
            "최악의 시나리오: 글로벌 금융위기 재현 시 코스피가 30~40% 하락하는 경우도 역사적으로 있었습니다. 레버리지(빚 투자)는 이런 시기에 특히 위험합니다."
        ),
    }

    CHECK = {
        ("반도체","positive"): (
            "① <b>SOX 지수(미국 반도체 ETF)</b> 매일 확인 — SOX가 상승 중이면 국내 반도체주도 긍정적. "
            "② <b>삼성전자·SK하이닉스 외국인 순매수</b> — 외국인이 사면 상승 추세 지속 신호. "
            "③ <b>엔비디아 실적 발표</b>(분기마다) — 엔비디아가 좋으면 HBM 수요도 좋다는 신호. "
            "④ <b>D램 현물 가격</b>(weekly) — 가격이 올라가면 반도체 업황 개선 확인."
        ),
        ("반도체","negative"): (
            "① <b>메모리 반도체 현물 가격</b> — 하락이 멈추고 반등하면 업황 바닥 신호. "
            "② <b>외국인 순매수 전환</b> — 3일 이상 연속 순매수면 추세 전환 가능성. "
            "③ <b>주요 고객사(엔비디아·애플·구글) 발주 동향</b> — 주문 증가 뉴스가 나오면 재진입 시점. "
            "④ <b>삼성전자 잠정 실적 발표</b>(분기 초) — 예상보다 좋으면 단기 반등 트리거."
        ),
        ("바이오","positive"): (
            "① <b>임상 2·3상 결과 발표 일정</b> — 발표 전 주가가 많이 올랐다면 익절 타이밍 체크. "
            "② <b>FDA 심사 일정(PDUFA Date)</b> — 허가 결정일 2~3주 전부터 기대감으로 오르는 패턴. "
            "③ <b>글로벌 빅파마 기술 수출 계약</b> — 계약금 규모와 마일스톤 조건을 확인. "
            "④ <b>해당 섹터 경쟁 파이프라인 동향</b> — 비슷한 신약이 실패하면 단독 수혜, 성공하면 경쟁 심화."
        ),
        ("바이오","negative"): (
            "① <b>동일 적응증 다른 기업 임상 동향</b> — 경쟁사 실패가 악재, 성공이 오히려 섹터 신뢰 회복. "
            "② <b>거래량 추이</b> — 급락 후 거래량이 줄어들면(매도 소진) 단기 반등 가능성. "
            "③ <b>해당 기업의 다른 파이프라인 발표 일정</b> — 다음 임상 결과가 주가 회복의 열쇠. "
            "④ <b>외국인·기관 순매수 전환 여부</b> — 전문 투자자들이 다시 사기 시작하면 신뢰 회복 신호."
        ),
        ("2차전지","positive"): (
            "① <b>월별 글로벌 전기차 판매량</b>(매월 초 발표) — 판매량 증가 = 배터리 수요 증가 확인. "
            "② <b>리튬·니켈 원자재 가격</b> — 원자재 하락 = 배터리 업체 마진 개선 긍정 신호. "
            "③ <b>LG에너지솔루션·삼성SDI 수주 공시</b> — 대형 수주 계약 발표 시 주가 상승 트리거. "
            "④ <b>미국 IRA 배터리 보조금 정책 동향</b> — 보조금 확대/축소가 한국 배터리 기업 수혜에 직접 영향."
        ),
        ("2차전지","negative"): (
            "① <b>전기차 판매량 데이터</b>(월별) — 예상 대비 실제 판매량이 증가 전환하면 재진입 신호. "
            "② <b>CATL(중국 배터리 1위) 주가·동향</b> — CATL이 약세면 한국 배터리주도 약세 지속 가능성. "
            "③ <b>국내 배터리 기업 수주 잔고</b> — 분기 실적 발표 시 수주 잔고가 증가하면 바닥 확인 신호. "
            "④ <b>배터리 원자재 가격 안정화</b> — 리튬 가격이 안정되면 마진 회복 기대감 형성 가능."
        ),
        ("금융","positive"): (
            "① <b>미국 연준(Fed) FOMC 회의</b>(연 8회, 한국 시간 새벽) — 금리 결정·발언 방향이 시장을 좌우. "
            "② <b>한국은행 금통위 결정</b>(격월) — 국내 기준금리 결정이 은행주·부동산 관련주에 직접 영향. "
            "③ <b>환율(원/달러)</b>(매일) — 1,400원 이상이면 외국인 이탈 우려, 1,300원 이하면 외국인 유입 기대. "
            "④ <b>외국인 코스피 순매수 추이</b> — 3거래일 이상 연속 순매수면 시장 상승 추세 신호."
        ),
        ("금융","negative"): (
            "① <b>미국 CPI(물가) 발표</b>(매월 중순) — 물가가 높으면 금리 추가 인상 우려. "
            "② <b>연준 위원 발언</b>(수시) — '매파적(금리 올려야)' 발언이 나오면 주식 약세. "
            "③ <b>환율 방향</b> — 달러가 강세(환율 상승)면 외국인이 한국 주식 팔고 나가는 신호. "
            "④ <b>VIX(공포 지수)</b> — 20 이상이면 불안, 30 이상이면 공황. VIX가 하락 전환하면 매수 타이밍."
        ),
        ("글로벌","positive"): (
            "① <b>미국 나스닥·S&P500 일일 등락</b> — 한국 증시 전날 뉴욕 마감 결과가 다음 날 시초가 결정. "
            "② <b>외국인 코스피 순매수</b>(장 마감 후 확인) — 외국인이 사면 상승 추세 확인. "
            "③ <b>원/달러 환율</b> — 환율 하락(원화 강세)이 동반되면 외국인 자금 유입 신호. "
            "④ <b>중국 경기 지표</b>(PMI 등) — 중국 경기 회복이 한국 수출주에 수혜를 줍니다."
        ),
        ("글로벌","negative"): (
            "① <b>VIX 지수</b>(매일) — 30 이상으로 급등하면 공황 국면, 이후 하락 전환 시 매수 기회. "
            "② <b>미국 국채 10년 금리</b> — 급등 시 성장주 타격, 안정·하락 시 주식 회복 신호. "
            "③ <b>달러 인덱스(DXY)</b> — 달러 강세(인덱스 상승) = 신흥국 주식 약세. 달러 약세 전환이 한국 증시 회복 신호. "
            "④ <b>지정학 리스크 뉴스</b> — 중동 분쟁, 미중 무역 갈등 등 지정학 리스크가 완화될 때 재진입 타이밍."
        ),
    }

    def _get(d, cat, sent, fallback_sent="positive"):
        k = (cat, sent)
        if k in d:
            return d[k]
        k2 = (cat, fallback_sent)
        if k2 in d:
            return d[k2]
        return list(d.values())[0] if d else ""

    _ts = title + " " + (summary or "")
    _neg_h = [kw for kw in NEGATIVE_KEYWORDS if kw in _ts]
    _pos_h = [kw for kw in POSITIVE_KEYWORDS if kw in _ts]
    eff_sent = (sentiment if sentiment in ["positive", "negative"]
                else "negative" if (sentiment == "mixed" or _neg_h)
                else "positive" if _pos_h
                else "positive")
    mood_text  = _get(MOOD,  category, eff_sent)
    trade_text = _get(TRADE, category, eff_sent)
    risk_text  = _get(RISK,  category, eff_sent)
    check_text = _get(CHECK, category, eff_sent)

    strategy_html = (
        "<b>🌡️ 지금 시장 분위기는?</b><br>" + mood_text + "<br><br>"
        "<b>💰 어떻게 사고팔까요?</b><br>" + trade_text + "<br><br>"
        "<b>🛡️ 내 돈 지키는 법</b><br>" + risk_text + "<br><br>"
        "<b>📌 앞으로 체크할 것들</b><br>" + check_text
    )
    return strategy_html, chip


# ─────────────────────────────────────────────────────────
# 네이버 뉴스 검색 API
# ─────────────────────────────────────────────────────────

_NAVER_ID     = os.getenv("NAVER_CLIENT_ID", "")
_NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 출처 도메인 → 매체명 매핑
_SOURCE_MAP = {
    "yna.co.kr":       "연합뉴스",
    "hankyung.com":    "한국경제",
    "mk.co.kr":        "매일경제",
    "chosun.com":      "조선비즈",
    "joins.com":       "중앙일보",
    "hani.co.kr":      "한겨레",
    "sedaily.com":     "서울경제",
    "etnews.com":      "전자신문",
    "edaily.co.kr":    "이데일리",
    "newsis.com":      "뉴시스",
    "heraldcorp.com":  "헤럴드경제",
    "khan.co.kr":      "경향신문",
    "fnnews.com":      "파이낸셜뉴스",
    "inews24.com":     "아이뉴스24",
    "dt.co.kr":        "디지털타임스",
    "zdnet.co.kr":     "지디넷코리아",
}


def _fetch_naver_news(query: str, max_items: int = 15, sort: str = "date") -> list:
    """네이버 뉴스 검색 API 호출. 실패 시 빈 목록 반환."""
    if not _NAVER_ID or not _NAVER_SECRET:
        return []
    try:
        import requests
        import html as html_mod

        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id":     _NAVER_ID,
                "X-Naver-Client-Secret": _NAVER_SECRET,
            },
            params={"query": query, "display": min(max_items * 2, 100), "sort": sort},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("items", []):
            title = html_mod.unescape(re.sub(r"<[^>]+>", "", item.get("title", ""))).strip()
            desc  = html_mod.unescape(re.sub(r"<[^>]+>", "", item.get("description", ""))).strip()
            link  = item.get("link") or item.get("originallink", "")
            orig  = item.get("originallink", "")

            # 발행일
            pub = ""
            pub_str = item.get("pubDate", "")
            if pub_str:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_str).astimezone(timezone(timedelta(hours=9)))
                    pub = dt.strftime("%m/%d %H:%M")
                except Exception:
                    pass

            # 출처 매체명
            source = "네이버뉴스"
            for domain, name in _SOURCE_MAP.items():
                if domain in orig:
                    source = name
                    break

            if title:
                results.append({
                    "title":    title,
                    "summary":  desc,
                    "url":      link,
                    "source":   source,
                    "pub_date": pub,
                })
            if len(results) >= max_items:
                break

        return results
    except Exception:
        return []


def _is_stock_relevant(item: dict) -> bool:
    """주식·경제 관련 뉴스인지 간단 필터."""
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    if any(kw in text for kw in _NON_STOCK_KW):
        return False
    return any(kw.lower() in text for kw in _STOCK_RELEVANCE_KW)


def _classify_item(item: dict) -> dict:
    """뉴스 항목에 sentiment / category / badge_type 필드 추가."""
    title   = item.get("title", "")
    summary = item.get("summary", "")
    cat     = classify_category(title, summary)
    sent    = classify_sentiment(title + " " + summary)
    return {
        **item,
        "category":      cat,
        "sentiment":     sent["sentiment"],
        "sentiment_label": sent["label"],
        "badge_type":    sent["badge_type"],
    }


def _dedup(items: list) -> list:
    """제목 앞 20자 기준 중복 제거."""
    seen, out = set(), []
    for it in items:
        key = it.get("title", "")[:20]
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


# ─────────────────────────────────────────────────────────
# 공개 fetch 함수 (네이버 우선 → RSS 폴백)
# ─────────────────────────────────────────────────────────

def fetch_market_news(max_items: int = 15) -> list:
    """시장 전체 뉴스 수집 (코스피/코스닥/증시)."""
    # 네이버 API — 여러 쿼리를 나눠서 수집 후 합산
    queries = [
        ("코스피 코스닥 증시 오늘",   8),
        ("외국인 기관 수급 증시",       4),
        ("금리 환율 주식 영향",         4),
    ]
    raw = []
    for q, n in queries:
        raw.extend(_fetch_naver_news(q, n, sort="date"))
    raw = _dedup(raw)

    # 주식 관련 필터
    raw = [it for it in raw if _is_stock_relevant(it)]

    # 폴백: 네이버 결과 부족하면 RSS 보완
    if len(raw) < 5:
        feed_quotas = [
            (_YONHAP_ECONOMY_RSS, 8, "연합뉴스"),
            (_HANKYUNG_RSS,       5, "한국경제"),
            (_MK_RSS,             5, "매일경제"),
        ]
        rss = _merge_feeds(feed_quotas, max_items)
        raw = _dedup(raw + rss)
        if not raw:
            raw = _parse_feed(_google_news_url("코스피 코스닥 증시 주식"), max_items, "구글뉴스")

    # 감성 + 카테고리 사전 분류
    return [_classify_item(it) for it in raw[:max_items]]


def fetch_category_news(category: str, max_items: int = 15) -> list:
    """카테고리별 뉴스 수집."""
    cfg = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["전체"])
    query = cfg["query"]

    raw = _fetch_naver_news(query, max_items, sort="date")

    # 폴백
    if len(raw) < 3:
        raw = _parse_feed(_google_news_url(query), max_items, "구글뉴스")

    raw = _dedup(raw)
    return [_classify_item(it) for it in raw[:max_items]]


def _stock_brief_fallback(title: str, sentiment: str) -> str:
    """Gemini 실패 시 키워드 기반 1줄 요약."""
    t = title.lower()
    if sentiment == "positive":
        if any(k in t for k in ["실적", "영업이익", "매출"]):
            return "실적 호조 신호 — 단기 상승 모멘텀 기대"
        if any(k in t for k in ["수주", "계약", "협력"]):
            return "신규 사업 확대 — 중기 성장 기대감 긍정적"
        if any(k in t for k in ["목표주가", "상향", "매수"]):
            return "애널리스트 긍정 평가 — 단기 수급 개선 가능"
        return "호재성 뉴스 — 단기 주가 상승 가능성, 비중 유지"
    elif sentiment == "negative":
        if any(k in t for k in ["적자", "손실", "하락"]):
            return "실적 악화 우려 — 손절선 점검 후 비중 축소 고려"
        if any(k in t for k in ["소송", "제재", "조사"]):
            return "리스크 이슈 — 추가 하락 가능, 관망 권장"
        if any(k in t for k in ["공급", "경쟁", "과잉"]):
            return "업황 부담 — 저점 확인 후 분할 매수 검토"
        return "악재성 뉴스 — 추가 하락 가능, 손절선 점검 필요"
    elif sentiment == "mixed":
        return "복합 신호 — 추가 정보 확인 후 대응, 단기 관망"
    else:
        return "중립 뉴스 — 주가 영향 제한적, 보유 유지"


def _generate_stock_brief(title: str, sentiment: str, stock_name: str) -> str:
    """뉴스 제목 → 투자자 관점 1줄 요약. Gemini 우선, 실패 시 키워드 폴백."""
    cache_key = hashlib.md5(("brief:" + title[:80]).encode()).hexdigest()
    sent_kor = {"positive": "호재", "negative": "악재", "mixed": "혼조", "neutral": "중립"}.get(sentiment, "중립")
    prompt = (
        f"다음은 '{stock_name}' 관련 뉴스 제목입니다: \"{title}\"\n"
        f"감성: {sent_kor}\n\n"
        f"주식 투자자 입장에서 이 뉴스의 의미와 대응 방향을 25자 이내 1문장으로 요약하세요. "
        f"예시: '실적 기대감으로 단기 상승 가능, 눌림목 매수 고려'\n"
        f"문장만 출력하세요."
    )
    result = _call_gemini(prompt, cache_key)
    return result if result else _stock_brief_fallback(title, sentiment)


def fetch_stock_news(stock_name: str, max_items: int = 10) -> list:
    """종목명으로 뉴스 검색."""
    query = stock_name + " 주가 주식"
    raw = _fetch_naver_news(query, max_items, sort="date")

    # 폴백
    if len(raw) < 3:
        from urllib.parse import quote_plus as _qp
        url = "https://news.google.com/rss/search?q=" + _qp(query) + "&hl=ko&gl=KR&ceid=KR:ko"
        raw = _parse_feed(url, max_items, "구글뉴스")

    raw = _dedup(raw)
    items = [_classify_item(it) for it in raw[:max_items]]
    for item in items:
        item["brief"] = _generate_stock_brief(item.get("title", ""), item.get("sentiment", "neutral"), stock_name)
    return items


def summarize_sentiment(items):
    counts = {"positive": 0, "negative": 0, "mixed": 0, "neutral": 0}
    for item in items:
        s = item.get("sentiment", "neutral")
        counts[s] = counts.get(s, 0) + 1
    total = len(items) or 1
    dominant = max(counts, key=counts.get)
    score = (counts["positive"] - counts["negative"]) / total
    label_map = {"positive": "긍정", "negative": "부정", "mixed": "혼조", "neutral": "중립"}
    return {
        "overall":        dominant,
        "dominant":       dominant,
        "label":          label_map.get(dominant, "중립"),
        "score":          round(score, 2),
        "positive_count": counts["positive"],
        "negative_count": counts["negative"],
        "mixed_count":    counts["mixed"],
        "neutral_count":  counts["neutral"],
        "counts":         counts,
        "total":          total,
    }


def rank_by_importance(items: list) -> list:
    """뉴스 목록을 중요도 점수 내림차순으로 정렬해 반환."""
    def _score(item):
        return _calc_impact_score(
            item.get("title", ""),
            item.get("summary", ""),
            item.get("category", "전체"),
        )
    return sorted(items, key=_score, reverse=True)


def enrich_top10_summaries(items: list) -> list:
    """상위 뉴스 목록에 AI 요약/전략 필드를 추가해 반환. (상위 3개만 Gemini 순차 처리)"""
    enriched = []
    for idx, item in enumerate(items):
        title   = item.get("title", "")
        summary = item.get("summary", "")
        sentiment_info = classify_sentiment(title + " " + summary)
        category = item.get("category") or classify_category(title, summary)
        sentiment = sentiment_info["sentiment"]
        if idx < 3:
            ai_summary = item.get("ai_summary") or generate_ai_summary(title, summary, sentiment, category)
            strategy, _ = generate_strategy(sentiment, category, title, summary)
        else:
            ai_summary = item.get("ai_summary") or ""
            strategy = ""
        enriched.append({
            **item,
            "category":        category,
            "sentiment":       sentiment,
            "sentiment_label": sentiment_info["label"],
            "badge_type":      sentiment_info["badge_type"],
            "ai_summary":      ai_summary,
            "strategy":        strategy,
            "related_stocks":  item.get("related_stocks") or extract_related_stocks(title, summary, category),
        })
    return enriched
