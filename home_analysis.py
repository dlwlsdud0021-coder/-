"""
home_analysis.py — 홈탭 전용 분석 엔진
- 이동평균선 계산 (20일/60일) + 정배열 판단
- Gemini: 미국→한국 증시 영향 분석 텍스트
- Gemini: 내일 시장 예측 생성 + rule-based 폴백
"""

import os
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pandas as pd

# ─────────────────────────────────────────────────────────
# 시간 유틸
# ─────────────────────────────────────────────────────────
_KST = timezone(timedelta(hours=9))

def _now_kst() -> datetime:
    return datetime.now(_KST)

def is_market_open() -> bool:
    """한국 증시 장중 여부 (평일 09:00~15:30 KST)"""
    now = _now_kst()
    if now.weekday() >= 5:          # 토·일
        return False
    t = now.hour * 100 + now.minute
    return 900 <= t < 1530

def market_phase() -> str:
    """
    'pre'   : 장 시작 전 (00:00~08:59)
    'open'  : 장중   (09:00~15:29)
    'close' : 장 마감 후 (15:30~23:59)
    'weekend': 주말
    """
    now = _now_kst()
    if now.weekday() >= 5:
        return "weekend"
    t = now.hour * 100 + now.minute
    if t < 900:
        return "pre"
    if t < 1530:
        return "open"
    return "close"

# ─────────────────────────────────────────────────────────
# Gemini 설정
# ─────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
_gemini_model = None
_gemini_cache: dict = {}


def _get_gemini():
    global _gemini_model
    if _gemini_model is None and _GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=_GEMINI_KEY)
            _gemini_model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={"temperature": 0.4, "max_output_tokens": 1200},
            )
        except Exception:
            _gemini_model = None
    return _gemini_model


def _call_gemini(prompt: str, cache_key: str) -> str:
    if cache_key in _gemini_cache:
        return _gemini_cache[cache_key]
    model = _get_gemini()
    if not model:
        return ""
    try:
        resp = model.generate_content(prompt)
        result = resp.text.strip()
        _gemini_cache[cache_key] = result
        return result
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────
# 이동평균선 계산
# ─────────────────────────────────────────────────────────

def calc_ma_status(df: pd.DataFrame) -> dict:
    """
    KOSPI/KOSDAQ 지수 OHLCV DataFrame으로 이동평균선 계산.
    Returns:
    {
      current: float,          # 현재(최신) 종가
      ma20: float,             # 20일 이동평균
      ma60: float,             # 60일 이동평균
      above_ma20: bool,        # 현재가 > 20일선
      above_ma60: bool,        # 현재가 > 60일선
      golden_cross: bool,      # 20일선 > 60일선 (정배열)
      trend: str,              # "강한 상승" / "상승" / "보합" / "하락" / "강한 하락"
      ma20_dist_pct: float,    # 현재가와 20일선 이격도 (%)
      ma60_dist_pct: float,    # 현재가와 60일선 이격도 (%)
      enough_data: bool,
    }
    """
    empty = {
        "current": 0, "ma20": 0, "ma60": 0, "ma200": None,
        "above_ma20": False, "above_ma60": False, "above_ma200": False,
        "golden_cross": False,
        "trend": "데이터 부족", "ma20_dist_pct": 0, "ma60_dist_pct": 0,
        "rsi": None, "enough_data": False,
    }
    if df is None or df.empty:
        return empty

    # 종가 컬럼명 탐색
    close_col = None
    for c in ["종가", "Close", "close"]:
        if c in df.columns:
            close_col = c
            break
    if close_col is None:
        return empty

    closes = df[close_col].dropna().astype(float)
    if len(closes) < 20:
        return empty

    cur   = float(closes.iloc[-1])
    ma20  = float(closes.tail(20).mean())
    ma60  = float(closes.tail(60).mean())  if len(closes) >= 60  else None
    ma200 = float(closes.tail(200).mean()) if len(closes) >= 200 else None

    above_ma20   = cur > ma20
    above_ma60   = (cur > ma60)   if ma60  else False
    above_ma200  = (cur > ma200)  if ma200 else False
    golden_cross = (ma20 > ma60)  if ma60  else False

    ma20_dist  = (cur - ma20)  / ma20  * 100 if ma20  else 0
    ma60_dist  = (cur - ma60)  / ma60  * 100 if ma60  else 0
    ma200_dist = (cur - ma200) / ma200 * 100 if ma200 else 0

    # RSI(14) 계산
    rsi = None
    if len(closes) >= 15:
        delta = closes.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss
        rsi_s = 100 - (100 / (1 + rs))
        rsi   = round(float(rsi_s.iloc[-1]), 1)

    # 추세 판단
    if above_ma20 and above_ma60 and golden_cross:
        trend = "강한 상승 (정배열)"
    elif above_ma20 and above_ma60:
        trend = "상승"
    elif above_ma20 and not above_ma60:
        trend = "단기 반등"
    elif not above_ma20 and above_ma60:
        trend = "단기 조정"
    elif not above_ma20 and not above_ma60 and not golden_cross:
        trend = "강한 하락 (역배열)"
    else:
        trend = "하락"

    return {
        "current":        round(cur,   2),
        "ma20":           round(ma20,  2),
        "ma60":           round(ma60,  2) if ma60  else None,
        "ma200":          round(ma200, 2) if ma200 else None,
        "above_ma20":     above_ma20,
        "above_ma60":     above_ma60,
        "above_ma200":    above_ma200,
        "golden_cross":   golden_cross,
        "trend":          trend,
        "ma20_dist_pct":  round(ma20_dist,  2),
        "ma60_dist_pct":  round(ma60_dist,  2) if ma60  else 0,
        "ma200_dist_pct": round(ma200_dist, 2) if ma200 else 0,
        "rsi":            rsi,
        "enough_data":    True,
    }


# ─────────────────────────────────────────────────────────
# 미국→한국 영향 분석 (Gemini)
# ─────────────────────────────────────────────────────────

def _extra_metrics(kp_hist, ma: dict) -> dict:
    """kp_hist DataFrame에서 이격도·수익률·거래량 등 추가 지표 계산."""
    result = {
        "dist_pct_20": ma.get("ma20_dist_pct", 0),   # 20일선 이격률
        "dist_pct_60": ma.get("ma60_dist_pct", 0),
        "disparity_20": 0.0,    # 이격도 (현재가/20일선 * 100)
        "ret_5d": 0.0,          # 5일 수익률
        "ret_20d": 0.0,         # 20일 수익률
        "vol_ratio": 0.0,       # 오늘 거래량 / 20일평균 거래량
        "high_52w": 0.0,
        "low_52w": 0.0,
    }
    if kp_hist is None or kp_hist.empty:
        return result
    try:
        closes = kp_hist["종가"].dropna().astype(float)
        cur    = float(closes.iloc[-1])
        ma20v  = ma.get("ma20") or 0
        ma60v  = ma.get("ma60") or 0
        if ma20v:
            result["disparity_20"] = round(cur / ma20v * 100, 1)
        if len(closes) >= 6:
            result["ret_5d"]  = round((cur / float(closes.iloc[-6]) - 1) * 100, 2)
        if len(closes) >= 21:
            result["ret_20d"] = round((cur / float(closes.iloc[-21]) - 1) * 100, 2)
        # 거래량
        if "거래량" in kp_hist.columns:
            vols = kp_hist["거래량"].dropna().astype(float)
            if len(vols) >= 2:
                today_vol   = float(vols.iloc[-1])
                avg_vol_20  = float(vols.tail(21).iloc[:-1].mean())
                if avg_vol_20 > 0:
                    result["vol_ratio"] = round(today_vol / avg_vol_20, 2)
        # 52주 고저
        if len(closes) >= 60:
            result["high_52w"] = round(float(closes.tail(252).max()), 2)
            result["low_52w"]  = round(float(closes.tail(252).min()), 2)
    except Exception:
        pass
    return result


def analyze_us_impact(us_data: dict, kr_data: dict, ma: dict, kp_hist=None) -> list:
    """
    미국 증시 → 한국 증시 영향 분석 (장중/마감후/주말 구분).
    Returns: [(dot_class, label, html_text), ...]
    """
    sp     = us_data.get("S&P500", {})
    nd     = us_data.get("나스닥",  {})
    dw     = us_data.get("다우",    {})
    kp     = kr_data.get("KOSPI",  {})
    kd     = kr_data.get("KOSDAQ", {})

    sp_pct  = sp.get("change_pct", 0)
    nd_pct  = nd.get("change_pct", 0)
    dw_pct  = dw.get("change_pct", 0)
    kp_pct  = kp.get("change_pct", 0)
    kp_cur  = kp.get("current", 0)
    kd_pct  = kd.get("change_pct", 0)
    ma20    = ma.get("ma20") or 0
    ma60    = ma.get("ma60") or 0
    trend   = ma.get("trend", "")
    above20 = ma.get("above_ma20", False)
    above60 = ma.get("above_ma60", False)
    gc      = ma.get("golden_cross", False)
    d20     = ma.get("ma20_dist_pct", 0)

    # 추가 지표 계산
    ex   = _extra_metrics(kp_hist, ma)
    disp = ex["disparity_20"]   # 이격도 (예: 110.2)
    r5   = ex["ret_5d"]         # 5일 수익률
    r20  = ex["ret_20d"]        # 20일 수익률
    vr   = ex["vol_ratio"]      # 거래량 비율

    phase  = market_phase()
    ma20_s = f"{ma20:,.0f}p" if ma20 else "미집계"
    ma60_s = f"{ma60:,.0f}p" if ma60 else "미집계"
    disp_s = f"{disp:.1f}%" if disp else "미집계"

    # ── Gemini 호출 ──
    cache_key = hashlib.md5(
        f"us_impact_v3:{sp_pct:.2f}:{nd_pct:.2f}:{kp_pct:.2f}:{r5:.1f}:{phase}:{datetime.today().strftime('%Y%m%d')}".encode()
    ).hexdigest()

    # 장중 vs 마감/주말 프롬프트 분기
    if phase == "open":
        context_prompt = "지금은 한국 증시 장중(9:00~15:30)입니다. 투자자가 지금 이 순간 어떤 신호를 주목해야 하는지, 구체적 수치 기준과 함께 알려주세요."
        section3_title = "지금 당장 봐야 할 것"
        section3_tag   = "지금봐야할것"
        section3_prompt = (
            "[지금봐야할것]\n"
            "소제목: (지금 장중 핵심 확인 포인트 한 줄)\n"
            "설명: (외국인 수급·지수 레벨·거래량 중 지금 가장 중요한 2가지 신호와 판단 기준. 구체적 수치 기준 포함 2~3문장.)\n"
            "핵심판단: ('X가 Y를 돌파/지지하면 매수 우위, 실패하면 조정 신호' 식으로 조건을 1문장으로 명확히.)\n"
        )
    else:
        context_prompt = "지금은 한국 증시 장 마감 후입니다. 오늘을 총결산하고 내일을 준비하는 분석을 해주세요."
        section3_title = "오늘 결론 & 내일 준비"
        section3_tag   = "오늘결론"
        section3_prompt = (
            "[오늘결론]\n"
            "소제목: (오늘 KOSPI 한 줄 결론)\n"
            "설명: (오늘 KOSPI 등락 수치, 이격도, 5일 수익률을 언급하며 오늘 장 성격(과열/정상/약세) 진단. "
            "내일 핵심 변수(지지선·저항선 수치 포함) 2가지를 2~4문장으로.)\n"
            "핵심판단: (내일 장에서 이 수준을 지키면 긍정, 이탈하면 주의라는 식으로 구체적 가격 기준 제시.)\n"
        )

    # 과열/침체 판단
    overheated = disp > 108 if disp else False
    oversold   = disp < 97  if disp else False
    heat_str   = f"이격도 {disp_s}로 {'단기 과열 구간' if overheated else '침체 구간' if oversold else '정상 범위'}"

    gap_to_ma20 = abs(kp_cur - ma20) if ma20 else 0

    prompt = (
        "당신은 한국 주식 시장 전문 애널리스트입니다.\n"
        f"{context_prompt}\n\n"
        "━━ 글쓰기 스타일 규칙 (반드시 따르세요) ━━\n"
        "① 수치를 먼저 제시하고 → ② 그 수치가 뭘 의미하는지 풀고 → ③ 쉬운 비유나 예시로 설명하고 → ④ 결론을 한 줄로 끝내세요.\n"
        "② 비유 예시: '고무줄이 많이 늘어났다', '천장에 가까워졌다', '바닥을 다지는 중', '속도를 줄이는 구간'\n"
        "③ 말투: '~이에요', '~거든요', '~해요' 처럼 친근하게. 딱딱한 보고서 말투(~입니다, ~됩니다) 금지.\n"
        "④ 초보자가 모를 만한 용어는 반드시 괄호로 설명. 예: '이격도(현재가÷이평선×100)'\n"
        "⑤ 각 섹션 설명은 4~5문장으로 충분히 상세하게.\n\n"
        f"[오늘 시장 수치 — 반드시 이 숫자들을 분석에 인용하세요]\n"
        f"- 미국: S&P500 {sp_pct:+.2f}% / 나스닥 {nd_pct:+.2f}% / 다우 {dw_pct:+.2f}%\n"
        f"- KOSPI 현재: {kp_cur:,.2f}p ({kp_pct:+.2f}%) / KOSDAQ: {kd_pct:+.2f}%\n"
        f"- KOSPI 20일 이평선: {ma20_s} (현재가에서 {gap_to_ma20:,.0f}p, {abs(d20):.1f}% {'아래' if d20 > 0 else '위'}가 20일선)\n"
        f"- KOSPI 60일 이평선: {ma60_s}\n"
        f"- 이격도(현재가÷20일선×100): {disp_s} — 108% 초과=단기 과열, 97% 미만=침체, 그 사이=정상\n"
        f"- 최근 5일 수익률: {r5:+.2f}% / 최근 20일 수익률: {r20:+.2f}%\n"
        f"- 거래량: 20일 평균 대비 {vr:.1f}배\n"
        f"- 기술 상태: {trend if trend and '부족' not in trend else '집계 중'} / 정배열(단기선>장기선): {'예' if gc else '아니오'}\n\n"
        "아래 3개 섹션을 작성하세요:\n\n"
        "[미국영향]\n"
        "소제목: (미국이 한국에 준 영향 핵심 한 줄 — 수치 포함)\n"
        "설명: S&P500·나스닥 수치 인용 → 왜 한국에 영향주는지(외국인 수급 경로) → 실제로 오늘 어떻게 반영됐는지. "
        "미국과 한국 방향이 같으면 '예상대로', 다르면 '한국만의 이유'를 찾아서 설명. 4~5문장.\n"
        "핵심판단: 외국인 수급 방향이 긍정/부정/중립인지 이유와 함께 1문장.\n\n"
        "[기술분석]\n"
        "소제목: (KOSPI 현재 기술적 위치 핵심 한 줄 — 수치 포함)\n"
        "설명: ① KOSPI가 20일선·60일선 대비 어디에 있는지 수치로 → ② 이격도가 몇 %인지 계산식 보여주며 → "
        "③ 그게 '고무줄 늘어남' 같은 비유로 과열/정상/침체 중 어느 상태인지 → "
        "④ 5일/20일 수익률로 최근 속도감 묘사 → ⑤ 초보자가 이걸 보고 어떻게 행동해야 하는지. 4~5문장.\n"
        "핵심판단: 만약 조정이 온다면 어디서 지지될지 수치로 명시하고, 그 수준이 현재가에서 얼마나 떨어진 곳인지.\n\n"
        f"{section3_prompt}\n"
        f"주의: [미국영향], [기술분석], [{section3_tag}] 태그와 '소제목:', '설명:', '핵심판단:' 레이블을 출력에 포함하세요."
    )

    raw = _call_gemini(prompt, cache_key)

    if raw:
        import re

        def _ext_section(tag):
            m = re.search(r"\[" + tag + r"\]\s*([\s\S]*?)(?=\[|$)", raw)
            return m.group(1).strip() if m else ""

        def _parse_fields(block):
            title  = re.search(r"소제목[:：]\s*(.+)", block)
            desc   = re.search(r"설명[:：]\s*([\s\S]*?)(?=핵심판단|$)", block)
            judge  = re.search(r"핵심판단[:：]\s*(.+)", block)
            return (
                title.group(1).strip()  if title  else "",
                desc.group(1).strip()   if desc   else block.strip(),
                judge.group(1).strip()  if judge  else "",
            )

        def _fmt(subtitle, desc, judge, judge_color="#5B5BD6", judge_icon="💡"):
            parts = []
            if subtitle:
                parts.append(f'<div style="font-size:13px;font-weight:700;color:#1A1A2E;margin-bottom:5px;">{subtitle}</div>')
            parts.append(f'<div style="font-size:12px;color:#3C3C43;line-height:1.7;">{desc}</div>')
            if judge:
                parts.append(
                    f'<div style="margin-top:8px;padding:7px 11px;background:{judge_color}11;'
                    f'border-left:3px solid {judge_color};border-radius:0 8px 8px 0;'
                    f'font-size:11px;color:{judge_color};font-weight:600;">'
                    f'{judge_icon} {judge}</div>'
                )
            return "".join(parts)

        tag3 = section3_tag
        us_t,   us_d,   us_j   = _parse_fields(_ext_section("미국영향"))
        tech_t, tech_d, tech_j = _parse_fields(_ext_section("기술분석"))
        pt_t,   pt_d,   pt_j   = _parse_fields(_ext_section(tag3))

        # 판단 색상 (방향에 따라)
        us_clr   = "#E24B4A" if sp_pct >= 0 else "#185FA5"
        tech_clr = "#30D158" if gc else "#BA7517"

        if us_d and tech_d:
            return [
                ("dot-blue",   "미국 증시 영향",    _fmt(us_t,   us_d,   us_j,   us_clr,   "🌐")),
                ("dot-orange", "이동평균선 분석",   _fmt(tech_t, tech_d, tech_j, tech_clr, "📊")),
                ("dot-green",  section3_title,       _fmt(pt_t,   pt_d,   pt_j,   "#5B5BD6", "🎯")),
            ]

    # ── Rule-based 폴백 ──
    return _rule_analysis(sp_pct, nd_pct, kp_pct, kp_cur, kd_pct,
                          ma20, ma60, ma20_s, ma60_s, trend, above20, above60, gc,
                          phase, disp, disp_s, r5, r20, vr, section3_title, d20)


def _rule_analysis(sp_pct, nd_pct, kp_pct, kp_cur, kd_pct,
                   ma20, ma60, ma20_s, ma60_s, trend, above20, above60, gc,
                   phase, disp, disp_s, r5, r20, vr, section3_title, d20=0) -> list:
    """Rule-based 분석 폴백 (Gemini 실패 시) — 실제 수치 기반"""

    def _card(subtitle, desc, judge, judge_color="#5B5BD6", judge_icon="💡"):
        parts = []
        if subtitle:
            parts.append(f'<div style="font-size:13px;font-weight:700;color:#1A1A2E;margin-bottom:5px;">{subtitle}</div>')
        parts.append(f'<div style="font-size:12px;color:#3C3C43;line-height:1.8;">{desc}</div>')
        if judge:
            parts.append(
                f'<div style="margin-top:8px;padding:7px 11px;background:{judge_color}11;'
                f'border-left:3px solid {judge_color};border-radius:0 8px 8px 0;'
                f'font-size:11px;color:{judge_color};font-weight:600;">'
                f'{judge_icon} {judge}</div>'
            )
        return "".join(parts)

    us_sum = sp_pct + nd_pct
    us_pos = us_sum > 0

    # ── ① 미국 영향 ──
    us_mag      = abs(us_sum) / 2
    us_mag_str  = "크게" if us_mag > 1.5 else "꽤" if us_mag > 0.7 else "소폭"
    corr_ok     = (us_pos == (kp_pct > 0.1)) or (not us_pos == (kp_pct < -0.1))
    kp_abs      = abs(kp_pct)

    if corr_ok and us_pos:
        corr_desc = f"오늘 KOSPI도 {kp_pct:+.2f}%로 그 흐름을 따라갔어요."
    elif corr_ok and not us_pos:
        corr_desc = f"오늘 KOSPI는 {kp_pct:+.2f}%로 미국 약세 영향을 받았어요."
    else:
        corr_desc = (
            f"그런데 오늘 KOSPI는 {kp_pct:+.2f}%로 미국과 반대로 움직였어요. "
            f"국내 수급이나 개별 이슈가 더 강하게 작용한 것으로 볼 수 있어요."
        )

    us_desc = (
        f"전날 미국 S&P500이 {sp_pct:+.2f}%, 나스닥이 {nd_pct:+.2f}% 마감했어요. "
        f"미국 증시가 {us_mag_str} {'오르면' if us_pos else '내리면'} 다음날 한국 외국인 투자자들이 "
        f"{'한국 주식을 더 사려는(매수)' if us_pos else '한국 주식을 팔려는(매도)'} 경향이 생기거든요. "
        f"{corr_desc}"
    )
    us_judge = f"미국 영향 {'긍정' if us_pos else '부정'} → 외국인 수급 {'개선' if us_pos else '악화'} 신호."
    us_clr   = "#E24B4A" if us_pos else "#185FA5"

    # ── ② 기술분석 ──
    if ma20:
        overheated = disp > 108 if disp else False
        oversold   = disp < 97  if disp else False
        gap_p      = abs(kp_cur - ma20)   # 현재가와 20일선 절대 거리
        gap_pct    = abs(d20)

        # 이격도 설명
        if overheated:
            heat_desc = (
                f"이격도(현재가 {kp_cur:,.0f}p ÷ 20일선 {ma20_s} × 100)를 계산하면 {disp_s}예요. "
                f"보통 108% 넘으면 '고무줄이 많이 늘어난 상태'로 봐요. "
                f"지금처럼 이평선 위로 많이 올라가면 평균으로 되돌아오려는 힘(조정)이 생기거든요."
            )
        elif oversold:
            heat_desc = (
                f"이격도가 {disp_s}로 97% 미만이에요. "
                f"이평선 아래로 많이 내려간 상태라 반대로 다시 올라오려는 힘이 생기기도 해요."
            )
        else:
            heat_desc = f"이격도가 {disp_s}로 정상 범위(97~108%)에 있어요."

        r5_desc = f" 최근 5일간 {r5:+.2f}% 움직여 {'빠른 상승 속도예요.' if r5 > 5 else '빠른 하락이 있었어요.' if r5 < -5 else '완만한 흐름이에요.'}" if r5 != 0 else ""

        tech_desc = (
            f"KOSPI 현재가({kp_cur:,.0f}p)는 20일선({ma20_s}) {'위' if above20 else '아래'}, "
            f"60일선({ma60_s})도 {'위' if above60 else '아래'}에 있어요. "
            f"{'정배열(단기 평균이 장기 평균보다 위)이라 상승 흐름이 건강한 상태예요.' if gc else '역배열(장기 평균이 단기 평균보다 위)이라 하락 압력이 있는 상태예요.'} "
            f"{heat_desc}{r5_desc}"
        )

        if above20:
            tech_judge = (
                f"조정이 와도 20일선({ma20_s})이 첫 번째 바닥 역할을 해요. "
                f"지금 현재가에서 {gap_p:,.0f}p({gap_pct:.1f}%) 내려온 수준이에요. "
                f"이 선을 지키면 상승 추세 유효, 이탈하면 추가 조정 주의."
            )
        else:
            tech_judge = (
                f"지금은 20일선({ma20_s}) 아래에 있어요. "
                f"여기서 {gap_p:,.0f}p({gap_pct:.1f}%) 올라가야 20일선 회복이에요. "
                f"이 선을 넘으면 반등 신호, 못 넘으면 약세 지속."
            )
        tech_clr = "#30D158" if above20 and gc and not overheated else "#E24B4A" if not above20 else "#BA7517"
    else:
        tech_desc  = f"이동평균선 데이터 집계 중이에요. 오늘 KOSPI는 {kp_pct:+.2f}% 움직였어요."
        tech_judge = "이평선 집계 완료 후 정확한 분석이 제공돼요."
        tech_clr   = "#BA7517"

    # ── ③ 3번째 섹션 ──
    if phase == "open":
        lvl1 = ma20_s if ma20 else "20일선"
        pt_desc = (
            f"지금 장중에 가장 중요한 신호 두 가지예요. "
            f"① 외국인 순매수 방향 — 오전 10시 기준으로 외국인이 순매수(사는 금액 > 파는 금액)면 오늘 장 긍정 신호예요. "
            f"② KOSPI {lvl1} 지지 여부 — {'현재 이 선 위에 있어 지지가 유지되는 중이에요. 이탈 시 단기 조정 경보.' if above20 else '현재 이 선 아래예요. 회복하면 반등, 못 하면 추가 하락을 봐야 해요.'}"
        )
        pt_judge = f"외국인 순매수 전환 + KOSPI {lvl1} 지지 → 오늘 장 매수 우위."
    elif phase == "close":
        result_str = "상승 마감" if kp_pct > 0.3 else "하락 마감" if kp_pct < -0.3 else "보합 마감"
        r5_str2    = f" 최근 5일 누적 {r5:+.2f}%로" if r5 != 0 else ""
        if ma20:
            gap_p2 = abs(kp_cur - ma20)
            gap_pct2 = abs(d20)
            if disp > 108:
                tmr_detail = (
                    f"이격도가 {disp_s}까지 벌어졌어요. 고무줄이 많이 늘어난 상태라 "
                    f"단기 조정 가능성을 열어두는 게 좋아요. "
                    f"조정 시 20일선({ma20_s})이 첫 번째 지지선인데, 지금 현재가에서 {gap_p2:,.0f}p({gap_pct2:.1f}%) 아래예요."
                )
            else:
                tmr_detail = (
                    f"이격도 {disp_s}로 아직 과열 부담은 크지 않아요. "
                    f"내일도 20일선({ma20_s}) 위를 유지하면 상승 흐름은 이어질 수 있어요."
                )
        else:
            tmr_detail = "내일 장 시작 전 미국 선물과 아시아 증시 방향을 꼭 확인하세요."

        pt_desc = (
            f"오늘 KOSPI는 {kp_pct:+.2f}%로 {result_str}했어요.{r5_str2} 미국 {'상승' if us_pos else '하락'} 영향이 "
            f"{'예상대로' if corr_ok else '예상과 달리'} 반영됐어요. "
            f"{tmr_detail}"
        )
        pt_judge = f"내일 핵심: {ma20_s if ma20 else 'KOSPI 주요 지지선'} 지지 여부 + 외국인 수급 방향."
    else:
        pt_desc = (
            f"미국 S&P500 {sp_pct:+.2f}%, 나스닥 {nd_pct:+.2f}% 마감이 이번 주 외국인 수급 방향에 영향을 줄 거예요. "
            f"{'KOSPI가 20일선(' + ma20_s + ') 위에 있어 기술적으로는 양호한 상태예요.' if above20 and ma20 else 'KOSPI가 20일선 아래에 있어 장 시작 후 회복 여부를 주목하세요.'}"
        )
        pt_judge = "장 시작 전 아시아 선물 + 환율 동향을 확인하세요."

    return [
        ("dot-blue",   "미국 증시 영향",  _card("미국 증시 → 한국 영향",  us_desc,   us_judge,   us_clr,   "🌐")),
        ("dot-orange", "이동평균선 분석", _card("KOSPI 기술적 위치",       tech_desc, tech_judge, tech_clr, "📊")),
        ("dot-green",  section3_title,    _card(section3_title,            pt_desc,   pt_judge,   "#5B5BD6","🎯")),
    ]


# ─────────────────────────────────────────────────────────
# 내일 시장 예측 (Gemini)
# ─────────────────────────────────────────────────────────

def generate_forecast(us_data: dict, kr_data: dict, ma: dict) -> dict:
    """
    내일 KOSPI 예측 생성.
    Returns: {
      direction: "up"/"down"/"sideways",
      direction_kor: str,
      predicted_pct: float,
      confidence: int,
      icon: str,          # tabler icon class
      icon_color: str,
      short_title: str,   # "소폭 상승 예상" 등
      reasons: [str],     # 2~3개
      points: [str],      # 2개
      full_gemini_text: str,
      basis: dict,
    }
    """
    sp_pct  = us_data.get("S&P500", {}).get("change_pct", 0)
    nd_pct  = us_data.get("나스닥",  {}).get("change_pct", 0)
    kp_pct  = kr_data.get("KOSPI",  {}).get("change_pct", 0)
    kp_cur  = kr_data.get("KOSPI",  {}).get("current", 0)
    ma20    = ma.get("ma20", 0) or 0
    ma60    = ma.get("ma60", 0) or 0
    gc      = ma.get("golden_cross", False)
    a20     = ma.get("above_ma20", False)
    a60     = ma.get("above_ma60", False)
    trend   = ma.get("trend", "")
    d20     = ma.get("ma20_dist_pct", 0)

    basis = {
        "sp500_pct": sp_pct, "nasdaq_pct": nd_pct,
        "kospi_pct": kp_pct, "kospi_current": kp_cur,
        "ma20": ma20, "ma60": ma60,
        "above_ma20": a20, "above_ma60": a60,
        "golden_cross": gc, "trend": trend,
    }

    # ── Gemini 호출 ──
    cache_key = hashlib.md5(
        f"forecast:{sp_pct:.2f}:{nd_pct:.2f}:{kp_pct:.2f}:{kp_cur:.0f}:{datetime.today().strftime('%Y%m%d')}".encode()
    ).hexdigest()

    ma20_s = f"{ma20:,.2f}p" if ma20 else "데이터 없음"
    ma60_s = f"{ma60:,.2f}p" if ma60 else "데이터 없음"

    prompt = (
        "당신은 한국 주식시장 전문 애널리스트입니다. 데이터를 기반으로 내일 KOSPI를 예측하고, "
        "주식 초보자도 이해할 수 있는 쉬운 언어로 작성하되 전문적 분석을 담아주세요.\n\n"
        f"[오늘 시장 마감 데이터]\n"
        f"- S&P500: {'+' if sp_pct>=0 else ''}{sp_pct:.2f}%\n"
        f"- 나스닥: {'+' if nd_pct>=0 else ''}{nd_pct:.2f}%\n"
        f"- KOSPI 오늘: {kp_cur:,.2f}p ({'+' if kp_pct>=0 else ''}{kp_pct:.2f}%)\n"
        f"- 20일 이동평균선: {ma20_s} (현재가와 이격: {d20:+.2f}%)\n"
        f"- 60일 이동평균선: {ma60_s}\n"
        f"- 20일선 위: {'예' if a20 else '아니오'} / 60일선 위: {'예' if a60 else '아니오'} / 정배열: {'예' if gc else '아니오'}\n"
        f"- 현재 추세: {trend}\n\n"
        "아래 5개 필드를 정확히 출력하세요:\n\n"
        "[방향] 상승 또는 하락 또는 횡보 (1단어만)\n\n"
        "[등락폭] 예상 등락률 숫자만 (예: +0.8 또는 -0.5)\n\n"
        "[신뢰도] 0~100 숫자만\n\n"
        "[근거] 내일 예측의 핵심 근거 3가지를 작성하세요.\n"
        "각 항목은 반드시 '•'로 시작하고 다음 형식을 따르세요:\n"
        "• (근거 제목): (구체적 수치를 포함한 설명 1~2문장. 왜 이게 중요한지 초보자가 이해하도록.)\n"
        "예시: • 미국 증시 상승: S&P500이 +1.2% 오르면 다음날 한국 외국인 수급이 개선되는 경향이 있어 긍정 신호입니다.\n\n"
        "[주목] 내일 장에서 초보 투자자가 꼭 확인해야 할 2가지를 작성하세요.\n"
        "각 항목은 반드시 '•'로 시작하고 다음 형식을 따르세요:\n"
        "• (확인 포인트): (무엇을, 언제, 어떻게 확인하는지 구체적으로 1~2문장.)\n"
        "예시: • 외국인 수급 방향: 오전 9시 30분~10시 외국인이 순매수(사는 쪽)면 오늘 장 긍정 신호입니다.\n\n"
        "주의: 태그([방향] 등)는 출력에 포함하세요."
    )

    raw = _call_gemini(prompt, cache_key)

    if raw:
        import re

        def _ext(tag):
            m = re.search(r"\[" + tag + r"\]\s*([\s\S]*?)(?=\[|$)", raw)
            return m.group(1).strip() if m else ""

        direction_kor = _ext("방향").strip()
        pct_str       = _ext("등락폭").strip().replace("%", "").replace(" ", "")
        conf_str      = _ext("신뢰도").strip()
        reason_block  = _ext("근거")
        point_block   = _ext("주목")

        dir_map = {"상승": "up", "하락": "down", "횡보": "sideways"}
        direction = dir_map.get(direction_kor, _rule_direction(sp_pct, nd_pct, kp_pct))

        try:
            predicted_pct = float(pct_str)
        except Exception:
            predicted_pct = _rule_pct(sp_pct, nd_pct)

        try:
            confidence = max(0, min(100, int(conf_str)))
        except Exception:
            confidence = _rule_confidence(sp_pct, nd_pct, a20, a60)

        reasons = [l.lstrip("•· ").strip() for l in reason_block.splitlines() if l.strip() and l.strip() not in ("", "\n")]
        reasons = [r for r in reasons if len(r) > 5][:4]
        points  = [l.lstrip("•· ").strip() for l in point_block.splitlines() if l.strip() and len(l.strip()) > 5][:2]

        icon, icon_color, short_title = _dir_to_visual(direction, predicted_pct)

        if direction_kor and reasons:
            return {
                "direction":       direction,
                "direction_kor":   direction_kor,
                "predicted_pct":   predicted_pct,
                "confidence":      confidence,
                "icon":            icon,
                "icon_color":      icon_color,
                "short_title":     short_title,
                "reasons":         reasons,
                "points":          points if points else ["외국인 수급 방향 확인", "20일선 지지 여부 확인"],
                "full_gemini_text": raw,
                "basis":           basis,
            }

    # ── Rule-based 폴백 ──
    return _rule_forecast(sp_pct, nd_pct, kp_pct, a20, a60, gc, basis)


def _rule_direction(sp_pct, nd_pct, kp_pct):
    score = sp_pct * 0.5 + nd_pct * 0.3 + kp_pct * 0.2
    if score >  0.5: return "up"
    if score < -0.5: return "down"
    return "sideways"


def _rule_pct(sp_pct, nd_pct):
    return round((sp_pct * 0.5 + nd_pct * 0.3) * 0.6, 2)


def _rule_confidence(sp_pct, nd_pct, a20, a60):
    base = 45
    if abs(sp_pct) > 1: base += 10
    if a20: base += 5
    if a60: base += 5
    return min(base, 75)


def _dir_to_visual(direction, predicted_pct):
    if direction == "up":
        icon = "ti-trending-up"
        color = "#E24B4A"
        title = f"상승 예상 ({'+' if predicted_pct >= 0 else ''}{predicted_pct:.1f}%)"
    elif direction == "down":
        icon = "ti-trending-down"
        color = "#185FA5"
        title = f"하락 예상 ({'+' if predicted_pct >= 0 else ''}{predicted_pct:.1f}%)"
    else:
        icon = "ti-minus"
        color = "#BA7517"
        title = "횡보 예상"
    return icon, color, title


def _rule_forecast(sp_pct, nd_pct, kp_pct, a20, a60, gc, basis):
    direction = _rule_direction(sp_pct, nd_pct, kp_pct)
    pred_pct  = _rule_pct(sp_pct, nd_pct)
    conf      = _rule_confidence(sp_pct, nd_pct, a20, a60)
    icon, color, title = _dir_to_visual(direction, pred_pct)

    dir_kor = {"up": "상승", "down": "하락", "sideways": "횡보"}[direction]

    reasons_map = {
        "up":       [f"미국 S&P500 {'+' if sp_pct>=0 else ''}{sp_pct:.2f}%, 나스닥 {'+' if nd_pct>=0 else ''}{nd_pct:.2f}% — 외국인 수급 유입 기대",
                     "현재가가 20일선 위에 위치 — 단기 상승 추세 유지 중" if a20 else "20일선 탈환 여부가 핵심 변수"],
        "down":     [f"미국 증시 약세({sp_pct:.2f}%) — 외국인 매도 압력 우려",
                     "20일선 하회 상태 — 단기 하락 압력 지속" if not a20 else "단기 반등 이후 조정 가능성"],
        "sideways": ["미국·국내 신호 엇갈림 — 뚜렷한 방향성 부재",
                     "20일선 근처 박스권 움직임 — 방향 확인 필요"],
    }
    points_map = {
        "up":       ["외국인 순매수 지속 여부 (오전 9~10시 수급 확인)", "코스피 20일선 지지 여부"],
        "down":     ["외국인 매도 규모 확인 (장 초반 수급 체크)", "코스피 전일 저점 지지 여부"],
        "sideways": ["거래량 변화 — 줄면 관망, 늘면 방향 결정 신호", "오전 11시 기준 방향성 확인"],
    }

    return {
        "direction":        direction,
        "direction_kor":    dir_kor,
        "predicted_pct":    pred_pct,
        "confidence":       conf,
        "icon":             icon,
        "icon_color":       color,
        "short_title":      title,
        "reasons":          reasons_map[direction],
        "points":           points_map[direction],
        "full_gemini_text": "",
        "basis":            basis,
    }
