"""
disclosure.py — DART 공시 수집 + Gemini AI 분석
- corpCode.xml 다운로드로 stock_code → corp_code 매핑
- DART OpenAPI로 최근 공시 목록 수집
- Gemini로 공시 내용 쉬운 설명 + 주가 영향 흐름 생성
"""

import os
import io
import zipfile
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

_DART_KEY  = os.getenv("DART_API_KEY", "")
_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
_gemini_model = None
DART_BASE  = "https://opendart.fss.or.kr/api"

# 종목코드 → corp_code 캐시 (프로세스 내 유지)
_CORP_MAP: dict[str, str] = {}
_corp_map_loaded = False

_REPORT_TYPE = {
    "A": "정기공시", "B": "주요사항보고", "C": "발행공시",
    "D": "지분공시", "E": "기타공시", "F": "외부감사관련",
    "G": "펀드공시", "H": "자산유동화", "I": "거래소공시", "J": "공정위공시",
}


# ─────────────────────────────────────────────────────────
# Gemini 초기화
# ─────────────────────────────────────────────────────────
def _gemini():
    global _gemini_model
    if _gemini_model is None and _GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=_GEMINI_KEY)
            _gemini_model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={"temperature": 0.3, "max_output_tokens": 800},
            )
        except Exception:
            pass
    return _gemini_model


# ─────────────────────────────────────────────────────────
# 기업 코드 맵 (ZIP 다운로드 → XML 파싱)
# ─────────────────────────────────────────────────────────
def _load_corp_map():
    """DART corpCode.xml 다운로드해서 stock_code → corp_code 사전 구축"""
    global _corp_map_loaded
    if _corp_map_loaded or not _DART_KEY:
        return
    try:
        r = requests.get(
            f"{DART_BASE}/corpCode.xml",
            params={"crtfc_key": _DART_KEY},
            timeout=15,
        )
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        xml_bytes = zf.read("CORPCODE.xml")
        root = ET.fromstring(xml_bytes)
        for item in root.findall("list"):
            stock_cd = (item.findtext("stock_code") or "").strip()
            corp_cd  = (item.findtext("corp_code") or "").strip()
            if stock_cd and corp_cd:
                _CORP_MAP[stock_cd] = corp_cd
        _corp_map_loaded = True
    except Exception:
        pass


def _get_corp_code(stock_code: str) -> str:
    _load_corp_map()
    return _CORP_MAP.get(stock_code.zfill(6), "")


# ─────────────────────────────────────────────────────────
# 공시 목록 수집
# ─────────────────────────────────────────────────────────
def fetch_disclosures(stock_code: str, stock_name: str, days: int = 30, max_items: int = 4) -> list:
    if not _DART_KEY:
        return []

    corp_code = _get_corp_code(stock_code)
    if not corp_code:
        return []

    end_date   = datetime.today()
    start_date = end_date - timedelta(days=days)

    try:
        r = requests.get(
            f"{DART_BASE}/list.json",
            params={
                "crtfc_key": _DART_KEY,
                "corp_code": corp_code,
                "bgn_de": start_date.strftime("%Y%m%d"),
                "end_de":  end_date.strftime("%Y%m%d"),
                "page_count": max_items,
                "sort": "date",
                "sort_mth": "desc",
            },
            timeout=10,
        )
        data = r.json()
    except Exception:
        return []

    if data.get("status") != "000":
        return []

    results = []
    for item in (data.get("list") or [])[:max_items]:
        title      = item.get("report_nm", "")
        date_str   = item.get("rcept_dt", "")
        rtype_code = item.get("pblntf_ty", "E")
        rtype_lbl  = _REPORT_TYPE.get(rtype_code, "기타")

        try:
            date_disp = datetime.strptime(date_str, "%Y%m%d").strftime("%Y.%m.%d")
        except Exception:
            date_disp = date_str

        analysis, impact = _analyze_disclosure(title, stock_name)
        results.append({
            "title": title,
            "date": date_disp,
            "report_type": rtype_lbl,
            "analysis": analysis,
            "impact": impact,
        })

    return results


# ─────────────────────────────────────────────────────────
# Gemini 공시 분석
# ─────────────────────────────────────────────────────────
def _analyze_disclosure(title: str, stock_name: str) -> tuple:
    model = _gemini()
    if not model:
        return _fallback_analysis(title), _fallback_impact(title)

    prompt = f"""주식 투자 초보자를 위해 아래 공시를 분석해주세요.

종목명: {stock_name}
공시 제목: {title}

두 항목을 반드시 아래 형식으로 작성하세요.

[공시 분석]
이 공시가 무슨 뜻인지 초보자가 이해할 수 있게 3~4문장으로 설명하세요.
전문 용어는 괄호 안에 쉬운 표현으로 보충해주세요.

[주가 영향 흐름]
이 공시가 주가에 미치는 영향을 아래 형식으로 작성하세요.
공시 당일: (한 문장)
단기(1~2주): (한 문장)
중기(1개월): (한 문장)
주의사항: (한 문장)"""

    try:
        text = model.generate_content(prompt).text.strip()
        analysis, impact = "", ""
        if "[공시 분석]" in text and "[주가 영향 흐름]" in text:
            parts    = text.split("[주가 영향 흐름]")
            analysis = parts[0].replace("[공시 분석]", "").strip()
            impact   = parts[1].strip()
        else:
            analysis = text[:400]
            impact   = ""
    except Exception:
        analysis = _fallback_analysis(title)
        impact   = _fallback_impact(title)

    return analysis, impact


# ─────────────────────────────────────────────────────────
# 폴백 (Gemini 실패 시 키워드 기반)
# ─────────────────────────────────────────────────────────
def _fallback_analysis(title: str) -> str:
    if "자기주식" in title or "자사주" in title:
        return "회사가 자기 주식을 시장에서 직접 사들이는 공시예요. 유통 주식 수가 줄어들어 주당 가치가 높아지는 효과가 있고, 경영진이 현재 주가가 저평가됐다고 판단한다는 신호이기도 해요."
    elif "유상증자" in title:
        return "새로운 주식을 발행해 자금을 조달하는 공시예요. 주식 수가 늘어나기 때문에 단기적으로 주가에 부담이 될 수 있어요. 조달 목적(시설 투자 vs 채무 상환)을 꼭 확인해보세요."
    elif "무상증자" in title:
        return "기존 주주에게 공짜로 주식을 나눠주는 공시예요. 회사 재무가 탄탄하다는 신호로 인식돼 호재로 받아들여지는 경우가 많아요."
    elif "배당" in title:
        return "주주에게 이익을 나눠주는 배당 관련 공시예요. 배당금 수령 기준일과 금액을 확인하세요."
    elif "합병" in title or "인수" in title:
        return "다른 회사와 합치거나 인수하는 중요한 공시예요. 합병 비율과 상대방 회사의 가치에 따라 주가에 큰 영향을 줄 수 있어요."
    else:
        return f"'{title}' 공시예요. DART(dart.fss.or.kr)에서 원문을 직접 확인하면 더 자세한 내용을 볼 수 있어요."


def _fallback_impact(title: str) -> str:
    if "자기주식" in title or "자사주" in title:
        return "공시 당일: 단기 호재로 갭 상승 가능\n단기(1~2주): 실제 매입 시작되면 하방 지지\n중기(1개월): 매입 완료 후 소각 여부 확인\n주의사항: 공시만으로 매수하기보다 실제 매입 확인 후 판단 권장"
    elif "유상증자" in title:
        return "공시 당일: 희석 우려로 주가 하락 가능\n단기(1~2주): 조달 목적에 따라 시장 반응 갈림\n중기(1개월): 신주 발행가 확정 후 재평가\n주의사항: 채무 상환 목적이면 악재, 성장 투자 목적이면 중립~호재"
    elif "배당" in title:
        return "배당 기준일 전: 배당 목적 매수로 주가 상승 가능\n배당락일: 배당금만큼 주가 조정 발생\n중기: 배당 수익률로 장기 보유 가치 재평가\n주의사항: 배당락 후 단기 하락은 자연스러운 현상이에요"
    else:
        return "공시 당일: 시장 반응 확인 필요\n단기(1~2주): 공시 내용의 실현 가능성 모니터링\n중기(1개월): 실제 영향 반영 여부 확인\n주의사항: 공시 하나만으로 매매 결정하지 마세요"
