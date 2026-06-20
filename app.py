"""
주식 대시보드 — Phase 3
원본 HTML 디자인 완전 복원 + 실데이터 (pykrx, yfinance, feedparser)
"""
import os
import time

# .env 파일 로드 (KRX_ID, KRX_PW 등 API 키)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import pandas as pd
from datetime import datetime

from market_data import (get_stock_name, get_index_data, get_us_indices,
    get_ohlcv, get_current_price, get_investor_trading, get_top_stocks,
    get_index_ohlcv_history, get_sector_performance, get_kospi_investor_value)
from analysis import analyze_stock, watchlist_timing
from news import (fetch_stock_news, fetch_market_news, fetch_category_news,
                   summarize_sentiment, rank_by_importance, enrich_top10_summaries,
                   CATEGORY_NAMES, CATEGORY_CONFIG)
from home_analysis import calc_ma_status, analyze_us_impact, generate_forecast, market_phase
from disclosure import fetch_disclosures
from database import (create_user, verify_user, get_username,
    add_holding, get_holdings, delete_holding, update_holding,
    add_watchlist, get_watchlist, delete_watchlist,
    save_prediction, update_prediction_result,
    get_recent_predictions, get_prediction_accuracy)

# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="주식 대시보드", page_icon="📈",
                   layout="centered", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────
# CSS (원본 HTML 디자인 토큰 완전 복원)
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.44.0/tabler-icons.min.css');
* { box-sizing: border-box; }
.main .block-container { padding: 0 !important; max-width: 420px !important; margin: 0 auto; }
#MainMenu, header, footer { visibility: hidden; }
body { background: #F5F5F7; color: #1A1A2E; }
/* 헤더 */
.hdr { background:#fff; padding:14px 20px 12px; display:flex; justify-content:space-between; align-items:center; border-bottom:0.5px solid #E5E5EA; }
.hdr-title { font-size:16px; font-weight:600; }
.hdr-sub { font-size:11px; color:#8E8E93; margin-top:2px; }
/* 히어로 카드 */
.hero { margin:12px 16px; background:#5B5BD6; border-radius:20px; padding:18px 20px; color:#fff; }
.hero-badge { display:inline-flex; align-items:center; gap:5px; background:rgba(255,255,255,0.18); border-radius:20px; padding:4px 10px; font-size:11px; margin-bottom:10px; }
.hero-status { font-size:18px; font-weight:700; margin-bottom:6px; }
.hero-desc { font-size:11px; color:rgba(255,255,255,0.8); line-height:1.5; }
.hero-tip { margin-top:10px; background:rgba(255,255,255,0.12); border-radius:10px; padding:8px 12px; font-size:11px; color:rgba(255,255,255,0.9); display:flex; align-items:flex-start; gap:6px; }
/* 지수 카드 */
.idx-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:0 16px 12px; }
.idx-card { background:#fff; border-radius:14px; padding:14px; border:0.5px solid #E5E5EA; }
.idx-card.up-card { border-top:3px solid #E24B4A; }
.idx-card.down-card { border-top:3px solid #185FA5; }
.idx-name { font-size:11px; color:#8E8E93; margin-bottom:4px; font-weight:500; }
.idx-val { font-size:18px; font-weight:700; letter-spacing:-0.5px; }
.idx-chg { font-size:11px; margin-top:3px; font-weight:500; }
/* 섹션 */
.section { margin:0 16px 12px; }
.sec-title { font-size:14px; font-weight:600; margin-bottom:10px; display:flex; align-items:center; gap:6px; }
.sec-lbl { font-size:11px; font-weight:600; color:#8E8E93; margin-bottom:6px; padding-left:2px; }
/* 카드 */
.card { background:#fff; border-radius:16px; padding:14px 16px; border:0.5px solid #E5E5EA; margin-bottom:8px; }
/* 분석 아이템 */
.analysis-item { padding:10px 0; border-bottom:0.5px solid #F0F0F5; }
.analysis-item:last-child { border-bottom:none; padding-bottom:0; }
.analysis-label { display:flex; align-items:center; gap:6px; font-size:12px; font-weight:600; margin-bottom:4px; }
.dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.dot-blue { background:#5B5BD6; } .dot-green { background:#3B6D11; } .dot-orange { background:#854F0B; }
.analysis-text { font-size:11px; color:#6B6B8A; line-height:1.6; }
.analysis-text strong { color:#1A1A2E; font-weight:600; }
.warn-text { font-size:11px; color:#A32D2D; margin-top:4px; display:flex; gap:4px; line-height:1.5; }
/* 예측 카드 */
.forecast-card { background:#fff; border-radius:16px; padding:16px; border:0.5px solid #E5E5EA; }
.forecast-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.forecast-title { font-size:14px; font-weight:600; display:flex; align-items:center; gap:6px; }
.confidence-badge { background:#EEEDFE; color:#3C3489; font-size:11px; padding:3px 8px; border-radius:6px; font-weight:500; }
.progress-bg { height:5px; background:#F0F0F5; border-radius:3px; margin-bottom:12px; }
.forecast-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.forecast-col-title { font-size:11px; color:#8E8E93; font-weight:500; margin-bottom:6px; display:flex; align-items:center; gap:4px; }
.forecast-item { font-size:11px; color:#3B3B5C; line-height:1.6; padding-left:8px; position:relative; }
.forecast-item::before { content:'·'; position:absolute; left:0; color:#5B5BD6; }
.warn-box2 { background:#FCEBEB; border-radius:10px; padding:8px 12px; margin-top:10px; font-size:11px; color:#A32D2D; line-height:1.5; display:flex; gap:6px; }
/* expand 버튼 */
.expand-btn { display:flex; align-items:center; justify-content:space-between; background:#fff; border-radius:14px; padding:14px 16px; border:0.5px solid #E5E5EA; margin-bottom:8px; }
/* 상세분석 페이지 */
.ma-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:0; }
.ma-card { background:#F8F8FA; border-radius:10px; padding:10px 12px; }
.ma-card-label { font-size:10px; color:#8E8E93; margin-bottom:3px; }
.ma-card-val { font-size:13px; font-weight:600; }
.ma-card-sub { font-size:10px; margin-top:2px; }
.ind-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:0.5px solid #F0F0F5; }
.ind-row:last-child { border-bottom:none; }
.ind-label { font-size:12px; color:#6B6B8A; }
.ind-right { display:flex; align-items:center; gap:8px; }
.ind-val { font-size:12px; font-weight:600; }
.ind-status { font-size:10px; padding:2px 7px; border-radius:5px; font-weight:500; }
.status-ok { background:#EEEDFE; color:#3C3489; }
.status-warn { background:#FAEEDA; color:#633806; }
.status-danger { background:#FCEBEB; color:#791F1F; }
.rsi-bar-wrap { width:60px; height:4px; background:#F0F0F5; border-radius:2px; overflow:hidden; }
.rsi-bar-fill { height:4px; border-radius:2px; }
.sector-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:0.5px solid #F0F0F5; }
.sector-row:last-child { border-bottom:none; }
.sector-name { font-size:12px; font-weight:500; }
.sector-bar-wrap { width:80px; height:4px; background:#F0F0F5; border-radius:2px; overflow:hidden; }
.sector-bar { height:4px; border-radius:2px; }
.sector-pct { font-size:11px; font-weight:600; min-width:48px; text-align:right; }
.advice-box { background:#EEEDFE; border-radius:14px; padding:14px 16px; margin:0 16px 8px; }
.advice-title { font-size:13px; font-weight:600; color:#3C3489; margin-bottom:6px; display:flex; align-items:center; gap:6px; }
.advice-text { font-size:11px; color:#534AB7; line-height:1.6; }
.expand-left { display:flex; align-items:center; gap:8px; font-size:13px; font-weight:500; }
.expand-icon { width:32px; height:32px; border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:16px; background:#EEEDFE; color:#5B5BD6; }
/* 색상 */
.up { color:#E24B4A; } .down { color:#185FA5; }
/* 뉴스 카드 */
.news-card { background:#fff; border-radius:16px; padding:14px 16px; border:0.5px solid #E5E5EA; margin-bottom:8px; }
.news-card.important { border-left:3px solid #5B5BD6; border-radius:0 16px 16px 16px; }
.news-card.negative { border-left:3px solid #185FA5; border-radius:0 16px 16px 16px; }
.news-card-top { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.news-source { font-size:10px; color:#8E8E93; margin-left:auto; }
.news-title { font-size:13px; font-weight:600; line-height:1.5; margin-bottom:6px; }
.news-summary { font-size:11px; color:#6B6B8A; line-height:1.6; margin-bottom:10px; }
.news-divider { height:0.5px; background:#F0F0F5; margin-bottom:10px; }
.ai-section { background:#F8F8FA; border-radius:10px; padding:10px 12px; }
.ai-label { font-size:10px; font-weight:600; color:#5B5BD6; margin-bottom:4px; display:flex; align-items:center; gap:4px; }
.ai-text { font-size:11px; color:#6B6B8A; line-height:1.6; }
.ai-strategy { margin-top:6px; padding-top:6px; border-top:0.5px solid #E5E5EA; }
.ai-strategy-label { font-size:10px; font-weight:600; color:#1A1A2E; margin-bottom:3px; display:flex; align-items:center; gap:4px; }
.ai-strategy-text { font-size:11px; color:#6B6B8A; line-height:1.6; }
.news-footer { display:flex; justify-content:space-between; align-items:center; margin-top:10px; }
.news-time { font-size:10px; color:#C7C7CC; }
.stock-chip { font-size:10px; background:#EEEDFE; color:#3C3489; padding:2px 8px; border-radius:5px; font-weight:500; margin-left:3px; }
/* 배지 */
.badge { font-size:10px; padding:3px 8px; border-radius:6px; font-weight:500; display:inline-block; margin:1px; }
.badge-pos { background:#EAF3DE; color:#27500A; }
.badge-neg { background:#FCEBEB; color:#791F1F; }
.badge-mix { background:#FAEEDA; color:#633806; }
.badge-ok  { background:#EEEDFE; color:#3C3489; }
.badge-buy { background:#EAF3DE; color:#27500A; }
.badge-sell{ background:#FCEBEB; color:#791F1F; }
.badge-warn{ background:#FAEEDA; color:#633806; }
.badge-neu { background:#F0F0F5; color:#6B6B8A; }
/* 총평가 스트립 */
.total-strip { background:#fff; padding:14px 20px; border-bottom:0.5px solid #E5E5EA; display:flex; justify-content:space-between; align-items:center; }
.total-lbl { font-size:11px; color:#8E8E93; margin-bottom:3px; }
.total-amt { font-size:22px; font-weight:700; letter-spacing:-0.5px; }
.total-pnl-lbl { font-size:10px; color:#8E8E93; margin-bottom:3px; text-align:right; }
.total-pnl { font-size:16px; font-weight:700; }
/* 주식 카드 공통 */
.stk-icon { width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0; }
.ico-purple { background:#EEEDFE; color:#3C3489; }
.ico-blue   { background:#E6F1FB; color:#0C447C; }
.ico-amber  { background:#FAEEDA; color:#633806; }
.ico-green  { background:#EAF3DE; color:#27500A; }
.ico-red    { background:#FCEBEB; color:#791F1F; }
/* 미니 그리드 */
.mini-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-top:10px; }
.mini-item { background:#F8F8FA; border-radius:8px; padding:7px 10px; }
.mini-lbl { font-size:9px; color:#8E8E93; margin-bottom:2px; }
.mini-val { font-size:12px; font-weight:600; }
/* 지지선 칩 */
.sup-chip { font-size:10px; color:#6B6B8A; background:#F0F0F5; padding:2px 8px; border-radius:5px; margin-right:5px; }
/* PNL 바 */
.pnl-bar-wrap { height:4px; background:#F0F0F5; border-radius:2px; margin-top:10px; overflow:hidden; }
.pnl-bar { height:4px; border-radius:2px; }
/* RSI 바 (미니) */
.rsi-mini { display:flex; align-items:center; gap:6px; margin-top:8px; }
.rsi-lbl-s { font-size:10px; color:#8E8E93; min-width:44px; }
.rsi-bar-s { flex:1; height:3px; background:#F0F0F5; border-radius:2px; overflow:hidden; }
.rsi-fill-s { height:3px; border-radius:2px; }
.rsi-val-s { font-size:10px; font-weight:600; min-width:28px; text-align:right; }
/* RSI 바 (큰) */
.rsi-row-b { display:flex; align-items:center; gap:6px; margin-bottom:5px; }
.rsi-lbl-b { font-size:10px; color:#8E8E93; min-width:28px; }
.rsi-bar-b { flex:1; height:4px; background:#F0F0F5; border-radius:2px; overflow:hidden; }
.rsi-fill-b { height:4px; border-radius:2px; }
.rsi-val-b { font-size:10px; font-weight:600; min-width:24px; text-align:right; }
/* OBV 행 */
.obv-row { display:flex; justify-content:space-between; align-items:center; }
.obv-lbl { font-size:10px; color:#8E8E93; }
.obv-val { font-size:10px; font-weight:600; color:#3C3489; }
/* 신호 도트 */
.sig-row { display:flex; gap:5px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }
.sig-item { display:flex; align-items:center; gap:3px; }
.sig-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.sig-on { background:#5B5BD6; } .sig-off { background:#D1D1D6; }
.sig-txt { font-size:10px; color:#6B6B8A; }
/* 카드 하단 */
.card-bottom { display:flex; justify-content:space-between; align-items:center; padding-top:8px; border-top:0.5px solid #F0F0F5; margin-top:8px; }
/* 스캐너 종목 카드 */
.stk-card { background:#fff; border-radius:16px; padding:14px 16px; margin-bottom:8px; border:0.5px solid #E5E5EA; }
.stk-card.high { border-left:3px solid #5B5BD6; border-radius:0 16px 16px 16px; }
.stk-card.mid  { border-left:3px solid #BA7517; border-radius:0 16px 16px 16px; }
.rank-num { font-size:13px; font-weight:700; color:#C7C7CC; min-width:18px; }
/* 스캐너 요약 */
.sum-row { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin:12px 16px; }
.sum-card { background:#fff; border-radius:12px; padding:10px 12px; border:0.5px solid #E5E5EA; text-align:center; }
.sum-lbl { font-size:10px; color:#8E8E93; margin-bottom:3px; }
.sum-val { font-size:18px; font-weight:700; }
/* 관심종목 reason chip */
.watch-reason { font-size:10px; padding:3px 8px; border-radius:5px; margin-top:6px; display:inline-block; }
.reason-buy { background:#EEEDFE; color:#534AB7; }
.reason-sell { background:#FCEBEB; color:#791F1F; }
/* 목표가 행 */
.target-row { display:flex; align-items:center; gap:6px; margin-top:8px; padding-top:8px; border-top:0.5px solid #F0F0F5; flex-wrap:wrap; }
.target-lbl { font-size:10px; color:#8E8E93; }
.target-val { font-size:11px; font-weight:600; color:#3C3489; }
.target-dist { font-size:10px; color:#3C3489; }
/* 상세 페이지 */
.price-section { background:#fff; padding:16px 20px; border-bottom:0.5px solid #E5E5EA; }
.current-price { font-size:28px; font-weight:700; letter-spacing:-0.5px; }
.price-meta { display:flex; gap:16px; margin-top:10px; }
.pm-item { font-size:11px; color:#8E8E93; }
.pm-item span { color:#1A1A2E; font-weight:500; }
.pos-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }
.pos-item { background:#F8F8FA; border-radius:10px; padding:10px 12px; }
.pos-label { font-size:10px; color:#8E8E93; margin-bottom:3px; }
.pos-val { font-size:14px; font-weight:700; }
.ind-row { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:0.5px solid #F0F0F5; }
.ind-row:last-child { border-bottom:none; }
.ind-label { font-size:12px; color:#6B6B8A; }
.ind-right { display:flex; align-items:center; gap:8px; }
.ind-val { font-size:12px; font-weight:600; }
.ind-status { font-size:10px; padding:2px 7px; border-radius:5px; font-weight:500; }
.status-ok { background:#EEEDFE; color:#3C3489; }
.status-good { background:#EAF3DE; color:#27500A; }
.status-danger { background:#FCEBEB; color:#791F1F; }
.rsi-bar-wrap2 { width:60px; height:4px; background:#F0F0F5; border-radius:2px; overflow:hidden; }
.rsi-bar-fill2 { height:4px; border-radius:2px; }
.sup-row { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:0.5px solid #F0F0F5; }
.sup-row:last-child { border-bottom:none; }
.sup-label { font-size:12px; color:#6B6B8A; }
.sup-right { display:flex; align-items:center; gap:8px; }
.sup-price { font-size:12px; font-weight:600; }
.sup-dist { font-size:11px; font-weight:500; }
.sup-note { font-size:10px; padding:2px 7px; border-radius:5px; }
.note-near { background:#EAF3DE; color:#27500A; }
.note-far { background:#F0F0F5; color:#6B6B8A; }
.supply-row { display:flex; align-items:center; gap:8px; padding:8px 0; border-bottom:0.5px solid #F0F0F5; }
.supply-row:last-child { border-bottom:none; }
.supply-who { font-size:12px; color:#6B6B8A; min-width:48px; }
.supply-bar-bg { flex:1; height:5px; background:#F0F0F5; border-radius:3px; overflow:hidden; }
.supply-bar-fill { height:5px; border-radius:3px; }
.bar-buy { background:#E24B4A; } .bar-sell { background:#185FA5; }
.supply-val { font-size:11px; font-weight:600; min-width:64px; text-align:right; }
.days-row { display:flex; gap:3px; padding:0 0 6px 56px; flex-wrap:wrap; }
.day-chip { font-size:10px; padding:2px 6px; border-radius:5px; }
.chip-buy { background:#FCEBEB; color:#A32D2D; }
.chip-sell { background:#E6F1FB; color:#0C447C; }
.warn-box { background:#FCEBEB; border-radius:14px; padding:14px 16px; margin-bottom:8px; }
.warn-title { font-size:13px; font-weight:600; color:#791F1F; margin-bottom:6px; display:flex; align-items:center; gap:6px; }
.warn-box .warn-text { font-size:11px; color:#A32D2D; line-height:1.6; }
.advice-box { background:#EEEDFE; border-radius:14px; padding:14px 16px; margin-bottom:8px; }
.advice-title { font-size:13px; font-weight:600; color:#3C3489; margin-bottom:6px; display:flex; align-items:center; gap:6px; }
.advice-text { font-size:11px; color:#534AB7; line-height:1.6; }
/* 로그인 */
.login-wrap { max-width:340px; margin:60px auto; padding:0 20px; }
.login-title { font-size:24px; font-weight:700; text-align:center; margin-bottom:6px; color:#5B5BD6; }
.login-sub { font-size:13px; color:#8E8E93; text-align:center; margin-bottom:28px; }
/* 보유 카드 액션 버튼 */
div[data-testid="stHorizontalBlock"]:has(.hld-nav-wrap) { gap:4px !important; margin-top:-2px !important; }
.hld-nav-wrap button { background:#F8F8FA !important; border:0.5px solid #E5E5EA !important; border-top:none !important;
  border-radius:0 0 0 14px !important; font-size:13px !important; color:#5B5BD6 !important;
  padding:6px 0 !important; min-height:34px !important; }
.hld-del-wrap button { background:#EAF3DE !important; border:0.5px solid #E5E5EA !important; border-top:none !important;
  border-radius:0 0 14px 0 !important; font-size:15px !important; color:#27500A !important;
  padding:6px 0 !important; min-height:34px !important; }
/* 탭 필터 */
.filter-row2 { display:flex; gap:6px; padding:10px 16px; overflow-x:auto; scrollbar-width:none; }
.filter-row2::-webkit-scrollbar { display:none; }
/* 수급 탭 pill 스타일 오버라이드 */
div[data-testid="stHorizontalBlock"]:has(button[kind="secondaryFormSubmit"]) { gap:6px !important; padding:8px 0; }
button[kind="secondaryFormSubmit"] { border-radius:20px !important; font-size:12px !important; font-weight:500 !important; border:none !important; background:#F0F0F5 !important; color:#6B6B8A !important; }
button[kind="primaryFormSubmit"], button[kind="primary"] { border-radius:20px !important; font-size:12px !important; font-weight:500 !important; }

/* ── Streamlit 다크모드 강제 라이트 오버라이드 ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
.stApp, .main, [data-testid="block-container"] {
  background-color: #F5F5F7 !important;
  color: #1A1A2E !important;
}
/* 탭 패널 배경 */
[data-testid="stTabsContent"], [data-baseweb="tab-panel"] {
  background-color: #F5F5F7 !important;
}
/* 버튼 기본 */
.stButton > button {
  background-color: #F0F0F5 !important;
  color: #1A1A2E !important;
  border: 0.5px solid #E5E5EA !important;
}
.stButton > button[kind="primary"], .stButton > button[data-testid*="primary"] {
  background-color: #5B5BD6 !important;
  color: #fff !important;
  border: none !important;
}
/* 입력 필드 */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stTextArea textarea {
  background-color: #fff !important;
  color: #1A1A2E !important;
  border: 0.5px solid #E5E5EA !important;
}
/* 라벨 / 텍스트 */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stTextArea label, .stCheckbox label, .stRadio label {
  color: #1A1A2E !important;
}
/* 보라 히어로 박스 안은 흰색 유지 */
.hero, .hero *, .hero p, .hero span, .hero div {
  color: #fff !important;
}
.hero strong, .hero b {
  color: #FFD60A !important;
}
/* 사이드바 */
[data-testid="stSidebar"] {
  background-color: #fff !important;
}
/* 경고/정보 박스 */
.stAlert {
  background-color: #fff !important;
  color: #1A1A2E !important;
}
/* 메트릭 */
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
  color: #1A1A2E !important;
}
/* 토스트/스피너 배경 */
[data-testid="stToast"] {
  background-color: #fff !important;
  color: #1A1A2E !important;
}
/* 팝오버 */
[data-testid="stPopover"] > div {
  background-color: #fff !important;
  color: #1A1A2E !important;
  border: 0.5px solid #E5E5EA !important;
}
/* 헤더 상단바 완전 숨김 */
#MainMenu, header[data-testid="stHeader"], footer { display:none !important; }
/* 스크롤바 */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #F5F5F7; }
::-webkit-scrollbar-thumb { background: #C7C7CC; border-radius: 2px; }

/* ── 바텀 네비게이션 ── */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 380px;
  max-width: 100vw;
  background: #fff;
  border-top: 0.5px solid #E5E5EA;
  display: flex;
  padding: 10px 0 16px;
  z-index: 9999;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
}
.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  color: #C7C7CC;
  font-size: 10px;
  cursor: pointer;
  text-decoration: none;
}
.nav-item.active { color: #5B5BD6; }
.nav-item i { font-size: 22px; }
/* 탭 active 색상만 */
[data-baseweb="tab-highlight"] { background: #5B5BD6 !important; }
[aria-selected="true"][data-baseweb="tab"] { color: #5B5BD6 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 세션 상태
# ─────────────────────────────────────────────────────────
def update_watchlist(user_id: int, code: str, target_price=None, stop_loss=None):
    import sqlite3, os
    db_path = os.path.join(os.path.dirname(__file__), "stocks.db")
    con = sqlite3.connect(db_path)
    con.execute("UPDATE watchlist SET target_price=?, stop_loss=? WHERE user_id=? AND code=?",
                (target_price, stop_loss, user_id, code))
    con.commit(); con.close()


def _init():
    for k, v in {
        "user_id": None, "username": "", "page": "main",
        "detail_code": "", "detail_name": "", "detail_avg": 0.0,
        "detail_qty": 0, "detail_target": 0.0, "detail_stop": 0.0,
        "scanner_results": [], "scanner_ran": False, "login_tab": "login",
        "show_supply_detail": False,
        "holdings_filter": "all",
        "watchlist_filter": "all",
        "scanner_filter": "all",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()


# ─────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────
_COLORS = ["ico-purple","ico-blue","ico-amber","ico-green","ico-red"]

def _ico_cls(i): return _COLORS[i % len(_COLORS)]
def _ico_lbl(name):
    n = (name or "?").strip()
    return n[:2] if len(n) > 2 else n

def _fp(v):
    if v is None: return "-"
    try: return f"{int(v):,}원"
    except: return str(v)

def _rsi_color(r):
    if r >= 70: return "#E24B4A"
    if r <= 30: return "#3B6D11"
    return "#5B5BD6"

def _badge(text, t):
    m = {"pos":"badge-pos","neg":"badge-neg","mix":"badge-mix",
         "ok":"badge-ok","buy":"badge-buy","sell":"badge-sell",
         "warn":"badge-warn","neutral":"badge-neu"}
    return f'<span class="badge {m.get(t,"badge-neu")}">{text}</span>'

def _rsi_mini_h(rsi, label=""):
    rc = _rsi_color(rsi)
    lbl = label or ("저점" if rsi<=30 else "과열" if rsi>=70 else "보통")
    return f"""<div class="rsi-mini">
  <span class="rsi-lbl-s">RSI {rsi:.0f}</span>
  <div class="rsi-bar-s"><div class="rsi-fill-s" style="width:{rsi}%;background:{rc};"></div></div>
  <span class="rsi-val-s" style="color:{rc};">{lbl}</span>
</div>"""

def _rsi_big_h(rsi):
    rc = _rsi_color(rsi)
    return f"""<div class="rsi-row-b">
  <span class="rsi-lbl-b">RSI</span>
  <div class="rsi-bar-b"><div class="rsi-fill-b" style="width:{rsi}%;background:{rc};"></div></div>
  <span class="rsi-val-b" style="color:{rc};">{rsi:.0f}</span>
</div>"""

def _sig_dots_h(sigs):
    labels = [("vol_surge","거래량"),("obv_up","OBV"),
              ("foreign_buy","외국인"),("inst_buy","기관"),("sideways","횡보")]
    items = "".join(
        f'<div class="sig-item"><div class="sig-dot {"sig-on" if sigs.get(k) else "sig-off"}"></div>'
        f'<span class="sig-txt">{lbl}</span></div>'
        for k, lbl in labels)
    return f'<div class="sig-row">{items}</div>'

def _today():
    return datetime.today().strftime("%Y.%m.%d")

def _now():
    return datetime.now().strftime("%Y.%m.%d %H:%M")

# ─────────────────────────────────────────────────────────
# 시장 상태 판단 (홈 히어로카드)
# ─────────────────────────────────────────────────────────
def _market_hero(idx):
    kp = idx.get("KOSPI", {})
    kd = idx.get("KOSDAQ", {})
    pct = (kp.get("change_pct", 0) + kd.get("change_pct", 0)) / 2
    if pct >= 3:   status = "강한 상승장";  badge_txt = "🚀 강한 상승장"; tip = "<strong>보유 종목 홀딩.</strong> 신규는 소량 분할 매수로."
    elif pct >= 1: status = "상승장";       badge_txt = "📈 상승장";      tip = "추세 유지 중. <strong>지지선 확인 후 진입.</strong>"
    elif pct >= -1:status = "보합장";       badge_txt = "➡️ 보합";        tip = "방향성 불명확. <strong>관망 후 신호 확인.</strong>"
    elif pct >= -3:status = "하락장";       badge_txt = "📉 하락장";      tip = "<strong>손절선 점검.</strong> 현금 비중 확대 고려."
    else:          status = "급락장";       badge_txt = "⚠️ 급락장";     tip = "추격 매도 자제. <strong>분할 매수는 반등 확인 후.</strong>"
    kp_pct = kp.get("change_pct", 0)
    kd_pct = kd.get("change_pct", 0)
    kp_arr = "▲" if kp_pct >= 0 else "▼"
    kd_arr = "▲" if kd_pct >= 0 else "▼"
    desc = f"KOSPI {kp_arr}{abs(kp_pct):.2f}% · KOSDAQ {kd_arr}{abs(kd_pct):.2f}%"
    return badge_txt, status, desc, tip

def _make_analysis_text(idx, us):
    kp = idx.get("KOSPI", {})
    kp_pct = kp.get("change_pct", 0)
    sp_pct = us.get("S&P500", {}).get("change_pct", 0)
    nd_pct = us.get("나스닥", {}).get("change_pct", 0)
    ma20 = kp.get("current", 0) / 1.03 if kp.get("current") else 0  # 근사
    lines = []
    # 미국 영향
    us_dir = "긍정적" if (sp_pct + nd_pct) > 0 else "부정적"
    lines.append(("dot-blue", "미국 증시 영향",
        f"S&P500 {'+' if sp_pct>=0 else ''}{sp_pct:.2f}%, 나스닥 {'+' if nd_pct>=0 else ''}{nd_pct:.2f}%. "
        f"외국인 수급에 <strong>{us_dir}</strong> 영향."))
    # 기술적
    if kp_pct > 2:
        tech = f"KOSPI <strong>강한 상승 추세</strong>. 단기 과열 주의."
    elif kp_pct > 0:
        tech = f"KOSPI <strong>완만한 상승</strong>. 정배열 유지 중."
    elif kp_pct > -2:
        tech = f"KOSPI <strong>보합 흐름</strong>. 방향성 확인 필요."
    else:
        tech = f"KOSPI <strong>하락 압력</strong>. 지지선 확인 필요."
    lines.append(("dot-orange", "기술적 분석", tech))
    return lines

def _make_forecast(kp_pct, sp_pct):
    if sp_pct > 0.5 and kp_pct > 0:
        title = "소폭 상승 예상"; icon = "ti-trending-up"; icon_color = "#E24B4A"; conf = 60
        reasons = ["미국 호조 → 외국인 수급 긍정", "현재 상승 추세 지속 가능성"]
        points = ["장중 20일선 지지 확인", "외국인 매매 방향 초반 확인"]
    elif sp_pct < -0.5 and kp_pct < 0:
        title = "소폭 하락 예상"; icon = "ti-trending-down"; icon_color = "#185FA5"; conf = 55
        reasons = ["미국 약세 → 외국인 매도 우려", "하락 추세 이어질 가능성"]
        points = ["손절선(-3%) 점검", "장 초반 외국인 방향 확인 후 판단"]
    else:
        title = "혼조세 예상"; icon = "ti-minus"; icon_color = "#BA7517"; conf = 45
        reasons = ["미국·국내 신호 엇갈림", "뚜렷한 방향성 부재"]
        points = ["무리한 매매 자제", "모멘텀 확인 후 진입"]
    return title, icon, icon_color, conf, reasons, points


# ─────────────────────────────────────────────────────────
# 로그인 페이지
# ─────────────────────────────────────────────────────────
def render_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">📈 주식 대시보드</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">로그인하여 나만의 포트폴리오를 관리하세요</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("로그인", use_container_width=True,
                     type="primary" if st.session_state.login_tab=="login" else "secondary"):
            st.session_state.login_tab = "login"
    with c2:
        if st.button("회원가입", use_container_width=True,
                     type="primary" if st.session_state.login_tab=="signup" else "secondary"):
            st.session_state.login_tab = "signup"
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.login_tab == "login":
        with st.form("lf"):
            uid = st.text_input("아이디", placeholder="아이디 입력")
            pw  = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
            if st.form_submit_button("로그인", use_container_width=True, type="primary"):
                if not uid or not pw:
                    st.error("아이디와 비밀번호를 입력해주세요.")
                else:
                    ok, uid2 = verify_user(uid, pw)
                    if ok:
                        st.session_state.user_id = uid2
                        st.session_state.username = uid
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 잘못되었습니다.")
    else:
        with st.form("sf"):
            uid = st.text_input("아이디 (2자 이상)")
            pw  = st.text_input("비밀번호 (4자 이상)", type="password")
            pw2 = st.text_input("비밀번호 확인", type="password")
            if st.form_submit_button("회원가입", use_container_width=True, type="primary"):
                if pw != pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    ok, msg = create_user(uid, pw)
                    if ok:
                        st.success(msg)
                        st.session_state.login_tab = "login"
                    else:
                        st.error(msg)
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 홈 탭
# ─────────────────────────────────────────────────────────
def render_home():
    # ── 데이터 수집 ──
    with st.spinner("시장 데이터 불러오는 중..."):
        idx     = get_index_data()
        us      = get_us_indices()
        kp_hist = get_index_ohlcv_history("1001", 250)
        kd_hist = get_index_ohlcv_history("2001", 250)

    ma_kp = calc_ma_status(kp_hist)

    kp  = idx.get("KOSPI",  {})
    kd  = idx.get("KOSDAQ", {})
    sp  = us.get("S&P500",  {})
    nd  = us.get("나스닥",   {})
    kp_pct = kp.get("change_pct", 0)
    kd_pct = kd.get("change_pct", 0)
    sp_pct = sp.get("change_pct", 0)
    nd_pct = nd.get("change_pct", 0)

    # ── 헤더 ──
    st.markdown(f"""<div class="hdr">
      <div><div class="hdr-title">오늘의 시장</div><div class="hdr-sub">{_now()} 기준</div></div>
      <div style="color:#8E8E93;font-size:20px;"><i class="ti ti-refresh"></i></div>
    </div>""", unsafe_allow_html=True)

    # ── 히어로 카드 ──
    badge_txt, status, desc, tip = _market_hero(idx)
    desc_full = (f"{desc} · S&P500 {'+' if sp_pct>=0 else ''}{sp_pct:.2f}%"
                 f" / 나스닥 {'+' if nd_pct>=0 else ''}{nd_pct:.2f}%")
    st.markdown(f"""<div class="hero">
      <div class="hero-badge"><i class="ti ti-rocket" style="font-size:13px;"></i> {badge_txt}</div>
      <div class="hero-status">{status}</div>
      <div class="hero-desc">{desc_full}</div>
      <div class="hero-tip"><i class="ti ti-bulb" style="font-size:14px;flex-shrink:0;"></i> {tip}</div>
    </div>""", unsafe_allow_html=True)

    # ── 지수 카드 ──
    kp_cls = "up-card" if kp_pct >= 0 else "down-card"
    kd_cls = "up-card" if kd_pct >= 0 else "down-card"
    kp_arr = "▲" if kp_pct >= 0 else "▼"
    kd_arr = "▲" if kd_pct >= 0 else "▼"
    st.markdown(f"""<div class="idx-row">
      <div class="idx-card {kp_cls}">
        <div class="idx-name">KOSPI</div>
        <div class="idx-val">{kp.get('current',0):,.2f}</div>
        <div class="idx-chg" style="color:{'#E24B4A' if kp_pct>=0 else '#185FA5'};">{kp_arr} {abs(kp.get('change',0)):,.2f} ({abs(kp_pct):.2f}%)</div>
      </div>
      <div class="idx-card {kd_cls}">
        <div class="idx-name">KOSDAQ</div>
        <div class="idx-val">{kd.get('current',0):,.2f}</div>
        <div class="idx-chg" style="color:{'#E24B4A' if kd_pct>=0 else '#185FA5'};">{kd_arr} {abs(kd.get('change',0)):,.2f} ({abs(kd_pct):.2f}%)</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 미국 지수 카드 (3개) ──
    dw_pct = us.get("다우", {}).get("change_pct", 0)
    def _us_chg(v): return f"{'▲' if v>=0 else '▼'} {abs(v):.2f}%"
    def _us_clr(v): return "#E24B4A" if v >= 0 else "#185FA5"
    st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:0 16px 12px;">
      <div style="background:#fff;border-radius:12px;padding:10px 12px;border:0.5px solid #E5E5EA;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:2px;">S&P500</div>
        <div style="font-size:13px;font-weight:700;">{us.get('S&P500',{}).get('current',0):,.0f}</div>
        <div style="font-size:10px;color:{_us_clr(sp_pct)};">{_us_chg(sp_pct)}</div>
      </div>
      <div style="background:#fff;border-radius:12px;padding:10px 12px;border:0.5px solid #E5E5EA;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:2px;">나스닥</div>
        <div style="font-size:13px;font-weight:700;">{us.get('나스닥',{}).get('current',0):,.0f}</div>
        <div style="font-size:10px;color:{_us_clr(nd_pct)};">{_us_chg(nd_pct)}</div>
      </div>
      <div style="background:#fff;border-radius:12px;padding:10px 12px;border:0.5px solid #E5E5EA;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:2px;">다우</div>
        <div style="font-size:13px;font-weight:700;">{us.get('다우',{}).get('current',0):,.0f}</div>
        <div style="font-size:10px;color:{_us_clr(dw_pct)};">{_us_chg(dw_pct)}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 시장 분석 (Gemini or rule-based) ──
    with st.spinner("AI 시장 분석 중..."):
        analysis_lines = analyze_us_impact(us, idx, ma_kp, kp_hist)

    dot_icon = {"dot-blue": "🔵", "dot-orange": "🟠", "dot-green": "🟢"}
    items_html = ""
    for cls, label, text in analysis_lines:
        items_html += f"""<div style="padding:14px 0;border-bottom:0.5px solid #F0F0F5;">
          <div style="display:flex;align-items:center;gap:7px;margin-bottom:6px;">
            <div class="dot {cls}"></div>
            <span style="font-size:13px;font-weight:600;color:#1A1A2E;">{label}</span>
          </div>
          <div style="font-size:12px;color:#3C3C43;line-height:1.65;">{text}</div>
        </div>"""
    # 마지막 border 제거
    items_html = items_html.rsplit("border-bottom:0.5px solid #F0F0F5;", 1)
    items_html = items_html[0] + ("border-bottom:none;" + items_html[1] if len(items_html) > 1 else "")

    _phase = market_phase()
    _analysis_title = {
        "open":    "장중 실시간 분석",
        "close":   "오늘 시장 총정리",
        "pre":     "장 시작 전 체크",
        "weekend": "이번 주 시장 분석",
    }.get(_phase, "시장 분석")
    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-search" style="font-size:15px;color:#5B5BD6;"></i>{_analysis_title}</div>
      <div class="card" style="padding:4px 16px 0;">{items_html}</div>
    </div>""", unsafe_allow_html=True)

    # ── 내일 예측 (Gemini or rule-based) ──
    with st.spinner("내일 시장 예측 생성 중..."):
        fc = generate_forecast(us, idx, ma_kp)

    def _reason_html(items):
        out = ""
        for r in items:
            # "제목: 내용" 형태 분리
            if ":" in r:
                title, body = r.split(":", 1)
                out += (
                    f'<div style="margin-bottom:10px;padding:10px 12px;background:#F8F8FC;border-radius:10px;">'
                    f'<div style="font-size:11px;font-weight:700;color:#5B5BD6;margin-bottom:3px;">{title.strip()}</div>'
                    f'<div style="font-size:11px;color:#3C3C43;line-height:1.6;">{body.strip()}</div>'
                    f'</div>'
                )
            else:
                out += (
                    f'<div style="margin-bottom:8px;padding:8px 12px;background:#F8F8FC;border-radius:10px;">'
                    f'<div style="font-size:11px;color:#3C3C43;line-height:1.6;">{r}</div>'
                    f'</div>'
                )
        return out

    def _point_html(items):
        out = ""
        for p in items:
            if ":" in p:
                title, body = p.split(":", 1)
                out += (
                    f'<div style="margin-bottom:10px;padding:10px 12px;background:#FFF8EC;border-radius:10px;border-left:3px solid #F8A521;">'
                    f'<div style="font-size:11px;font-weight:700;color:#B46E00;margin-bottom:3px;">{title.strip()}</div>'
                    f'<div style="font-size:11px;color:#3C3C43;line-height:1.6;">{body.strip()}</div>'
                    f'</div>'
                )
            else:
                out += (
                    f'<div style="margin-bottom:8px;padding:8px 12px;background:#FFF8EC;border-radius:10px;border-left:3px solid #F8A521;">'
                    f'<div style="font-size:11px;color:#3C3C43;line-height:1.6;">{p}</div>'
                    f'</div>'
                )
        return out

    reasons_html = _reason_html(fc["reasons"])
    points_html  = _point_html(fc["points"])
    bar_w = int(fc["confidence"] * 0.8)
    conf_clr = "#30D158" if fc["confidence"] >= 65 else "#F8A521" if fc["confidence"] >= 50 else "#E24B4A"

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-calendar" style="font-size:15px;color:#5B5BD6;"></i>내일 시장 예측</div>
      <div class="forecast-card">
        <div class="forecast-header">
          <div class="forecast-title">
            <i class="ti {fc['icon']}" style="color:{fc['icon_color']};"></i>
            {fc['short_title']}
          </div>
          <span class="confidence-badge" style="background:{conf_clr}22;color:{conf_clr};border:1px solid {conf_clr}44;">신뢰도 {fc['confidence']}%</span>
        </div>
        <div style="margin:8px 0 12px;">
          <div style="display:flex;justify-content:space-between;font-size:10px;color:#8E8E93;margin-bottom:4px;">
            <span>예측 신뢰도</span><span style="color:{conf_clr};font-weight:600;">{fc['confidence']}%</span>
          </div>
          <div style="height:6px;background:#F0F0F5;border-radius:3px;overflow:hidden;">
            <div style="height:100%;border-radius:3px;background:{conf_clr};width:{bar_w}%;transition:width 0.6s;"></div>
          </div>
        </div>
        <div style="margin-bottom:6px;">
          <div style="font-size:12px;font-weight:700;color:#1A1A2E;margin-bottom:8px;">
            <i class="ti ti-pin" style="color:#E24B4A;font-size:12px;"></i> 예측 근거
          </div>
          {reasons_html}
        </div>
        <div>
          <div style="font-size:12px;font-weight:700;color:#1A1A2E;margin-bottom:8px;">
            <i class="ti ti-eye" style="color:#F8A521;font-size:12px;"></i> 내일 꼭 확인할 포인트
          </div>
          {points_html}
        </div>
        <div class="warn-box2">
          <i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>
          예측은 참고용이며 투자 결정은 본인 판단으로 하세요
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 예측 DB 저장 (하루 1회) ──
    _save_today_prediction(fc)

    # ── 예측 히스토리 ──
    _render_prediction_history()

    # ── 수급 링크 ──
    if st.button("› KOSPI · KOSDAQ 상세 분석 보기", key="btn_market_detail",
                 use_container_width=True):
        st.session_state["show_market_detail"] = True
        st.rerun()
    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 흐름</div>
    </div>""", unsafe_allow_html=True)
    if st.button("📊 외국인·기관 KOSPI 수급 상세 보기 ›",
                 key="btn_supply_detail", use_container_width=True):
        st.session_state["show_supply_detail"] = True
        st.rerun()


def render_supply_detail(inv_df: "pd.DataFrame"):
    """외국인·기관 수급 상세 페이지 (09_supply_demand_screen.html 스타일)."""
    import numpy as np

    # ── 뒤로가기 헤더 ──
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("‹ 홈", key="btn_back_supply"):
            st.session_state["show_supply_detail"] = False
            st.rerun()
    with col_title:
        st.markdown(f"""<div style="padding:6px 0;">
          <div style="font-size:15px;font-weight:600;">외국인·기관 수급 흐름</div>
          <div style="font-size:11px;color:#8E8E93;">KOSPI 전체 · {_now()}</div>
        </div>""", unsafe_allow_html=True)

    # ── 탭 선택 (pill 스타일) ──
    if "supply_view" not in st.session_state:
        st.session_state["supply_view"] = "외국인"
    view = st.session_state["supply_view"]

    _tabs = ["외국인", "기관", "동반매수"]
    _tc = st.columns(3)
    for _i, _t in enumerate(_tabs):
        with _tc[_i]:
            _active = view == _t
            if st.button(
                _t,
                key=f"sv_{_t}",
                use_container_width=True,
                type="primary" if _active else "secondary",
            ):
                st.session_state["supply_view"] = _t
                st.rerun()
    view = st.session_state["supply_view"]

    # ── 데이터 준비 ──
    if inv_df is None or inv_df.empty:
        st.warning("수급 데이터를 일시적으로 불러오지 못했어요. 잠시 후 새로고침해보세요.")
        st.caption("⚠️ 투자 결정은 본인 책임입니다")
        return

    has_f = "외국인" in inv_df.columns
    has_i = "기관"   in inv_df.columns

    f_series = inv_df["외국인"] if has_f else pd.Series(dtype=float)
    i_series = inv_df["기관"]   if has_i else pd.Series(dtype=float)

    def _streak(s: "pd.Series") -> int:
        """최근 연속 순매수 일수 (양수 기준)"""
        cnt = 0
        for v in reversed(s.values):
            if v > 0:
                cnt += 1
            else:
                break
        return cnt

    def _buy_days(s: "pd.Series") -> int:
        return int((s > 0).sum())

    def _to_eok(v: float) -> float:
        """원 → 억원"""
        return round(v / 1e8, 1)

    def _cumul_eok(s: "pd.Series") -> float:
        return _to_eok(s.sum())

    is_combined = (view == "동반매수")

    if view == "외국인":
        main_s = f_series
        main_lbl = "외국인"
    elif view == "기관":
        main_s = i_series
        main_lbl = "기관"
    else:
        main_s = f_series   # 동반매수 - streak/요약은 외국인 기준
        main_lbl = "외국인+기관"

    # 동반 매수/매도일 계산 (항상)
    both_buy  = int(((f_series > 0) & (i_series > 0)).sum()) if (has_f and has_i) else 0
    both_sell = int(((f_series < 0) & (i_series < 0)).sum()) if (has_f and has_i) else 0

    streak   = _streak(main_s)  if len(main_s) else 0
    buy_days = _buy_days(main_s) if len(main_s) else 0
    cumul_jo = _cumul_eok(main_s) if len(main_s) else 0

    # ── 요약 카드 ──
    cumul_sign = "+" if cumul_jo >= 0 else ""
    cumul_clr  = "#E24B4A" if cumul_jo >= 0 else "#185FA5"
    if is_combined:
        card1_lbl = "동반 매수일"
        card1_val = f'<div style="font-size:15px;font-weight:700;color:#3C3489;">{both_buy}일</div>'
        card2_lbl = "동반 매도일"
        card2_val = f'<div style="font-size:15px;font-weight:700;color:#E24B4A;">{both_sell}일</div>'
        card3_lbl = "엇갈린 날"
        card3_val = f'<div style="font-size:15px;font-weight:700;color:#8E8E93;">{len(inv_df)-both_buy-both_sell}일</div>'
    else:
        card1_lbl = "25일 순매수"
        card1_val = f'<div style="font-size:15px;font-weight:700;color:{cumul_clr};">{cumul_sign}{cumul_jo:,.1f}억원</div>'
        card2_lbl = "연속 매수일"
        card2_val = f'<div style="font-size:15px;font-weight:700;color:#3C3489;">{streak}일</div>'
        card3_lbl = "매수 우위일"
        card3_val = f'<div style="font-size:15px;font-weight:700;color:#E24B4A;">{buy_days}일</div>'

    st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:0 16px 12px;">
      <div style="background:#fff;border-radius:12px;padding:10px 12px;border:0.5px solid #E5E5EA;text-align:center;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">{card1_lbl}</div>{card1_val}
      </div>
      <div style="background:#fff;border-radius:12px;padding:10px 12px;border:0.5px solid #E5E5EA;text-align:center;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">{card2_lbl}</div>{card2_val}
      </div>
      <div style="background:#fff;border-radius:12px;padding:10px 12px;border:0.5px solid #E5E5EA;text-align:center;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">{card3_lbl}</div>{card3_val}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 바 차트 (Plotly) ──
    import plotly.graph_objects as go
    if is_combined and has_f and has_i:
        # 동반매수: 외국인(파랑)+기관(녹) 누적 막대, 동반매수일 강조
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=f_series.index, y=f_series.values / 1e8,
            name="외국인", marker_color="rgba(91,91,214,0.7)",
        ))
        fig.add_trace(go.Bar(
            x=i_series.index, y=i_series.values / 1e8,
            name="기관", marker_color="rgba(59,109,17,0.6)",
        ))
        fig.update_layout(barmode="overlay")
        chart_title = "📊 외국인·기관 동반 매수·매도 현황 (억원)"
    else:
        vals   = main_s.values / 1e8  # 원 → 억원
        colors = ["#E24B4A" if v >= 0 else "#185FA5" for v in vals]
        fig = go.Figure(go.Bar(
            x=main_s.index, y=vals,
            marker_color=colors, name=main_lbl,
        ))
        chart_title = f"📊 {main_lbl} 일별 순매수 (억원, KOSPI 전체)"

    fig.update_layout(
        height=180, margin=dict(l=4, r=4, t=28, b=4),
        paper_bgcolor="#ffffff", plot_bgcolor="#F8F8FA",
        xaxis=dict(showgrid=False, tickfont=dict(size=9), tickformat="%m/%d"),
        yaxis=dict(showgrid=True, gridcolor="#F0F0F5", tickfont=dict(size=9),
                   ticksuffix="억", zeroline=True, zerolinecolor="#E5E5EA"),
        title=dict(text=chart_title, font=dict(size=11), x=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, font=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── 연속매수 streak 박스 ──
    if is_combined:
        ratio = int(both_buy / len(inv_df) * 100) if len(inv_df) else 0
        if both_buy >= both_sell:
            streak_msg = f"외국인·기관 동반 매수 우위"
            streak_sub = f"25일 중 동반 매수 {both_buy}일({ratio}%) · 동반 매도 {both_sell}일"
        else:
            streak_msg = f"외국인·기관 동반 매도 우위"
            streak_sub = f"25일 중 동반 매도 {both_sell}일 · 동반 매수 {both_buy}일({ratio}%)"
    elif streak >= 3:
        streak_msg = f"{main_lbl} {streak}일 연속 순매수 중"
        streak_sub = f"누적 {cumul_sign}{cumul_jo:,.1f}억원 · 강한 매집 신호"
    elif streak == 0:
        sell_streak = 0
        for v in reversed(main_s.values):
            if v < 0: sell_streak += 1
            else: break
        streak_msg = f"{main_lbl} {sell_streak}일 연속 순매도 중"
        streak_sub = f"누적 {cumul_sign}{cumul_jo:,.1f}억원 · 매도 압력 주의"
    else:
        streak_msg = f"{main_lbl} {streak}일 연속 순매수"
        streak_sub = f"누적 {cumul_sign}{cumul_jo:,.1f}억원"

    icon_bg = "#5B5BD6" if streak >= 3 else "#BA7517" if streak > 0 else "#E24B4A"
    icon_nm = "ti-flame" if streak >= 3 else "ti-minus" if streak == 0 else "ti-trending-up"
    st.markdown(f"""<div style="background:#EEEDFE;border-radius:12px;padding:12px 14px;margin:0 16px 12px;display:flex;align-items:center;gap:12px;">
      <div style="width:36px;height:36px;background:{icon_bg};border-radius:10px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;flex-shrink:0;">
        <i class="ti {icon_nm}"></i>
      </div>
      <div>
        <div style="font-size:13px;font-weight:600;color:#3C3489;">{streak_msg}</div>
        <div style="font-size:11px;color:#534AB7;margin-top:2px;">{streak_sub}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 일별 상세 테이블 ──
    recent = inv_df.tail(8).iloc[::-1]  # 최신순
    max_abs = max(
        float(abs(recent.get("외국인", pd.Series([0])).max())),
        float(abs(recent.get("외국인", pd.Series([0])).min())),
        float(abs(recent.get("기관",   pd.Series([0])).max())),
        float(abs(recent.get("기관",   pd.Series([0])).min())),
        1
    )
    rows_html = ""
    for dt, row in recent.iterrows():
        date_s = pd.Timestamp(dt).strftime("%m/%d")
        f_val  = float(row.get("외국인", 0))
        i_val  = float(row.get("기관",   0))
        # 추세 바 (외국인 기준)
        bar_w  = int(abs(f_val) / max_abs * 85)
        bar_cls = "bar-buy" if f_val >= 0 else "bar-sell"

        def _fmt(v):
            sign = "+" if v >= 0 else ""
            color = "#E24B4A" if v >= 0 else "#185FA5"
            eok = v / 1e8
            return f'<span style="color:{color};font-weight:600;">{sign}{eok:,.1f}억</span>'

        rows_html += f"""<div style="display:grid;grid-template-columns:44px 1fr 72px 72px;gap:4px;align-items:center;padding:7px 0;border-bottom:0.5px solid #F0F0F5;font-size:11px;">
          <span style="color:#8E8E93;">{date_s}</span>
          <div style="height:5px;background:#F0F0F5;border-radius:3px;overflow:hidden;">
            <div style="height:5px;border-radius:3px;width:{bar_w}%;{'background:rgba(226,75,74,0.4)' if f_val>=0 else 'background:rgba(24,95,165,0.3)'};"></div>
          </div>
          <div style="text-align:right;">{_fmt(f_val)}</div>
          <div style="text-align:right;">{_fmt(i_val)}</div>
        </div>"""

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-list-details" style="font-size:15px;color:#5B5BD6;"></i>일별 상세 (최근 8일)</div>
      <div class="card" style="padding:10px 16px;">
        <div style="display:grid;grid-template-columns:44px 1fr 72px 72px;gap:4px;padding-bottom:6px;border-bottom:0.5px solid #E5E5EA;font-size:10px;color:#8E8E93;font-weight:500;">
          <span>날짜</span><span>추세</span>
          <span style="text-align:right;">외국인</span>
          <span style="text-align:right;">기관</span>
        </div>
        {rows_html}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 누적 현황 ──
    f_cumul  = _to_eok(f_series.sum()) if has_f else 0.0   # 억원
    i_cumul  = _to_eok(i_series.sum()) if has_i else 0.0
    f_bdays  = _buy_days(f_series) if has_f else 0
    i_bdays  = _buy_days(i_series) if has_i else 0
    both_b   = int(((f_series > 0) & (i_series > 0)).sum()) if (has_f and has_i) else 0
    both_s   = int(((f_series < 0) & (i_series < 0)).sum()) if (has_f and has_i) else 0
    total_d  = len(inv_df)

    def _jo(v): return f"{'+'if v>=0 else ''}{v:,.1f}억원"
    fc_clr = "#E24B4A" if f_cumul >= 0 else "#185FA5"
    ic_clr = "#E24B4A" if i_cumul >= 0 else "#185FA5"

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-calculator" style="font-size:15px;color:#5B5BD6;"></i>누적 현황 (25일)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">외국인 누적</div>
          <div style="font-size:14px;font-weight:700;color:{fc_clr};">{_jo(f_cumul)}</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:2px;">매수 우위 {f_bdays}일</div>
        </div>
        <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">기관 누적</div>
          <div style="font-size:14px;font-weight:700;color:{ic_clr};">{_jo(i_cumul)}</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:2px;">매수 우위 {i_bdays}일</div>
        </div>
        <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">동반 매수일</div>
          <div style="font-size:14px;font-weight:700;color:#3C3489;">{both_b}일</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:2px;">전체의 {int(both_b/total_d*100) if total_d else 0}%</div>
        </div>
        <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">동반 매도일</div>
          <div style="font-size:14px;font-weight:700;color:#8E8E93;">{both_s}일</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:2px;">전체의 {int(both_s/total_d*100) if total_d else 0}%</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 시스템 판단 ──
    if f_cumul > 0 and streak >= 5:
        advice = (f"외국인이 {streak}일 연속 순매수하며 25일 누적 {_jo(f_cumul)}를 기록하고 있어요. "
                  f"{'기관도 동반 매수 흐름이라 수급 기반이 탄탄해요.' if i_cumul > 0 else '기관은 아직 관망세예요.'} "
                  f"다만 외국인·기관이 동반 매도로 전환되는 날을 주의깊게 모니터링할 필요가 있어요.")
    elif f_cumul > 0 and streak > 0:
        advice = (f"외국인이 최근 {streak}일 연속 순매수 중이고 25일 누적 {_jo(f_cumul)}예요. "
                  f"아직 강한 매집 신호는 아니지만 긍정적인 흐름이에요. "
                  f"연속 매수가 지속되는지 확인하며 접근하세요.")
    elif f_cumul < 0 and streak == 0:
        advice = (f"외국인이 25일 누적 {_jo(f_cumul)}으로 순매도 우위예요. "
                  f"외국인 매도세가 이어지는 동안은 상승 탄력이 제한될 수 있어요. "
                  f"순매수 전환 신호가 나올 때까지 신중하게 접근하세요.")
    else:
        advice = (f"외국인 25일 누적 {_jo(f_cumul)}, 기관 {_jo(i_cumul)}예요. "
                  f"수급 방향이 명확하지 않은 구간이에요. 동반 매수일({both_b}일) 추이를 확인하세요.")

    st.markdown(f"""<div class="advice-box" style="margin:0 0 12px;">
      <div class="advice-title"><i class="ti ti-bulb" style="font-size:15px;"></i>시스템 판단</div>
      <div class="advice-text">{advice}</div>
    </div>""", unsafe_allow_html=True)

    st.caption("⚠️ 투자 결정은 본인 책임입니다")
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)


def render_market_detail(idx, us, ma_kp, ma_kd, kp_hist, kd_hist):
    """KOSPI·KOSDAQ 상세 분석 페이지 (08_market_detail_screen.html 스타일)."""
    from home_analysis import _extra_metrics

    # ── 뒤로가기 헤더 ──
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("‹ 홈", key="btn_back_detail"):
            st.session_state["show_market_detail"] = False
            st.rerun()
    with col_title:
        st.markdown(f"""<div style="padding:6px 0;">
          <div style="font-size:15px;font-weight:600;">KOSPI · KOSDAQ 상세 분석</div>
          <div style="font-size:11px;color:#8E8E93;">{_now()} 기준</div>
        </div>""", unsafe_allow_html=True)

    kp  = idx.get("KOSPI",  {})
    kd  = idx.get("KOSDAQ", {})
    kp_cur = kp.get("current", 0)
    kd_cur = kd.get("current", 0)
    kp_pct = kp.get("change_pct", 0)
    kd_pct = kd.get("change_pct", 0)

    ex_kp = _extra_metrics(kp_hist, ma_kp)
    ex_kd = _extra_metrics(kd_hist, ma_kd)

    # ── 지수 카드 ──
    def _idx_card(name, cur, pct, vol_b):
        cls = "up-card" if pct >= 0 else "down-card"
        clr = "#E24B4A" if pct >= 0 else "#185FA5"
        arr = "▲" if pct >= 0 else "▼"
        vol_str = f"거래대금 {vol_b:.1f}조" if vol_b else ""
        return (f'<div class="idx-card {cls}">'
                f'<div class="idx-name">{name}</div>'
                f'<div class="idx-val">{cur:,.2f}</div>'
                f'<div class="idx-chg" style="color:{clr};">{arr} {abs(pct):.2f}%</div>'
                f'<div style="font-size:10px;color:#8E8E93;margin-top:4px;">{vol_str}</div>'
                f'</div>')
    st.markdown(f'<div class="idx-row">'
                f'{_idx_card("KOSPI", kp_cur, kp_pct, kp.get("volume_billion",0))}'
                f'{_idx_card("KOSDAQ", kd_cur, kd_pct, kd.get("volume_billion",0))}'
                f'</div>', unsafe_allow_html=True)

    # ── KOSPI 차트 ──
    if not kp_hist.empty and "종가" in kp_hist.columns:
        import plotly.graph_objects as go
        closes_raw   = kp_hist["종가"].dropna()
        close_s      = closes_raw.tail(60)
        ma20_s_chart = closes_raw.rolling(20).mean().tail(60)
        ma60_s_chart = closes_raw.rolling(60).mean().tail(60)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=close_s.index, y=close_s.values, mode="lines",
            line=dict(color="#5B5BD6", width=2), fill="tozeroy",
            fillcolor="rgba(91,91,214,0.08)", name="KOSPI", showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=ma20_s_chart.index, y=ma20_s_chart.values, mode="lines",
            line=dict(color="#F0A500", width=1.5, dash="dot"), name="20일선"
        ))
        fig.add_trace(go.Scatter(
            x=ma60_s_chart.index, y=ma60_s_chart.values, mode="lines",
            line=dict(color="#5B5BD6", width=1.5, dash="dash"), name="60일선"
        ))
        fig.update_layout(
            height=200, margin=dict(l=4, r=4, t=28, b=4),
            paper_bgcolor="#ffffff", plot_bgcolor="#F8F8FA",
            xaxis=dict(showgrid=False, tickfont=dict(size=9), tickformat="%m/%d"),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F5", tickfont=dict(size=9)),
            legend=dict(orientation="h", yanchor="top", y=1.12, x=0, font=dict(size=10)),
            title=dict(text="📈 KOSPI 60일 추이", font=dict(size=12), x=0),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── 이동평균선 현황 ──
    def _ma_box(label, val, dist_pct, above):
        if not val:
            return (f'<div class="ma-card"><div class="ma-card-label">{label}</div>'
                    f'<div class="ma-card-val" style="color:#C7C7CC;">미집계</div></div>')
        clr = "#E24B4A" if above else "#185FA5"
        arrow = "▲" if above else "▼"
        dist_s = f"{'+' if dist_pct >= 0 else ''}{dist_pct:.1f}%"
        return (f'<div class="ma-card"><div class="ma-card-label">{label}</div>'
                f'<div class="ma-card-val">{val:,.0f}p</div>'
                f'<div class="ma-card-sub" style="color:{clr};">현재가 {arrow} {dist_s}</div></div>')

    gc     = ma_kp.get("golden_cross", False)
    a20    = ma_kp.get("above_ma20", False)
    a60    = ma_kp.get("above_ma60", False)
    a200   = ma_kp.get("above_ma200", False)
    ma20v  = ma_kp.get("ma20")
    ma60v  = ma_kp.get("ma60")
    ma200v = ma_kp.get("ma200")
    d20    = ma_kp.get("ma20_dist_pct", 0)
    d60    = ma_kp.get("ma60_dist_pct", 0)
    d200   = ma_kp.get("ma200_dist_pct", 0)

    gc_label = "완전 정배열" if (a20 and a60 and a200 and gc) else "정배열" if (a20 and gc) else "역배열"
    gc_color = "#3C3489" if gc else "#791F1F"
    gc_sub   = "상승 모멘텀 강함" if gc else "하락 압력 주의"

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>이동평균선 현황 (KOSPI)</div>
      <div class="ma-grid">
        {_ma_box("20일선 (단기)", ma20v, d20, a20)}
        {_ma_box("60일선 (중기)", ma60v, d60, a60)}
        {_ma_box("200일선 (장기)", ma200v, d200, a200)}
        <div class="ma-card">
          <div class="ma-card-label">정배열 상태</div>
          <div class="ma-card-val" style="color:{gc_color};">{gc_label}</div>
          <div class="ma-card-sub" style="color:{gc_color};">{gc_sub}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 주요 지표 ──
    rsi     = ma_kp.get("rsi")
    disp    = ex_kp.get("disparity_20", 0)
    r5      = ex_kp.get("ret_5d", 0)
    vr      = ex_kp.get("vol_ratio", 0)
    vol_b   = kp.get("volume_billion", 0)

    def _rsi_status(v):
        if v is None: return ("집계중", "status-ok", 50)
        if v >= 70:   return ("과열 주의", "status-warn", int(v))
        if v <= 30:   return ("침체 구간", "status-warn", int(v))
        return ("정상", "status-ok", int(v))

    def _disp_status(v):
        if v >= 110:  return ("강한 과열", "status-danger")
        if v >= 108:  return ("과열 주의", "status-warn")
        if v <= 97:   return ("침체 구간", "status-warn")
        return ("정상", "status-ok")

    def _r5_status(v):
        if v >= 10:   return ("급등 피로", "status-danger")
        if v >= 5:    return ("강한 상승", "status-warn")
        if v <= -10:  return ("급락 과매도", "status-danger")
        return ("정상", "status-ok")

    def _vr_status(v):
        if v >= 1.5:  return ("매우 활발", "status-ok")
        if v >= 1.2:  return ("활발", "status-ok")
        if v <= 0.6:  return ("관망", "status-warn")
        return ("보통", "status-ok")

    rsi_lbl, rsi_cls, rsi_w  = _rsi_status(rsi)
    disp_lbl, disp_cls       = _disp_status(disp)
    r5_lbl,   r5_cls         = _r5_status(r5)
    vr_lbl,   vr_cls         = _vr_status(vr)

    rsi_str  = f"{rsi:.0f}" if rsi else "—"
    disp_str = f"{disp:.1f}%" if disp else "—"
    r5_str   = f"{r5:+.2f}%" if r5 else "—"
    vr_str   = f"{vr:.1f}배" if vr else f"{vol_b:.1f}조"

    rsi_bar_color = '#BA7517' if rsi and rsi >= 70 else '#3B6D11' if rsi and rsi <= 30 else '#5B5BD6'
    r5_color = '#E24B4A' if r5 >= 0 else '#185FA5'

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-chart-bar" style="font-size:15px;color:#5B5BD6;"></i>주요 기술 지표
        <span style="font-size:10px;color:#8E8E93;font-weight:400;margin-left:6px;">지표 이름 눌러서 상세 해석 보기</span>
      </div>
      <div class="card">
        <div class="ind-row">
          <span class="ind-label">RSI (14일)</span>
          <div class="ind-right">
            <div class="rsi-bar-wrap"><div class="rsi-bar-fill" style="width:{rsi_w}%;background:{rsi_bar_color};"></div></div>
            <span class="ind-val">{rsi_str}</span>
            <span class="ind-status {rsi_cls}">{rsi_lbl}</span>
          </div>
        </div>
        <div class="ind-row">
          <span class="ind-label">이격도 (20일선)</span>
          <div class="ind-right">
            <span class="ind-val">{disp_str}</span>
            <span class="ind-status {disp_cls}">{disp_lbl}</span>
          </div>
        </div>
        <div class="ind-row">
          <span class="ind-label">5일 누적 등락률</span>
          <div class="ind-right">
            <span class="ind-val" style="color:{r5_color};">{r5_str}</span>
            <span class="ind-status {r5_cls}">{r5_lbl}</span>
          </div>
        </div>
        <div class="ind-row">
          <span class="ind-label">거래량 (20일 평균비)</span>
          <div class="ind-right">
            <span class="ind-val">{vr_str}</span>
            <span class="ind-status {vr_cls}">{vr_lbl}</span>
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 지표 상세 팝오버 버튼 ──
    _pc1, _pc2, _pc3, _pc4 = st.columns(4)

    # RSI 팝오버
    with _pc1:
        with st.popover("📊 RSI", use_container_width=True):
            st.markdown(f"### 📊 RSI (상대강도지수)")
            st.markdown(f"**현재값: {rsi_str} → {rsi_lbl}**")
            st.divider()
            st.markdown("""
**RSI가 뭐예요?**

주식 시장에서 최근 14거래일 동안 "오른 날의 평균 상승폭"과 "내린 날의 평균 하락폭"을 비교해서 0~100 사이 숫자로 표현한 지표예요.

쉽게 말하면 — **"시장이 지금 얼마나 달아올랐거나, 얼마나 지쳐있는가"** 를 수치로 보여주는 온도계 같은 거예요.

---

**숫자별로 어떤 의미예요?**

🔴 **RSI 70 이상 → 과열 구간**
사람들이 너무 흥분해서 계속 사고 있는 상태예요. 고무줄이 한쪽으로 너무 많이 당겨진 것처럼, 언제든 반대 방향으로 튕겨나올 준비가 된 상태거든요. 이 구간에서 새로 사면 "고점 매수"가 될 확률이 높아요.

🟢 **RSI 30~70 → 정상 구간**
과열도, 침체도 아닌 건강한 흐름이에요. 추세 방향을 따라가는 게 가장 합리적인 구간이에요.

🔵 **RSI 30 이하 → 침체 구간**
너무 많이 팔려서 시장이 지쳐있는 상태예요. 반대로 말하면 "쌀 때 살 수 있는 기회"가 가까울 수 있어요. 다만 RSI가 낮다고 무조건 반등하는 건 아니라서, 다른 지표와 함께 확인해야 해요.

---
""")
            ma20_ref = kp_cur / (disp / 100) if disp else 0
            if rsi:
                if rsi >= 70:
                    st.warning(f"⚠️ 지금은 RSI {rsi:.0f}으로 과열 구간이에요. 지금 새로 사는 건 고점 매수 위험이 있어요. 이미 보유 중이라면 홀딩하되 목표가에 가까워지면 일부 매도를 고려해보세요.")
                elif rsi <= 30:
                    st.success(f"✅ RSI {rsi:.0f}으로 침체 구간이에요. 시장이 많이 지쳐있다는 신호예요. 분할 매수를 검토할 수 있는 구간이지만, 추가 하락 가능성도 있으니 한 번에 다 사지 말고 나눠서 접근하세요.")
                elif rsi >= 60:
                    st.info(f"ℹ️ RSI {rsi:.0f}으로 정상이지만 약간 달아오르는 중이에요. 추세는 좋으나 70에 가까워지면 속도를 조절하세요.")
                else:
                    st.info(f"ℹ️ RSI {rsi:.0f}으로 정상 범위예요. 과열도 침체도 아닌 건강한 상태예요. 추세를 따라가세요.")
            st.caption("⚠️ 투자 결정은 본인 책임입니다")

    # 이격도 팝오버
    with _pc2:
        with st.popover("📏 이격도", use_container_width=True):
            st.markdown(f"### 📏 이격도 (괴리율)")
            st.markdown(f"**현재값: {disp_str} → {disp_lbl}**")
            st.divider()
            st.markdown("""
**이격도가 뭐예요?**

지금 KOSPI 지수가 20일 평균선에서 얼마나 멀어져 있는지를 % 로 나타낸 거예요.

계산식은 간단해요: **현재가 ÷ 20일 평균 × 100**

100%면 딱 평균선 위에 있다는 뜻이고, 110%면 평균보다 10% 위에 있다는 거예요.

비유하자면 — 용수철을 생각해보세요. 용수철이 평균 위치에서 멀어질수록, 다시 제자리로 돌아오려는 힘이 세지죠. 주가도 비슷해요. 평균선에서 너무 멀어지면 결국 다시 가까워지는 경향이 있어요.

---

**숫자별로 어떤 의미예요?**

🔴 **110% 이상 → 강한 과열**
평균보다 10% 이상 위에 있는 거예요. 용수철이 아주 많이 당겨진 상태, 조정(하락) 가능성이 높아져요.

🟡 **108~110% → 과열 주의**
평균보다 8~10% 위에 있어요. 슬슬 긴장해야 할 구간이에요.

🟢 **97~108% → 정상**
평균선 근처에서 움직이는 건강한 흐름이에요. 이 구간이 가장 안정적이에요.

🔵 **97% 이하 → 침체**
평균 아래로 내려왔어요. 저가 매수 기회일 수 있지만, 하락 추세가 이어질 수도 있어요.

---
""")
            if disp:
                ma20_ref = kp_cur / (disp / 100) if disp else 0
                gap_p = kp_cur - ma20_ref
                if disp >= 110:
                    st.warning(f"⚠️ 현재 이격도 {disp_str} — 20일 평균선({ma20_ref:,.0f}p)에서 {gap_p:+,.0f}p나 위에 있어요. 용수철이 많이 당겨진 상태예요. 조정이 오면 {ma20_ref:,.0f}p 근처까지 내려올 수 있으니 신규 진입은 신중하게 하세요.")
                elif disp >= 108:
                    st.warning(f"⚠️ 이격도 {disp_str} — 과열 주의 구간이에요. 20일선({ma20_ref:,.0f}p)에서 {gap_p:+,.0f}p 올라와 있어요. 눌림목(잠깐 내려오는 구간)을 기다려서 진입하는 게 더 유리해요.")
                elif disp <= 97:
                    st.success(f"✅ 이격도 {disp_str} — 20일선 아래에 있어요. 평균보다 싸게 살 수 있는 구간이에요. 추세 반전 신호가 나오면 분할 매수를 고려해보세요.")
                else:
                    st.info(f"ℹ️ 이격도 {disp_str} — 20일 평균선({ma20_ref:,.0f}p)에서 {abs(gap_p):,.0f}p 떨어진 정상 범위예요. 안정적인 흐름이에요.")
            st.caption("⚠️ 투자 결정은 본인 책임입니다")

    # 5일 수익률 팝오버
    with _pc3:
        with st.popover("📈 5일 수익률", use_container_width=True):
            st.markdown(f"### 📈 5일 누적 등락률")
            st.markdown(f"**현재값: {r5_str} → {r5_lbl}**")
            st.divider()
            st.markdown("""
**5일 누적 등락률이 뭐예요?**

최근 5거래일(영업일 기준, 약 1주일) 동안 KOSPI가 얼마나 올랐거나 내렸는지를 합산한 수치예요.

이 지표가 중요한 이유는 — **단기적으로 너무 빨리 오른 건지, 너무 빨리 내린 건지**를 파악할 수 있거든요.

비유하자면 — 달리기 선수가 1주일 동안 매일 풀스피드로 달리면 결국 지쳐서 속도가 느려지잖아요. 주가도 같아요. 짧은 기간에 너무 많이 오르면 "숨 고르기(조정)"이 필요해져요.

---

**숫자별로 어떤 의미예요?**

🔴 **+10% 이상 → 급등 피로**
1주일 만에 10% 이상 올랐다는 건 정말 빠른 속도예요. 이미 많이 오른 걸 따라가서 사는 건 위험할 수 있어요.

🟡 **+5~+10% → 강한 상승**
추세는 분명히 좋지만, 속도가 빠른 편이에요. 흐름을 탄다면 좋지만 분할 매수로 리스크를 나누는 게 좋아요.

🟢 **-5~+5% → 정상**
일반적인 한 주의 등락 범위예요. 특별한 신호 없이 건강한 흐름이에요.

🔵 **-10% 이하 → 과매도**
1주일에 10% 이상 하락은 패닉셀(공포 매도)이 나왔을 가능성이 있어요. 반등 기회를 노릴 수 있지만, 하락 이유를 먼저 파악해야 해요.

---
""")
            if r5:
                if r5 >= 10:
                    st.warning(f"⚠️ 최근 5일 {r5_str} 급등했어요. 단기 피로가 누적된 상태예요. 지금 추격 매수는 고점 매수가 될 가능성이 높아요. 조정을 기다려보세요.")
                elif r5 <= -10:
                    st.success(f"✅ 최근 5일 {r5_str} 급락했어요. 과매도 구간이에요. 패닉셀이 나왔을 가능성이 있으니, 하락 원인이 일시적이라면 분할 매수를 검토해볼 수 있어요.")
                elif r5 >= 5:
                    st.info(f"ℹ️ 최근 5일 {r5_str} 오른 건 좋은 흐름이에요. 다만 속도가 빠른 편이니, 눌림목에서 나눠서 진입하는 전략이 안전해요.")
                elif r5 <= -5:
                    st.info(f"ℹ️ 최근 5일 {r5_str} 하락했어요. 단기 조정이 나오는 중이에요. 추세가 꺾인 건지, 일시적 조정인지 확인이 필요해요.")
                else:
                    st.info(f"ℹ️ 최근 5일 {r5_str}으로 정상 등락 범위예요. 큰 이슈 없이 안정적인 흐름이에요.")
            st.caption("⚠️ 투자 결정은 본인 책임입니다")

    # 거래량 팝오버
    with _pc4:
        with st.popover("📦 거래량", use_container_width=True):
            st.markdown(f"### 📦 거래량 (20일 평균비)")
            st.markdown(f"**현재값: {vr_str} → {vr_lbl}**")
            st.divider()
            st.markdown("""
**거래량 평균비가 뭐예요?**

오늘 거래량이 최근 20일(약 1달) 평균 거래량의 몇 배인지를 나타낸 지표예요.

거래량이 왜 중요하냐면 — **주가의 움직임에 얼마나 많은 사람이 참여했는지**를 알 수 있거든요.

비유하자면 — 선거 투표율이 높으면 결과의 신뢰도가 높은 것처럼, 거래량이 많을 때의 주가 움직임은 신뢰도가 높아요. 반대로 거래량이 적은 날의 상승은 "속임수 상승"일 수 있어요.

---

**숫자별로 어떤 의미예요?**

🔴 **1.5배 이상 → 매우 활발**
평소보다 1.5배 이상 많은 사람들이 거래에 참여한 거예요. 큰 뉴스가 있거나, 기관/외국인이 대량 매수/매도했을 가능성이 있어요. 방향이 위라면 강한 상승 신호, 아래라면 강한 하락 신호예요.

🟡 **1.2~1.5배 → 활발**
평소보다 조금 더 많이 거래됐어요. 시장 참여도가 높아지는 중이에요. 이 상태에서의 방향성은 신뢰도가 올라가요.

🟢 **0.6~1.2배 → 보통**
일반적인 거래량 수준이에요. 큰 이슈 없이 평범한 하루예요.

🔵 **0.6배 이하 → 관망세**
평소보다 훨씬 적게 거래됐어요. 시장이 방향을 못 잡고 눈치만 보는 상태예요. 이 구간에서의 돌파(상승/하락)는 믿기 어려워요.

---
""")
            if vr:
                if vr >= 1.5:
                    st.info(f"ℹ️ 거래량이 평균 대비 {vr_str}으로 매우 활발해요. 강한 수급이 몰린 거예요. 이 날의 방향(상승/하락)이 이후 추세를 결정할 가능성이 높아요.")
                elif vr >= 1.2:
                    st.info(f"ℹ️ 거래량이 평균 대비 {vr_str}으로 활발한 편이에요. 시장 참여자들이 관심을 갖고 있다는 신호예요. 현재 추세의 신뢰도가 높아요.")
                elif vr <= 0.6:
                    st.warning(f"⚠️ 거래량이 평균의 {vr_str} 수준으로 관망세예요. 방향성이 불분명한 상태예요. 지금 무리하게 진입하기보다 거래량이 회복되는 걸 확인한 후 움직이는 게 좋아요.")
                else:
                    st.info(f"ℹ️ 거래량이 평균 대비 {vr_str} 수준으로 정상이에요. 특별한 이슈 없는 평범한 거래일이에요.")
            else:
                st.info(f"ℹ️ 오늘 거래 대금은 {vol_b:.1f}조원이에요.")
            st.caption("⚠️ 투자 결정은 본인 책임입니다")

    # ── 섹터별 등락률 ──
    with st.spinner("섹터 데이터 불러오는 중..."):
        sectors = get_sector_performance()

    if sectors:
        rows = ""
        max_abs = max(abs(s["pct"]) for s in sectors) or 1
        for s in sectors:
            pct  = s["pct"]
            clr  = "#E24B4A" if pct >= 0 else "#185FA5"
            arr  = "▲" if pct >= 0 else "▼"
            bw   = int(abs(pct) / max_abs * 85)
            rows += (f'<div class="sector-row">'
                     f'<span class="sector-name">{s["name"]}</span>'
                     f'<div class="sector-bar-wrap"><div class="sector-bar" style="width:{bw}%;background:{clr};"></div></div>'
                     f'<span class="sector-pct" style="color:{clr};">{arr} {abs(pct):.1f}%</span>'
                     f'</div>')
        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-building-store" style="font-size:15px;color:#5B5BD6;"></i>섹터별 등락률</div>
          <div class="card">{rows}</div>
        </div>""", unsafe_allow_html=True)

    # ── 시스템 판단 ──
    trend_str = ma_kp.get("trend", "")
    if disp >= 110 or (r5 and r5 >= 10):
        advice = (f"KOSPI {trend_str} 상태이지만 이격도 {disp_str}, 5일 누적 {r5_str}로 단기 과열 신호가 나타나고 있어요. "
                  f"신규 진입보다 보유 유지, 눌림목에서 분할 매수 전략이 적절해요.")
    elif not a20:
        advice = (f"KOSPI가 20일선 아래에 있어 단기 하락 압력이 있어요. "
                  f"20일선({ma20v:,.0f}p) 회복 여부를 확인하고 접근하세요.")
    elif gc:
        advice = (f"KOSPI {trend_str} 상태로 추세가 건강해요. "
                  f"20일선({ma20v:,.0f}p) 지지 유지 시 추가 상승 여력이 있어요.")
    else:
        advice = f"KOSPI 추세 {trend_str}. 이평선 흐름을 주시하며 신중하게 접근하세요."

    st.markdown(f"""<div class="advice-box">
      <div class="advice-title"><i class="ti ti-bulb" style="font-size:15px;"></i>시스템 판단</div>
      <div class="advice-text">{advice}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)


def _save_today_prediction(fc: dict):
    """오늘 예측을 DB에 저장하고, 어제 예측 결과를 업데이트한다."""
    from datetime import date, timedelta
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    # 오늘 예측 저장 (INSERT OR IGNORE — 이미 있으면 무시)
    save_prediction(
        date=today_str,
        index_name="KOSPI",
        predicted_direction=fc["direction"],
        predicted_change=fc["predicted_pct"],
        confidence=fc["confidence"],
        prediction_basis=fc["basis"],
        gemini_text=fc.get("full_gemini_text", ""),
    )

    # 어제 예측의 실제 결과 업데이트 (actual_direction이 없는 경우)
    try:
        preds = get_recent_predictions(limit=5)
        for p in preds:
            if p["date"] == yesterday_str and p["actual_direction"] is None:
                idx_now = get_index_data()
                kp_now = idx_now.get("KOSPI", {})
                actual_pct = kp_now.get("change_pct", 0)
                if actual_pct > 0.3:
                    actual_dir = "up"
                elif actual_pct < -0.3:
                    actual_dir = "down"
                else:
                    actual_dir = "sideways"
                update_prediction_result(yesterday_str, "KOSPI", actual_dir, actual_pct)
                break
    except Exception:
        pass


def _render_prediction_history():
    """예측 히스토리 카드 렌더링."""
    try:
        preds   = get_recent_predictions(limit=7)
        stats   = get_prediction_accuracy()
        if not preds:
            return

        accuracy = stats.get("accuracy")
        evaluated = stats.get("evaluated", 0)
        acc_html = (
            f'<span style="font-size:12px;font-weight:700;color:#5B5BD6;">{accuracy}%</span>'
            f'<span style="font-size:10px;color:#8E8E93;margin-left:4px;">({evaluated}회 검증)</span>'
            if accuracy is not None else
            '<span style="font-size:11px;color:#8E8E93;">아직 검증 데이터 없음</span>'
        )

        dir_icon = {"up": "▲", "down": "▼", "sideways": "➡"}
        dir_clr  = {"up": "#E24B4A", "down": "#185FA5", "sideways": "#BA7517"}
        dir_kor  = {"up": "상승", "down": "하락", "sideways": "횡보"}

        rows_html = ""
        for p in preds[:5]:
            pred_dir = p.get("predicted_direction", "")
            act_dir  = p.get("actual_direction")
            correct  = p.get("is_correct")
            conf     = p.get("confidence") or 0
            pct      = p.get("predicted_change") or 0
            date_str = p.get("date", "")

            pred_html = (
                f'<span style="color:{dir_clr.get(pred_dir,"#8E8E93")};">'
                f'{dir_icon.get(pred_dir,"?")} {dir_kor.get(pred_dir,"?")}'
                f' ({"+"}{ pct:.1f}%)</span>'
            )
            if act_dir is not None:
                result_badge = (
                    '<span style="font-size:10px;background:#EAF3DE;color:#27500A;padding:1px 6px;border-radius:4px;">✓ 적중</span>'
                    if correct else
                    '<span style="font-size:10px;background:#FCEBEB;color:#791F1F;padding:1px 6px;border-radius:4px;">✗ 빗나감</span>'
                )
                act_html = (
                    f'<span style="font-size:10px;color:{dir_clr.get(act_dir,"#8E8E93")};">'
                    f'실제 {dir_icon.get(act_dir,"?")} {p.get("actual_change",0):+.1f}%</span>'
                )
            else:
                result_badge = '<span style="font-size:10px;color:#8E8E93;">결과 대기</span>'
                act_html = ""

            rows_html += f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:0.5px solid #F0F0F5;">
              <div>
                <div style="font-size:10px;color:#8E8E93;">{date_str}</div>
                <div style="font-size:11px;margin-top:2px;">{pred_html}</div>
              </div>
              <div style="text-align:right;">
                {result_badge}
                <div style="margin-top:3px;">{act_html}</div>
              </div>
            </div>"""

        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-history" style="font-size:15px;color:#5B5BD6;"></i>예측 히스토리</div>
          <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
              <span style="font-size:12px;font-weight:600;">누적 정확도</span>
              {acc_html}
            </div>
            {rows_html}
            <div style="margin-top:8px;font-size:10px;color:#8E8E93;">최근 {len(preds[:5])}일 예측 기록 · 매일 자동 업데이트</div>
          </div>
        </div>""", unsafe_allow_html=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# 뉴스 탭 — TOP10 의사결정 엔진
# ─────────────────────────────────────────────────────────
_NEWS_TTL = 600  # TOP10 갱신 주기 (초)


def render_news():
    # ── TOP10 — 10분 세션 캐시 ──
    now_ts = time.time()
    if ("top10_news" not in st.session_state or
            now_ts - st.session_state.get("top10_ts", 0) > _NEWS_TTL):
        with st.spinner("시장 핵심 뉴스 분석 중..."):
            all_news = fetch_market_news(max_items=15)
            top10 = rank_by_importance(all_news)[:10]
        with st.spinner("기사 본문 수집 중... (최대 8초)"):
            top10 = enrich_top10_summaries(top10)
        st.session_state.top10_news = top10
        st.session_state.top10_ts   = now_ts

    top10 = st.session_state.top10_news

    # ── 헤더 ──
    st.markdown(
        '<div class="hdr">'
        '<div><div class="hdr-title">시장 핵심 뉴스 TOP10</div>'
        '<div class="hdr-sub">' + _now() + ' 기준 · 수급+뉴스 중요도 분석</div></div>'
        '<div style="color:rgba(255,255,255,0.6);font-size:20px;"><i class="ti ti-chart-bar"></i></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not top10:
        st.info("뉴스를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        return

    # ── 감성 분포 (헤더 바로 아래, 구분 없이 이어지는 스타일) ──
    summ  = summarize_sentiment(top10)
    total = len(top10)
    pos_pct = round(summ["positive_count"] / total * 100) if total else 0
    neg_pct = round(summ["negative_count"] / total * 100) if total else 0
    neu_pct = max(0, 100 - pos_pct - neg_pct)
    overall_map = {"positive": ("긍정 우세", "#30D158"), "negative": ("부정 우세", "#E24B4A"),
                   "mixed": ("혼조", "#FF9F0A"), "neutral": ("중립", "#8E8E93")}
    ov_lbl, ov_clr = overall_map.get(summ["overall"], ("중립", "#8E8E93"))
    p_cnt = summ["positive_count"]
    n_cnt = summ["negative_count"]
    m_cnt = summ["mixed_count"]
    u_cnt = summ["neutral_count"]
    bar_pos  = f'<div style="width:{pos_pct}%;background:#30D158;"></div>'
    bar_neg  = f'<div style="width:{neg_pct}%;background:#E24B4A;"></div>'
    bar_neu  = f'<div style="width:{neu_pct}%;background:#E5E5EA;"></div>'
    lbl_html = (
        f'<span style="font-size:10px;color:#30D158;">● 긍정 {p_cnt}건</span>'
        f'<span style="font-size:10px;color:#E24B4A;margin-left:10px;">● 부정 {n_cnt}건</span>'
        f'<span style="font-size:10px;color:#FF9F0A;margin-left:10px;">● 혼조 {m_cnt}건</span>'
        f'<span style="font-size:10px;color:#8E8E93;margin-left:10px;">● 중립 {u_cnt}건</span>'
    )
    ov_span = f'<span style="font-size:11px;font-weight:700;color:{ov_clr};">{ov_lbl}</span>'
    st.markdown(
        '<div style="padding:10px 20px 14px;background:#fff;border-bottom:0.5px solid #E5E5EA;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        '<span style="font-size:11px;color:#8E8E93;">TOP10 감성 분포</span>' + ov_span +
        '</div>'
        '<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;gap:2px;">' +
        bar_pos + bar_neg + bar_neu +
        '</div>'
        '<div style="display:flex;margin-top:5px;">' + lbl_html + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── 2탭: 뉴스+분석 통합 / 전략 ──
    tab1, tab2 = st.tabs(["📰 뉴스 & 분석", "⚡ 투자 전략"])
    with tab1:
        st.markdown('<div class="section"><div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>시장 핵심 뉴스 TOP10</div></div>', unsafe_allow_html=True)
        _render_fact_tab(top10)
    with tab2:
        st.markdown('<div class="section"><div class="sec-title"><i class="ti ti-bulb" style="font-size:15px;color:#F0A500;"></i>투자 대응 전략</div></div>', unsafe_allow_html=True)
        _render_strategy_tab(top10)

    # ── 새로고침 버튼 (맨 아래) ──
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 TOP10 새로고침", key="news_refresh", use_container_width=True):
        st.session_state.pop("top10_news", None)
        st.session_state.pop("top10_ts",   None)
        st.rerun()


def _rank_badge(rank: int, score: float) -> str:
    """순위 + 중요도 점수 배지"""
    return (f'<span style="font-size:10px;font-weight:700;color:#fff;'
            f'background:#5B5BD6;padding:2px 7px;border-radius:8px;">#{rank}</span>'
            f'<span style="font-size:10px;color:#8E8E93;margin-left:4px;">{score:.0f}pt</span>')


def _render_fact_tab(items: list):
    """뉴스 탭 (FACT) — 제목 + 기사 요약 3줄 + 핵심 의미 분석."""
    cat_color = {n: c["color"] for n, c in CATEGORY_CONFIG.items()}
    for rank, n in enumerate(items, 1):
        sent     = n.get("sentiment", "neutral")
        label    = n.get("label", "중립")
        category = n.get("category", "전체")
        score    = n.get("importance_score", 0)
        bdg_type = {"positive": "pos", "negative": "neg", "mixed": "mix"}.get(sent, "neu")
        clr      = cat_color.get(category, "#5B5BD6")
        sent_bdg = f'<span class="badge badge-{bdg_type}">{label}</span>'
        cat_bdg  = f'<span style="font-size:10px;font-weight:600;color:{clr};background:{clr}18;padding:2px 7px;border-radius:10px;">{category}</span>'
        card_cls = "important" if sent == "positive" else ("negative" if sent == "negative" else "")

        # ── 기사 내용 + AI 분석 (항상 표시) ──
        summary = n.get("summary", "")
        ai_full = n.get("ai_summary", "")

        # 기사 내용: summary 항상 표시 (실제 본문이든 제목 기반 요약이든)
        summ_html = ""
        if summary:
            summ_html = (
                f'<div style="margin:8px 0;padding:10px 12px;'
                f'background:#F8F9FF;border-radius:8px;border-left:3px solid {clr};">'
                f'<div style="font-size:10px;font-weight:600;color:{clr};margin-bottom:5px;">📰 내용</div>'
                f'<div style="font-size:12px;color:#3C3C43;line-height:1.6;">{summary}</div>'
                f'</div>'
            )

        # AI 분석: 3섹션 전체 표시
        brief_html = ""
        if ai_full:
            brief_html = (
                f'<div style="margin-top:8px;padding:10px 12px;'
                f'background:#F2F0FF;border-radius:8px;border-left:3px solid #5B5BD6;">'
                f'<div style="font-size:12px;color:#3C3C43;line-height:1.7;">{ai_full}</div>'
                f'</div>'
            )

        # ── 푸터: 시간 + 관련종목 + 원문 링크 ──
        related  = n.get("related_stocks") or []
        chips    = "".join(f'<span class="stock-chip">{s["name"]}</span>' for s in related[:4] if isinstance(s, dict) and s.get("name"))
        link     = n.get("link", "")
        link_html = (f'<a href="{link}" target="_blank" style="font-size:10px;color:#5B5BD6;'
                     f'text-decoration:none;font-weight:600;">원문 →</a>') if link else ""
        footer   = (f'<div class="news-footer"><span class="news-time">{n.get("published","")}</span>'
                    f'<div style="display:flex;align-items:center;gap:6px;">{chips}{link_html}</div></div>')

        card_html = (
            f'<div class="news-card {card_cls}">'
            f'<div class="news-card-top">{_rank_badge(rank, score)}&nbsp;{sent_bdg}{cat_bdg}'
            f'<span class="news-source">{n.get("source","")}</span></div>'
            f'<div class="news-title">{n["title"]}</div>'
            f'{summ_html}'
            f'{brief_html}'
            f'{footer}'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)


def _render_analysis_tab(items: list):
    """분석 탭 (MEANING) — 제목 + generate_ai_summary + 관련종목."""
    cat_color = {n: c["color"] for n, c in CATEGORY_CONFIG.items()}
    for rank, n in enumerate(items, 1):
        sent     = n.get("sentiment", "neutral")
        label    = n.get("label", "중립")
        category = n.get("category", "전체")
        score    = n.get("importance_score", 0)
        bdg_type = {"positive": "pos", "negative": "neg", "mixed": "mix"}.get(sent, "neu")
        clr      = cat_color.get(category, "#5B5BD6")
        sent_bdg = f'<span class="badge badge-{bdg_type}">{label}</span>'
        cat_bdg  = f'<span style="font-size:10px;font-weight:600;color:{clr};background:{clr}18;padding:2px 7px;border-radius:10px;">{category}</span>'
        card_cls = "important" if sent == "positive" else ("negative" if sent == "negative" else "")
        ai_summary = n.get("ai_summary", "")
        related  = n.get("related_stocks") or []
        chips    = "".join(f'<span class="stock-chip">{s["name"]}</span>' for s in related[:4] if isinstance(s, dict) and s.get("name"))
        footer   = f'<div class="news-footer"><span class="news-time">{n.get("published","")}</span><div>{chips}</div></div>'
        card_html = (
            f'<div class="news-card {card_cls}">'
            f'<div class="news-card-top">{_rank_badge(rank, score)}&nbsp;{sent_bdg}{cat_bdg}'
            f'<span class="news-source">{n.get("source","")}</span></div>'
            f'<div class="news-title">{n["title"]}</div>'
            f'<div class="news-divider"></div>'
            f'<div class="ai-section">'
            f'<div class="ai-label"><i class="ti ti-sparkles" style="font-size:12px;"></i>AI 분석</div>'
            f'<div class="ai-text">{ai_summary}</div>'
            f'</div>'
            f'{footer}'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)


def _render_strategy_tab(items: list):
    """전략 탭 (ACTION) — 제목 + generate_strategy + 관련종목."""
    cat_color  = {n: c["color"] for n, c in CATEGORY_CONFIG.items()}
    _chip_style = {
        "chip-buy":  ("매수", "#E8FBF0", "#1A7C3F"),
        "chip-sell": ("매도", "#FEEDED", "#B01E1E"),
        "chip-warn": ("관망·주의", "#FFF3E0", "#B45309"),
        "chip-neu":  ("중립", "#F2F2F7", "#3C3C43"),
    }
    for rank, n in enumerate(items, 1):
        sent      = n.get("sentiment", "neutral")
        category  = n.get("category", "전체")
        score     = n.get("importance_score", 0)
        clr       = cat_color.get(category, "#5B5BD6")
        cat_bdg   = f'<span style="font-size:10px;font-weight:600;color:{clr};background:{clr}18;padding:2px 7px;border-radius:10px;">{category}</span>'
        card_cls  = "important" if sent == "positive" else ("negative" if sent == "negative" else "")
        strategy  = n.get("strategy", "관망.")
        sc        = n.get("strat_cls", "chip-neu")
        lbl, bg, fg = _chip_style.get(sc, ("중립", "#F2F2F7", "#3C3C43"))
        strat_chip = f'<span style="font-size:10px;font-weight:700;background:{bg};color:{fg};padding:2px 8px;border-radius:8px;">{lbl}</span>'
        related   = n.get("related_stocks") or []
        chips     = "".join(f'<span class="stock-chip">{s["name"]}</span>' for s in related[:4] if isinstance(s, dict) and s.get("name"))
        footer    = f'<div class="news-footer"><span class="news-time">{n.get("published","")}</span><div>{chips}</div></div>'
        card_html = (
            f'<div class="news-card {card_cls}">'
            f'<div class="news-card-top">{_rank_badge(rank, score)}&nbsp;{strat_chip}{cat_bdg}'
            f'<span class="news-source">{n.get("source","")}</span></div>'
            f'<div class="news-title">{n["title"]}</div>'
            f'<div class="news-divider"></div>'
            f'<div class="ai-section">'
            f'<div class="ai-strategy-label"><i class="ti ti-bulb" style="font-size:12px;color:#F0A500;"></i>대응 전략</div>'
            f'<div class="ai-strategy-text">{strategy}</div>'
            f'</div>'
            f'{footer}'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)


def _render_news_cards(news_list: list):
    """뉴스 카드 공통 렌더링"""
    if not news_list:
        st.info("뉴스를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        return

    # 카테고리별 색상 맵
    cat_color = {cfg_name: cfg["color"] for cfg_name, cfg in CATEGORY_CONFIG.items()}

    for n in news_list:
        sent = n.get("sentiment", "neutral")
        label = n.get("label", "중립")
        category = n.get("category", "전체")
        bdg_type = {"positive": "pos", "negative": "neg", "mixed": "mix"}.get(sent, "neu")
        sent_bdg = f'<span class="badge badge-{bdg_type}">{label}</span>'
        clr = cat_color.get(category, "#5B5BD6")
        cat_bdg = f'<span style="font-size:10px;font-weight:600;color:{clr};background:{clr}18;padding:2px 7px;border-radius:10px;">{category}</span>'
        card_cls = "important" if sent == "positive" else ("negative" if sent == "negative" else "")
        summ_html  = f'<div class="news-summary">{n["summary"]}</div>' if n.get("summary") else ""
        ai_summary = n.get("ai_summary", "")
        strategy   = n.get("strategy", "관망.")

        # 관련 종목 칩 (최대 4개)
        related = n.get("related_stocks") or []
        chips = "".join(
            f'<span class="stock-chip">{s["name"]}</span>'
            for s in related[:4] if isinstance(s, dict) and s.get("name")
        )
        footer_html = f'<div class="news-footer"><span class="news-time">{n.get("published","")}</span><div>{chips}</div></div>'

        # HTML을 한 줄로 구성 — 빈 줄 + 들여쓰기가 Markdown code block 트리거되는 것 방지
        card_html = (
            f'<div class="news-card {card_cls}">'
            f'<div class="news-card-top">{sent_bdg}{cat_bdg}<span class="news-source">{n.get("source","")}</span></div>'
            f'<div class="news-title">{n["title"]}</div>'
            f'{summ_html}'
            f'<div class="news-divider"></div>'
            f'<div class="ai-section">'
            f'<div class="ai-label"><i class="ti ti-sparkles" style="font-size:12px;"></i>AI 분석</div>'
            f'<div class="ai-text">{ai_summary}</div>'
            f'<div class="ai-strategy">'
            f'<div class="ai-strategy-label"><i class="ti ti-bulb" style="font-size:12px;color:#F0A500;"></i>대응 전략</div>'
            f'<div class="ai-strategy-text">{strategy}</div>'
            f'</div>'
            f'</div>'
            f'{footer_html}'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 보유종목 탭
# ─────────────────────────────────────────────────────────
def render_holdings():
    st.markdown(f"""<div class="hdr">
      <div><div class="hdr-title">보유종목 관리</div><div class="hdr-sub">{_today()} 기준</div></div>
    </div>""", unsafe_allow_html=True)

    with st.expander("➕ 종목 추가"):
        with st.form("ahf", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: code = st.text_input("종목코드", placeholder="005930")
            with c2: name_in = st.text_input("종목명", placeholder="삼성전자")
            c3, c4 = st.columns(2)
            with c3: avg_p = st.number_input("평균 매수가", min_value=0, step=100)
            with c4: qty = st.number_input("수량 (주)", min_value=0, step=1)
            if st.form_submit_button("추가", use_container_width=True, type="primary"):
                if not code or not avg_p or not qty:
                    st.error("종목코드, 평균가, 수량을 모두 입력해주세요.")
                else:
                    code = code.strip().zfill(6)
                    name = name_in.strip() or get_stock_name(code) or code
                    ok, msg = add_holding(st.session_state.user_id, code, name, avg_p, int(qty))
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)

    holdings = get_holdings(st.session_state.user_id)
    if not holdings:
        st.info("아직 보유종목이 없습니다. 위에서 종목을 추가해보세요!")
        return

    # 전체 평가
    total_eval = total_cost = 0
    enriched = []
    for i, h in enumerate(holdings):
        pd2 = get_current_price(h["code"])
        cur = pd2.get("current_price") or h["avg_price"]
        chg_pct = pd2.get("change_pct", 0)
        ohlcv = get_ohlcv(h["code"], days=60)
        inv = get_investor_trading(h["code"], days=5)
        a = analyze_stock(ohlcv, inv, h["avg_price"], h["qty"])
        eval_amt = cur * h["qty"]
        cost_amt = h["avg_price"] * h["qty"]
        total_eval += eval_amt; total_cost += cost_amt
        enriched.append({**h, "cur":cur, "chg_pct":chg_pct, "analysis":a, "idx":i})

    total_pnl = total_eval - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0
    pnl_cls = "up" if total_pnl >= 0 else "down"
    pnl_sign = "+" if total_pnl >= 0 else ""
    st.markdown(f"""<div class="total-strip">
      <div><div class="total-lbl">총 평가금액</div><div class="total-amt">{total_eval:,.0f}원</div></div>
      <div><div class="total-pnl-lbl">총 평가손익</div>
        <div class="total-pnl {pnl_cls}">{pnl_sign}{total_pnl:,.0f}원 ({pnl_sign}{total_pnl_pct:.1f}%)</div></div>
    </div>""", unsafe_allow_html=True)

    profit       = [e for e in enriched if (e["analysis"].get("pnl_pct") or 0) >= 0]
    loss         = [e for e in enriched if (e["analysis"].get("pnl_pct") or 0) <  0]
    sell_signal  = [e for e in enriched if any(b.get("type") in ("sell","warn") for b in e["analysis"].get("badges",[]))]

    # 필터 탭
    filt = st.session_state.holdings_filter
    filter_labels = [("all","전체"), ("profit","수익"), ("loss","손실"), ("sell","매도신호")]
    cols = st.columns(len(filter_labels))
    for i, (key, label) in enumerate(filter_labels):
        with cols[i]:
            is_active = filt == key
            btn_style = "primary" if is_active else "secondary"
            if st.button(label, key=f"hflt_{key}", use_container_width=True, type=btn_style):
                st.session_state.holdings_filter = key
                st.rerun()

    filt = st.session_state.holdings_filter
    if filt == "profit":
        sections = [("수익 중인 종목", profit)]
    elif filt == "loss":
        sections = [("손실 중인 종목", loss)]
    elif filt == "sell":
        sections = [("매도신호 종목", sell_signal)]
    else:
        sections = [("수익 중인 종목", profit), ("손실 중인 종목", loss)]

    for lbl, items in sections:
        if not items:
            st.info("해당하는 종목이 없습니다.")
            continue
        st.markdown(f'<div class="section"><div class="sec-lbl">{lbl}</div></div>', unsafe_allow_html=True)
        for e in items:
            _holding_card(e)


def _holding_card(e):
    h, a = e, e["analysis"]
    pnl_pct = a.get("pnl_pct", 0) or 0
    pnl_amt = a.get("pnl_amount", 0) or 0
    pnl_cls = "up" if pnl_pct >= 0 else "down"
    pnl_sign = "+" if pnl_pct >= 0 else ""
    cur = e["cur"]
    chg_pct = e["chg_pct"]
    chg_cls = "up" if chg_pct >= 0 else "down"
    chg_arr = "▲" if chg_pct >= 0 else "▼"
    rsi = a.get("rsi", 50)
    gap20 = a.get("gap20") or 100
    pnl_bar_pct = min(abs(pnl_pct) * 2, 100)
    pnl_bar_clr = "#E24B4A" if pnl_pct >= 0 else "#185FA5"
    ico = _ico_cls(e["idx"]); lbl = _ico_lbl(h["name"])
    ma20 = a.get("ma20"); ma60 = a.get("ma60"); boll = a.get("bollinger", {})
    sup_chips = ""
    if ma20:
        dist20 = (cur - ma20) / ma20 * 100
        d_cls = "up" if dist20 >= 0 else "down"
        sup_chips += f'<span class="sup-chip">20일선 <span class="{d_cls}">{dist20:+.1f}%</span></span>'
    if ma60:
        dist60 = (cur - ma60) / ma60 * 100
        d_cls = "up" if dist60 >= 0 else "down"
        sup_chips += f'<span class="sup-chip">60일선 <span class="{d_cls}">{dist60:+.1f}%</span></span>'
    if boll.get("lower"):
        dist_b = (cur - boll["lower"]) / boll["lower"] * 100
        d_cls = "up" if dist_b >= 0 else "down"
        sup_chips += f'<span class="sup-chip">볼하단 <span class="{d_cls}">{dist_b:+.1f}%</span></span>'
    _bdg_map = {"ok":"ok","buy":"buy","sell":"sell","warn":"warn"}
    badges_html = " ".join(
        f'<span class="badge badge-{_bdg_map.get(b["type"],"neu")}">{b["text"]}</span>'
        for b in a.get("badges", [])[:2])
    pnl_10k = int(pnl_amt / 10000)

    # 카드 (하단 모서리 없음 — 아래 버튼 행과 연결)
    st.markdown(f"""<div class="stk-card" style="border-radius:16px 16px 0 0;margin-bottom:0;border-bottom:none;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div class="stk-icon {ico}">{lbl}</div>
        <div><div style="font-size:13px;font-weight:600;">{h['name']}</div>
          <div style="font-size:10px;color:#8E8E93;">평단 {_fp(h['avg_price'])} · {h['qty']}주</div></div>
        <div style="text-align:right;margin-left:auto;padding-right:4px;">
          <div style="font-size:13px;font-weight:600;">{_fp(cur)}</div>
          <div class="{chg_cls}" style="font-size:11px;font-weight:500;">{chg_arr} {abs(chg_pct):.2f}%</div>
        </div>
      </div>
      <div class="mini-grid">
        <div class="mini-item"><div class="mini-lbl">평가손익</div><div class="mini-val {pnl_cls}">{pnl_sign}{pnl_10k}만</div></div>
        <div class="mini-item"><div class="mini-lbl">RSI</div><div class="mini-val" style="color:{_rsi_color(rsi)};">{rsi:.0f}</div></div>
        <div class="mini-item"><div class="mini-lbl">이격도</div><div class="mini-val">{gap20:.0f}%</div></div>
      </div>
      <div class="pnl-bar-wrap"><div class="pnl-bar" style="width:{pnl_bar_pct}%;background:{pnl_bar_clr};"></div></div>
      <div style="margin-top:8px;display:flex;flex-wrap:wrap;">{sup_chips}</div>
      <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-top:10px;padding-top:8px;border-top:0.5px solid #F0F0F5;">
        {badges_html or ''}
      </div>
    </div>""", unsafe_allow_html=True)

    # 하단 액션 바 (카드와 시각적으로 연결)
    col_nav, col_del = st.columns([6, 1])
    with col_nav:
        st.markdown('<div class="hld-nav-wrap">', unsafe_allow_html=True)
        if st.button("상세분석 보기  ›", key=f"h_{h['code']}", use_container_width=True):
            st.session_state.page = "holdings_detail"
            st.session_state.detail_code = h["code"]
            st.session_state.detail_name = h["name"]
            st.session_state.detail_avg  = h["avg_price"]
            st.session_state.detail_qty  = h["qty"]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_del:
        st.markdown('<div class="hld-del-wrap">', unsafe_allow_html=True)
        if st.button("✕", key=f"hdel_{h['code']}", use_container_width=True):
            st.session_state[f"confirm_del_{h['code']}"] = True
        st.markdown('</div>', unsafe_allow_html=True)

    # 삭제 확인 다이얼로그
    if st.session_state.get(f"confirm_del_{h['code']}"):
        st.warning(f"**'{h['name']}'** 종목을 보유 목록에서 삭제하시겠습니까?")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("확인", key=f"hdel_ok_{h['code']}", type="primary", use_container_width=True):
                delete_holding(st.session_state.user_id, h["code"])
                st.session_state.pop(f"confirm_del_{h['code']}", None)
                st.rerun()
        with cc2:
            if st.button("취소", key=f"hdel_cancel_{h['code']}", use_container_width=True):
                st.session_state.pop(f"confirm_del_{h['code']}", None)
                st.rerun()
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 관심종목 탭
# ─────────────────────────────────────────────────────────
def render_watchlist():
    st.markdown(f"""<div class="hdr">
      <div><div class="hdr-title">관심종목 모니터링</div>
        <div class="hdr-sub">매수 타이밍 · 추격금지 신호</div></div>
    </div>""", unsafe_allow_html=True)

    with st.expander("➕ 관심종목 추가"):
        with st.form("awf", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: code = st.text_input("종목코드", placeholder="277810")
            with c2: name_in = st.text_input("종목명", placeholder="레인보우로보틱스")
            c3, c4 = st.columns(2)
            with c3: target = st.number_input("목표가 (선택)", min_value=0, step=100)
            with c4: stop = st.number_input("손절가 (선택)", min_value=0, step=100)
            if st.form_submit_button("추가", use_container_width=True, type="primary"):
                if not code: st.error("종목코드를 입력해주세요.")
                else:
                    code = code.strip().zfill(6)
                    name = name_in.strip() or get_stock_name(code) or code
                    ok, msg = add_watchlist(st.session_state.user_id, code, name,
                                           target or None, stop or None)
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)

    watchlist = get_watchlist(st.session_state.user_id)
    if not watchlist:
        st.info("관심종목을 추가해보세요!")
        return

    buy_ok = []; chase_no = []; watch_lst = []
    for i, w in enumerate(watchlist):
        pd2 = get_current_price(w["code"])
        cur = pd2.get("current_price", 0); chg_pct = pd2.get("change_pct", 0)
        ohlcv = get_ohlcv(w["code"], days=60)
        inv = get_investor_trading(w["code"], days=5)
        a = analyze_stock(ohlcv, inv)
        t = watchlist_timing(a, w.get("target_price"), w.get("stop_loss"))
        item = {**w, "cur":cur, "chg_pct":chg_pct, "analysis":a, "timing":t, "idx":i}
        if t["status"] == "buy_ok": buy_ok.append(item)
        elif t["status"] == "chase_no": chase_no.append(item)
        else: watch_lst.append(item)

    # 필터 탭
    filt = st.session_state.watchlist_filter
    filter_labels = [("all","전체"), ("buy_ok","매수검토"), ("chase_no","추격금지"), ("watch","관망")]
    cols = st.columns(len(filter_labels))
    for i, (key, label) in enumerate(filter_labels):
        with cols[i]:
            if st.button(label, key=f"wflt_{key}", use_container_width=True,
                         type="primary" if filt == key else "secondary"):
                st.session_state.watchlist_filter = key; st.rerun()

    filt = st.session_state.watchlist_filter
    if filt == "buy_ok":
        sections = [("매수 검토 가능", buy_ok)]
    elif filt == "chase_no":
        sections = [("추격매수 금지", chase_no)]
    elif filt == "watch":
        sections = [("관망", watch_lst)]
    else:
        sections = [("매수 검토 가능", buy_ok), ("추격매수 금지", chase_no), ("관망", watch_lst)]

    for sec_lbl, items in sections:
        if not items:
            st.info("해당하는 종목이 없습니다.")
            continue
        st.markdown(f'<div class="section"><div class="sec-lbl">{sec_lbl}</div></div>', unsafe_allow_html=True)
        for item in items:
            _watchlist_card(item)


def _watchlist_card(item):
    w, a, t = item, item["analysis"], item["timing"]
    rsi = a.get("rsi", 50)
    ico = _ico_cls(item["idx"]); lbl = _ico_lbl(w["name"])
    chg_pct = item["chg_pct"]
    chg_cls = "up" if chg_pct >= 0 else "down"
    chg_arr = "▲" if chg_pct >= 0 else "▼"
    reason_cls = "reason-buy" if t["status"] == "buy_ok" else "reason-sell"
    reason = t.get("reason", "")
    target_html = ""
    cur = item["cur"] or 1
    if w.get("target_price"):
        tp = w["target_price"]
        dist = (tp - cur) / cur * 100; s = "+" if dist >= 0 else ""
        target_html += f'<span class="target-lbl">목표가</span><span class="target-val">{_fp(tp)}</span><span class="target-dist">({s}{dist:.1f}%)</span>'
    if w.get("stop_loss"):
        sl = w["stop_loss"]
        dist = (sl - cur) / cur * 100; s = "+" if dist >= 0 else ""
        target_html += f'<span class="target-lbl" style="margin-left:8px;">손절가</span><span class="target-val" style="color:#A32D2D;">{_fp(sl)}</span><span class="target-dist" style="color:#A32D2D;">({s}{dist:.1f}%)</span>'
    bdg_map = {"buy_ok":"badge-buy","chase_no":"badge-sell","watch":"badge-neu"}
    timing_bdg = f'<span class="badge {bdg_map.get(t["status"],"badge-neu")}">{t["label"]}</span>'
    _abm = {"ok":"badge-ok","buy":"badge-buy","sell":"badge-sell","warn":"badge-warn"}
    extra_bdgs = " ".join(
        f'<span class="badge {_abm.get(b["type"],"badge-neu")}">{b["text"]}</span>'
        for b in a.get("badges", [])[:2])

    st.markdown(f"""<div class="stk-card" style="border-radius:16px 16px 0 0;margin-bottom:0;border-bottom:none;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div class="stk-icon {ico}">{lbl}</div>
        <div><div style="font-size:13px;font-weight:600;">{w['name']}</div>
          <div style="font-size:10px;color:#8E8E93;">{w['code']}</div></div>
        <div style="text-align:right;margin-left:auto;padding-right:4px;">
          <div style="font-size:13px;font-weight:600;">{_fp(item['cur'])}</div>
          <div class="{chg_cls}" style="font-size:11px;font-weight:500;">{chg_arr} {abs(chg_pct):.2f}%</div>
        </div>
      </div>
      {_rsi_mini_h(rsi)}
      <div class="watch-reason {reason_cls}" style="margin-top:8px;">{reason}</div>{('<div class="target-row">' + target_html + '</div>') if target_html else ''}
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-top:10px;padding-top:8px;border-top:0.5px solid #F0F0F5;">
        <div style="display:flex;gap:5px;flex-wrap:wrap;">{timing_bdg}{(' ' + extra_bdgs) if extra_bdgs else ''}</div>
        <span style="color:#C7C7CC;font-size:15px;">›</span>
      </div>
    </div>""", unsafe_allow_html=True)

    col_nav, col_del = st.columns([6, 1])
    with col_nav:
        st.markdown('<div class="hld-nav-wrap">', unsafe_allow_html=True)
        if st.button("상세분석 보기  ›", key=f"w_{w['code']}", use_container_width=True):
            st.session_state.page = "watchlist_detail"
            st.session_state.detail_code = w["code"]
            st.session_state.detail_name = w["name"]
            st.session_state.detail_target = w.get("target_price", 0) or 0
            st.session_state.detail_stop = w.get("stop_loss", 0) or 0
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_del:
        st.markdown('<div class="hld-del-wrap">', unsafe_allow_html=True)
        if st.button("✕", key=f"wdel_{w['code']}", use_container_width=True):
            st.session_state[f"confirm_wdel_{w['code']}"] = True
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get(f"confirm_wdel_{w['code']}"):
        st.warning(f"**'{w['name']}'** 종목을 관심목록에서 삭제하시겠습니까?")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("확인", key=f"wdel_ok_{w['code']}", type="primary", use_container_width=True):
                delete_watchlist(st.session_state.user_id, w["code"])
                st.session_state.pop(f"confirm_wdel_{w['code']}", None); st.rerun()
        with cc2:
            if st.button("취소", key=f"wdel_cancel_{w['code']}", use_container_width=True):
                st.session_state.pop(f"confirm_wdel_{w['code']}", None); st.rerun()
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 매집 스캐너 탭
# ─────────────────────────────────────────────────────────
def render_scanner():
    st.markdown(f"""<div class="hdr">
      <div><div class="hdr-title">매집신호 스캐너</div>
        <div class="hdr-sub">코스피·코스닥 상위 200종목 · {_today()} 기준</div></div>
      <div style="color:#8E8E93;font-size:20px;"><i class="ti ti-adjustments-horizontal"></i></div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.scanner_ran:
        st.markdown("""<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:12px 16px 8px;">
          <div style="font-size:13px;font-weight:700;color:#3C3489;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
            <i class="ti ti-bulb" style="font-size:14px;"></i> 매집이란 뭔가요?
          </div>
          <div style="font-size:11px;color:#534AB7;line-height:1.7;">
            <b>매집</b>이란 큰 손(외국인·기관)이 조용히 주식을 사 모으는 행위예요.<br>
            가격이 크게 오르지 않으면서 거래량이 증가하고, 외국인·기관이 꾸준히 사들이면 매집 가능성이 높아요.<br>
            매집이 끝나면 주가가 급등하는 경우가 많아서, 미리 발견하면 좋은 진입 기회가 돼요.
          </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("상위 200개 종목을 분석하여 매집 신호를 찾습니다.\n약 2~3분 소요됩니다.")
        if st.button("🚀 스캔 시작", use_container_width=True, type="primary"):
            _run_scanner()
        return

    results = st.session_state.scanner_results
    high = [r for r in results if r["confidence"] == "high"]
    mid  = [r for r in results if r["confidence"] == "mid"]
    # 필터 버튼 (summary HTML 보다 먼저 배치 — DOM 조정 오류 방지)
    cf = st.session_state.scanner_filter
    filter_defs = [("all", "전체"), ("high", "강한신호"), ("foreign", "외국인매수"), ("inst", "기관매수")]
    cols = st.columns(len(filter_defs))
    for i, (fk, flbl) in enumerate(filter_defs):
        with cols[i]:
            if st.button(flbl, key=f"sf_{fk}", use_container_width=True,
                         type="primary" if cf == fk else "secondary"):
                st.session_state.scanner_filter = fk
                st.rerun()

    col_rescan, _ = st.columns([1, 3])
    with col_rescan:
        if st.button("🔄 재스캔"):
            _run_scanner()

    st.markdown(f"""<div class="sum-row">
      <div class="sum-card"><div class="sum-lbl">신뢰도 높음</div><div class="sum-val" style="color:#3C3489;">{len(high)}</div></div>
      <div class="sum-card"><div class="sum-lbl">신뢰도 보통</div><div class="sum-val" style="color:#854F0B;">{len(mid)}</div></div>
      <div class="sum-card"><div class="sum-lbl">전체 감지</div><div class="sum-val" style="color:#3B6D11;">{len(results)}</div></div>
    </div>""", unsafe_allow_html=True)

    if not results:
        st.info("현재 매집 신호 종목이 없습니다.")
        return

    # 필터 적용
    cf = st.session_state.scanner_filter
    if cf == "high":
        filtered = high
    elif cf == "foreign":
        filtered = [r for r in results if r.get("signals", {}).get("foreign_buy")]
    elif cf == "inst":
        filtered = [r for r in results if r.get("signals", {}).get("inst_buy")]
    else:
        filtered = results

    if not filtered:
        st.info("해당 조건의 종목이 없습니다.")
        return

    f_high = [r for r in filtered if r["confidence"] == "high"]
    f_mid  = [r for r in filtered if r["confidence"] == "mid"]

    if f_high:
        st.markdown('<div class="section"><div class="sec-lbl"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#5B5BD6;margin-right:5px;vertical-align:middle;"></span>신뢰도 높음 (4~5/5)</span></div></div>', unsafe_allow_html=True)
        for i, r in enumerate(f_high[:10]):
            _scanner_card(r, i+1, "high")
    if f_mid:
        st.markdown('<div class="section"><div class="sec-lbl"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#BA7517;margin-right:5px;vertical-align:middle;"></span>신뢰도 보통 (3/5)</span></div></div>', unsafe_allow_html=True)
        for i, r in enumerate(f_mid[:10]):
            _scanner_card(r, len(f_high)+i+1, "mid")


def _run_scanner():
    with st.spinner("종목 목록 가져오는 중..."):
        stocks = get_top_stocks(200)
    if not stocks:
        st.error("종목 목록을 가져오지 못했습니다."); return
    pb = st.progress(0, text="스캔 시작...")
    results = []
    for i, s in enumerate(stocks):
        try:
            ohlcv = get_ohlcv(s["code"], days=60)
            inv = get_investor_trading(s["code"], days=5)
            a = analyze_stock(ohlcv, inv)
            if a["score"] >= 3:
                pd2 = get_current_price(s["code"])
                results.append({"code":s["code"],"name":s["name"],"market":s.get("market",""),
                                 "cur":pd2.get("current_price",0),"chg_pct":pd2.get("change_pct",0),**a})
        except: pass
        pb.progress((i+1)/len(stocks), text=f"분석 중... {i+1}/{len(stocks)}")
    pb.empty()
    results.sort(key=lambda x:(x["score"],x.get("volume_ratio",0)), reverse=True)
    st.session_state.scanner_results = results
    st.session_state.scanner_ran = True
    st.rerun()


def _scanner_card(r, rank, conf):
    rsi = r.get("rsi", 50); vol_ratio = r.get("volume_ratio", 1)
    ico = _ico_cls(rank-1); lbl = _ico_lbl(r["name"])
    chg = r.get("chg_pct",0); chg_cls = "up" if chg>=0 else "down"; chg_arr = "▲" if chg>=0 else "▼"
    bdg_type = "badge-ok" if conf=="high" else "badge-warn"
    conf_lbl = f"신뢰도 높음 {r['score']}/5" if conf=="high" else f"보통 {r['score']}/5"
    vol_pct = int((vol_ratio-1)*100)
    st.markdown(f"""<div class="stk-card {conf}">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
        <span class="rank-num">{rank}</span>
        <div class="stk-icon {ico}">{lbl}</div>
        <div><div style="font-size:13px;font-weight:600;">{r['name']}</div>
          <div style="font-size:10px;color:#8E8E93;">{r['code']} · {r['market']}</div></div>
        <div style="text-align:right;margin-left:auto;">
          <div style="font-size:13px;font-weight:600;">{_fp(r['cur'])}</div>
          <div class="{chg_cls}" style="font-size:11px;font-weight:500;">{chg_arr} {abs(chg):.2f}%</div>
        </div>
      </div>
      {_sig_dots_h(r.get('signals',{}))}
      {_rsi_big_h(rsi)}
      <div class="obv-row"><span class="obv-lbl">거래량 평균 대비</span>
        <span class="obv-val"><i class="ti ti-trending-up" style="font-size:12px;"></i>+{vol_pct}%</span></div>
      <div class="card-bottom"><span class="badge {bdg_type}">{conf_lbl}</span></div>
    </div>""", unsafe_allow_html=True)
    if st.button("📊 상세보기", key=f"sc_{r['code']}_{rank}"):
        st.session_state.page = "scanner_detail"
        st.session_state.detail_code = r["code"]
        st.session_state.detail_name = r["name"]
        st.rerun()


# ─────────────────────────────────────────────────────────
# 보유종목 상세 페이지
# ─────────────────────────────────────────────────────────
def render_holdings_detail():
    code = st.session_state.detail_code
    name = st.session_state.detail_name
    avg_p = st.session_state.detail_avg
    qty   = st.session_state.detail_qty
    if st.button("← 뒤로"):
        st.session_state.page = "main"; st.rerun()

    with st.spinner("분석 중..."):
        pd2  = get_current_price(code)
        ohlcv= get_ohlcv(code, days=60)
        inv  = get_investor_trading(code, days=25)
        a    = analyze_stock(ohlcv, inv, avg_p, qty)
        auto_tp = _calc_auto_targets(a, ohlcv, avg_price=avg_p)

    cur = pd2.get("current_price") or a.get("current_price", avg_p)
    chg = pd2.get("change", 0); chg_pct = pd2.get("change_pct", 0)
    pnl_pct = a.get("pnl_pct",0) or 0; pnl_amt = a.get("pnl_amount",0) or 0
    pnl_cls = "up" if pnl_pct>=0 else "down"; pnl_sign = "+" if pnl_pct>=0 else ""
    chg_cls = "up" if chg_pct>=0 else "down"
    hdg_bdg_cls = "badge-buy" if pnl_pct>=0 else "badge-sell"
    h_tp = auto_tp["target_price"]; h_sp = auto_tp["stop_price"]
    h_tu = auto_tp["target_upside"]; h_sd = auto_tp["stop_downside"]
    h_tb = auto_tp["target_basis"];  h_sb = auto_tp["stop_basis"]
    h_avs = auto_tp["avg_vs_stop"]
    h_rr  = abs(h_tu / h_sd) if h_sd else 0

    st.markdown(f"""<div class="hdr">
      <div style="width:100%;display:flex;align-items:center;gap:12px;">
        <div style="flex:1;">
          <div class="hdr-title">{name}</div>
          <div style="font-size:11px;color:#8E8E93;">{code}</div>
        </div>
        <span class="badge {hdg_bdg_cls}">{'수익' if pnl_pct>=0 else '손실'} {pnl_sign}{pnl_pct:.2f}%</span>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="price-section">
      <div class="current-price">{_fp(cur)}</div>
      <div style="display:flex;gap:8px;margin-top:4px;">
        <span class="{chg_cls}" style="font-size:14px;font-weight:600;">{'▲' if chg_pct>=0 else '▼'} {abs(chg):,.0f}원</span>
        <span class="{chg_cls}" style="font-size:14px;font-weight:600;">({abs(chg_pct):.2f}%)</span>
      </div>
      <div class="price-meta">
        <div class="pm-item">고가 <span>{_fp(pd2.get('high'))}</span></div>
        <div class="pm-item">저가 <span>{_fp(pd2.get('low'))}</span></div>
        <div class="pm-item">거래량 <span>{pd2.get('volume',0):,}</span></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # 내 보유 현황
    pnl_bar_pct = min(abs(pnl_pct)*2, 100)
    pnl_bar_clr = "#E24B4A" if pnl_pct>=0 else "#185FA5"
    pnl_10k = int(pnl_amt/10000)
    st.markdown(f"""<div style="margin:12px 16px 0;">
      <div class="card">
        <div style="font-size:11px;font-weight:600;color:#8E8E93;margin-bottom:10px;display:flex;align-items:center;gap:5px;">
          <i class="ti ti-briefcase" style="font-size:12px;color:#5B5BD6;"></i>내 보유 현황
        </div>
        <div class="pos-grid">
          <div class="pos-item"><div class="pos-label">평단가</div><div class="pos-val" style="color:#6B6B8A;">{_fp(avg_p)}</div></div>
          <div class="pos-item"><div class="pos-label">보유 수량</div><div class="pos-val" style="color:#6B6B8A;">{qty}주</div></div>
          <div class="pos-item"><div class="pos-label">평가손익</div>
            <div class="pos-val {pnl_cls}">{pnl_sign}{pnl_10k}만원</div></div>
        </div>
        <div class="pnl-bar-wrap" style="height:5px;margin-top:10px;">
          <div style="height:5px;border-radius:3px;background:{pnl_bar_clr};width:{pnl_bar_pct}%;"></div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # 차트
    if ohlcv is not None and not ohlcv.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=ohlcv.index,
            open=ohlcv["open"], high=ohlcv["high"],
            low=ohlcv["low"],   close=ohlcv["close"],
            increasing_line_color="#E24B4A", decreasing_line_color="#185FA5",
            increasing_fillcolor="#E24B4A", decreasing_fillcolor="#185FA5",
            name="가격", showlegend=False,
        ))
        fig.add_hline(y=avg_p, line_color="#F0A500", line_width=1.5,
                      annotation_text=f"평단 {avg_p:,}", annotation_font_size=10,
                      annotation_font_color="#F0A500")
        if h_tp:
            fig.add_hline(y=h_tp, line_color="#27500A", line_width=1.2, line_dash="dot",
                          annotation_text=f"목표 {h_tp:,}", annotation_font_size=9,
                          annotation_font_color="#27500A")
        if h_sp:
            fig.add_hline(y=h_sp, line_color="#A32D2D", line_width=1.2, line_dash="dot",
                          annotation_text=f"손절 {h_sp:,}", annotation_font_size=9,
                          annotation_font_color="#A32D2D")
        fig.update_layout(
            margin=dict(l=0, r=0, t=8, b=0), height=200,
            paper_bgcolor="#F8F8FA", plot_bgcolor="#F8F8FA",
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#C7C7CC"),
                       rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F5", tickfont=dict(size=9, color="#C7C7CC")),
        )
        st.markdown('<div style="background:#fff;padding:14px 16px 0;margin-bottom:8px;">'
                    '<div style="font-size:12px;font-weight:600;margin-bottom:8px;">'
                    '<i class="ti ti-chart-candle" style="font-size:13px;color:#5B5BD6;vertical-align:middle;"></i>'
                    ' 가격 차트 (주황선 = 평단가)</div></div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # 기술 지표
    rsi = a.get("rsi",50); boll = a.get("bollinger",{})
    ma20 = a.get("ma20"); ma60 = a.get("ma60"); gap20 = a.get("gap20") or 100

    def _ind_status(val, good_cond, label_good, label_bad):
        cls = "status-good" if good_cond else "status-danger"
        lbl = label_good if good_cond else label_bad
        return f'<span class="ind-status {cls}">{lbl}</span>'

    rsi_status = _ind_status(rsi, rsi<70, "정상" if rsi>30 else "과매도 근접", "과매수")
    gap_status = _ind_status(gap20, 95<=gap20<=115, "평균선 근처", "이격 과대")
    boll_pos = boll.get("position",0.5)
    boll_lbl = "하단 근처" if boll_pos<0.2 else ("상단 근처" if boll_pos>0.8 else "중간")
    boll_cls = "status-good" if boll_pos<0.3 else ("status-danger" if boll_pos>0.8 else "status-ok")

    ma20_row = ""
    if ma20:
        d = (cur-ma20)/ma20*100
        s_cls = "status-ok" if d>=0 else "status-danger"
        ma20_row = f'<div class="ind-row"><span class="ind-label">20일선</span><div class="ind-right"><span class="ind-val">{_fp(ma20)}</span><span class="ind-status {s_cls}">{"위" if d>=0 else "아래"} {abs(d):.1f}%</span></div></div>'
    ma60_row = ""
    if ma60:
        d = (cur-ma60)/ma60*100
        s_cls = "status-ok" if d>=0 else "status-danger"
        ma60_row = f'<div class="ind-row"><span class="ind-label">60일선</span><div class="ind-right"><span class="ind-val">{_fp(ma60)}</span><span class="ind-status {s_cls}">{"위" if d>=0 else "아래"} {abs(d):.1f}%</span></div></div>'

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>기술적 지표</div>
      <div class="card">
        <div class="ind-row"><span class="ind-label">RSI (14일)</span>
          <div class="ind-right">
            <div class="rsi-bar-wrap2"><div class="rsi-bar-fill2" style="width:{rsi}%;background:{_rsi_color(rsi)};"></div></div>
            <span class="ind-val">{rsi:.0f}</span>{rsi_status}
          </div>
        </div>
        <div class="ind-row"><span class="ind-label">이격도 (20일)</span>
          <div class="ind-right"><span class="ind-val">{gap20:.0f}%</span>{gap_status}</div>
        </div>
        <div class="ind-row"><span class="ind-label">볼린저밴드</span>
          <div class="ind-right"><span class="ind-val">{boll_lbl}</span><span class="ind-status {boll_cls}">{'지지 시도' if boll_pos<0.3 else '과열' if boll_pos>0.8 else '보통'}</span></div>
        </div>
        {ma20_row}{ma60_row}
      </div>
    </div>""", unsafe_allow_html=True)

    # 지표 해석 카드 (현재 값이 무엇을 의미하는지)
    # RSI 해석
    if rsi >= 70:
        rsi_interp = f"RSI {rsi:.0f}으로 <b>과열 구간</b>이에요. 너무 빠르게 올라온 상태예요. 추가 상승보다 숨 고르기 가능성이 높아요."
        rsi_icon = "🔴"
    elif rsi <= 30:
        rsi_interp = f"RSI {rsi:.0f}으로 <b>과매도 구간</b>이에요. 너무 많이 떨어진 상태예요. 단기 반등 시도가 나올 수 있어요."
        rsi_icon = "🟢"
    elif rsi >= 60:
        rsi_interp = f"RSI {rsi:.0f}으로 <b>정상 범위 상단</b>이에요. 과열도 침체도 아닌 건강한 상승세예요. 추세를 따라가세요."
        rsi_icon = "🟡"
    elif rsi <= 40:
        rsi_interp = f"RSI {rsi:.0f}으로 <b>정상 범위 하단</b>이에요. 힘이 빠지는 구간이지만 아직 위험하진 않아요. 추가 하락 여부를 지켜보세요."
        rsi_icon = "🟡"
    else:
        rsi_interp = f"RSI {rsi:.0f}으로 <b>정상 범위</b>예요. 과열도 침체도 아닌 건강한 상태예요. 추세를 따라가세요."
        rsi_icon = "🟢"

    # 이격도 해석
    if gap20 >= 115:
        gap_interp = f"이격도 {gap20:.0f}%로 20일 평균보다 <b>{gap20-100:.0f}% 위</b>에 있어요. 용수철처럼 평균으로 되돌아오려는 힘이 강해요. 단기 조정 가능성을 염두에 두세요."
        gap_icon = "⚠️"
    elif gap20 >= 105:
        gap_interp = f"이격도 {gap20:.0f}%로 20일 평균보다 <b>{gap20-100:.0f}% 위</b>에 있어요. 약간 올라온 상태지만 아직 과열 수준은 아니에요."
        gap_icon = "🟡"
    elif gap20 <= 85:
        gap_interp = f"이격도 {gap20:.0f}%로 20일 평균보다 <b>{100-gap20:.0f}% 아래</b>에 있어요. 많이 떨어진 상태로 반등 시도 가능성이 있어요."
        gap_icon = "🟢"
    elif gap20 <= 95:
        gap_interp = f"이격도 {gap20:.0f}%로 20일 평균보다 <b>{100-gap20:.0f}% 아래</b>에 있어요. 평균선 아래에 있지만 크게 이탈한 건 아니에요."
        gap_icon = "🟡"
    else:
        gap_interp = f"이격도 {gap20:.0f}%로 20일 평균 근처에 있어요. 안정적인 위치예요."
        gap_icon = "🟢"

    # 볼린저밴드 해석
    boll_pos = boll.get("position", 0.5)
    if boll_pos >= 0.8:
        boll_interp = "볼린저밴드 <b>상단 근처</b>에요. 주가가 터널 천장에 닿아있어요. 여기서 저항을 받으면 단기 조정이 올 수 있어요."
        boll_icon = "⚠️"
    elif boll_pos <= 0.2:
        boll_interp = "볼린저밴드 <b>하단 근처</b>예요. 주가가 터널 바닥에 있어요. 여기서 지지를 받으면 반등이 나올 수 있어요."
        boll_icon = "🟢"
    else:
        boll_interp = f"볼린저밴드 <b>중간 구간</b>에 있어요. 터널 안에서 방향을 탐색하는 중이에요. 상단 또는 하단 돌파 방향을 지켜보세요."
        boll_icon = "🟡"

    st.markdown(f"""<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:0 0 12px 0;">
      <div style="font-size:12px;font-weight:700;color:#3C3489;margin-bottom:12px;display:flex;align-items:center;gap:6px;">
        <i class="ti ti-microscope" style="font-size:14px;"></i> 지금 이 숫자가 의미하는 것
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{rsi_icon} RSI (상대강도지수)</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">{rsi_interp}</div>
        </div>
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{gap_icon} 이격도 (20일 평균 기준)</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">{gap_interp}</div>
        </div>
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{boll_icon} 볼린저밴드</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">{boll_interp}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


    # 지지선
    sup_rows = ""
    if ma20:
        d = (cur-ma20)/ma20*100; s="+" if d>=0 else ""; cls="up" if d>=0 else "down"
        note_cls = "note-near" if abs(d)<5 else "note-far"
        note_txt = "현재 위" if d>=0 else "이탈"
        sup_rows += f'<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">{_fp(ma20)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">{note_txt}</span></div></div>'
    if boll.get("lower"):
        bl = boll["lower"]; d = (cur-bl)/bl*100; s="+" if d>=0 else ""; cls="up" if d>=0 else "down"
        note_cls = "note-near" if abs(d)<5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">{_fp(bl)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">근접</span></div></div>'
    if ma60:
        d = (cur-ma60)/ma60*100; s="+" if d>=0 else ""; cls="up" if d>=0 else "down"
        note_cls = "note-near" if abs(d)<5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">{_fp(ma60)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">주요 지지</span></div></div>'

    if sup_rows:
        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-barrier-block" style="font-size:15px;color:#5B5BD6;"></i>바닥 지지선</div>
          <div class="card">{sup_rows}</div>
        </div>""", unsafe_allow_html=True)

    # 수급
    _render_supply(a, inv)

    # 경고/조언
    verdict = a.get("verdict","")
    badges  = a.get("badges",[])
    sell_signals = [b for b in badges if b.get("type") in ("sell","warn")]
    buy_signals  = [b for b in badges if b.get("type") in ("buy","ok")]

    if sell_signals:
        warn_txt = verdict if verdict else " · ".join(b["text"] for b in sell_signals)
        st.markdown(f"""<div class="section">
          <div class="warn-box">
            <div class="warn-title"><i class="ti ti-alert-triangle" style="font-size:15px;"></i>주의 신호</div>
            <div class="warn-text">{warn_txt}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── 목표가 / 손절가 자동 분석 카드 ──
    avg_vs_stop_txt = f"평단 대비 {h_avs:+.1f}%" if h_avs is not None else ""
    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-target" style="font-size:15px;color:#5B5BD6;"></i>목표가 / 손절가 분석</div>
    </div>
    <div class="card" style="margin-bottom:6px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
        <div>
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">추천 목표가</div>
          <div style="font-size:17px;font-weight:700;color:#27500A;">{_fp(h_tp)}</div>
          <div style="font-size:11px;color:#27500A;margin-top:2px;">+{h_tu:.1f}%</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:3px;">기준: {h_tb}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">추천 손절가</div>
          <div style="font-size:17px;font-weight:700;color:#A32D2D;">{_fp(h_sp)}</div>
          <div style="font-size:11px;color:#A32D2D;margin-top:2px;">{h_sd:.1f}%</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:3px;">기준: {h_sb}{(' · ' + avg_vs_stop_txt) if avg_vs_stop_txt else ''}</div>
        </div>
      </div>
      <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:4px;">리스크/리워드 비율</div>
        <div style="font-size:13px;font-weight:600;color:{'#27500A' if h_rr >= 2 else '#BA7517' if h_rr >= 1 else '#A32D2D'};">
          1 : {h_rr:.1f} {'✅ 양호' if h_rr >= 2 else '⚠️ 보통' if h_rr >= 1 else '❌ 불리'}
        </div>
        <div style="font-size:10px;color:#8E8E93;margin-top:3px;">손실 1원 대비 수익 {h_rr:.1f}원 기대 — 2 이상이면 진입 적합</div>
      </div>
    </div>""", unsafe_allow_html=True)

    col_b_only, _ = st.columns([1, 1])
    with col_b_only:
        if st.button("⭐ 관심종목 추가", use_container_width=True):
            ok, msg = add_watchlist(st.session_state.user_id, code, name, None, None)
            if ok: st.success(f"{name}을 관심종목에 추가했습니다.")
            else: st.info(msg)

    # 공시 섹션
    with st.spinner("공시 불러오는 중..."):
        disclosures = fetch_disclosures(code, name, days=30, max_items=4)

    if disclosures:
        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-speakerphone" style="font-size:15px;color:#5B5BD6;"></i>최근 공시 (30일)</div>
        </div>""", unsafe_allow_html=True)
        for d in disclosures:
            # 주가 영향 흐름을 줄바꿈 기준으로 파싱해서 리스트 표시
            impact_items = [line.strip() for line in d["impact"].split("\n") if line.strip()]
            impact_html = "".join(
                f'<div style="font-size:11px;color:#534AB7;line-height:1.7;padding:2px 0;">'
                f'<span style="color:#5B5BD6;font-weight:600;">·</span> {line}</div>'
                for line in impact_items
            )
            st.markdown(f"""<div class="card" style="margin:0 0 10px 0;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:10px;background:#EEEDFE;color:#3C3489;padding:2px 8px;border-radius:6px;font-weight:500;">{d['report_type']}</span>
                <span style="font-size:10px;color:#8E8E93;">{d['date']}</span>
              </div>
              <div style="font-size:13px;font-weight:600;color:#1A1A2E;margin-bottom:10px;line-height:1.5;">{d['title']}</div>
              <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;margin-bottom:8px;">
                <div style="font-size:10px;font-weight:700;color:#5B5BD6;margin-bottom:6px;display:flex;align-items:center;gap:4px;">
                  <i class="ti ti-bulb" style="font-size:12px;"></i> 이 공시가 의미하는 것
                </div>
                <div style="font-size:11px;color:#3B3B5C;line-height:1.7;">{d['analysis']}</div>
              </div>
              <div style="background:#EEEDFE;border-radius:10px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;color:#3C3489;margin-bottom:6px;display:flex;align-items:center;gap:4px;">
                  <i class="ti ti-timeline" style="font-size:12px;"></i> 주가 영향 흐름
                </div>
                {impact_html}
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="margin:0 0 8px 0;background:#F8F8FA;border-radius:12px;padding:14px 16px;text-align:center;">
          <div style="font-size:12px;color:#8E8E93;">최근 30일 공시가 없습니다.</div>
        </div>""", unsafe_allow_html=True)

    # 관련 뉴스
    news = fetch_stock_news(name, max_items=3)
    if news:
        st.markdown(f'<div class="section"><div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>{name} 뉴스</div></div>', unsafe_allow_html=True)
        for n in news:
            sent = n.get("sentiment","neutral")
            bdg_t = {"positive":"pos","negative":"neg","mixed":"mix"}.get(sent,"neu")
            st.markdown(f"""<div style="margin:0 16px;"><div class="news-card">
              <div class="news-card-top"><span class="badge badge-{bdg_t}">{n.get('label','중립')}</span>
                <span class="news-source">{n.get('source','')} · {n.get('published','')}</span></div>
              <div class="news-title">{n['title']}</div>
            </div></div>""", unsafe_allow_html=True)

    st.caption("⚠️ 투자 결정은 본인 책임입니다. 이 앱의 정보는 참고용이며 투자 권유가 아닙니다.")


# ─────────────────────────────────────────────────────────
# 기술적 분석 기반 목표가 / 손절가 자동 산출
# ─────────────────────────────────────────────────────────
def _calc_auto_targets(a: dict, ohlcv, avg_price: float = None) -> dict:
    """
    분석 데이터와 OHLCV로 목표가·손절가를 자동 산출.
    avg_price 제공 시 보유종목 기준(평단 대비) 추가 적용.
    Returns: {
      target_price, target_basis, target_upside,
      stop_price,   stop_basis,   stop_downside,
      avg_vs_stop   (평단 대비 손절가 %, avg_price 있을 때만)
    }
    """
    cur        = a.get("current_price") or 0
    boll       = a.get("bollinger", {})
    ma20       = a.get("ma20")
    boll_upper = boll.get("upper")
    boll_lower = boll.get("lower")

    # ── 목표가: 볼린저 상단 > 60일 고점 > +8% (보유: 평단+10% 비교 후 높은 쪽) ──
    target_price = None
    target_basis = ""
    if boll_upper and boll_upper > cur:
        target_price = round(boll_upper / 100) * 100
        target_basis = "볼린저 상단"
    elif ohlcv is not None and not ohlcv.empty:
        high60 = float(ohlcv["high"].tail(60).max())
        if high60 > cur * 1.03:
            target_price = round(high60 / 100) * 100
            target_basis = "60일 고점"
    if avg_price and avg_price > 0:
        avg_target = round(avg_price * 1.10 / 100) * 100
        if not target_price or avg_target > target_price:
            target_price = avg_target
            target_basis = "평단가 +10%"
    if not target_price:
        target_price = round(cur * 1.08 / 100) * 100
        target_basis = "현재가 +8%"

    # ── 손절가: 볼린저 하단 > 20일선-3% > 평단-7% > 현재가-5% ──
    stop_price = None
    stop_basis = ""
    if boll_lower and boll_lower < cur:
        stop_price = round(boll_lower / 100) * 100
        stop_basis = "볼린저 하단"
    elif ma20 and ma20 * 0.97 < cur:
        stop_price = round(ma20 * 0.97 / 100) * 100
        stop_basis = "20일선 -3%"
    if avg_price and avg_price > 0:
        avg_stop = round(avg_price * 0.93 / 100) * 100
        if not stop_price or avg_stop > stop_price:
            stop_price = avg_stop
            stop_basis = "평단가 -7%"
    if not stop_price:
        stop_price = round(cur * 0.95 / 100) * 100
        stop_basis = "현재가 -5%"

    target_upside  = (target_price - cur) / cur * 100 if cur else 0
    stop_downside  = (stop_price  - cur) / cur * 100 if cur else 0

    avg_vs_stop = (stop_price - avg_price) / avg_price * 100 if avg_price and stop_price else None

    return {
        "target_price":   target_price,
        "target_basis":   target_basis,
        "target_upside":  target_upside,
        "stop_price":     stop_price,
        "stop_basis":     stop_basis,
        "stop_downside":  stop_downside,
        "avg_vs_stop":    avg_vs_stop,
    }


# ─────────────────────────────────────────────────────────
# 관심종목 상세 페이지
# ─────────────────────────────────────────────────────────
def render_watchlist_detail():
    code   = st.session_state.detail_code
    name   = st.session_state.detail_name
    target = st.session_state.detail_target
    stop   = st.session_state.detail_stop

    if st.button("← 뒤로"):
        st.session_state.page = "main"; st.rerun()

    with st.spinner("분석 중..."):
        pd2  = get_current_price(code)
        ohlcv = get_ohlcv(code, days=60)
        inv   = get_investor_trading(code, days=25)
        a     = analyze_stock(ohlcv, inv)
        t     = watchlist_timing(a, target or None, stop or None)
        auto_tp = _calc_auto_targets(a, ohlcv)

    cur = pd2.get("current_price") or a.get("current_price", 0)
    chg = pd2.get("change", 0); chg_pct = pd2.get("change_pct", 0)
    chg_cls = "up" if chg_pct >= 0 else "down"

    # 타이밍 배지
    bdg_map  = {"buy_ok": ("badge-buy","매수 검토"), "chase_no": ("badge-sell","추격 금지"), "watch": ("badge-neu","관망")}
    bdg_cls, bdg_txt = bdg_map.get(t["status"], ("badge-neu", "분석 중"))
    timing_bdg = f'<span class="badge {bdg_cls}">{bdg_txt}</span>'

    # ── 헤더 ──
    st.markdown(f"""<div class="hdr">
      <div style="display:flex;align-items:center;gap:12px;width:100%;">
        <div style="flex:1;"><div class="hdr-title">{name}</div>
          <div style="font-size:11px;color:#8E8E93;">{code}</div></div>
        {timing_bdg}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 현재가 ──
    st.markdown(f"""<div class="price-section">
      <div class="current-price">{_fp(cur)}</div>
      <div style="display:flex;gap:8px;margin-top:4px;">
        <span class="{chg_cls}" style="font-size:14px;font-weight:600;">{'▲' if chg_pct>=0 else '▼'} {abs(chg):,.0f}원</span>
        <span class="{chg_cls}" style="font-size:14px;font-weight:600;">({abs(chg_pct):.2f}%)</span>
      </div>
      <div class="price-meta">
        <div class="pm-item">고가 <span>{_fp(pd2.get('high'))}</span></div>
        <div class="pm-item">저가 <span>{_fp(pd2.get('low'))}</span></div>
        <div class="pm-item">거래량 <span>{pd2.get('volume',0):,}</span></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 매수 타이밍 히어로 카드 ──
    rsi  = a.get("rsi", 50)
    gap20 = a.get("gap20") or 100
    boll = a.get("bollinger", {})
    ma20 = a.get("ma20"); ma60 = a.get("ma60")

    if t["status"] == "buy_ok":
        hero_bg = "#5B5BD6"; hero_title = "✅ 매수 검토 가능"; hero_color = "#fff"
        hero_sub_color = "rgba(255,255,255,0.8)"
    elif t["status"] == "chase_no":
        hero_bg = "#E24B4A"; hero_title = "⛔ 추격매수 금지"; hero_color = "#fff"
        hero_sub_color = "rgba(255,255,255,0.8)"
    else:
        hero_bg = "#8E8E93"; hero_title = "👀 관망"; hero_color = "#fff"
        hero_sub_color = "rgba(255,255,255,0.8)"

    reason_txt = t.get("reason", "지표를 종합 분석 중이에요.")

    # 핵심 근거 3개
    entry_items = []
    if rsi <= 35:
        entry_items.append(f"RSI {rsi:.0f} — 과매도 구간, 반등 가능성")
    elif rsi >= 70:
        entry_items.append(f"RSI {rsi:.0f} — 과열 구간, 진입 주의")
    else:
        entry_items.append(f"RSI {rsi:.0f} — 정상 범위")
    if gap20 <= 97:
        entry_items.append(f"이격도 {gap20:.0f}% — 평균선 아래, 저점 근처")
    elif gap20 >= 110:
        entry_items.append(f"이격도 {gap20:.0f}% — 평균선 위로 많이 올라온 상태")
    else:
        entry_items.append(f"이격도 {gap20:.0f}% — 평균선 근처, 안정적")
    boll_pos = boll.get("position", 0.5)
    if boll_pos <= 0.2:
        entry_items.append("볼린저 하단 근처 — 지지선 테스트 중")
    elif boll_pos >= 0.8:
        entry_items.append("볼린저 상단 근처 — 저항선 근처, 추격 주의")
    else:
        entry_items.append("볼린저 중간 구간 — 방향 탐색 중")

    entry_html = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-top:6px;">'
        f'<span style="width:4px;height:4px;border-radius:50%;background:rgba(255,255,255,0.6);flex-shrink:0;"></span>'
        f'<span style="font-size:11px;color:{hero_sub_color};">{e}</span></div>'
        for e in entry_items
    )
    st.markdown(f"""<div style="margin:12px 16px 8px;background:{hero_bg};border-radius:16px;padding:16px 18px;color:{hero_color};">
      <div style="font-size:11px;opacity:0.8;margin-bottom:4px;">지금 사도 될까?</div>
      <div style="font-size:17px;font-weight:700;margin-bottom:6px;">{hero_title}</div>
      <div style="font-size:11px;color:{hero_sub_color};line-height:1.6;">{reason_txt}</div>
      {entry_html}
    </div>""", unsafe_allow_html=True)

    # ── 목표가 / 손절가 자동 분석 카드 ──
    tp = auto_tp["target_price"]; sp = auto_tp["stop_price"]
    tu = auto_tp["target_upside"]; sd = auto_tp["stop_downside"]
    tb = auto_tp["target_basis"];  sb = auto_tp["stop_basis"]
    rr = abs(tu / sd) if sd else 0
    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-target" style="font-size:15px;color:#5B5BD6;"></i>목표가 / 손절가 분석</div>
    </div>
    <div class="card" style="margin-bottom:6px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
        <div>
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">추천 목표가</div>
          <div style="font-size:17px;font-weight:700;color:#27500A;">{_fp(tp)}</div>
          <div style="font-size:11px;color:#27500A;margin-top:2px;">+{tu:.1f}%</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:3px;">기준: {tb}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">추천 손절가</div>
          <div style="font-size:17px;font-weight:700;color:#A32D2D;">{_fp(sp)}</div>
          <div style="font-size:11px;color:#A32D2D;margin-top:2px;">{sd:.1f}%</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:3px;">기준: {sb}</div>
        </div>
      </div>
      <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:4px;">리스크/리워드 비율</div>
        <div style="font-size:13px;font-weight:600;color:{'#27500A' if rr >= 2 else '#BA7517' if rr >= 1 else '#A32D2D'};">
          1 : {rr:.1f} {'✅ 양호' if rr >= 2 else '⚠️ 보통' if rr >= 1 else '❌ 불리'}
        </div>
        <div style="font-size:10px;color:#8E8E93;margin-top:3px;">손실 1원 대비 수익 {rr:.1f}원 기대 — 2 이상이면 진입 적합</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Plotly 캔들 차트 (목표가·손절가 선 포함) ──
    if ohlcv is not None and not ohlcv.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=ohlcv.index,
            open=ohlcv["open"], high=ohlcv["high"],
            low=ohlcv["low"],   close=ohlcv["close"],
            increasing_line_color="#E24B4A", decreasing_line_color="#185FA5",
            increasing_fillcolor="#E24B4A", decreasing_fillcolor="#185FA5",
            name="가격", showlegend=False,
        ))
        if tp:
            fig.add_hline(y=tp, line_color="#27500A", line_width=1.5, line_dash="dot",
                          annotation_text=f"목표 {tp:,}", annotation_font_size=9,
                          annotation_font_color="#27500A")
        if sp:
            fig.add_hline(y=sp, line_color="#A32D2D", line_width=1.5, line_dash="dot",
                          annotation_text=f"손절 {sp:,}", annotation_font_size=9,
                          annotation_font_color="#A32D2D")
        fig.update_layout(
            margin=dict(l=0, r=0, t=8, b=0), height=200,
            paper_bgcolor="#F8F8FA", plot_bgcolor="#F8F8FA",
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#C7C7CC"),
                       rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F5", tickfont=dict(size=9, color="#C7C7CC")),
        )
        st.markdown('<div style="background:#fff;padding:14px 16px 0;margin-bottom:8px;">'
                    '<div style="font-size:12px;font-weight:600;margin-bottom:8px;">'
                    '<i class="ti ti-chart-candle" style="font-size:13px;color:#5B5BD6;vertical-align:middle;"></i>'
                    ' 가격 차트</div></div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── 기술적 지표 (매수 관점) ──
    def _ind_status_w(val, good_cond, label_good, label_bad):
        cls = "status-good" if good_cond else "status-danger"
        return f'<span class="ind-status {cls}">{"✅ " + label_good if good_cond else "⚠️ " + label_bad}</span>'

    rsi_status_w = _ind_status_w(rsi, rsi < 70, "저점권" if rsi <= 45 else "정상", "과열 — 추격 주의")
    gap_status_w = _ind_status_w(gap20, gap20 <= 105, "평균선 근처" if gap20 >= 95 else "평균선 아래(매수 기회)", "평균선 위 과대")
    boll_lbl_w   = "하단 근처" if boll_pos < 0.25 else ("상단 근처" if boll_pos > 0.75 else "중간")
    boll_cls_w   = "status-good" if boll_pos < 0.3 else ("status-danger" if boll_pos > 0.75 else "status-ok")

    ma20_row = ""
    if ma20:
        d = (cur - ma20) / ma20 * 100; s_cls = "status-ok" if d >= 0 else "status-good"
        ma20_row = f'<div class="ind-row"><span class="ind-label">20일선</span><div class="ind-right"><span class="ind-val">{_fp(ma20)}</span><span class="ind-status {s_cls}">{"위" if d>=0 else "아래"} {abs(d):.1f}%</span></div></div>'
    ma60_row = ""
    if ma60:
        d = (cur - ma60) / ma60 * 100; s_cls = "status-ok" if d >= 0 else "status-good"
        ma60_row = f'<div class="ind-row"><span class="ind-label">60일선</span><div class="ind-right"><span class="ind-val">{_fp(ma60)}</span><span class="ind-status {s_cls}">{"위" if d>=0 else "아래"} {abs(d):.1f}%</span></div></div>'

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>기술적 지표 (매수 관점)</div>
      <div class="card">
        <div class="ind-row"><span class="ind-label">RSI (14일)</span>
          <div class="ind-right">
            <div class="rsi-bar-wrap2"><div class="rsi-bar-fill2" style="width:{rsi}%;background:{_rsi_color(rsi)};"></div></div>
            <span class="ind-val">{rsi:.0f}</span>{rsi_status_w}
          </div>
        </div>
        <div class="ind-row"><span class="ind-label">이격도 (20일)</span>
          <div class="ind-right"><span class="ind-val">{gap20:.0f}%</span>{gap_status_w}</div>
        </div>
        <div class="ind-row"><span class="ind-label">볼린저밴드</span>
          <div class="ind-right"><span class="ind-val">{boll_lbl_w}</span>
            <span class="ind-status {boll_cls_w}">{'✅ 지지 테스트' if boll_pos<0.3 else '⚠️ 저항 근처' if boll_pos>0.75 else '중립'}</span>
          </div>
        </div>
        {ma20_row}{ma60_row}
      </div>
    </div>""", unsafe_allow_html=True)

    # 지표 해석 카드 (매수 관점)
    if rsi <= 30:
        rsi_interp = f"RSI {rsi:.0f} — 과매도 구간이에요. 너무 많이 떨어진 상태로, 단기 반등 시도가 나올 수 있어요. 분할 매수 진입을 고려해볼 시점이에요."
        rsi_icon = "🟢"
    elif rsi <= 45:
        rsi_interp = f"RSI {rsi:.0f} — 저점 구간에 진입 중이에요. 추가 하락 가능성은 있지만, 장기적으로 매수를 고민해볼 수 있는 구간이에요."
        rsi_icon = "🟡"
    elif rsi >= 70:
        rsi_interp = f"RSI {rsi:.0f} — 과열 구간이에요. 지금 따라 사는 건 고점 매수 위험이 있어요. 눌림목(잠깐 떨어지는 구간)을 기다리는 게 좋아요."
        rsi_icon = "🔴"
    else:
        rsi_interp = f"RSI {rsi:.0f} — 정상 범위예요. 지금 진입하면 큰 위험은 없지만, 더 좋은 타이밍을 기다려도 좋아요."
        rsi_icon = "🟡"

    if gap20 <= 95:
        gap_interp = f"이격도 {gap20:.0f}% — 20일 평균선보다 {100-gap20:.0f}% 아래에 있어요. 평균으로 되돌아오는 힘이 작용할 수 있어 매수 관점에서 유리한 위치예요."
        gap_icon = "🟢"
    elif gap20 >= 110:
        gap_interp = f"이격도 {gap20:.0f}% — 평균선보다 {gap20-100:.0f}% 위에 있어요. 지금 사면 이미 많이 올라온 가격에 사는 거예요. 눌림목을 기다리는 게 좋아요."
        gap_icon = "🔴"
    else:
        gap_interp = f"이격도 {gap20:.0f}% — 평균선 근처에 있어요. 안정적인 진입 구간이에요."
        gap_icon = "🟢"

    if boll_pos <= 0.2:
        boll_interp = "볼린저 하단 근처예요. 주가가 터널 바닥에서 지지를 받고 있어요. 여기서 반등하면 매수 기회가 될 수 있어요."
        boll_icon = "🟢"
    elif boll_pos >= 0.75:
        boll_interp = "볼린저 상단 근처예요. 주가가 터널 천장에 닿아있어요. 여기서 사면 저항을 받을 수 있으니 주의하세요."
        boll_icon = "🔴"
    else:
        boll_interp = "볼린저 중간 구간이에요. 방향을 탐색 중으로, 상단·하단 돌파 방향을 확인 후 진입하는 게 좋아요."
        boll_icon = "🟡"

    st.markdown(f"""<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:0 0 12px 0;">
      <div style="font-size:12px;font-weight:700;color:#3C3489;margin-bottom:12px;display:flex;align-items:center;gap:6px;">
        <i class="ti ti-microscope" style="font-size:14px;"></i> 지금 사기 좋은 자리인가요?
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{rsi_icon} RSI 분석</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">{rsi_interp}</div>
        </div>
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{gap_icon} 이격도 분석</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">{gap_interp}</div>
        </div>
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{boll_icon} 볼린저밴드 분석</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">{boll_interp}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 바닥 지지선 ──
    sup_rows = ""
    if ma20:
        d = (cur-ma20)/ma20*100; s="+" if d>=0 else ""; cls="up" if d>=0 else "down"
        note_cls = "note-near" if abs(d)<5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">{_fp(ma20)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">{"위" if d>=0 else "이탈"}</span></div></div>'
    if boll.get("lower"):
        bl = boll["lower"]; d = (cur-bl)/bl*100; s="+" if d>=0 else ""; cls="up" if d>=0 else "down"
        note_cls = "note-near" if abs(d)<5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">{_fp(bl)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">근접</span></div></div>'
    if ma60:
        d = (cur-ma60)/ma60*100; s="+" if d>=0 else ""; cls="up" if d>=0 else "down"
        note_cls = "note-near" if abs(d)<5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">{_fp(ma60)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">주요 지지</span></div></div>'
    if sup_rows:
        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-barrier-block" style="font-size:15px;color:#5B5BD6;"></i>바닥 지지선</div>
          <div class="card">{sup_rows}</div>
        </div>""", unsafe_allow_html=True)

    # ── 수급 ──
    _render_supply(a, inv)

    # ── 주의 신호 ──
    badges = a.get("badges", [])
    sell_signals = [b for b in badges if b.get("type") in ("sell", "warn")]
    if sell_signals:
        verdict = a.get("verdict", " · ".join(b["text"] for b in sell_signals))
        st.markdown(f"""<div class="section">
          <div class="warn-box">
            <div class="warn-title"><i class="ti ti-alert-triangle" style="font-size:15px;"></i>주의 신호</div>
            <div class="warn-text">{verdict}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── 공시 ──
    with st.spinner("공시 불러오는 중..."):
        disclosures = fetch_disclosures(code, name, days=30, max_items=4)
    if disclosures:
        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-speakerphone" style="font-size:15px;color:#5B5BD6;"></i>최근 공시 (30일)</div>
        </div>""", unsafe_allow_html=True)
        for d in disclosures:
            impact_items = [line.strip() for line in d["impact"].split("\n") if line.strip()]
            impact_html = "".join(
                f'<div style="font-size:11px;color:#534AB7;line-height:1.7;padding:2px 0;">'
                f'<span style="color:#5B5BD6;font-weight:600;">·</span> {line}</div>'
                for line in impact_items
            )
            st.markdown(f"""<div class="card" style="margin:0 0 10px 0;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:10px;background:#EEEDFE;color:#3C3489;padding:2px 8px;border-radius:6px;font-weight:500;">{d['report_type']}</span>
                <span style="font-size:10px;color:#8E8E93;">{d['date']}</span>
              </div>
              <div style="font-size:13px;font-weight:600;color:#1A1A2E;margin-bottom:10px;">{d['title']}</div>
              <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;margin-bottom:8px;">
                <div style="font-size:10px;font-weight:700;color:#5B5BD6;margin-bottom:6px;">💡 이 공시가 의미하는 것</div>
                <div style="font-size:11px;color:#3B3B5C;line-height:1.7;">{d['analysis']}</div>
              </div>
              <div style="background:#EEEDFE;border-radius:10px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;color:#3C3489;margin-bottom:6px;">📅 주가 영향 흐름</div>
                {impact_html}
              </div>
            </div>""", unsafe_allow_html=True)

    # ── 뉴스 ──
    news = fetch_stock_news(name, max_items=3)
    if news:
        st.markdown(f'<div class="section"><div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>{name} 뉴스</div></div>', unsafe_allow_html=True)
        for n in news:
            sent = n.get("sentiment", "neutral")
            bdg_t = {"positive":"pos","negative":"neg","mixed":"mix"}.get(sent, "neu")
            st.markdown(f"""<div style="margin:0 16px;"><div class="news-card">
              <div class="news-card-top"><span class="badge badge-{bdg_t}">{n.get('label','중립')}</span>
                <span class="news-source">{n.get('source','')} · {n.get('published','')}</span></div>
              <div class="news-title">{n['title']}</div>
            </div></div>""", unsafe_allow_html=True)

    st.caption("⚠️ 투자 결정은 본인 책임입니다. 이 앱의 정보는 참고용이며 투자 권유가 아닙니다.")


# ─────────────────────────────────────────────────────────
# 스캐너 상세 페이지
# ─────────────────────────────────────────────────────────
def render_scanner_detail():
    code = st.session_state.detail_code
    name = st.session_state.detail_name
    if st.button("← 뒤로"):
        st.session_state.page = "main"; st.rerun()

    with st.spinner("분석 중..."):
        pd2   = get_current_price(code)
        ohlcv = get_ohlcv(code, days=60)
        inv   = get_investor_trading(code, days=25)
        a     = analyze_stock(ohlcv, inv)
        auto_tp = _calc_auto_targets(a, ohlcv)

    cur = pd2.get("current_price") or a.get("current_price", 0)
    chg = pd2.get("change", 0); chg_pct = pd2.get("change_pct", 0)
    chg_cls = "up" if chg_pct >= 0 else "down"
    conf_map = {"high": ("badge-ok", "신뢰도 높음"), "mid": ("badge-warn", "신뢰도 보통"), "low": ("badge-neu", "신호 약함")}
    bdg_cls, conf_lbl = conf_map.get(a["confidence"], ("badge-neu", "분석 중"))
    score = a.get("score", 0)
    sigs = a.get("signals", {})
    rsi = a.get("rsi", 50)
    vol_ratio = a.get("volume_ratio", 1)
    gap20 = a.get("gap20") or 100
    boll = a.get("bollinger", {})
    ma20 = a.get("ma20"); ma60 = a.get("ma60")
    tp = auto_tp["target_price"]; sp = auto_tp["stop_price"]
    tu = auto_tp["target_upside"]; sd_pct = auto_tp["stop_downside"]
    tb = auto_tp["target_basis"];  sb = auto_tp["stop_basis"]
    rr = abs(tu / sd_pct) if sd_pct else 0

    # ── 헤더 ──
    st.markdown(f"""<div class="hdr">
      <div style="display:flex;align-items:center;gap:12px;width:100%;">
        <div style="flex:1;"><div class="hdr-title">{name}</div>
          <div style="font-size:11px;color:#8E8E93;">{code} · 매집신호 상세</div></div>
        <span class="badge {bdg_cls}">{conf_lbl} {score}/5</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 현재가 ──
    st.markdown(f"""<div class="price-section">
      <div class="current-price">{_fp(cur)}</div>
      <div style="display:flex;gap:8px;margin-top:4px;">
        <span class="{chg_cls}" style="font-size:14px;font-weight:600;">{'▲' if chg_pct>=0 else '▼'} {abs(chg):,.0f}원</span>
        <span class="{chg_cls}" style="font-size:14px;font-weight:600;">({abs(chg_pct):.2f}%)</span>
      </div>
      <div class="price-meta">
        <div class="pm-item">고가 <span>{_fp(pd2.get('high'))}</span></div>
        <div class="pm-item">저가 <span>{_fp(pd2.get('low'))}</span></div>
        <div class="pm-item">거래량 <span>{pd2.get('volume',0):,}</span></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 왜 이 종목이 포착됐는지 히어로 카드 ──
    if score >= 4:
        hero_bg = "#5B5BD6"
        why_title = f"✅ {score}가지 매집 신호 동시 감지"
        why_sub = "신뢰도 높은 매집 패턴이에요. 큰 손(외국인·기관)이 이 종목을 조용히 사 모으고 있는 것으로 판단돼요."
    else:
        hero_bg = "#BA7517"
        why_title = f"⚠️ {score}가지 신호 감지 — 추가 확인 필요"
        why_sub = "일부 매집 신호가 감지됐지만, 모든 조건이 충족되지 않았어요. 조금 더 지켜봐야 해요."

    detected_signals = []
    if sigs.get("vol_surge"):   detected_signals.append(f"거래량 {vol_ratio:.0f}배 급증")
    if sigs.get("obv_up"):      detected_signals.append("OBV 꾸준히 상승 중")
    if sigs.get("foreign_buy"): detected_signals.append(f"외국인 순매수 {a.get('foreign_net_3d',0):+,}주")
    if sigs.get("inst_buy"):    detected_signals.append(f"기관 순매수 {a.get('institution_net_3d',0):+,}주")
    if sigs.get("sideways"):    detected_signals.append("박스권 횡보 (매집 패턴)")

    detected_html = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-top:5px;">'
        f'<span style="width:4px;height:4px;border-radius:50%;background:rgba(255,255,255,0.7);flex-shrink:0;"></span>'
        f'<span style="font-size:11px;color:rgba(255,255,255,0.9);">{s}</span></div>'
        for s in detected_signals
    )
    st.markdown(f"""<div style="margin:12px 16px 8px;background:{hero_bg};border-radius:16px;padding:16px 18px;">
      <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;">왜 이 종목이 포착됐나요?</div>
      <div style="font-size:16px;font-weight:700;color:#fff;margin-bottom:6px;">{why_title}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.85);line-height:1.6;">{why_sub}</div>
      {detected_html}
    </div>""", unsafe_allow_html=True)

    # ── 5신호 상세 그리드 ──
    sig_items = [
        ("vol_surge", "거래량 급증", f"{vol_ratio:.1f}배", sigs.get("vol_surge")),
        ("obv_up", "OBV 상승", "상승 중" if sigs.get("obv_up") else "보합/하락", sigs.get("obv_up")),
        ("foreign_buy", "외국인 매수", f"{a.get('foreign_net_3d',0):+,}주", sigs.get("foreign_buy")),
        ("inst_buy", "기관 매수", f"{a.get('institution_net_3d',0):+,}주", sigs.get("inst_buy")),
        ("sideways", "횡보 패턴", "20일 박스" if sigs.get("sideways") else "추세 중", sigs.get("sideways")),
    ]
    grid_html = "".join(f"""<div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
      <div style="font-size:10px;color:#8E8E93;margin-bottom:4px;display:flex;align-items:center;gap:4px;">
        <div class="sig-dot {'sig-on' if ok else 'sig-off'}"></div>{label}</div>
      <div style="font-size:13px;font-weight:600;color:{'#3C3489' if ok else '#A32D2D'};">{val}</div>
    </div>""" for _, label, val, ok in sig_items)
    st.markdown(f"""<div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-radar" style="font-size:15px;color:#5B5BD6;"></i>5대 매집 신호 ({score}/5)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">{grid_html}</div>
    </div>""", unsafe_allow_html=True)

    # ── 각 신호의 의미 설명 (초보자용) ──
    sig_explanations = []
    if sigs.get("vol_surge"):
        sig_explanations.append(("📦", "거래량 급증", f"거래량이 평소보다 <b>{vol_ratio:.0f}배</b> 많이 거래됐어요. 가격은 크게 안 올랐는데 거래량만 늘었다면, 누군가 조용히 많은 물량을 사들이고 있다는 신호예요. 이게 매집의 가장 대표적인 흔적이에요."))
    if sigs.get("obv_up"):
        sig_explanations.append(("📈", "OBV 지속 상승", "OBV(On Balance Volume)는 '돈이 어디로 흘러가는지'를 보여주는 지표예요. OBV가 꾸준히 올라간다는 건, 주가가 크게 안 올라도 꾸준히 매수세가 쌓이고 있다는 의미예요. 주가보다 먼저 방향을 알려주는 선행 지표예요."))
    if sigs.get("foreign_buy"):
        f3 = a.get("foreign_net_3d", 0)
        sig_explanations.append(("🌍", "외국인 순매수", f"외국인이 최근 3일간 총 <b>{f3:+,}주</b>를 순매수했어요. 외국인 투자자들은 보통 수개월~수년 앞을 내다보며 투자해요. 꾸준히 사들인다면 이 종목에 강한 확신이 있다는 신호예요."))
    if sigs.get("inst_buy"):
        i3 = a.get("institution_net_3d", 0)
        sig_explanations.append(("🏦", "기관 순매수", f"기관(펀드·증권사 등)이 최근 3일간 <b>{i3:+,}주</b>를 순매수했어요. 외국인+기관이 <b>함께</b> 살 때는 신뢰도가 훨씬 높아져요. 둘 다 동시에 사는 건 강력한 매집 신호예요."))
    if sigs.get("sideways"):
        sig_explanations.append(("📊", "박스권 횡보", "20일 동안 주가가 좁은 가격대에서 움직이고 있어요. 이를 '박스권 횡보'라고 해요. 매집 세력이 일부러 가격을 일정하게 유지하면서 물량을 쌓는 전형적인 패턴이에요. 박스권을 돌파하면 급등이 나올 수 있어요."))

    if sig_explanations:
        expl_html = "".join(
            f'<div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">'
            f'<div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">{icon} {title}</div>'
            f'<div style="font-size:11px;color:#3C3489;line-height:1.6;">{desc}</div>'
            f'</div>'
            for icon, title, desc in sig_explanations
        )
        st.markdown(f"""<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:0 0 12px 0;">
          <div style="font-size:12px;font-weight:700;color:#3C3489;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
            <i class="ti ti-microscope" style="font-size:14px;"></i> 각 신호가 의미하는 것
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">{expl_html}</div>
        </div>""", unsafe_allow_html=True)

    # ── 목표가 / 손절가 분석 카드 ──
    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-target" style="font-size:15px;color:#5B5BD6;"></i>목표가 / 손절가 분석</div>
    </div>
    <div class="card" style="margin-bottom:6px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
        <div>
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">추천 목표가</div>
          <div style="font-size:17px;font-weight:700;color:#27500A;">{_fp(tp)}</div>
          <div style="font-size:11px;color:#27500A;margin-top:2px;">+{tu:.1f}%</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:3px;">기준: {tb}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:10px;color:#8E8E93;margin-bottom:3px;">추천 손절가</div>
          <div style="font-size:17px;font-weight:700;color:#A32D2D;">{_fp(sp)}</div>
          <div style="font-size:11px;color:#A32D2D;margin-top:2px;">{sd_pct:.1f}%</div>
          <div style="font-size:10px;color:#8E8E93;margin-top:3px;">기준: {sb}</div>
        </div>
      </div>
      <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
        <div style="font-size:10px;color:#8E8E93;margin-bottom:4px;">리스크/리워드 비율</div>
        <div style="font-size:13px;font-weight:600;color:{'#27500A' if rr >= 2 else '#BA7517' if rr >= 1 else '#A32D2D'};">
          1 : {rr:.1f} {'✅ 양호' if rr >= 2 else '⚠️ 보통' if rr >= 1 else '❌ 불리'}
        </div>
        <div style="font-size:10px;color:#8E8E93;margin-top:3px;">손실 1원 대비 수익 {rr:.1f}원 기대 — 2 이상이면 진입 적합</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Plotly 캔들 차트 ──
    if ohlcv is not None and not ohlcv.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=ohlcv.index,
            open=ohlcv["open"], high=ohlcv["high"],
            low=ohlcv["low"], close=ohlcv["close"],
            increasing_line_color="#E24B4A", decreasing_line_color="#185FA5",
            increasing_fillcolor="#E24B4A", decreasing_fillcolor="#185FA5",
            name="가격", showlegend=False,
        ))
        if tp:
            fig.add_hline(y=tp, line_color="#27500A", line_width=1.2, line_dash="dot",
                          annotation_text=f"목표 {tp:,}", annotation_font_size=9,
                          annotation_font_color="#27500A")
        if sp:
            fig.add_hline(y=sp, line_color="#A32D2D", line_width=1.2, line_dash="dot",
                          annotation_text=f"손절 {sp:,}", annotation_font_size=9,
                          annotation_font_color="#A32D2D")
        fig.update_layout(
            margin=dict(l=0, r=0, t=8, b=0), height=200,
            paper_bgcolor="#F8F8FA", plot_bgcolor="#F8F8FA",
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#C7C7CC"),
                       rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F5", tickfont=dict(size=9, color="#C7C7CC")),
        )
        st.markdown('<div style="background:#fff;padding:14px 16px 0;margin-bottom:8px;">'
                    '<div style="font-size:12px;font-weight:600;margin-bottom:8px;">'
                    '<i class="ti ti-chart-candle" style="font-size:13px;color:#5B5BD6;vertical-align:middle;"></i>'
                    ' 가격 차트 (초록점선=목표가 · 빨강점선=손절가)</div></div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── 기술적 지표 ──
    def _ind_status_s(cond, label_good, label_bad):
        cls = "status-good" if cond else "status-danger"
        return f'<span class="ind-status {cls}">{label_good if cond else label_bad}</span>'

    rsi_status = _ind_status_s(rsi < 70, "정상" if rsi > 30 else "과매도", "과매수")
    gap_status = _ind_status_s(95 <= gap20 <= 115, "평균선 근처", "이격 과대")
    boll_pos = boll.get("position", 0.5)
    boll_lbl = "하단 근처" if boll_pos < 0.2 else ("상단 근처" if boll_pos > 0.8 else "중간")
    boll_cls = "status-good" if boll_pos < 0.3 else ("status-danger" if boll_pos > 0.8 else "status-ok")

    ma20_row = ""
    if ma20:
        d = (cur-ma20)/ma20*100; s_cls = "status-ok" if d >= 0 else "status-danger"
        ma20_row = f'<div class="ind-row"><span class="ind-label">20일선</span><div class="ind-right"><span class="ind-val">{_fp(ma20)}</span><span class="ind-status {s_cls}">{"위" if d>=0 else "아래"} {abs(d):.1f}%</span></div></div>'
    ma60_row = ""
    if ma60:
        d = (cur-ma60)/ma60*100; s_cls = "status-ok" if d >= 0 else "status-danger"
        ma60_row = f'<div class="ind-row"><span class="ind-label">60일선</span><div class="ind-right"><span class="ind-val">{_fp(ma60)}</span><span class="ind-status {s_cls}">{"위" if d>=0 else "아래"} {abs(d):.1f}%</span></div></div>'

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>기술적 지표</div>
      <div class="card">
        <div class="ind-row"><span class="ind-label">RSI (14일)</span>
          <div class="ind-right">
            <div class="rsi-bar-wrap2"><div class="rsi-bar-fill2" style="width:{rsi}%;background:{_rsi_color(rsi)};"></div></div>
            <span class="ind-val">{rsi:.0f}</span>{rsi_status}
          </div>
        </div>
        <div class="ind-row"><span class="ind-label">거래량 비율</span>
          <div class="ind-right"><span class="ind-val">{vol_ratio:.1f}배</span>
            <span class="ind-status {'status-good' if vol_ratio>=2 else 'status-ok'}">{'급증' if vol_ratio>=2 else '보통'}</span>
          </div>
        </div>
        <div class="ind-row"><span class="ind-label">이격도 (20일)</span>
          <div class="ind-right"><span class="ind-val">{gap20:.0f}%</span>{gap_status}</div>
        </div>
        <div class="ind-row"><span class="ind-label">볼린저밴드</span>
          <div class="ind-right"><span class="ind-val">{boll_lbl}</span>
            <span class="ind-status {boll_cls}">{'지지 시도' if boll_pos<0.3 else '과열' if boll_pos>0.8 else '보통'}</span>
          </div>
        </div>
        {ma20_row}{ma60_row}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 바닥 지지선 ──
    sup_rows = ""
    if ma20:
        d = (cur-ma20)/ma20*100; s = "+" if d>=0 else ""; cls = "up" if d>=0 else "down"
        note_cls = "note-near" if abs(d) < 5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">{_fp(ma20)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">{"위" if d>=0 else "이탈"}</span></div></div>'
    if boll.get("lower"):
        bl = boll["lower"]; d = (cur-bl)/bl*100; s = "+" if d>=0 else ""; cls = "up" if d>=0 else "down"
        note_cls = "note-near" if abs(d) < 5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">{_fp(bl)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">근접</span></div></div>'
    if ma60:
        d = (cur-ma60)/ma60*100; s = "+" if d>=0 else ""; cls = "up" if d>=0 else "down"
        note_cls = "note-near" if abs(d) < 5 else "note-far"
        sup_rows += f'<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">{_fp(ma60)}</span><span class="sup-dist {cls}">{s}{d:.1f}%</span><span class="sup-note {note_cls}">주요 지지</span></div></div>'
    if sup_rows:
        st.markdown(f"""<div class="section">
          <div class="sec-title"><i class="ti ti-barrier-block" style="font-size:15px;color:#5B5BD6;"></i>바닥 지지선</div>
          <div class="card">{sup_rows}</div>
        </div>""", unsafe_allow_html=True)

    # ── 수급 ──
    _render_supply(a, inv)

    # ── 신호 종합 분석 & 전략 ──
    if score >= 4 and sigs.get("foreign_buy") and sigs.get("inst_buy"):
        combined_msg = f"외국인과 기관이 <b>동시에</b> 순매수하면서 거래량까지 급증했어요. 이 3가지가 함께 나타나는 건 매집 신호 중에서도 가장 강력한 패턴이에요."
    elif score >= 4:
        combined_msg = f"5가지 매집 신호 중 <b>{score}가지</b>가 동시에 켜졌어요. 이 정도면 신뢰도가 높은 매집 구간으로 볼 수 있어요."
    elif sigs.get("vol_surge") and sigs.get("obv_up"):
        combined_msg = "거래량 급증과 OBV 상승이 함께 나타났어요. 매수 세력이 꾸준히 물량을 쌓고 있는 흔적이에요."
    else:
        combined_msg = "일부 매집 신호가 감지됐지만 모든 조건을 충족하진 않았어요. 추가 신호를 기다리는 게 좋아요."

    if rsi >= 70:
        strategy = f"RSI {rsi:.0f}으로 이미 과열된 상태예요. <b>지금 당장 쫓아가기보다 눌림목(잠깐 떨어지는 구간)을 기다리는 게 좋아요.</b> 손절선은 {_fp(sp)}으로 설정하고, 5% 이상 빠질 때 재진입을 노려보세요."
    elif score >= 4:
        strategy = f"신뢰도 높은 매집 구간이에요. <b>분할 매수</b>로 접근하되, 손절선({_fp(sp)})을 반드시 지키세요. 한 번에 많은 돈을 넣기보다 2~3번에 나눠 사는 게 리스크를 줄이는 방법이에요."
    else:
        strategy = f"신호가 일부만 확인됐어요. <b>소량만 먼저 진입</b>하고, 추가 신호(외국인·기관 연속 매수)가 확인되면 물량을 늘려가는 전략을 권장해요."

    st.markdown(f"""<div class="section">
      <div class="advice-box">
        <div class="advice-title"><i class="ti ti-bulb" style="font-size:15px;"></i>시스템 종합 판단</div>
        <div class="advice-text" style="margin-bottom:10px;">{combined_msg}</div>
        <div style="height:0.5px;background:rgba(91,91,214,0.2);margin-bottom:10px;"></div>
        <div style="font-size:10px;font-weight:700;color:#3C3489;margin-bottom:5px;">💡 접근 전략</div>
        <div class="advice-text">{strategy}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 관심종목 추가 버튼 ──
    col_add, _ = st.columns([1, 1])
    with col_add:
        if st.button("⭐ 관심종목 추가", use_container_width=True):
            ok2, msg = add_watchlist(st.session_state.user_id, code, name, None, None)
            if ok2: st.success(f"{name}을 관심종목에 추가했습니다.")
            else: st.info(msg)

    # ── 뉴스 ──
    news = fetch_stock_news(name, max_items=3)
    if news:
        st.markdown(f'<div class="section"><div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>{name} 뉴스</div></div>', unsafe_allow_html=True)
        for n in news:
            sent = n.get("sentiment", "neutral")
            bdg_t = {"positive": "pos", "negative": "neg", "mixed": "mix"}.get(sent, "neu")
            st.markdown(f"""<div style="margin:0 16px;"><div class="news-card">
              <div class="news-card-top"><span class="badge badge-{bdg_t}">{n.get('label','중립')}</span>
                <span class="news-source">{n.get('source','')} · {n.get('published','')}</span></div>
              <div class="news-title">{n['title']}</div>
            </div></div>""", unsafe_allow_html=True)

    st.caption("⚠️ 투자 결정은 본인 책임입니다. 이 앱의 정보는 참고용이며 투자 권유가 아닙니다.")


# ─────────────────────────────────────────────────────────
# 공통: 외국인/기관 수급
# ─────────────────────────────────────────────────────────
def _render_supply(a, inv_df):
    foreign = a.get("foreign_net_3d", 0)
    inst    = a.get("institution_net_3d", 0)
    f_cls = "up" if foreign>=0 else "down"; f_s = "+" if foreign>=0 else ""
    i_cls = "up" if inst>=0 else "down";    i_s = "+" if inst>=0 else ""
    f_bar = min(abs(foreign)/(max(abs(foreign),abs(inst),1))*80,80)
    i_bar = min(abs(inst)/(max(abs(foreign),abs(inst),1))*80,80)
    f_bar_cls = "bar-buy" if foreign>=0 else "bar-sell"
    i_bar_cls = "bar-buy" if inst>=0 else "bar-sell"

    # 일별 칩
    f_chips = ""; i_chips = ""
    if inv_df is not None and not inv_df.empty:
        for _, row in inv_df.tail(5).iterrows():
            fv = int(row.get("외국인",0)); iv = int(row.get("기관",0))
            fc = "chip-buy" if fv>=0 else "chip-sell"; ic = "chip-buy" if iv>=0 else "chip-sell"
            fs = "+" if fv>=0 else ""; is_ = "+" if iv>=0 else ""
            f_chips += f'<span class="day-chip {fc}">{fs}{fv//1000}K</span>'
            i_chips += f'<span class="day-chip {ic}">{is_}{iv//1000}K</span>'

    st.markdown(f"""<div class="section">
      <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (5일)</div>
      <div class="card">
        <div class="supply-row">
          <span class="supply-who">외국인</span>
          <div class="supply-bar-bg"><div class="supply-bar-fill {f_bar_cls}" style="width:{f_bar}%;"></div></div>
          <span class="supply-val {f_cls}">{f_s}{foreign:,}주</span>
        </div>
        {('<div class="days-row">' + f_chips + '</div>') if f_chips else ''}
        <div class="supply-row">
          <span class="supply-who">기관</span>
          <div class="supply-bar-bg"><div class="supply-bar-fill {i_bar_cls}" style="width:{i_bar}%;"></div></div>
          <span class="supply-val {i_cls}">{i_s}{inst:,}주</span>
        </div>
        {('<div class="days-row">' + i_chips + '</div>') if i_chips else ''}
      </div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 메인 진입점
# ─────────────────────────────────────────────────────────
if not st.session_state.user_id:
    render_login()
    st.stop()

page = st.session_state.page
if page == "holdings_detail":
    render_holdings_detail(); st.stop()
elif page == "watchlist_detail":
    render_watchlist_detail(); st.stop()
elif page == "scanner_detail":
    render_scanner_detail(); st.stop()

# ── 수급 상세 분석 (탭 밖에서 렌더링 — DOM 충돌 방지) ──
if st.session_state.get("show_supply_detail"):
    with st.spinner("수급 데이터 불러오는 중..."):
        _inv_df = get_kospi_investor_value(days=25)
    render_supply_detail(_inv_df)
    st.stop()

# ── 시장 상세 분석 (탭 밖에서 렌더링 — DOM 충돌 방지) ──
if st.session_state.get("show_market_detail"):
    with st.spinner("시장 데이터 불러오는 중..."):
        _idx     = get_index_data()
        _us      = get_us_indices()
        _kp_hist = get_index_ohlcv_history("1001", 250)
        _kd_hist = get_index_ohlcv_history("2001", 250)
    _ma_kp = calc_ma_status(_kp_hist)
    _ma_kd = calc_ma_status(_kd_hist)
    render_market_detail(_idx, _us, _ma_kp, _ma_kd, _kp_hist, _kd_hist)
    st.stop()

# ── 원래대로 st.tabs() 사용 — 기능은 그대로, JS로 탭바만 하단 이동 ──
tab1, tab2, tab3, tab4, tab5 = st.tabs(["홈", "뉴스", "보유", "관심", "매집"])
with tab1: render_home()
with tab2: render_news()
with tab3: render_holdings()
with tab4: render_watchlist()
with tab5: render_scanner()




with st.sidebar:
    st.markdown(f"**{st.session_state.username}** 님")
    if st.button("로그아웃"):
        for k in ["user_id","username","scanner_ran","scanner_results"]:
            st.session_state[k] = None if k=="user_id" else ([] if k=="scanner_results" else ("" if k=="username" else False))
        st.rerun()
