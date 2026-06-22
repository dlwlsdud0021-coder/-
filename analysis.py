"""
analysis.py — 규칙 기반 기술적 분석 엔진
- RSI, 볼린저 밴드, OBV, 이격도, 이동평균
- 5신호 매집 스코어링 (거래량급증 / OBV상승 / 외국인매수 / 기관매수 / 횡보)
- 자연어 판단 코멘트 생성 (한국어)
"""

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────
# 기술 지표 계산
# ─────────────────────────────────────────────────────────

def calc_rsi(close: pd.Series, period: int = 14) -> float:
    """RSI (0~100). 데이터 부족 시 50 반환"""
    if len(close) < period + 1:
        return 50.0
    delta = close.diff().dropna()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def calc_ma(close: pd.Series, period: int) -> float | None:
    """단순이동평균. 데이터 부족 시 None"""
    if len(close) < period:
        return None
    return round(float(close.tail(period).mean()), 0)


def calc_bollinger(close: pd.Series, period: int = 20, sigma: float = 2.0) -> dict:
    """볼린저밴드 {upper, mid, lower, position}"""
    if len(close) < period:
        cur = float(close.iloc[-1])
        return {"upper": cur, "mid": cur, "lower": cur, "position": 0.5}
    mid = close.tail(period).mean()
    std = close.tail(period).std()
    upper = mid + sigma * std
    lower = mid - sigma * std
    cur = float(close.iloc[-1])
    band_width = upper - lower
    position = (cur - lower) / band_width if band_width > 0 else 0.5
    return {
        "upper": round(upper, 0),
        "mid":   round(mid, 0),
        "lower": round(lower, 0),
        "position": round(position, 3),   # 0=하단, 1=상단
    }


def calc_obv(close: pd.Series, volume: pd.Series) -> dict:
    """OBV 계산 및 최근 추세 {obv_list, trend, change_pct}"""
    if len(close) < 2:
        return {"obv_list": [], "trend": "neutral", "change_pct": 0}
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    obv_series = pd.Series(obv)
    # 최근 5일 OBV 추세
    recent = obv_series.tail(5)
    if len(recent) >= 2:
        slope = recent.iloc[-1] - recent.iloc[0]
        change_pct = slope / (abs(recent.iloc[0]) + 1) * 100
    else:
        change_pct = 0
    trend = "up" if change_pct > 1 else ("down" if change_pct < -1 else "neutral")
    return {
        "obv_list": obv_series.tolist(),
        "trend": trend,
        "change_pct": round(change_pct, 1),
    }


def calc_gap_ratio(close: pd.Series, ma_period: int = 20) -> float | None:
    """이격도 = 현재가 / MA × 100. 없으면 None"""
    ma = calc_ma(close, ma_period)
    if ma is None or ma == 0:
        return None
    return round(float(close.iloc[-1]) / ma * 100, 1)


def calc_volume_surge(volume: pd.Series, period: int = 20) -> float:
    """현재 거래량이 과거 N일 평균의 몇 배인가"""
    if len(volume) < period + 1:
        return 1.0
    avg = float(volume.tail(period + 1).iloc[:-1].mean())
    cur = float(volume.iloc[-1])
    if avg == 0:
        return 1.0
    return round(cur / avg, 2)


def is_sideways(close: pd.Series, period: int = 20, threshold: float = 0.08) -> bool:
    """최근 N일 고가/저가 변동폭이 threshold 이하면 횡보 판단"""
    if len(close) < period:
        return False
    recent = close.tail(period)
    high = recent.max()
    low = recent.min()
    if low == 0:
        return False
    return (high - low) / low < threshold


def calc_ad_line(close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> dict:
    """Accumulation/Distribution Line — 당일 종가 위치까지 반영한 매집/분산선"""
    if len(close) < 5:
        return {"trend": "neutral", "change_pct": 0}
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan).fillna(0)
    ad = (clv * volume).cumsum()
    recent = ad.tail(10)
    if len(recent) < 2:
        return {"trend": "neutral", "change_pct": 0}
    slope = recent.iloc[-1] - recent.iloc[0]
    base = abs(recent.iloc[0]) + 1
    change_pct = slope / base * 100
    trend = "up" if change_pct > 1 else ("down" if change_pct < -1 else "neutral")
    return {"trend": trend, "change_pct": round(float(change_pct), 1)}


def calc_buy_sell_vol_ratio(close: pd.Series, volume: pd.Series, period: int = 10) -> float:
    """상승일 거래량 합 / 하락일 거래량 합. 1.3 이상이면 매수 우위"""
    if len(close) < period + 1:
        return 1.0
    c = close.tail(period + 1)
    v = volume.tail(period + 1)
    up_vol = sum(v.iloc[i] for i in range(1, len(c)) if c.iloc[i] > c.iloc[i-1])
    dn_vol = sum(v.iloc[i] for i in range(1, len(c)) if c.iloc[i] < c.iloc[i-1])
    if dn_vol == 0:
        return 2.0
    return round(up_vol / dn_vol, 2)


def calc_consecutive_net_buy(investor_df, actor: str = "both") -> int:
    """외국인 or 기관의 연속 순매수 일수 반환"""
    if investor_df is None or investor_df.empty:
        return 0
    has_f = "외국인" in investor_df.columns
    has_i = "기관" in investor_df.columns
    consecutive = 0
    for _, row in investor_df.iloc[::-1].iterrows():
        f_buy = (has_f and row.get("외국인", 0) > 0)
        i_buy = (has_i and row.get("기관", 0) > 0)
        if actor == "both":
            bought = f_buy or i_buy
        elif actor == "foreign":
            bought = f_buy
        else:
            bought = i_buy
        if bought:
            consecutive += 1
        else:
            break
    return consecutive


def calc_vcp(close: pd.Series, period: int = 20) -> bool:
    """Volatility Contraction Pattern — 변동폭이 점점 좁아지는지 확인"""
    if len(close) < period:
        return False
    segments = [close.iloc[i:i+5] for i in range(0, period-4, 5)]
    if len(segments) < 3:
        return False
    ranges = [(s.max() - s.min()) / s.min() if s.min() > 0 else 0 for s in segments]
    # 각 구간 변동폭이 이전보다 줄어드는 추세
    contracting = sum(1 for i in range(1, len(ranges)) if ranges[i] < ranges[i-1])
    return contracting >= len(ranges) - 1


def calc_near_52w_low(close: pd.Series, threshold: float = 0.15) -> bool:
    """현재가가 52주 저점 대비 threshold 이내에 위치하는지"""
    if len(close) < 20:
        return False
    low_52w = close.min()
    cur = float(close.iloc[-1])
    if low_52w == 0:
        return False
    return (cur - low_52w) / low_52w < threshold


# ─────────────────────────────────────────────────────────
# 종목 종합 분석
# ─────────────────────────────────────────────────────────

def analyze_stock(
    ohlcv: pd.DataFrame,           # columns: open, high, low, close, volume
    investor_df: pd.DataFrame,     # columns: 외국인, 기관 (index=날짜)
    avg_price: float = None,       # 평균 매수가 (보유종목)
    qty: int = 0,                  # 보유수량
) -> dict:
    """
    종목 전체 분석 결과 반환
    Returns: {
      rsi, ma20, ma60, ma200,
      bollinger: {upper, mid, lower, position},
      obv: {trend, change_pct},
      gap20, gap60,
      volume_ratio,
      is_sideways,
      foreign_net_3d, institution_net_3d,    # 최근 3일 순매수 합계
      signals: {vol_surge, obv_up, foreign_buy, inst_buy, sideways},
      score: int (0~5),
      confidence: "high" | "mid" | "low",
      badges: [...],
      verdict: str,
      pnl_pct: float | None,
      eval_amount: int | None,
    }
    """
    result = {}

    if ohlcv is None or ohlcv.empty:
        return _empty_analysis(avg_price, qty)

    close = ohlcv["close"]
    volume = ohlcv["volume"]
    cur = int(close.iloc[-1])

    # ── 지표 계산 ──
    rsi = calc_rsi(close)
    ma20  = calc_ma(close, 20)
    ma60  = calc_ma(close, 60)
    ma200 = calc_ma(close, 200)
    boll  = calc_bollinger(close)
    obv   = calc_obv(close, volume)
    gap20 = calc_gap_ratio(close, 20)
    gap60 = calc_gap_ratio(close, 60)
    vol_ratio = calc_volume_surge(volume)
    sideways = is_sideways(close)

    # ── 신규 매집 지표 ──
    high_col  = ohlcv["high"]  if "high"  in ohlcv.columns else close
    low_col   = ohlcv["low"]   if "low"   in ohlcv.columns else close
    ad        = calc_ad_line(close, high_col, low_col, volume)
    bsv_ratio = calc_buy_sell_vol_ratio(close, volume)
    vcp       = calc_vcp(close)
    near_low  = calc_near_52w_low(close)

    result.update({
        "current_price": cur,
        "rsi": rsi,
        "ma20": ma20,
        "ma60": ma60,
        "ma200": ma200,
        "bollinger": boll,
        "obv": obv,
        "gap20": gap20,
        "gap60": gap60,
        "volume_ratio": vol_ratio,
        "is_sideways": sideways,
    })

    # ── 외국인/기관 최근 3일 순매수 + 5일 일별 리스트 ──
    foreign_net = 0
    inst_net = 0
    inv_list = []
    consecutive_buy = 0
    if investor_df is not None and not investor_df.empty:
        recent_inv = investor_df.tail(3)
        if "외국인" in recent_inv.columns:
            foreign_net = int(recent_inv["외국인"].sum())
        if "기관" in recent_inv.columns:
            inst_net = int(recent_inv["기관"].sum())
        # 5일 일별 데이터
        recent5 = investor_df.tail(5)
        for idx2, row in recent5.iterrows():
            inv_list.append({
                "date": str(idx2)[:10],
                "foreign": int(row.get("외국인", 0)),
                "inst": int(row.get("기관", 0)),
            })
        consecutive_buy = calc_consecutive_net_buy(investor_df)

    result["foreign_net_3d"] = foreign_net
    result["institution_net_3d"] = inst_net
    result["inv_list"] = inv_list
    result["consecutive_buy_days"] = consecutive_buy

    # ── 5일 거래량 리스트 ──
    vol_list = []
    recent_vol = ohlcv.tail(5)
    for idx2, row in recent_vol.iterrows():
        vol_list.append({
            "date": str(idx2)[:10],
            "volume": int(row.get("volume", 0)),
        })
    result["vol_list"] = vol_list

    # ── 급등/급락 필터 — 매집 구간이 아님 ──
    daily_chg = float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) if len(close) >= 2 else 0.0
    chg_20d   = float((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) if len(close) >= 20 else 0.0
    if abs(daily_chg) > 0.05 or chg_20d > 0.20:
        result["signals"]     = {k: False for k in ["vol_surge","obv_up","foreign_buy","inst_buy","sideways","ad_line_up","buy_sell_vol","consecutive","vcp","near_52w_low"]}
        result["signal_desc"] = {}
        result["score"]       = 0
        result["confidence"]  = "low"
        result["accumulation_score"] = 0
        result["accumulation_confidence"] = "low"
        return result

    # ── 10신호 판단 ──
    sig_vol    = vol_ratio >= 1.3              # 거래량 평균 1.3배+ (조용한 매집)
    sig_obv    = obv["trend"] == "up"          # OBV 상승
    sig_fore   = foreign_net > 0               # 외국인 순매수 (3일 합산)
    sig_inst   = inst_net > 0                  # 기관 순매수 (3일 합산)
    sig_side   = bool(sideways)                # 횡보 패턴
    sig_ad     = ad["trend"] == "up"           # A/D Line 상승 (매집선)
    sig_bsv    = bsv_ratio >= 1.3              # 상승일 거래량 > 하락일 1.3배
    sig_consec = consecutive_buy >= 3          # 외국인 or 기관 3일 이상 연속 순매수
    sig_vcp    = bool(vcp)                     # 변동폭 수축 패턴
    sig_low    = bool(near_low) and (foreign_net > 0 or inst_net > 0)  # 52주 저점 + 매수세

    signals = {
        "vol_surge":     sig_vol,
        "obv_up":        sig_obv,
        "foreign_buy":   sig_fore,
        "inst_buy":      sig_inst,
        "sideways":      sig_side,
        "ad_line_up":    sig_ad,
        "buy_sell_vol":  sig_bsv,
        "consecutive":   sig_consec,
        "vcp":           sig_vcp,
        "near_52w_low":  sig_low,
    }
    score = sum(signals.values())

    # 10개 기준 신뢰도
    if score >= 6:
        confidence = "high"
    elif score >= 4:
        confidence = "mid"
    else:
        confidence = "low"

    # 신호별 설명 (UI 표시용)
    signal_desc = {
        "vol_surge":    {"label": "거래량 증가",      "desc": f"평균 대비 {vol_ratio:.1f}배 거래량. 조용한 매집 흔적"},
        "obv_up":       {"label": "OBV 상승",         "desc": "거래량 누적 추세 우상향. 매수세가 꾸준히 유입 중"},
        "foreign_buy":  {"label": "외국인 순매수",    "desc": f"최근 3일 외국인 {foreign_net:+,}주 순매수"},
        "inst_buy":     {"label": "기관 순매수",      "desc": f"최근 3일 기관 {inst_net:+,}주 순매수"},
        "sideways":     {"label": "횡보 패턴",        "desc": "20일간 박스권 유지. 기관이 특정 가격대 방어 중"},
        "ad_line_up":   {"label": "A/D Line 상승",    "desc": "주가 횡보인데 매집선은 오르는 중. 강한 매집 신호"},
        "buy_sell_vol": {"label": "매수일 거래량 우위", "desc": f"상승일 거래량이 하락일의 {bsv_ratio:.1f}배. 매수 압력 우세"},
        "consecutive":  {"label": f"연속 순매수 {consecutive_buy}일", "desc": "외국인·기관이 며칠째 꾸준히 매수 중"},
        "vcp":          {"label": "변동폭 수축(VCP)", "desc": "가격 변동폭이 점점 좁아지는 중. 돌파 전 압축 패턴"},
        "near_52w_low": {"label": "52주 저점 매집",  "desc": "저점 부근인데 기관·외국인 매수 유입. 바닥 매집 신호"},
    }

    result["signals"] = signals
    result["signal_desc"] = signal_desc
    result["score"] = score
    result["confidence"] = confidence
    result["ad_line"] = ad
    result["buy_sell_vol_ratio"] = bsv_ratio
    result["vcp"] = bool(vcp)
    result["near_52w_low"] = bool(near_low)

    # ── 매집 종목 손절가 / 목표가 ──
    try:
        recent_low  = float(low_col.tail(20).min())   # 20일 최저점
        recent_high = float(close.tail(252).max())    # 52주 고점
        bb_upper    = boll.get("upper", cur * 1.10) if isinstance(boll, dict) else cur * 1.10

        stop_loss   = round(recent_low * 0.97)        # 20일 저점 -3%
        target1     = round(ma20 * 1.03) if ma20 else round(cur * 1.08)   # 20일선 +3%
        target2     = round(min(bb_upper, recent_high * 0.95))            # 볼린저 상단 or 52주 고점 -5%
        risk        = round((cur - stop_loss) / cur * 100, 1) if cur > 0 else 0
        reward1     = round((target1 - cur) / cur * 100, 1) if cur > 0 else 0
        reward2     = round((target2 - cur) / cur * 100, 1) if cur > 0 else 0

        result["acc_stop_loss"]  = int(stop_loss)
        result["acc_target1"]    = int(target1)
        result["acc_target2"]    = int(target2)
        result["acc_risk_pct"]   = risk
        result["acc_reward1_pct"]= reward1
        result["acc_reward2_pct"]= reward2
    except Exception:
        result["acc_stop_loss"]  = None
        result["acc_target1"]    = None
        result["acc_target2"]    = None

    # ── 배지 (badges) ──
    badges = _make_badges(rsi, boll, gap20, gap60, ma20, ma60, ma200,
                          vol_ratio, obv, foreign_net, inst_net, sideways, cur)
    result["badges"] = badges

    # ── 자연어 코멘트 ──
    result["verdict"] = _make_verdict(rsi, boll, gap20, vol_ratio, obv,
                                       foreign_net, inst_net, sideways, score)

    # ── 보유 종목 손익 ──
    if avg_price and avg_price > 0 and qty > 0:
        pnl_pct = (cur - avg_price) / avg_price * 100
        eval_amount = cur * qty
        pnl_amount = (cur - avg_price) * qty
        result["pnl_pct"] = round(pnl_pct, 2)
        result["eval_amount"] = eval_amount
        result["pnl_amount"] = pnl_amount
    else:
        result["pnl_pct"] = None
        result["eval_amount"] = None
        result["pnl_amount"] = None

    return result


# ─────────────────────────────────────────────────────────
# 배지 생성
# ─────────────────────────────────────────────────────────

def _make_badges(rsi, boll, gap20, gap60, ma20, ma60, ma200,
                 vol_ratio, obv, foreign_net, inst_net, sideways, cur) -> list:
    """
    배지 리스트: [{"text": ..., "type": "ok"|"sell"|"warn"|"buy"|"neutral"}]
    HTML 디자인의 badge-ok / badge-sell / badge-warn / badge-buy / badge-neutral 매핑
    """
    badges = []

    # RSI
    if rsi >= 70:
        badges.append({"text": f"RSI 과매수({rsi:.0f})", "type": "sell"})
    elif rsi <= 30:
        badges.append({"text": f"RSI 과매도({rsi:.0f})", "type": "buy"})
    elif 30 < rsi <= 45:
        badges.append({"text": f"RSI 저점권({rsi:.0f})", "type": "ok"})

    # 볼린저
    if boll["position"] <= 0.1:
        badges.append({"text": "볼하단 근접", "type": "buy"})
    elif boll["position"] >= 0.9:
        badges.append({"text": "볼상단 돌파", "type": "sell"})
    elif 0.1 < boll["position"] <= 0.3:
        badges.append({"text": "볼하단 반등", "type": "ok"})

    # 이격도
    if gap20 is not None:
        if gap20 >= 115:
            badges.append({"text": f"이격도 과열({gap20:.0f}%)", "type": "sell"})
        elif gap20 <= 95:
            badges.append({"text": f"20일선 이탈", "type": "warn"})

    # 이동평균 정배열
    if ma20 and ma60 and ma200:
        if cur > ma20 > ma60 > ma200:
            badges.append({"text": "정배열 유지", "type": "ok"})
        elif cur < ma20 < ma60:
            badges.append({"text": "역배열", "type": "sell"})

    # 거래량
    if vol_ratio >= 3:
        badges.append({"text": f"거래량 {vol_ratio:.0f}배↑", "type": "ok"})
    elif vol_ratio >= 2:
        badges.append({"text": "거래량 급증", "type": "ok"})

    # OBV
    if obv["trend"] == "up":
        badges.append({"text": "OBV 상승", "type": "ok"})

    # 수급
    if foreign_net > 0 and inst_net > 0:
        badges.append({"text": "외국인·기관 동반매수", "type": "ok"})
    elif foreign_net > 0:
        badges.append({"text": "외국인 순매수", "type": "ok"})
    elif inst_net > 0:
        badges.append({"text": "기관 순매수", "type": "ok"})
    elif foreign_net < 0 and inst_net < 0:
        badges.append({"text": "외국인·기관 동반매도", "type": "sell"})

    # 횡보
    if sideways:
        badges.append({"text": "박스권 횡보", "type": "neutral"})

    if not badges:
        badges.append({"text": "특이사항 없음", "type": "neutral"})

    return badges


# ─────────────────────────────────────────────────────────
# 자연어 판단 코멘트
# ─────────────────────────────────────────────────────────

def _make_verdict(rsi, boll, gap20, vol_ratio, obv,
                  foreign_net, inst_net, sideways, score) -> str:
    """한 문장 자연어 판단 코멘트"""
    parts = []

    # RSI 상태
    if rsi >= 70:
        parts.append(f"RSI {rsi:.0f} 과매수 구간으로 단기 조정 가능성")
    elif rsi <= 30:
        parts.append(f"RSI {rsi:.0f} 과매도 — 반등 시도 구간")
    elif rsi <= 45:
        parts.append(f"RSI {rsi:.0f} 저점권 회복 중")

    # 볼린저
    if boll["position"] <= 0.15:
        parts.append("볼린저 하단 지지 확인")
    elif boll["position"] >= 0.85:
        parts.append("볼린저 상단 돌파 — 추격 주의")

    # 이격도
    if gap20 is not None and gap20 >= 115:
        parts.append(f"이격도 {gap20:.0f}% 과열")

    # 거래량
    if vol_ratio >= 2:
        parts.append(f"거래량 {vol_ratio:.0f}배 급증")

    # OBV
    if obv["trend"] == "up":
        parts.append("OBV 지속 상승")

    # 수급
    if foreign_net > 0 and inst_net > 0:
        parts.append("외국인·기관 동반 순매수")
    elif foreign_net > 0:
        parts.append("외국인 3일 연속 순매수")
    elif inst_net > 0:
        parts.append("기관 순매수 유입")

    # 횡보
    if sideways:
        parts.append("박스권 횡보 — 매집 패턴 의심")

    # 종합 판단
    if score >= 4:
        conclusion = "→ 매집 신호 강함, 분할 매수 검토"
    elif score == 3:
        conclusion = "→ 매집 신호 감지, 추가 확인 필요"
    elif rsi >= 70 or (gap20 and gap20 >= 115):
        conclusion = "→ 추격 매수 자제, 눌림목 대기"
    elif rsi <= 30:
        conclusion = "→ 저점 매수 기회 가능, 손절선 설정 권장"
    else:
        conclusion = "→ 뚜렷한 신호 없음, 관망"

    if parts:
        return " · ".join(parts) + " " + conclusion
    return conclusion


def _empty_analysis(avg_price, qty) -> dict:
    """데이터 없을 때 기본 반환값"""
    return {
        "current_price": 0,
        "rsi": 50, "ma20": None, "ma60": None, "ma200": None,
        "bollinger": {"upper": 0, "mid": 0, "lower": 0, "position": 0.5},
        "obv": {"trend": "neutral", "change_pct": 0},
        "gap20": None, "gap60": None,
        "volume_ratio": 1.0,
        "is_sideways": False,
        "foreign_net_3d": 0, "institution_net_3d": 0,
        "signals": {"vol_surge": False, "obv_up": False,
                    "foreign_buy": False, "inst_buy": False, "sideways": False},
        "score": 0, "confidence": "low",
        "badges": [{"text": "데이터 없음", "type": "neutral"}],
        "verdict": "→ 데이터를 불러오는 중입니다",
        "pnl_pct": None, "eval_amount": None, "pnl_amount": None,
    }


# ─────────────────────────────────────────────────────────
# 스캐너 배치 처리
# ─────────────────────────────────────────────────────────

def scan_stocks(
    stock_list: list,        # [{"code":..., "name":..., "market":...}, ...]
    fetch_ohlcv_fn,          # callable(code) -> pd.DataFrame
    fetch_investor_fn,       # callable(code) -> pd.DataFrame
) -> list:
    """
    종목 리스트 스캔 → 매집 신호 감지
    Returns: [{"code", "name", "market", "score", "confidence", "signals",
               "current_price", "rsi", "volume_ratio", "obv", ...}, ...]
    score 내림차순 정렬
    """
    results = []
    for stock in stock_list:
        code = stock["code"]
        try:
            ohlcv = fetch_ohlcv_fn(code)
            investor = fetch_investor_fn(code)
            analysis = analyze_stock(ohlcv, investor)
            if analysis["score"] >= 3:   # 3점 이상만 포함
                results.append({
                    "code": code,
                    "name": stock["name"],
                    "market": stock.get("market", ""),
                    **analysis,
                })
        except Exception:
            continue
    results.sort(key=lambda x: (x["score"], x.get("volume_ratio", 0)), reverse=True)
    return results


# ─────────────────────────────────────────────────────────
# 관심종목 타이밍 판단
# ─────────────────────────────────────────────────────────

def watchlist_timing(analysis: dict, target_price: float = None, stop_loss: float = None) -> dict:
    """
    관심종목 매수 타이밍 분류
    Returns: {
      status: "buy_ok" | "chase_no" | "watch",
      label: str,
      reason: str,
      badge_type: "buy" | "sell" | "neutral",
    }
    """
    rsi = analysis.get("rsi", 50)
    boll_pos = analysis.get("bollinger", {}).get("position", 0.5)
    gap20 = analysis.get("gap20", 100)
    score = analysis.get("score", 0)
    cur = analysis.get("current_price", 0)

    # 과열 판단 (추격 금지)
    if rsi >= 70 or (gap20 and gap20 >= 115) or boll_pos >= 0.9:
        reasons = []
        if rsi >= 70:
            reasons.append(f"RSI {rsi:.0f} 과매수")
        if gap20 and gap20 >= 115:
            reasons.append(f"이격도 {gap20:.0f}% 과열")
        if boll_pos >= 0.9:
            reasons.append("볼린저 상단 돌파")
        return {
            "status": "chase_no",
            "label": "추격금지",
            "reason": " · ".join(reasons),
            "badge_type": "sell",
        }

    # 매수 검토 가능
    if rsi <= 45 or boll_pos <= 0.25 or score >= 3:
        reasons = []
        if rsi <= 45:
            reasons.append(f"RSI {rsi:.0f} 저점권")
        if boll_pos <= 0.25:
            reasons.append("볼린저 하단 반등")
        if score >= 3:
            reasons.append(f"매집신호 {score}/5")
        return {
            "status": "buy_ok",
            "label": "매수 검토",
            "reason": " · ".join(reasons) if reasons else "기술적 저점 근접",
            "badge_type": "buy",
        }

    # 목표가/손절가 체크
    if target_price and cur and cur >= target_price * 0.97:
        return {
            "status": "chase_no",
            "label": "목표가 근접",
            "reason": f"현재가 목표가 {int(target_price):,}원에 근접",
            "badge_type": "warn",
        }
    if stop_loss and cur and cur <= stop_loss * 1.03:
        return {
            "status": "chase_no",
            "label": "손절선 근접",
            "reason": f"손절가 {int(stop_loss):,}원 근접 — 리스크 관리 필요",
            "badge_type": "sell",
        }

    return {
        "status": "watch",
        "label": "관망",
        "reason": "뚜렷한 진입 신호 없음 — 눌림목 대기",
        "badge_type": "neutral",
    }
