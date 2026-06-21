// ─────────────────────────────────────────────────────────
// 포켓주식 앱 JS
// ─────────────────────────────────────────────────────────

const API = '';  // 같은 서버에서 서빙되므로 빈 문자열

// ─────────────────────────────────────────────────────────
// 커스텀 Confirm 모달
// ─────────────────────────────────────────────────────────
function showSentimentInfo() {
  const existing = document.getElementById('_info-modal');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.id = '_info-modal';
  el.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:flex-end;justify-content:center;background:rgba(0,0,0,0.45);backdrop-filter:blur(4px);';
  el.innerHTML = `
    <div style="width:100%;max-width:430px;background:#fff;border-radius:20px 20px 0 0;padding:24px 20px 36px;animation:slideUp .22s ease;max-height:85vh;overflow-y:auto;">
      <div style="width:40px;height:4px;background:#E5E5EA;border-radius:4px;margin:0 auto 18px;"></div>
      <div style="font-size:16px;font-weight:700;color:#1C1C1E;margin-bottom:4px;">투자심리 지수란?</div>
      <div style="font-size:13px;color:#8E8E9A;line-height:1.6;margin-bottom:18px;">CNN의 Fear &amp; Greed Index와 동일한 방식으로, 8가지 시장 지표를 각각 0~100점으로 정규화한 뒤 가중평균해 산출해요. 숫자가 낮을수록 공포, 높을수록 탐욕이에요.</div>

      ${[
        { icon:'ti-activity', name:'VKOSPI (공포지수)', w:'20%', desc:'한국판 VIX예요. 옵션 시장이 예상하는 향후 변동성으로, 낮을수록 시장이 안정적이에요. 가장 중요한 지표로 20% 비중을 줬어요.' },
        { icon:'ti-chart-line', name:'KOSPI 등락률', w:'15%', desc:'당일 KOSPI가 얼마나 올랐는지 내렸는지예요. -3% 이하면 0점, +3% 이상이면 100점으로 환산해요.' },
        { icon:'ti-user-dollar', name:'외국인 3일 순매수', w:'15%', desc:'외국인이 최근 3거래일간 사고판 금액의 합계예요. 외국인은 시장 방향을 선도하는 경우가 많아 중요하게 봐요.' },
        { icon:'ti-building-bank', name:'기관 3일 순매수', w:'12%', desc:'국내 기관(펀드·보험·연기금 등)의 3일 순매수예요. 외국인과 함께 수급의 핵심 지표예요.' },
        { icon:'ti-arrows-up-down', name:'등락비율 ADR', w:'13%', desc:'KOSPI 전체 종목 중 오른 종목 비율이에요. 70% 이상이면 시장 전반이 좋은 상태, 30% 이하면 광범위한 하락이에요.' },
        { icon:'ti-timeline', name:'60일 고점 대비 위치', w:'10%', desc:'현재 KOSPI가 최근 60일 고점·저점 범위에서 어디쯤 있는지예요. 고점 근처면 탐욕, 저점 근처면 공포예요.' },
        { icon:'ti-coin', name:'거래대금 vs 20일 평균', w:'8%', desc:'오늘 시장 거래대금이 20일 평균 대비 얼마나 활발한지예요. 거래가 활발하면 관심·참여도가 높다는 의미예요.' },
        { icon:'ti-wave-sine', name:'시장 변동성 (10일)', w:'7%', desc:'최근 10거래일 KOSPI 일별 등락 표준편차예요. 변동폭이 작을수록 안정적(탐욕), 클수록 불안정(공포)이에요.' },
      ].map(f => `
        <div style="display:flex;gap:12px;padding:10px 0;border-bottom:0.5px solid #F5F5F7;">
          <div style="width:32px;height:32px;border-radius:10px;background:#F0F0F5;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <i class="ti ${f.icon}" style="font-size:16px;color:#5B5BD6;"></i>
          </div>
          <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
              <span style="font-size:13px;font-weight:600;color:#1C1C1E;">${f.name}</span>
              <span style="font-size:10px;background:#EEEDFE;color:#5B5BD6;padding:2px 6px;border-radius:4px;font-weight:600;">${f.w}</span>
            </div>
            <div style="font-size:12px;color:#8E8E9A;line-height:1.6;">${f.desc}</div>
          </div>
        </div>`).join('')}

      <div style="margin-top:16px;background:#FFF8F0;border-radius:12px;padding:12px 14px;">
        <div style="font-size:12px;font-weight:600;color:#854F0B;margin-bottom:4px;">⚠️ 참고 사항</div>
        <div style="font-size:12px;color:#854F0B;line-height:1.6;">이 지수는 참고용이에요. 정규화 범위와 가중치는 시장 특성에 맞게 추정한 값으로, 실데이터 백테스트로 지속 개선 중이에요. 투자 결정의 단독 근거로 사용하지 마세요.</div>
      </div>

      <button onclick="document.getElementById('_info-modal').remove()" style="width:100%;height:48px;margin-top:16px;border-radius:14px;border:none;background:#F2F2F7;color:#3C3C43;font-size:15px;font-weight:600;cursor:pointer;">닫기</button>
    </div>`;
  document.body.appendChild(el);
  el.addEventListener('click', e => { if (e.target === el) el.remove(); });
}

function showConfirm({ title, message, confirmText = '삭제', cancelText = '취소', onConfirm }) {
  const existing = document.getElementById('_confirm-modal');
  if (existing) existing.remove();

  const el = document.createElement('div');
  el.id = '_confirm-modal';
  el.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:flex-end;justify-content:center;background:rgba(0,0,0,0.45);backdrop-filter:blur(4px);';
  el.innerHTML = `
    <div style="width:100%;max-width:430px;background:#fff;border-radius:20px 20px 0 0;padding:28px 20px 36px;animation:slideUp .22s ease;">
      <div style="width:40px;height:4px;background:#E5E5EA;border-radius:4px;margin:0 auto 20px;"></div>
      <div style="text-align:center;margin-bottom:18px;">
        <div style="width:52px;height:52px;border-radius:50%;background:#FFF0F0;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;">
          <i class="ti ti-trash" style="font-size:24px;color:#E24B4A;"></i>
        </div>
        <div style="font-size:17px;font-weight:700;color:#1C1C1E;margin-bottom:6px;">${title}</div>
        <div style="font-size:14px;color:#8E8E9A;line-height:1.6;">${message}</div>
      </div>
      <div style="display:flex;gap:10px;margin-top:8px;">
        <button id="_confirm-cancel" style="flex:1;height:50px;border-radius:14px;border:none;background:#F2F2F7;color:#3C3C43;font-size:16px;font-weight:600;cursor:pointer;">${cancelText}</button>
        <button id="_confirm-ok" style="flex:1;height:50px;border-radius:14px;border:none;background:#E24B4A;color:#fff;font-size:16px;font-weight:700;cursor:pointer;">${confirmText}</button>
      </div>
    </div>`;

  document.body.appendChild(el);

  const close = () => el.remove();
  el.addEventListener('click', e => { if (e.target === el) close(); });
  document.getElementById('_confirm-cancel').onclick = close;
  document.getElementById('_confirm-ok').onclick = () => { close(); onConfirm(); };
}

// ─────────────────────────────────────────────────────────
// 상태
// ─────────────────────────────────────────────────────────
let _token = localStorage.getItem('pk_token') || '';
let _username = localStorage.getItem('pk_user') || '';
let _currentTab = 'home';
let _prevScreen = '';
let _allNews = [];
let _allHoldings = [];
let _autoRefreshTimer = null;
const _AUTO_REFRESH_MS = 60000; // 1분
let _allWatchlist = [];
let _scannerPollTimer = null;

// ─────────────────────────────────────────────────────────
// API 유틸
// ─────────────────────────────────────────────────────────
async function api(method, path, body, timeoutMs = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    signal: controller.signal
  };
  if (_token) opts.headers['Authorization'] = 'Bearer ' + _token;
  if (body) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(API + path, opts);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || '오류가 발생했습니다');
    return data;
  } finally {
    clearTimeout(timer);
  }
}

// ─────────────────────────────────────────────────────────
// 화면 전환
// ─────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-' + id).classList.add('active');
  const nav = document.getElementById('bottom-nav');
  const noNav = ['login', 'register', 'holding-detail', 'watchlist-detail', 'news-detail', 'index-detail', 'forecast-detail', 'supply-detail', 'scanner-detail'];
  nav.style.display = noNav.includes(id) ? 'none' : 'flex';
}

function _startAutoRefresh(tab) {
  clearInterval(_autoRefreshTimer);
  _autoRefreshTimer = null;
  const refreshFns = {
    home:      () => loadHome(true),
    holdings:  () => refreshHoldingsPrices(),
    watchlist: () => refreshWatchlistPrices(),
  };
  if (refreshFns[tab]) {
    _autoRefreshTimer = setInterval(refreshFns[tab], _AUTO_REFRESH_MS);
  }
}

function switchTab(tab) {
  if (tab !== 'scanner') { clearTimeout(_scannerPollTimer); _scannerPollTimer = null; }
  clearInterval(_autoRefreshTimer); _autoRefreshTimer = null;
  _currentTab = tab;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navEl = document.getElementById('nav-' + tab);
  if (navEl) navEl.classList.add('active');
  showScreen(tab);
  if (tab === 'home') loadHome();
  else if (tab === 'news') loadNews();
  else if (tab === 'holdings') loadHoldings();
  else if (tab === 'watchlist') loadWatchlist();
  else if (tab === 'scanner') loadScanner();
  _startAutoRefresh(tab);
}

function goBack() {
  clearInterval(_autoRefreshTimer); _autoRefreshTimer = null;
  switchTab(_currentTab);
}

function showRegister() {
  showScreen('register');
}

// ─────────────────────────────────────────────────────────
// 인증
// ─────────────────────────────────────────────────────────
async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';
  if (!username || !password) { errEl.textContent = '아이디와 비밀번호를 입력하세요'; return; }
  try {
    const data = await api('POST', '/api/auth/login', { username, password });
    _token = data.token;
    _username = data.username;
    localStorage.setItem('pk_token', _token);
    localStorage.setItem('pk_user', _username);
    afterLogin();
  } catch(e) {
    errEl.textContent = e.message;
  }
}

async function doRegister() {
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const errEl = document.getElementById('reg-error');
  errEl.textContent = '';
  if (!username || !password) { errEl.textContent = '모든 항목을 입력하세요'; return; }
  try {
    const data = await api('POST', '/api/auth/register', { username, password });
    _token = data.token;
    _username = data.username;
    localStorage.setItem('pk_token', _token);
    localStorage.setItem('pk_user', _username);
    afterLogin();
  } catch(e) {
    errEl.textContent = e.message;
  }
}

function afterLogin() {
  document.getElementById('bottom-nav').style.display = 'flex';
  switchTab('home');
}

function logout() {
  _token = '';
  _username = '';
  localStorage.removeItem('pk_token');
  localStorage.removeItem('pk_user');
  showScreen('login');
  document.getElementById('bottom-nav').style.display = 'none';
}

// ─────────────────────────────────────────────────────────
// 유틸
// ─────────────────────────────────────────────────────────
function fmtNum(n) {
  if (!n && n !== 0) return '-';
  return Math.round(n).toLocaleString('ko-KR');
}
function fmtPct(n) {
  if (!n && n !== 0) return '-';
  const sign = n > 0 ? '+' : '';
  return sign + n.toFixed(2) + '%';
}
function fmtPnl(n) {
  if (!n && n !== 0) return '-';
  const sign = n > 0 ? '+' : '';
  const abs = Math.abs(n);
  if (abs >= 1e8) return sign + (n/1e8).toFixed(1) + '억';
  if (abs >= 1e4) return sign + Math.round(n/1e4) + '만';
  return sign + fmtNum(n);
}
function pnlClass(n) { return n > 0 ? 'up' : n < 0 ? 'down' : ''; }
function iconColors(name) {
  const cs = ['icon-purple','icon-blue','icon-red','icon-amber','icon-green','icon-gray'];
  let h = 0; for (let c of (name||'')) h = (h*31 + c.charCodeAt(0)) % cs.length;
  return cs[h];
}
function iconText(name) { return (name||'').substring(0,2); }
function nowStr() {
  const d = new Date();
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')} 기준`;
}

// ─────────────────────────────────────────────────────────
// 홈 탭
// ─────────────────────────────────────────────────────────
let _homeLoaded = false;
async function loadHome(force) {
  if (_homeLoaded && !force) return;
  _homeLoaded = true;
  const el = document.getElementById('home-content');
  const silent = force && el.children.length > 0; // 이미 콘텐츠 있으면 스피너 없이 갱신
  if (!silent) {
    el.innerHTML = '<div class="loading"><div class="spinner"></div> 시장 분석 중...</div>';
  }
  document.getElementById('home-date').textContent = nowStr();
  try {
    const d = await api('GET', '/api/home');
    renderHome(d, el);
  } catch(e) {
    el.innerHTML = `<div class="loading">데이터를 불러오지 못했습니다<br><small>${e.message}</small></div>`;
  }
}

function renderHome(d, el) {
  const idx = d.indices || {};
  const kospi = idx.kospi || 0;
  const kpPct = idx.kospi_change_pct || 0;
  const kosdaq = idx.kosdaq || 0;
  const kdPct = idx.kosdaq_change_pct || 0;
  const sp = idx.sp500 || 0;
  const spPct = idx.sp500_change_pct || 0;
  const nd = idx.nasdaq || 0;
  const ndPct = idx.nasdaq_change_pct || 0;

  const phase = d.market_phase || 'close';
  const phaseLabel = { pre:'장 시작 전', open:'장중', close:'장 마감', weekend:'주말' }[phase] || '장 마감';

  const analysis = Array.isArray(d.analysis) ? d.analysis : [];
  const forecast = d.forecast || {};
  const investor = Array.isArray(d.investor) ? d.investor : [];
  const investorHtml = buildInvestorSection(investor);

  const heroTitle = kpPct >= 1.5 ? '강한 상승장' : kpPct >= 0.3 ? '상승장' : kpPct <= -1.5 ? '하락장' : kpPct <= -0.3 ? '약세장' : '보합장';
  const heroIcon = kpPct >= 0 ? 'ti-trending-up' : 'ti-trending-down';

  let analysisHtml = '';
  const dotColors = ['dot-blue','dot-green','dot-orange'];
  (analysis.slice(0,3)).forEach((a, i) => {
    // analyze_us_impact 반환: {dot, label, text} 형식
    // text에 HTML이 포함될 수 있음
    const label = a.label || a.title || '분석';
    const text = a.text || a.content || '';
    // warn 텍스트가 text 안에 포함된 경우 처리
    analysisHtml += `
      <div class="analysis-item">
        <div class="analysis-label"><div class="dot ${dotColors[i]||'dot-blue'}"></div>${label}</div>
        <div class="analysis-text">${text}</div>
      </div>`;
  });
  if (!analysisHtml) {
    analysisHtml = `<div class="analysis-item"><div class="analysis-text">KOSPI ${fmtNum(kospi)} (${fmtPct(kpPct)}) · KOSDAQ ${fmtNum(kosdaq)} (${fmtPct(kdPct)})</div></div>`;
  }

  const fDir = forecast.direction_kor || (forecast.direction === 'up' ? '상승' : forecast.direction === 'down' ? '하락' : '횡보');
  const fTitle = forecast.short_title || fDir + ' 예상';
  const fConf = forecast.confidence || 55;
  const fReasons = Array.isArray(forecast.reasons) ? forecast.reasons : [];
  const fPoints = Array.isArray(forecast.points) ? forecast.points : [];

  let basisHtml = fReasons.slice(0,3).map(b => `<div class="forecast-item">${b}</div>`).join('');
  let pointsHtml = fPoints.slice(0,2).map(p => `<div class="forecast-item">${p}</div>`).join('');
  if (!basisHtml) basisHtml = `<div class="forecast-item">전일 미국 S&P500 ${fmtPct(spPct)} 참고</div>`;
  if (!pointsHtml) pointsHtml = `<div class="forecast-item">장 초반 외국인 매매 방향 확인</div>`;

  const fWarn = '예측은 참고용이며 투자 결정은 본인 판단으로 하세요';

  el.innerHTML = `
    <div class="hero">
      <div class="hero-badge"><i class="ti ${heroIcon}" style="font-size:13px;"></i>${heroTitle}</div>
      <div class="hero-status">KOSPI ${fmtNum(kospi)} ${kpPct>=0?'▲':'▼'} ${Math.abs(kpPct).toFixed(2)}%</div>
      <div class="hero-desc">KOSPI ${fmtPct(kpPct)} · KOSDAQ ${fmtPct(kdPct)} · S&P500 ${fmtPct(spPct)} / 나스닥 ${fmtPct(ndPct)}</div>
      <div class="hero-tip"><i class="ti ti-bulb" style="font-size:14px;flex-shrink:0;"></i>${forecast.tip||'보유 종목 동향을 확인하세요'}</div>
    </div>

    <div class="index-row">
      <div class="index-card ${kpPct>=0?'up-border':'down-border'} clickable" onclick="openIndexDetail('KOSPI')" style="cursor:pointer;">
        <div class="index-name">KOSPI <i class="ti ti-chevron-right" style="font-size:10px;color:#C7C7CC;"></i></div>
        <div class="index-val">${fmtNum(kospi)}</div>
        <div class="index-change ${pnlClass(kpPct)}">${kpPct>=0?'▲':'▼'} ${fmtPct(Math.abs(kpPct))}</div>
      </div>
      <div class="index-card ${kdPct>=0?'up-border':'down-border'} clickable" onclick="openIndexDetail('KOSDAQ')" style="cursor:pointer;">
        <div class="index-name">KOSDAQ <i class="ti ti-chevron-right" style="font-size:10px;color:#C7C7CC;"></i></div>
        <div class="index-val">${fmtNum(kosdaq)}</div>
        <div class="index-change ${pnlClass(kdPct)}">${kdPct>=0?'▲':'▼'} ${fmtPct(Math.abs(kdPct))}</div>
      </div>
      <div class="index-card ${spPct>=0?'up-border':'down-border'}">
        <div class="index-name">S&P500</div>
        <div class="index-val">${fmtNum(sp)}</div>
        <div class="index-change ${pnlClass(spPct)}">${spPct>=0?'▲':'▼'} ${fmtPct(Math.abs(spPct))}</div>
      </div>
      <div class="index-card ${ndPct>=0?'up-border':'down-border'}">
        <div class="index-name">나스닥</div>
        <div class="index-val">${fmtNum(nd)}</div>
        <div class="index-change ${pnlClass(ndPct)}">${ndPct>=0?'▲':'▼'} ${fmtPct(Math.abs(ndPct))}</div>
      </div>
    </div>

    <div class="section">
      <div class="sec-title"><i class="ti ti-search" style="font-size:15px;color:#5B5BD6;"></i>오늘 시장 분석</div>
      <div class="card">${analysisHtml}</div>
    </div>

    <div class="section">
      <div class="sec-title"><i class="ti ti-calendar" style="font-size:15px;color:#5B5BD6;"></i>내일 시장 예측</div>
      <div class="forecast-card clickable" onclick="openForecastDetail()" style="cursor:pointer;">
        <div class="forecast-header">
          <div class="forecast-title"><i class="ti ti-trending-up" style="color:#E24B4A;"></i>${fTitle}</div>
          <span class="confidence-badge">신뢰도 ${fConf}%</span>
        </div>
        <div class="progress-bg"><div class="progress-fill" style="width:${fConf}%;"></div></div>
        <div class="forecast-grid">
          <div>
            <div class="forecast-col-title"><i class="ti ti-pin" style="color:#E24B4A;font-size:12px;"></i>근거</div>
            ${basisHtml}
          </div>
          <div>
            <div class="forecast-col-title"><i class="ti ti-eye" style="color:#5B5BD6;font-size:12px;"></i>주목 포인트</div>
            ${pointsHtml}
          </div>
        </div>
        <div style="margin-top:8px;text-align:right;font-size:11px;color:#5B5BD6;font-weight:600;">
          자세한 분석 + 예측 히스토리 보기 <i class="ti ti-chevron-right" style="font-size:11px;"></i>
        </div>
      </div>
    </div>
    ${investorHtml}`;
}

function fmtInv(v, unit) {
  // unit: "억" | "만주" — 백엔드가 이미 해당 단위로 정규화해서 줌
  if (v === null || v === undefined || (Math.abs(v) < 0.01 && v !== 0)) return '—';
  const u = unit || '억';
  if (u === '억') {
    const abs = Math.abs(v);
    if (abs >= 10000) return (v/10000).toFixed(1) + '조';
    return v.toFixed(0) + '억';
  }
  // 만주
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '만주';
}
// 하위호환
function fmtEok(v) { return fmtInv(v, '억'); }

function buildInvestorSection(investor) {
  if (!investor || !investor.length) return '';
  const total5 = investor.reduce((acc, r) => ({
    foreign: acc.foreign + (r.foreign || 0),
    inst: acc.inst + (r.inst || 0),
  }), { foreign: 0, inst: 0 });
  const fDir = total5.foreign > 0 ? '순매수' : '순매도';
  const iDir = total5.inst > 0 ? '순매수' : '순매도';
  const fCls = total5.foreign > 0 ? 'up' : 'down';
  const iCls = total5.inst > 0 ? 'up' : 'down';

  const unit = investor[0]?.unit || '억';
  const rows = [...investor].reverse().map(r => {
    const fc = r.foreign > 0 ? 'up' : 'down';
    const ic = r.inst > 0 ? 'up' : 'down';
    const maxAbs = Math.max(...investor.map(x => Math.max(Math.abs(x.foreign||0), Math.abs(x.inst||0))), 1);
    const bw = Math.min(Math.abs(r.foreign||0)/maxAbs*70+5, 80);
    return `<div style="display:grid;grid-template-columns:44px 1fr 80px 80px;gap:4px;align-items:center;padding:8px 0;border-bottom:0.5px solid #F0F0F5;font-size:12px;">
      <span style="color:#8E8E9A;">${r.date.slice(5)}</span>
      <div style="height:5px;background:#F0F0F5;border-radius:3px;overflow:hidden;">
        <div style="height:5px;border-radius:3px;width:${bw}%;background:${(r.foreign||0)>=0?'rgba(226,75,74,0.4)':'rgba(24,95,165,0.3)'};"></div>
      </div>
      <span class="${fc}" style="text-align:right;font-weight:600;">${(r.foreign||0)>=0?'+':''}${fmtInv(r.foreign, unit)}</span>
      <span class="${ic}" style="text-align:right;font-weight:600;">${(r.inst||0)>=0?'+':''}${fmtInv(r.inst, unit)}</span>
    </div>`;
  }).join('');

  return `
    <div class="section">
      <div class="sec-title clickable" onclick="openSupplyDetail()" style="cursor:pointer;">
        <i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (5일)
        <i class="ti ti-chevron-right" style="font-size:13px;color:#C7C7CC;margin-left:auto;"></i>
      </div>
      <div class="card clickable" onclick="openSupplyDetail()" style="cursor:pointer;">
        <div style="display:flex;gap:10px;margin-bottom:12px;">
          <div style="flex:1;text-align:center;padding:10px 6px;background:#F8F8FA;border-radius:10px;">
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">외국인 5일 합계</div>
            <div class="${fCls}" style="font-size:17px;font-weight:700;">${total5.foreign>=0?'+':''}${fmtInv(total5.foreign, unit)}</div>
            <div class="${fCls}" style="font-size:11px;">${fDir}</div>
          </div>
          <div style="flex:1;text-align:center;padding:10px 6px;background:#F8F8FA;border-radius:10px;">
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">기관 5일 합계</div>
            <div class="${iCls}" style="font-size:17px;font-weight:700;">${total5.inst>=0?'+':''}${fmtInv(total5.inst, unit)}</div>
            <div class="${iCls}" style="font-size:11px;">${iDir}</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:44px 1fr 80px 80px;gap:4px;padding-bottom:6px;border-bottom:0.5px solid #E5E5EA;font-size:10px;color:#8E8E9A;">
          <span>날짜</span><span>추세</span><span style="text-align:right;">외국인(${unit})</span><span style="text-align:right;">기관(${unit})</span>
        </div>
        ${rows}
        <div style="text-align:center;margin-top:10px;font-size:11px;color:#5B5BD6;font-weight:600;">
          25일 상세 보기 <i class="ti ti-arrow-right" style="font-size:11px;"></i>
        </div>
      </div>
    </div>`;
}

// ─────────────────────────────────────────────────────────
// 시황 탭
// ─────────────────────────────────────────────────────────
function buildGaugeSVG(score, color, label) {
  const cx = 150, cy = 148, ro = 118, ri = 76;
  // score → 각도: score=0이면 180°(왼쪽), score=100이면 0°(오른쪽), score=50이면 90°(위)
  function pt(s, r) {
    const a = Math.PI * (1 - s / 100);
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  }
  function seg(s1, s2, clr) {
    const [x1o, y1o] = pt(s1, ro), [x2o, y2o] = pt(s2, ro);
    const [x1i, y1i] = pt(s1, ri), [x2i, y2i] = pt(s2, ri);
    const lg = (s2 - s1) > 50 ? 1 : 0;
    return `<path d="M${x1o.toFixed(1)},${y1o.toFixed(1)} A${ro},${ro} 0 ${lg},1 ${x2o.toFixed(1)},${y2o.toFixed(1)} L${x2i.toFixed(1)},${y2i.toFixed(1)} A${ri},${ri} 0 ${lg},0 ${x1i.toFixed(1)},${y1i.toFixed(1)}Z" fill="${clr}" opacity="0.9"/>`;
  }
  const segments = [[0,20,'#27500A'],[20,40,'#5B5BD6'],[40,60,'#8E8E9A'],[60,80,'#F5A623'],[80,100,'#E24B4A']];
  const segs = segments.map(([s1,s2,c]) => seg(s1+1.5, s2-1.5, c)).join('');
  // 바늘
  const [nx, ny] = pt(score, 92);
  // 활성 세그먼트 위에 하이라이트
  const activeColor = segments.find(([s1,s2]) => score >= s1 && score <= s2)?.[2] || color;
  return `<svg viewBox="0 0 300 190" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:300px;display:block;margin:0 auto;">
    <!-- 배경 트랙 -->
    <path d="M${cx-ro},${cy} A${ro},${ro} 0 0,1 ${cx+ro},${cy}" fill="none" stroke="#F0F0F5" stroke-width="${ro-ri}"/>
    <!-- 컬러 세그먼트 -->
    ${segs}
    <!-- 바늘 -->
    <line x1="${cx}" y1="${cy}" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="${activeColor}" stroke-width="3.5" stroke-linecap="round"/>
    <!-- 중앙 허브 -->
    <circle cx="${cx}" cy="${cy}" r="11" fill="${activeColor}"/>
    <circle cx="${cx}" cy="${cy}" r="5.5" fill="white"/>
    <!-- 점수 텍스트 -->
    <text x="${cx}" y="${cy-28}" text-anchor="middle" font-size="36" font-weight="800" fill="${activeColor}" font-family="-apple-system,BlinkMacSystemFont,sans-serif">${score}</text>
    <text x="${cx}" y="${cy+28}" text-anchor="middle" font-size="15" font-weight="700" fill="#1C1C1E" font-family="-apple-system,BlinkMacSystemFont,sans-serif">${label}</text>
    <!-- 양끝 레이블 -->
    <text x="16" y="${cy+12}" text-anchor="middle" font-size="10" fill="#8E8E9A" font-family="-apple-system,sans-serif">공포</text>
    <text x="284" y="${cy+12}" text-anchor="middle" font-size="10" fill="#8E8E9A" font-family="-apple-system,sans-serif">탐욕</text>
  </svg>`;
}

let _newsLoaded = false;
async function loadNews(force) {
  if (_newsLoaded && !force) return;
  _newsLoaded = true;
  const el = document.getElementById('news-content');
  if (force) {
    el.innerHTML = '<div class="loading"><div class="spinner"></div> 시황 새로고침 중...</div>';
  } else {
    el.innerHTML = '<div class="loading"><div class="spinner"></div> 시황 분석 중...</div>';
  }
  try {
    const url = force ? '/api/sentiment?force=true' : '/api/sentiment';
    const d = await api('GET', url, null, 120000);
    renderSentiment(d);
  } catch(e) {
    el.innerHTML = `<div class="loading" style="flex-direction:column;gap:8px;">
      <span>시황을 불러오지 못했습니다</span>
      <button class="btn-secondary" style="margin-top:8px;" onclick="loadNews(true)">다시 시도</button>
    </div>`;
  }
}

function renderSentiment(d) {
  const el = document.getElementById('news-content');
  const s = d.sentiment || {};
  const score = s.score ?? 50;
  const label = s.label || '중립';
  const color = s.color || '#8E8E9A';
  const factorDetails = s.factor_details || [];

  const gaugeSVG = buildGaugeSVG(score, color, label);

  const detailMap = [
    { min:75, title:'극단적 탐욕 — 조심할 때예요', body:'시장 참여자 대부분이 낙관적이에요. 주가가 실제 가치보다 높게 형성되는 경우가 많으니 신규 매수보다는 보유 종목 수익 실현을 고려해보세요.' },
    { min:60, title:'탐욕 — 시장이 달아오르고 있어요', body:'투자자들이 적극적으로 매수에 나서고 있어요. 상승 모멘텀이 유지되고 있지만 과열 구간 진입 전 분할 매도로 수익을 일부 챙기는 전략을 고려해보세요.' },
    { min:40, title:'중립 — 균형 잡힌 시장이에요', body:'시장이 뚜렷한 방향 없이 보합세를 보이고 있어요. 관심 종목을 차분히 분석하고 매수 기회를 탐색하기 좋은 시기예요.' },
    { min:25, title:'공포 — 투자자들이 불안해하고 있어요', body:'시장 참여자들이 손실을 두려워하며 매도하고 있어요. 하지만 이런 공포 구간이 종종 좋은 매수 기회가 됐어요. 우량 종목 위주로 분할 매수를 검토해보세요.' },
    { min:0,  title:'극단적 공포 — 패닉 상태예요', body:'시장이 극도의 공포 상태예요. 단기 변동성이 크지만 역사적으로 극단적 공포 구간 이후 강한 반등이 나온 경우가 많았어요.' },
  ];
  const detail = detailMap.find(x => score >= x.min) || detailMap[detailMap.length-1];

  // 8요소 분해 표 (sub_score 0~100 기준)
  const factorHtml = factorDetails.length ? factorDetails.map(f => {
    const sub = f.sub_score ?? 50;
    // sub_score: 0~40=공포(파랑), 40~60=중립(회색), 60~100=탐욕(주황~빨강)
    const barColor = sub >= 60 ? '#F5A623' : sub <= 40 ? '#5B5BD6' : '#8E8E9A';
    const ic = f.direction === 'up' ? '#E24B4A' : f.direction === 'down' ? '#5B5BD6' : '#8E8E9A';
    const arrow = f.direction === 'up' ? '▲' : f.direction === 'down' ? '▼' : '–';
    return `<div style="padding:7px 0;border-bottom:0.5px solid #F5F5F7;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <div style="flex:1;font-size:12px;color:#1C1C1E;font-weight:500;">${f.name}</div>
        <div style="font-size:11px;color:${ic};font-weight:700;">${arrow} ${f.value||''}</div>
        <div style="font-size:11px;font-weight:700;color:${barColor};min-width:28px;text-align:right;">${sub}</div>
      </div>
      <div style="height:4px;background:#F0F0F5;border-radius:2px;overflow:hidden;">
        <div style="height:100%;width:${sub}%;background:${barColor};border-radius:2px;transition:width .4s;"></div>
      </div>
      ${f.desc ? `<div style="font-size:10px;color:#C7C7CC;margin-top:3px;">${f.desc}</div>` : ''}
    </div>`;
  }).join('') : '';

  // 환율
  const fx = d.fx || [];
  const fxHtml = fx.length ? fx.map(f => {
    const up = f.change_pct >= 0;
    const cls = up ? 'up' : 'down';
    return `<div style="flex:1;text-align:center;">
      <div style="font-size:11px;color:#8E8E9A;margin-bottom:3px;">${f.name}</div>
      <div style="font-size:15px;font-weight:700;color:#1C1C1E;">${f.price?.toLocaleString()}</div>
      <div style="font-size:11px;class:${cls};color:${up?'#E24B4A':'#185FA5'};">${up?'+':''}${f.change_pct?.toFixed(2)}%</div>
    </div>`;
  }).join('<div style="width:1px;background:#F0F0F5;"></div>') : '';

  // 미국 선물
  const futures = d.us_futures || [];
  const futHtml = futures.length ? futures.map(f => {
    const up = f.change_pct >= 0;
    return `<div style="flex:1;text-align:center;">
      <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">${f.name}</div>
      <div style="font-size:14px;font-weight:700;color:#1C1C1E;">${f.price?.toLocaleString()}</div>
      <div style="font-size:11px;color:${up?'#E24B4A':'#185FA5'};">${up?'+':''}${f.change_pct?.toFixed(2)}%</div>
    </div>`;
  }).join('<div style="width:1px;background:#F0F0F5;"></div>') : '';

  // 업종별 등락
  const sectors = d.sectors || [];
  const secHtml = sectors.length ? sectors.map(s2 => {
    const up = s2.pct >= 0;
    return `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:0.5px solid #F5F5F7;">
      <div style="flex:1;font-size:13px;color:#1C1C1E;">${s2.name}</div>
      <div style="font-size:13px;font-weight:700;color:${up?'#E24B4A':'#185FA5'};">${up?'+':''}${s2.pct?.toFixed(2)}%</div>
    </div>`;
  }).join('') : '<div style="font-size:13px;color:#8E8E9A;padding:10px 0;">데이터 없음</div>';

  // 순매수 TOP5
  const nb = d.net_buy || {};
  function netBuyRows(list) {
    if (!list || !list.length) return '<div style="font-size:12px;color:#8E8E9A;padding:8px 0;">데이터 없음</div>';
    return list.map((item, i) => `
      <div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:0.5px solid #F5F5F7;">
        <div style="width:18px;font-size:11px;color:#8E8E9A;font-weight:700;">${i+1}</div>
        <div style="flex:1;font-size:13px;color:#1C1C1E;">${item.name}</div>
        <div style="font-size:12px;font-weight:700;color:#E24B4A;">+${item.value_str}</div>
      </div>`).join('');
  }

  // 거래대금 상위
  const topVol = d.top_volume || [];
  const volHtml = topVol.length ? topVol.map((item, i) => {
    const up = item.change_pct >= 0;
    return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:0.5px solid #F5F5F7;">
      <div style="width:18px;font-size:11px;color:#8E8E9A;font-weight:700;">${i+1}</div>
      <div style="flex:1;font-size:13px;color:#1C1C1E;">${item.name}</div>
      <div style="font-size:11px;color:${up?'#E24B4A':'#185FA5'};min-width:44px;text-align:right;">${up?'+':''}${item.change_pct?.toFixed(1)}%</div>
      <div style="font-size:11px;color:#8E8E9A;min-width:36px;text-align:right;">${item.value_str}</div>
    </div>`;
  }).join('') : '<div style="font-size:12px;color:#8E8E9A;padding:8px 0;">데이터 없음</div>';

  const secLabel = (title) => `<div style="font-size:13px;font-weight:700;color:#1C1C1E;margin:16px 0 8px;">${title}</div>`;

  el.innerHTML = `
    <!-- 업데이트 시간 + 새로고침 -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin:12px 0 8px;">
      <div>
        <span style="font-size:11px;color:#8E8E9A;">${d.market_note||''}</span>
        ${d.base_date ? `<span style="font-size:11px;color:#C7C7CC;margin-left:4px;">· ${d.base_date}</span>` : ''}
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        ${d.updated_at ? `<span style="font-size:11px;color:#C7C7CC;">업데이트 ${d.updated_at}</span>` : ''}
        <button onclick="_newsLoaded=false;loadNews(true);" style="display:flex;align-items:center;gap:3px;background:none;border:none;cursor:pointer;padding:4px 8px;border-radius:8px;background:#F2F2F7;">
          <i class="ti ti-refresh" style="font-size:14px;color:#5B5BD6;"></i>
          <span style="font-size:11px;color:#5B5BD6;font-weight:600;">새로고침</span>
        </button>
      </div>
    </div>
    <!-- 투자심리 지수 -->
    <div class="card" style="margin:0 0 10px;">
      <div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:4px;">
        <span style="font-size:13px;color:#8E8E9A;">투자심리 지수</span>
        <button onclick="showSentimentInfo()" style="width:18px;height:18px;border-radius:50%;background:#F0F0F5;border:none;cursor:pointer;font-size:11px;font-weight:700;color:#8E8E9A;line-height:18px;padding:0;display:flex;align-items:center;justify-content:center;">?</button>
      </div>
      ${gaugeSVG}
      <div style="border-top:1px solid #F0F0F5;padding-top:12px;margin-top:10px;">
        <div style="font-size:13px;font-weight:700;color:#1C1C1E;margin-bottom:4px;">${detail.title}</div>
        <div style="font-size:12px;color:#8E8E9A;line-height:1.7;margin-bottom:12px;">${detail.body}</div>
        ${factorHtml ? `<div style="font-size:11px;font-weight:600;color:#8E8E9A;margin-bottom:6px;">구성 지표 (8개)</div>${factorHtml}` : ''}
      </div>
    </div>

    <!-- 환율 -->
    ${fxHtml ? `${secLabel('환율')}
    <div class="card" style="margin-bottom:10px;">
      <div style="display:flex;align-items:stretch;gap:0;">${fxHtml}</div>
    </div>` : ''}

    <!-- 미국 선물 -->
    ${futHtml ? `${secLabel('미국 선물')}
    <div class="card" style="margin-bottom:10px;">
      <div style="display:flex;align-items:stretch;gap:0;">${futHtml}</div>
    </div>` : ''}

    <!-- 업종별 등락 -->
    ${secLabel('업종별 등락')}
    <div class="card" style="margin-bottom:10px;">${secHtml}</div>

    <!-- 외국인·기관 순매수 TOP5 -->
    ${secLabel('외국인 순매수 TOP 5')}
    <div class="card" style="margin-bottom:10px;">${netBuyRows(nb.foreign)}</div>
    ${secLabel('기관 순매수 TOP 5')}
    <div class="card" style="margin-bottom:10px;">${netBuyRows(nb.institution)}</div>

    <!-- 거래대금 상위 -->
    ${secLabel('거래대금 상위 5')}
    <div class="card" style="margin-bottom:24px;">${volHtml}</div>
  `;
}

// ─────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────
// 수급 상세 화면
// ─────────────────────────────────────────────────────────
async function openSupplyDetail() {
  _currentTab = 'home';
  showScreen('supply-detail');
  const el = document.getElementById('supply-detail-content');
  el.innerHTML = '<div class="loading" style="padding:40px;"><div class="spinner"></div> 수급 데이터 불러오는 중...</div>';
  try {
    const d = await api('GET', '/api/supply');
    renderSupplyDetail(d, el);
  } catch(e) {
    el.innerHTML = `<div style="padding:24px;color:#8E8E9A;">수급 데이터를 불러오지 못했습니다.<br>${e.message}</div>`;
  }
}

function renderSupplyDetail(d, el) {
  const rows = Array.isArray(d.rows) ? d.rows : [];
  const unit = d.unit || '억';
  const tf = d.total_foreign || 0;
  const ti = d.total_inst || 0;
  const bdf = d.buy_days_foreign || 0;
  const bdi = d.buy_days_inst || 0;
  const bothBuy = d.both_buy || 0;
  const bothSell = d.both_sell || 0;
  const sf = d.streak_foreign || 0;
  const si = d.streak_inst || 0;
  const days = d.days || rows.length;

  const maxAbs = Math.max(...rows.map(r => Math.max(Math.abs(r.foreign), Math.abs(r.inst))), 1);

  function buildTabContent(tab) {
    // 탭별 메타
    const total = tab === 'inst' ? ti : tf;
    const streak = tab === 'inst' ? si : sf;
    const buyDays = tab === 'inst' ? bdi : bdf;
    const label = tab === 'inst' ? '기관' : tab === 'both' ? '동반' : '외국인';

    // 요약 카드
    const summaryHtml = tab === 'both'
      ? `<div class="summary-row">
          <div class="sum-card"><div class="sum-label">동반 매수일</div><div class="sum-val" style="color:#3C3489;">${bothBuy}일</div></div>
          <div class="sum-card"><div class="sum-label">동반 매도일</div><div class="sum-val" style="color:#8E8E9A;">${bothSell}일</div></div>
          <div class="sum-card"><div class="sum-label">전체 기간</div><div class="sum-val" style="color:#3C3C43;">${days}일</div></div>
        </div>`
      : `<div class="summary-row">
          <div class="sum-card"><div class="sum-label">${days}일 순매수</div><div class="sum-val ${total>=0?'up':'down'}">${total>=0?'+':''}${fmtInv(total,unit)}</div></div>
          <div class="sum-card"><div class="sum-label">연속 ${streak>=0?'매수':'매도'}일</div><div class="sum-val" style="color:#3C3489;">${Math.abs(streak)}일</div></div>
          <div class="sum-card"><div class="sum-label">매수 우위일</div><div class="sum-val up">${buyDays}일</div></div>
        </div>`;

    // 바 차트
    const barCols = rows.map(r => {
      const val = tab === 'inst' ? r.inst : r.foreign;
      const h = Math.min(Math.abs(val) / maxAbs * 90, 90);
      const isUp = val >= 0;
      const label2 = r.date.slice(5);
      return `<div class="bar-col">
        ${isUp ? `<div class="bar-up" style="height:${h}px;background:rgba(226,75,74,${0.3+h/90*0.5});"></div>` : `<div style="flex:1;"></div>`}
        <div class="zero-line"></div>
        ${!isUp ? `<div class="bar-down" style="height:${h}px;background:rgba(24,95,165,${0.3+h/90*0.4});"></div>` : ''}
        <div class="bar-label">${label2}</div>
      </div>`;
    });

    // 상세 테이블 (최근 8일)
    const singleGrid = 'grid-template-columns:44px 1fr auto';
    const tableRows = [...rows].reverse().slice(0, 8).map(r => {
      const fv = r.foreign, iv = r.inst;
      const activeVal = tab === 'inst' ? iv : fv;
      const fCls = fv >= 0 ? 'up' : 'down';
      const iCls = iv >= 0 ? 'up' : 'down';
      const barW = Math.min(Math.max(Math.abs(activeVal) / maxAbs * 80, 5), 80);
      const barCls = activeVal >= 0 ? 'bar-buy' : 'bar-sell';
      const fCell = tab === 'inst' ? '' : `<span class="${fCls}" style="text-align:right;font-weight:600;">${fv>=0?'+':''}${fmtInv(fv,unit)}</span>`;
      const iCell = tab === 'foreign' ? '' : `<span class="${iCls}" style="text-align:right;font-weight:600;">${iv>=0?'+':''}${fmtInv(iv,unit)}</span>`;
      const rowStyle = tab !== 'both' ? ` style="${singleGrid}"` : '';
      return `<div class="day-row"${rowStyle}>
        <span class="day-date">${r.date.slice(5)}</span>
        <div class="net-bar-bg"><div class="net-bar ${barCls}" style="width:${barW}%;"></div></div>
        ${fCell}${iCell}
      </div>`;
    }).join('');

    // 스트릭 박스 (동반 탭 제외)
    let streakBox = '';
    if (tab !== 'both') {
      if (streak > 0) {
        const strength = streak >= 10 ? '강한 매집 신호' : streak >= 5 ? '지속 매집 중' : '매수 흐름';
        streakBox = `<div class="streak-box">
          <div class="streak-icon"><i class="ti ti-flame" style="font-size:20px;"></i></div>
          <div><div class="streak-title">${label} ${streak}일 연속 순매수 중</div><div class="streak-sub">누적 ${total>=0?'+':''}${fmtInv(total,unit)} · ${strength}</div></div>
        </div>`;
      } else if (streak < 0) {
        const warn = streak <= -5 ? '이탈 흐름 · 주의 필요' : streak <= -3 ? '매도 지속 · 관찰 필요' : '단기 매도 흐름';
        streakBox = `<div class="streak-box" style="background:#FCEBEB;">
          <div class="streak-icon" style="background:#E24B4A;"><i class="ti ti-trending-down" style="font-size:20px;"></i></div>
          <div><div class="streak-title" style="color:#A32D2D;">${label} ${Math.abs(streak)}일 연속 순매도 중</div><div class="streak-sub" style="color:#791F1F;">${warn}</div></div>
        </div>`;
      } else {
        streakBox = `<div class="streak-box" style="background:#F0F0F5;">
          <div class="streak-icon" style="background:#8E8E9A;"><i class="ti ti-minus" style="font-size:20px;"></i></div>
          <div><div class="streak-title" style="color:#3C3C43;">${label} 방향 혼조</div><div class="streak-sub" style="color:#6B6B8A;">누적 ${total>=0?'+':''}${fmtInv(total,unit)} · 뚜렷한 방향성 없음</div></div>
        </div>`;
      }
    }

    const tableHeader = tab === 'both'
      ? `<div class="day-header"><span>날짜</span><span>외국인</span><span style="text-align:right;">기관</span><span style="text-align:right;">동반</span></div>`
      : tab === 'inst'
        ? `<div class="day-header" style="${singleGrid}"><span>날짜</span><span>추세</span><span style="text-align:right;">기관</span></div>`
        : `<div class="day-header" style="${singleGrid}"><span>날짜</span><span>추세</span><span style="text-align:right;">외국인</span></div>`;

    return `
      ${summaryHtml}
      <div class="chart-area">
        <div class="chart-title"><i class="ti ti-chart-bar" style="font-size:14px;color:#5B5BD6;"></i>일별 ${label} 순매수</div>
        <div class="bar-chart">${barCols.join('')}</div>
        <div class="legend-row">
          <div class="legend-item"><div class="legend-dot" style="background:rgba(226,75,74,0.6);"></div>순매수</div>
          <div class="legend-item"><div class="legend-dot" style="background:rgba(24,95,165,0.4);"></div>순매도</div>
        </div>
      </div>
      ${streakBox}
      <div class="section">
        <div class="sec-title"><i class="ti ti-list-details" style="font-size:15px;color:#5B5BD6;"></i>일별 상세 (최근 8일)</div>
        <div class="card">
          ${tableHeader}
          ${tableRows}
        </div>
      </div>`;
  }

  el.innerHTML = `
    <div style="padding:14px 16px 10px;background:#fff;border-bottom:0.5px solid #E5E5EA;">
      <div style="font-size:14px;font-weight:700;">외국인·기관 수급 흐름</div>
      <div style="font-size:11px;color:#8E8E9A;margin-top:2px;">KOSPI ${days}일 기준</div>
    </div>

    <div class="tab-row" style="display:flex;padding:10px 16px;gap:6px;background:#fff;border-bottom:0.5px solid #E5E5EA;">
      <button id="tab-foreign" class="tab active" onclick="switchSupplyTab('foreign')">외국인</button>
      <button id="tab-inst" class="tab inactive" onclick="switchSupplyTab('inst')">기관</button>
      <button id="tab-both" class="tab inactive" onclick="switchSupplyTab('both')">동반매수</button>
    </div>

    <div id="supply-tab-content">
      ${buildTabContent('foreign')}
    </div>

    <div class="section">
      <div class="sec-title"><i class="ti ti-calculator" style="font-size:15px;color:#5B5BD6;"></i>누적 현황 (${days}일)</div>
      <div class="cumul-row">
        <div class="cumul-card"><div class="cumul-label">외국인 누적</div><div class="cumul-val ${tf>=0?'up':'down'}">${tf>=0?'+':''}${fmtInv(tf,unit)}</div><div class="cumul-sub">매수 우위 ${bdf}일</div></div>
        <div class="cumul-card"><div class="cumul-label">기관 누적</div><div class="cumul-val ${ti>=0?'up':'down'}">${ti>=0?'+':''}${fmtInv(ti,unit)}</div><div class="cumul-sub">매수 우위 ${bdi}일</div></div>
        <div class="cumul-card"><div class="cumul-label">동반 매수일</div><div class="cumul-val" style="color:#3C3489;">${bothBuy}일</div><div class="cumul-sub">전체의 ${Math.round(bothBuy/days*100)}%</div></div>
        <div class="cumul-card"><div class="cumul-label">동반 매도일</div><div class="cumul-val" style="color:#8E8E9A;">${bothSell}일</div><div class="cumul-sub">전체의 ${Math.round(bothSell/days*100)}%</div></div>
      </div>
    </div>

    ${d.advice ? `<div class="advice-box">
      <div class="advice-title"><i class="ti ti-bulb" style="font-size:15px;"></i>시스템 판단</div>
      <div class="advice-text">${d.advice}</div>
    </div>` : ''}
    <div style="height:24px;"></div>`;

  window.switchSupplyTab = function(tab) {
    ['foreign','inst','both'].forEach(t => {
      const btn = document.getElementById('tab-'+t);
      if (btn) { btn.className = 'tab ' + (t===tab?'active':'inactive'); }
    });
    document.getElementById('supply-tab-content').innerHTML = buildTabContent(tab);
  };
}

// 예측 상세 + 히스토리
// ─────────────────────────────────────────────────────────
async function openForecastDetail() {
  _currentTab = 'home';
  showScreen('forecast-detail');
  const el = document.getElementById('forecast-detail-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 예측 분석 중...</div>';
  try {
    const d = await api('GET', '/api/forecast/detail');
    renderForecastDetail(d, el);
  } catch(e) {
    el.innerHTML = `<div class="loading">데이터를 불러오지 못했습니다</div>`;
  }
}

function renderForecastDetail(d, el) {
  const forecast = d.forecast || {};
  const history  = Array.isArray(d.history) ? d.history : [];
  const stats    = d.stats || {};

  const fDir   = forecast.direction_kor || '횡보';
  const fTitle = forecast.short_title || fDir + ' 예상';
  const fConf  = forecast.confidence || 0;
  const fPct   = forecast.predicted_pct || 0;
  const isUp   = (forecast.direction || '') === 'up';
  const isDown = (forecast.direction || '') === 'down';
  const dirColor = isUp ? '#E24B4A' : isDown ? '#185FA5' : '#BA7517';
  const dirIcon  = isUp ? 'ti-trending-up' : isDown ? 'ti-trending-down' : 'ti-minus';

  // 근거 + 주목 포인트
  const reasons = Array.isArray(forecast.reasons) ? forecast.reasons : [];
  const points  = Array.isArray(forecast.points)  ? forecast.points  : [];

  const reasonsHtml = reasons.map(r =>
    `<div style="padding:10px 12px;background:#F8F8FA;border-radius:10px;font-size:13px;color:#3C3C43;line-height:1.6;margin-bottom:8px;">
      <i class="ti ti-circle-dot" style="color:${dirColor};font-size:12px;margin-right:4px;"></i>${r}
    </div>`
  ).join('');

  const pointsHtml = points.map(p =>
    `<div style="padding:10px 12px;background:#F0F0FF;border-radius:10px;font-size:13px;color:#3C3C43;line-height:1.6;margin-bottom:8px;">
      <i class="ti ti-eye" style="color:#5B5BD6;font-size:12px;margin-right:4px;"></i>${p}
    </div>`
  ).join('');

  // 전체 Gemini 원문 (있으면)
  const fullText = forecast.full_gemini_text || '';
  const fullHtml = fullText ? `
    <div class="section">
      <div class="sec-title"><i class="ti ti-brain" style="font-size:15px;color:#5B5BD6;"></i>AI 전체 분석</div>
      <div class="card" style="font-size:13px;color:#3C3C43;line-height:1.8;white-space:pre-line;">${fullText}</div>
    </div>` : '';

  // 예측 히스토리
  const dirIcon2 = {up:'▲', down:'▼', sideways:'➡'};
  const dirClr2  = {up:'#E24B4A', down:'#185FA5', sideways:'#BA7517'};
  const dirKor2  = {up:'상승', down:'하락', sideways:'횡보'};

  const accuracy = stats.accuracy;
  const evaluated = stats.evaluated || 0;
  const accHtml = accuracy !== null && accuracy !== undefined
    ? `<span style="font-size:16px;font-weight:700;color:#5B5BD6;">${accuracy}%</span>
       <span style="font-size:11px;color:#8E8E9A;margin-left:4px;">(${evaluated}회 검증)</span>`
    : `<span style="font-size:12px;color:#8E8E9A;">아직 검증 데이터 없음</span>`;

  const histRows = history.slice(0, 7).map(p => {
    const pd  = p.predicted_direction || '';
    const ad  = p.actual_direction;
    const pct = p.predicted_change || 0;
    const correct = p.is_correct;
    const predHtml = `<span style="color:${dirClr2[pd]||'#8E8E9A'};font-weight:600;">
      ${dirIcon2[pd]||'?'} ${dirKor2[pd]||'?'} (${pct>0?'+':''}${pct.toFixed(1)}%)
    </span>`;
    let resultBadge, actHtml = '';
    if (ad !== null && ad !== undefined) {
      resultBadge = correct
        ? `<span class="badge badge-buy" style="font-size:10px;">✓ 적중</span>`
        : `<span class="badge badge-sell" style="font-size:10px;">✗ 빗나감</span>`;
      const ac = p.actual_change || 0;
      actHtml = `<div style="font-size:11px;color:${dirClr2[ad]||'#8E8E9A'};margin-top:3px;">
        실제 ${dirIcon2[ad]||'?'} ${ac>0?'+':''}${ac.toFixed(1)}%
      </div>`;
    } else {
      resultBadge = `<span style="font-size:10px;color:#8E8E9A;">결과 대기</span>`;
    }
    return `<div style="display:flex;justify-content:space-between;align-items:flex-start;padding:10px 0;border-bottom:0.5px solid #F0F0F5;">
      <div>
        <div style="font-size:11px;color:#8E8E9A;margin-bottom:3px;">${p.date||''}</div>
        ${predHtml}
      </div>
      <div style="text-align:right;">${resultBadge}${actHtml}</div>
    </div>`;
  }).join('');

  const historyHtml = history.length ? `
    <div class="section">
      <div class="sec-title"><i class="ti ti-history" style="font-size:15px;color:#5B5BD6;"></i>예측 히스토리</div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:10px;border-bottom:0.5px solid #F0F0F5;margin-bottom:4px;">
          <span style="font-size:13px;font-weight:600;color:#1C1C1E;">누적 정확도</span>
          <div>${accHtml}</div>
        </div>
        ${histRows}
        <div style="margin-top:8px;font-size:10px;color:#8E8E9A;">최근 ${Math.min(history.length,7)}일 예측 기록 · 매일 자동 업데이트</div>
      </div>
    </div>` : '';

  el.innerHTML = `
    <div class="detail-hero">
      <div style="font-size:13px;opacity:0.8;margin-bottom:6px;">내일 KOSPI 예측</div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <i class="ti ${dirIcon}" style="font-size:28px;color:#fff;"></i>
        <div style="font-size:24px;font-weight:800;">${fTitle}</div>
      </div>
      <div style="font-size:15px;opacity:0.85;">예상 등락률 ${fPct>0?'+':''}${fPct.toFixed(1)}%</div>
      <div style="margin-top:12px;">
        <div style="font-size:11px;opacity:0.7;margin-bottom:6px;">신뢰도</div>
        <div style="background:rgba(255,255,255,0.2);border-radius:20px;height:8px;">
          <div style="width:${fConf}%;background:#fff;border-radius:20px;height:8px;"></div>
        </div>
        <div style="font-size:13px;margin-top:4px;opacity:0.9;">${fConf}%</div>
      </div>
    </div>

    <div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-pin" style="font-size:15px;color:#E24B4A;"></i>예측 근거</div>
      <div>${reasonsHtml || '<div class="card"><div class="analysis-text">데이터 수집 중...</div></div>'}</div>
    </div>

    <div class="section">
      <div class="sec-title"><i class="ti ti-eye" style="font-size:15px;color:#5B5BD6;"></i>내일 주목 포인트</div>
      <div>${pointsHtml || '<div class="card"><div class="analysis-text">데이터 수집 중...</div></div>'}</div>
    </div>

    ${fullHtml}
    ${historyHtml}

    <div style="padding:0 16px 8px;">
      <div class="warn-box"><i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>예측은 참고용이며 투자 결정은 본인 판단으로 하세요</div>
    </div>`;
}

// ─────────────────────────────────────────────────────────
// 지수 상세 (KOSPI / KOSDAQ)
// ─────────────────────────────────────────────────────────
async function openIndexDetail(name) {
  _currentTab = 'home';
  showScreen('index-detail');
  const el = document.getElementById('index-detail-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 분석 중...</div>';
  try {
    const d = await api('GET', `/api/index/${name}`);
    renderIndexDetail(d, el);
  } catch(e) {
    el.innerHTML = `<div class="loading">데이터를 불러오지 못했습니다</div>`;
  }
}

// ─────────────────────────────────────────────────────────
// 지표 용어 설명 모달
// ─────────────────────────────────────────────────────────
const _TERM_CONTENT = {
  rsi: {
    icon: '📊', title: 'RSI (상대강도지수)',
    what: 'RSI는 주식 시장에서 최근 14거래일 동안 "오른 날의 평균 상승폭"과 "내린 날의 평균 하락폭"을 비교해서 0~100 사이 숫자로 표현한 지표예요.\n\n쉽게 말하면 — "시장이 지금 얼마나 달아올랐거나, 얼마나 지쳐있는가"를 수치로 보여주는 온도계 같은 거예요.',
    levels: [
      { dot: '#E24B4A', text: 'RSI 70 이상 → 과열 구간. 사람들이 너무 흥분해서 계속 사고 있는 상태예요. 고무줄이 한쪽으로 너무 당겨진 것처럼 조정이 올 수 있어요.' },
      { dot: '#FF9F0A', text: 'RSI 50~70 → 상승 중인 정상 구간. 시장 분위기가 좋고 매수 압력이 강한 상태예요. 추세를 타고 있어요.' },
      { dot: '#5B5BD6', text: 'RSI 30~50 → 하락 중인 정상 구간. 관망하는 분위기거나 약한 하락 흐름이에요. 급격한 움직임은 없어요.' },
      { dot: '#185FA5', text: 'RSI 30 이하 → 과매도 구간. 사람들이 너무 팔아서 주가가 지나치게 내려온 상태예요. 반등 기회가 올 수 있어요.' },
    ],
  },
  disp: {
    icon: '📏', title: '이격도 (괴리율)',
    what: '이격도는 현재 주가가 20일 이동평균선(최근 20거래일 평균 가격)보다 얼마나 위아래로 벗어나 있는지 보여주는 지표예요.\n\n쉽게 말하면 — 주가가 평균값에서 얼마나 "멀어졌는가"를 %로 나타낸 거예요. 용수철처럼 너무 늘어나면 다시 돌아오려는 힘이 생겨요.',
    levels: [
      { dot: '#E24B4A', text: '이격도 110% 이상 → 강한 과열. 평균선보다 10% 이상 위에 있어요. 지금 사면 고점 매수 위험이 있어요.' },
      { dot: '#FF9F0A', text: '이격도 105~110% → 과열 주의. 상승세가 강하지만 조정이 올 수 있는 구간이에요.' },
      { dot: '#5B5BD6', text: '이격도 97~105% → 정상 범위. 평균선 근처에서 안정적으로 움직이는 건강한 상태예요.' },
      { dot: '#185FA5', text: '이격도 97% 이하 → 침체 구간. 평균선 아래에 있어요. 상대적으로 싸게 살 수 있는 구간일 수 있어요.' },
    ],
  },
  r5: {
    icon: '📈', title: '5일 누적 등락률',
    what: '최근 5거래일(약 1주일) 동안 지수가 얼마나 올랐거나 내렸는지를 보여주는 지표예요.\n\n쉽게 말하면 — "이번 주에 시장이 얼마나 빠르게 움직였나?"를 알려주는 속도계예요. 너무 빠르면 쉬어갈 수 있어요.',
    levels: [
      { dot: '#E24B4A', text: '+10% 이상 → 급등 피로. 한 주에 너무 많이 올랐어요. 차익 실현 매물이 나올 수 있어요.' },
      { dot: '#FF9F0A', text: '+5~10% → 강한 상승. 좋은 흐름이지만 눌림목(잠깐 조정)이 올 수 있어요.' },
      { dot: '#5B5BD6', text: '-5~+5% → 정상 범위. 큰 이슈 없이 안정적인 흐름이에요.' },
      { dot: '#185FA5', text: '-10% 이하 → 급락 과매도. 한 주에 너무 많이 내렸어요. 반등 기회가 올 수 있지만 추가 하락도 주의해야 해요.' },
    ],
  },
  vol: {
    icon: '📦', title: '거래량 (20일 평균비)',
    what: '오늘 거래량이 최근 20일 평균 거래량에 비해 얼마나 많은지를 배수로 나타낸 지표예요.\n\n쉽게 말하면 — 평소보다 얼마나 많은 사람이 사고팔았는지 보여줘요. 거래량이 많다는 건 "관심이 높다"는 신호예요.',
    levels: [
      { dot: '#E24B4A', text: '1.5배 이상 → 매우 활발. 평소보다 훨씬 많이 거래됐어요. 중요한 이슈가 있거나 큰 세력이 움직이는 신호일 수 있어요.' },
      { dot: '#5B5BD6', text: '0.8~1.5배 → 보통. 평소와 비슷한 수준이에요. 특이 신호 없이 평범한 하루예요.' },
      { dot: '#8E8E9A', text: '0.6배 이하 → 관망. 거래가 적어요. 눈치를 보며 기다리는 분위기예요. 방향성이 아직 결정 안 된 상태예요.' },
    ],
  },
};

function showTermModal(type, val, valStr, statusLabel) {
  const existing = document.getElementById('term-modal-overlay');
  if (existing) existing.remove();

  const content = _TERM_CONTENT[type];
  if (!content) return;

  const levelsHtml = content.levels.map(l => `
    <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:0.5px solid #F0F0F5;">
      <div style="width:10px;height:10px;border-radius:50%;background:${l.dot};flex-shrink:0;margin-top:4px;"></div>
      <div style="font-size:12px;color:#3C3C43;line-height:1.7;">${l.text}</div>
    </div>`).join('');

  const overlay = document.createElement('div');
  overlay.id = 'term-modal-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.45);z-index:9999;display:flex;align-items:flex-end;justify-content:center;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:22px 22px 0 0;width:100%;max-width:420px;max-height:82vh;overflow-y:auto;padding:20px 20px 36px;">
      <div style="width:36px;height:4px;background:#E5E5EA;border-radius:2px;margin:0 auto 16px;"></div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <span style="font-size:22px;">${content.icon}</span>
        <div>
          <div style="font-size:16px;font-weight:700;color:#1C1C1E;">${content.title}</div>
          <div style="font-size:12px;color:#8E8E9A;margin-top:2px;">현재값: ${valStr} → ${statusLabel}</div>
        </div>
      </div>
      <hr style="border:none;border-top:0.5px solid #F0F0F5;margin:12px 0;">
      <div style="font-size:13px;font-weight:600;color:#1C1C1E;margin-bottom:8px;">${content.title.split('(')[0].trim()}가 뭐예요?</div>
      <div style="font-size:13px;color:#3C3C43;line-height:1.8;white-space:pre-line;">${content.what}</div>
      <hr style="border:none;border-top:0.5px solid #F0F0F5;margin:14px 0 10px;">
      <div style="font-size:13px;font-weight:600;color:#1C1C1E;margin-bottom:4px;">숫자별로 어떤 의미예요?</div>
      ${levelsHtml}
      <button onclick="document.getElementById('term-modal-overlay').remove()" style="width:100%;margin-top:16px;padding:14px;background:#5B5BD6;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;cursor:pointer;">닫기</button>
    </div>`;
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function renderIndexDetail(d, el) {
  const name = d.name || 'KOSPI';
  const info = d.info || {};
  const ma   = d.ma   || {};
  const ex   = d.ex   || {};
  const investor = d.investor || [];
  const sectors  = d.sectors  || [];
  const analysis = d.analysis || [];

  const cur    = info.current || 0;
  const chg    = info.change  || 0;
  const chgPct = info.change_pct || 0;
  const isUp   = chgPct >= 0;
  const clr    = isUp ? '#E24B4A' : '#185FA5';
  const volB   = info.volume_billion || 0;

  // ── MA 값 ──
  const ma20v  = ma.ma20 || 0;
  const ma60v  = ma.ma60 || 0;
  const d20    = ma.ma20_dist_pct || 0;
  const d60    = ma.ma60_dist_pct || 0;
  const gc     = ma.golden_cross;
  const a20    = ma.above_ma20;
  const a60    = ma.above_ma60;
  const trend  = ma.trend || '';

  // 정배열 라벨
  const gcLabel = (a20 && a60 && gc) ? '완전 정배열' : gc ? '정배열' : '역배열';
  const gcSub   = gc ? '상승 모멘텀 강함' : '하락 압력 주의';
  const gcColor = gc ? '#3C3489' : '#791F1F';

  function maCard(label, val, dist, above) {
    if (!val) return `<div class="ma-card"><div class="ma-card-label">${label}</div><div class="ma-card-val" style="color:#C7C7CC;">집계중</div></div>`;
    const c = above ? '#E24B4A' : '#185FA5';
    const a = above ? '▲' : '▼';
    return `<div class="ma-card">
      <div class="ma-card-label">${label}</div>
      <div class="ma-card-val">${val.toLocaleString('ko-KR', {maximumFractionDigits:0})}</div>
      <div class="ma-card-sub" style="color:${c};">현재가 ${a} ${dist > 0 ? '+' : ''}${dist.toFixed(1)}%</div>
    </div>`;
  }

  // ── Extra metrics ──
  const rsi  = ex.rsi || null;
  const disp = ex.disparity_20 || 0;   // 이격도 (100=평균선)
  const r5   = ex.ret_5d || 0;          // 5일 수익률
  const vr   = ex.vol_ratio || 0;

  // RSI 상태
  const rsiW   = rsi ? Math.min(rsi, 100) : 50;
  const rsiStr = rsi ? rsi.toFixed(0) : '—';
  const rsiColor = rsi >= 70 ? '#BA7517' : rsi <= 30 ? '#3B6D11' : '#5B5BD6';
  const rsiLbl = rsi >= 70 ? '과열 주의' : rsi <= 30 ? '침체 구간' : '정상';
  const rsiCls = rsi >= 70 || rsi <= 30 ? 'status-warn' : 'status-ok';

  // 이격도 상태
  const dispStr = disp ? disp.toFixed(1) + '%' : '—';
  const dispLbl = disp >= 110 ? '강한 과열' : disp >= 108 ? '과열 주의' : disp > 0 && disp <= 97 ? '침체 구간' : '정상';
  const dispCls = disp >= 110 ? 'status-danger' : disp >= 108 || (disp > 0 && disp <= 97) ? 'status-warn' : 'status-ok';

  // 5일 수익률 상태
  const r5Str  = r5 ? (r5 > 0 ? '+' : '') + r5.toFixed(2) + '%' : '—';
  const r5Lbl  = r5 >= 10 ? '급등 피로' : r5 >= 5 ? '강한 상승' : r5 <= -10 ? '급락 과매도' : '정상';
  const r5Cls  = Math.abs(r5) >= 10 ? 'status-danger' : Math.abs(r5) >= 5 ? 'status-warn' : 'status-ok';
  const r5Color = r5 >= 0 ? '#E24B4A' : '#185FA5';

  // 거래량비
  const vrStr = vr ? vr.toFixed(1) + '배' : (volB ? volB.toFixed(1) + '조' : '—');
  const vrLbl = vr >= 1.5 ? '매우 활발' : vr >= 1.2 ? '활발' : vr > 0 && vr <= 0.6 ? '관망' : '보통';
  const vrCls = vr >= 1.2 ? 'status-ok' : vr > 0 && vr <= 0.6 ? 'status-warn' : 'status-ok';

  // ── 지표 해석 카드 (보라색) ──
  let rsiInterp = '', dispInterp = '', r5Interp = '';
  if (rsi) {
    if (rsi >= 70)      rsiInterp = `RSI ${rsi.toFixed(0)}으로 <b>과열 구간</b>이에요. 시장이 너무 달아올라 있어요. 지금 새로 사는 건 고점 매수 위험이 있으니 조정을 기다리세요.`;
    else if (rsi <= 30) rsiInterp = `RSI ${rsi.toFixed(0)}으로 <b>침체 구간</b>이에요. 시장이 많이 지쳐있는 상태예요. 분할 매수를 검토할 수 있지만 추가 하락 가능성도 있어요.`;
    else if (rsi >= 60) rsiInterp = `RSI ${rsi.toFixed(0)}으로 <b>정상이지만 약간 달아오르는 중</b>이에요. 추세는 좋으나 70에 가까워지면 속도를 조절하세요.`;
    else                rsiInterp = `RSI ${rsi.toFixed(0)}으로 <b>정상 범위</b>예요. 과열도 침체도 아닌 건강한 시장 상태예요.`;
  }
  if (disp) {
    const ma20_ref = cur / (disp / 100);
    const gap_p = (cur - ma20_ref).toFixed(0);
    if (disp >= 110)      dispInterp = `이격도 ${disp.toFixed(1)}%로 20일 평균선보다 <b>${(disp-100).toFixed(1)}% 위</b>에 있어요. 용수철이 많이 당겨진 상태로 조정이 오면 ${ma20_ref.toFixed(0)} 근처까지 내려올 수 있어요. 신규 진입은 신중하게 하세요.`;
    else if (disp >= 108) dispInterp = `이격도 ${disp.toFixed(1)}%로 <b>과열 주의</b> 구간이에요. 20일선에서 ${gap_p}p 올라와 있어요. 눌림목을 기다려서 진입하는 게 유리해요.`;
    else if (disp <= 97)  dispInterp = `이격도 ${disp.toFixed(1)}%로 20일선 아래에 있어요. <b>평균보다 싸게 살 수 있는 구간</b>이에요. 추세 반전 신호가 나오면 분할 매수를 고려해보세요.`;
    else                  dispInterp = `이격도 ${disp.toFixed(1)}%로 20일 평균선 <b>근처의 정상 범위</b>예요. 안정적인 흐름이에요.`;
  }
  if (r5) {
    if (r5 >= 10)      r5Interp = `최근 5일 <b>${r5Str} 급등</b>했어요. 단기 피로가 누적된 상태예요. 지금 추격 매수는 고점 매수가 될 가능성이 높아요. 조정을 기다려보세요.`;
    else if (r5 <= -10) r5Interp = `최근 5일 <b>${r5Str} 급락</b>했어요. 과매도 구간이에요. 하락 원인이 일시적이라면 분할 매수를 검토해볼 수 있어요.`;
    else if (r5 >= 5)   r5Interp = `최근 5일 <b>${r5Str} 상승</b>한 건 좋은 흐름이에요. 다만 속도가 빠른 편이니, 눌림목에서 나눠서 진입하는 전략이 안전해요.`;
    else if (r5 <= -5)  r5Interp = `최근 5일 <b>${r5Str} 하락</b>했어요. 단기 조정이 나오는 중이에요. 추세가 꺾인 건지 일시적 조정인지 확인이 필요해요.`;
    else                r5Interp = `최근 5일 <b>${r5Str}</b>으로 정상 등락 범위예요. 큰 이슈 없이 안정적인 흐름이에요.`;
  }

  // ── 외국인/기관 수급 ──
  let investorHtml = '';
  if (investor.length) {
    const invUnit = investor[0]?.unit || '억';
    const maxAbs = Math.max(...investor.map(x => Math.max(Math.abs(x.foreign||0), Math.abs(x.inst||0))), 1);
    const invRows = investor.slice().reverse().map(r => {
      const fCls = (r.foreign||0) >= 0 ? 'up' : 'down';
      const iCls = (r.inst||0) >= 0 ? 'up' : 'down';
      const bw = Math.min(Math.abs(r.foreign||0) / maxAbs * 70 + 10, 80);
      const bc = (r.foreign||0) >= 0 ? 'rgba(226,75,74,0.35)' : 'rgba(24,95,165,0.3)';
      return `<div class="day-row">
        <span class="day-date">${r.date.slice(5)}</span>
        <div class="net-bar-bg"><div class="net-bar" style="width:${bw}%;background:${bc};"></div></div>
        <span class="${fCls}" style="text-align:right;font-weight:600;">${(r.foreign||0)>=0?'+':''}${fmtInv(r.foreign,invUnit)}</span>
        <span class="${iCls}" style="text-align:right;font-weight:600;">${(r.inst||0)>=0?'+':''}${fmtInv(r.inst,invUnit)}</span>
      </div>`;
    }).join('');
    const totF = investor.reduce((s,r) => s + (r.foreign||0), 0);
    const totI = investor.reduce((s,r) => s + (r.inst||0), 0);
    investorHtml = `
      <div class="section">
        <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (5일)</div>
        <div class="card">
          <div style="display:flex;gap:8px;margin-bottom:12px;">
            <div style="flex:1;background:#F8F8FA;border-radius:10px;padding:10px 12px;text-align:center;">
              <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">외국인 합계</div>
              <div class="${totF>=0?'up':'down'}" style="font-size:16px;font-weight:700;">${totF>=0?'+':''}${fmtInv(totF,invUnit)}</div>
            </div>
            <div style="flex:1;background:#F8F8FA;border-radius:10px;padding:10px 12px;text-align:center;">
              <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">기관 합계</div>
              <div class="${totI>=0?'up':'down'}" style="font-size:16px;font-weight:700;">${totI>=0?'+':''}${fmtInv(totI,invUnit)}</div>
            </div>
          </div>
          <div class="day-header"><span>날짜</span><span>추세</span><span style="text-align:right;">외국인(${invUnit})</span><span style="text-align:right;">기관(${invUnit})</span></div>
          ${invRows}
        </div>
      </div>`;
  }

  // ── 섹터 ──
  let sectorHtml = '';
  if (sectors.length) {
    const maxPct = Math.max(...sectors.map(s => Math.abs(s.pct)), 1);
    const rows = sectors.map(s => {
      const cls = s.pct >= 0 ? 'up' : 'down';
      const bw  = Math.min(Math.abs(s.pct) / maxPct * 80, 80);
      const bc  = s.pct >= 0 ? '#E24B4A' : '#185FA5';
      return `<div class="sector-row">
        <span class="sector-name">${s.name}</span>
        <div class="sector-bar-wrap"><div class="sector-bar" style="width:${bw}%;background:${bc};"></div></div>
        <span class="sector-pct ${cls}">${s.pct >= 0 ? '▲ +' : '▼ '}${s.pct}%</span>
      </div>`;
    }).join('');
    sectorHtml = `
      <div class="section">
        <div class="sec-title"><i class="ti ti-building-store" style="font-size:15px;color:#5B5BD6;"></i>섹터별 등락률</div>
        <div class="card">${rows}</div>
      </div>`;
  }

  // ── AI 분석 ──
  let aiHtml = '';
  if (analysis.length) {
    const items = analysis.map(a => `
      <div style="padding:10px 0;border-bottom:0.5px solid #F0F0F5;">
        <div style="font-size:11px;font-weight:600;color:#3C3489;margin-bottom:5px;">${a.label||''}</div>
        <div style="font-size:13px;color:#3C3C43;line-height:1.7;">${a.text||''}</div>
      </div>`).join('');
    aiHtml = `
      <div class="advice-box" style="margin-top:4px;">
        <div class="advice-title"><i class="ti ti-brain" style="font-size:15px;"></i>AI 시장 분석</div>
        <div>${items}</div>
      </div>`;
  }

  el.innerHTML = `
    <!-- 히어로 -->
    <div class="detail-hero" style="background:linear-gradient(135deg,${isUp?'#C0392B,#E24B4A':'#0D4C8A,#185FA5'});">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <div style="font-size:11px;opacity:0.75;margin-bottom:4px;">${name === 'KOSPI' ? '코스피 종합지수' : '코스닥 종합지수'}</div>
          <div class="detail-name">${name}</div>
        </div>
        <span class="badge" style="background:rgba(255,255,255,0.2);color:#fff;font-size:11px;">${trend}</span>
      </div>
      <div class="detail-price" style="font-size:32px;">${cur.toLocaleString('ko-KR',{minimumFractionDigits:2,maximumFractionDigits:2})}</div>
      <div style="font-size:14px;margin-top:4px;opacity:0.9;">${isUp?'▲':'▼'} ${Math.abs(chg).toFixed(2)} (${isUp?'+':''}${chgPct.toFixed(2)}%)</div>
      ${volB ? `<div style="font-size:11px;opacity:0.65;margin-top:6px;">거래대금 ${volB.toFixed(1)}조</div>` : ''}
    </div>

    <!-- 이동평균선 현황 -->
    <div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>이동평균선 현황</div>
      <div class="ma-grid">
        ${maCard('20일선 (단기)', ma20v, d20, a20)}
        ${maCard('60일선 (중기)', ma60v, d60, a60)}
        <div class="ma-card" style="grid-column:span 2;">
          <div class="ma-card-label">정배열 상태</div>
          <div class="ma-card-val" style="color:${gcColor};">${gcLabel}</div>
          <div class="ma-card-sub" style="color:${gcColor};">${gcSub}</div>
        </div>
      </div>
    </div>

    <!-- 주요 기술 지표 (항목 클릭 → 설명 모달) -->
    <div class="section">
      <div class="sec-title"><i class="ti ti-chart-bar" style="font-size:15px;color:#5B5BD6;"></i>주요 기술 지표 <span style="font-size:10px;color:#8E8E9A;font-weight:400;">항목을 누르면 설명이 나와요</span></div>
      <div class="card">
        ${rsi ? `<div class="ind-row clickable" onclick="showTermModal('rsi',${rsiW},'${rsiStr}','${rsiLbl}')" style="cursor:pointer;">
          <span class="ind-label" style="color:#5B5BD6;text-decoration:underline dotted;">RSI (14일) <i class="ti ti-info-circle" style="font-size:11px;"></i></span>
          <div class="ind-right">
            <div class="rsi-bar-wrap"><div class="rsi-bar-fill" style="width:${rsiW}%;background:${rsiColor};"></div></div>
            <span class="ind-val">${rsiStr}</span>
            <span class="ind-status ${rsiCls}">${rsiLbl}</span>
          </div>
        </div>` : ''}
        ${disp ? `<div class="ind-row clickable" onclick="showTermModal('disp',${disp},'${dispStr}','${dispLbl}')" style="cursor:pointer;">
          <span class="ind-label" style="color:#5B5BD6;text-decoration:underline dotted;">이격도 (20일선) <i class="ti ti-info-circle" style="font-size:11px;"></i></span>
          <div class="ind-right"><span class="ind-val">${dispStr}</span><span class="ind-status ${dispCls}">${dispLbl}</span></div>
        </div>` : ''}
        ${r5 ? `<div class="ind-row clickable" onclick="showTermModal('r5',${r5},'${r5Str}','${r5Lbl}')" style="cursor:pointer;">
          <span class="ind-label" style="color:#5B5BD6;text-decoration:underline dotted;">5일 누적 등락률 <i class="ti ti-info-circle" style="font-size:11px;"></i></span>
          <div class="ind-right"><span class="ind-val" style="color:${r5Color};">${r5Str}</span><span class="ind-status ${r5Cls}">${r5Lbl}</span></div>
        </div>` : ''}
        <div class="ind-row clickable" onclick="showTermModal('vol',${vr||0},'${vrStr}','${vrLbl}')" style="cursor:pointer;">
          <span class="ind-label" style="color:#5B5BD6;text-decoration:underline dotted;">거래량 (20일 평균비) <i class="ti ti-info-circle" style="font-size:11px;"></i></span>
          <div class="ind-right"><span class="ind-val">${vrStr}</span><span class="ind-status ${vrCls}">${vrLbl}</span></div>
        </div>
      </div>
    </div>

    <!-- 지표 해석 카드 -->
    ${rsiInterp || dispInterp || r5Interp ? `<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:0 16px 12px;">
      <div style="font-size:12px;font-weight:700;color:#3C3489;margin-bottom:12px;display:flex;align-items:center;gap:6px;">
        <i class="ti ti-microscope" style="font-size:14px;"></i> 지금 이 숫자가 의미하는 것
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        ${rsiInterp ? `<div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">📊 RSI (상대강도지수)</div>
          <div style="font-size:12px;color:#3C3489;line-height:1.7;">${rsiInterp}</div>
        </div>` : ''}
        ${dispInterp ? `<div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">📏 이격도 (괴리율)</div>
          <div style="font-size:12px;color:#3C3489;line-height:1.7;">${dispInterp}</div>
        </div>` : ''}
        ${r5Interp ? `<div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">📈 5일 누적 등락률</div>
          <div style="font-size:12px;color:#3C3489;line-height:1.7;">${r5Interp}</div>
        </div>` : ''}
      </div>
    </div>` : ''}

    ${investorHtml}
    ${sectorHtml}
    <div style="height:24px;"></div>`;
}

// ─────────────────────────────────────────────────────────
// 뉴스 상세
// ─────────────────────────────────────────────────────────
async function openNewsDetail(idx) {
  const n = _allNews[idx];
  if (!n) return;
  _currentTab = 'news';
  showScreen('news-detail');
  const el = document.getElementById('news-detail-content');
  const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
  const lbl = n.sentiment === 'positive' ? '긍정' : n.sentiment === 'negative' ? '부정' : '혼조';
  const borderColor = n.sentiment === 'positive' ? '#185FA5' : n.sentiment === 'negative' ? '#E24B4A' : '#F0A500';

  const header = `
    <div style="padding:16px 16px 0;">
      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
        <span class="badge ${bdg}">${lbl}</span>
        ${n.category && n.category !== '전체' ? `<span class="badge badge-ok" style="font-size:11px;">${n.category}</span>` : ''}
        <span style="font-size:11px;color:#8E8E9A;margin-left:auto;">${n.source||''}</span>
        <span style="font-size:11px;color:#C7C7CC;">${n.published||''}</span>
      </div>
      <div style="font-size:17px;font-weight:700;color:#1C1C1E;line-height:1.5;margin-bottom:14px;border-left:3px solid ${borderColor};padding-left:10px;">${n.title||''}</div>
    </div>`;

  const linkBtn = n.link ? `<div style="padding:0 16px 20px;"><a href="${n.link}" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:center;gap:6px;padding:14px;background:#5B5BD6;border-radius:12px;color:#fff;font-size:14px;font-weight:600;text-decoration:none;"><i class="ti ti-external-link" style="font-size:15px;"></i> 원문 기사 전체 보기</a></div>` : '';

  // 로딩 상태 먼저 표시
  el.innerHTML = header + `<div style="padding:0 16px 16px;"><div class="loading" style="padding:24px;"><div class="spinner"></div> 기사 본문 불러오는 중...</div></div>` + linkBtn;

  // 본문 크롤링
  if (n.link) {
    try {
      const res = await api('GET', '/api/news/fetch-body?url=' + encodeURIComponent(n.link), null, 12000);
      const body = res.body || '';
      if (body && body.length > 50) {
        const bodyHtml = body.split('\n').filter(l => l.trim()).map(l => `<p style="margin:0 0 10px;">${l}</p>`).join('');
        el.innerHTML = header + `<div style="padding:0 16px 16px;"><div class="card" style="font-size:14px;color:#3C3C43;line-height:1.8;">${bodyHtml}</div></div>` + linkBtn;
      } else {
        // 본문 추출 실패 → summary로 폴백
        el.innerHTML = header + `<div style="padding:0 16px 16px;">${n.summary ? `<div class="card" style="font-size:14px;color:#3C3C43;line-height:1.8;">${n.summary}</div>` : '<div style="color:#8E8E9A;font-size:13px;">본문을 불러오지 못했어요. 원문 링크에서 확인하세요.</div>'}</div>` + linkBtn;
      }
    } catch(e) {
      el.innerHTML = header + `<div style="padding:0 16px 16px;">${n.summary ? `<div class="card" style="font-size:14px;color:#3C3C43;line-height:1.8;">${n.summary}</div>` : ''}</div>` + linkBtn;
    }
  } else {
    el.innerHTML = header + `<div style="padding:0 16px 16px;">${n.summary ? `<div class="card" style="font-size:14px;color:#3C3C43;line-height:1.8;">${n.summary}</div>` : ''}</div>`;
  }
}

function buildNewsAnalysisHtml(n) {
  if (!n.ai_summary) return '';

  // 관련 종목 칩
  const stocks = Array.isArray(n.related_stocks) ? n.related_stocks : [];
  const stocksHtml = stocks.length ? `
    <div style="padding:0 16px 10px;">
      <div style="font-size:10px;color:#8E8E9A;margin-bottom:5px;">관련 종목</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;">
        ${stocks.map(s => {
          const nm = typeof s === 'object' ? (s.name||'') : s;
          const tk = typeof s === 'object' ? (s.ticker||'') : '';
          return `<span class="badge badge-ok" style="font-size:11px;">${nm}${tk?` <span style="opacity:0.6;font-size:9px;">${tk}</span>`:''}</span>`;
        }).join('')}
      </div>
    </div>` : '';

  const strategyHtml = n.strategy ? `
    <div style="margin-top:12px;background:#FFFBF0;border:1px solid #F5E6B2;border-radius:14px;padding:16px;font-size:13px;line-height:1.9;color:#3C3C43;">
      <div style="font-size:12px;font-weight:700;color:#8B6914;margin-bottom:8px;display:flex;align-items:center;gap:5px;">
        <span>☀️</span> 투자 전략
      </div>
      ${n.strategy}
    </div>` : '';

  return `${stocksHtml}
    <div style="padding:0 16px 20px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
        <i class="ti ti-brain" style="font-size:15px;color:#5B5BD6;"></i>
        <span style="font-size:13px;font-weight:700;color:#1C1C1E;">AI 분석</span>
      </div>
      <div style="background:#F5F4FF;border:1px solid #E0DEFF;border-radius:14px;padding:16px;font-size:13px;line-height:1.9;color:#1C1C1E;">
        ${n.ai_summary}
      </div>
      ${strategyHtml}
    </div>`;
}

// ─────────────────────────────────────────────────────────
// 보유종목 탭
// ─────────────────────────────────────────────────────────
let _holdingsLoaded = false;
let _holdingsFilter = '전체';
async function refreshHoldingsPrices() {
  // 전체 재렌더 없이 현재가만 조용히 갱신
  if (!_allHoldings.length) return;
  try {
    const d = await api('GET', '/api/holdings');
    _allHoldings = d.holdings || [];
    renderHoldings();
    document.getElementById('holdings-date').textContent = nowStr();
  } catch(e) {}
}

async function refreshWatchlistPrices() {
  if (!_watchlistLoaded) return;
  try {
    const d = await api('GET', '/api/watchlist');
    renderWatchlistFromData(d);
  } catch(e) {}
}

async function loadHoldings(force) {
  if (_holdingsLoaded && !force) return;
  _holdingsLoaded = true;
  const el = document.getElementById('holdings-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 불러오는 중...</div>';
  document.getElementById('holdings-date').textContent = nowStr();
  try {
    const d = await api('GET', '/api/holdings');
    _allHoldings = d.holdings || [];
    const totalEl = document.getElementById('holdings-total');
    if (d.total_value) {
      totalEl.style.display = 'flex';
      totalEl.innerHTML = `
        <div><div class="total-label">총 평가금액</div><div class="total-amount">${fmtNum(d.total_value)}원</div></div>
        <div><div class="total-pnl-label">총 평가손익</div>
          <div class="total-pnl ${pnlClass(d.total_pnl)}">${fmtPnl(d.total_pnl)}원 (${fmtPct(d.total_pnl_pct)})</div></div>`;
    } else {
      totalEl.style.display = 'none';
    }
    renderHoldings();
  } catch(e) {
    el.innerHTML = `<div class="loading">불러오지 못했습니다</div>`;
  }
}

function filterHoldings(filter, btn) {
  _holdingsFilter = filter;
  document.querySelectorAll('#screen-holdings .tab').forEach(b => {
    b.className = 'tab ' + (b === btn ? 'active' : 'inactive');
  });
  renderHoldings();
}

function renderHoldings() {
  const all = _allHoldings;
  const profit  = all.filter(h => (h.pnl_pct || 0) >= 0);
  const loss    = all.filter(h => (h.pnl_pct || 0) < 0);
  const sellSig = all.filter(h => (h.badges||[]).some(b => b.type === 'sell' || b.type === 'warn'));

  let sections;
  if (_holdingsFilter === '수익')       sections = [['수익 중인 종목', profit]];
  else if (_holdingsFilter === '손실')  sections = [['손실 중인 종목', loss]];
  else if (_holdingsFilter === '매도신호') sections = [['매도신호 종목', sellSig]];
  else sections = [['수익 중인 종목', profit], ['손실 중인 종목', loss]];

  const el = document.getElementById('holdings-content');
  const hasAny = sections.some(([,items]) => items.length > 0);
  if (!hasAny) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-briefcase"></i>해당하는 종목이 없습니다</div>';
    return;
  }
  let html = '';
  for (const [lbl, items] of sections) {
    if (!items.length) continue;
    html += `<div class="section"><div class="sec-label">${lbl}</div>${items.map(holdingCard).join('')}</div>`;
  }
  el.innerHTML = html;
}
function holdingCard(h) {
  const pnlPct = h.pnl_pct || 0;
  const barWidth = Math.min(Math.abs(pnlPct) * 2, 100);
  const barColor = pnlPct >= 0 ? '#E24B4A' : '#185FA5';
  const rsi = h.rsi || 50;
  const gap20 = h.gap20 || 100;
  const cur = h.cur_price || h.avg_price;

  // RSI 색상
  const rsiColor = rsi >= 70 ? '#E24B4A' : rsi <= 30 ? '#185FA5' : rsi >= 60 ? '#BA7517' : '#3B6D11';

  // 지지선 거리 칩
  let supChips = '';
  if (h.ma20) {
    const d = (cur - h.ma20) / h.ma20 * 100;
    supChips += `<span class="sup-chip">20일선 <span class="${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span></span>`;
  }
  if (h.ma60) {
    const d = (cur - h.ma60) / h.ma60 * 100;
    supChips += `<span class="sup-chip">60일선 <span class="${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span></span>`;
  }
  if (h.boll_lower) {
    const d = (cur - h.boll_lower) / h.boll_lower * 100;
    supChips += `<span class="sup-chip">볼하단 <span class="${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span></span>`;
  }

  // 분석 배지 (최대 2개)
  const bdgMap = {sell:'badge-sell', warn:'badge-warn', buy:'badge-buy', ok:'badge-ok'};
  const badgesArr = Array.isArray(h.badges) ? h.badges : [];
  const badgesHtml = badgesArr.slice(0,2).map(b =>
    `<span class="badge ${bdgMap[b.type]||'badge-ok'}">${b.text}</span>`
  ).join('') || `<span class="badge ${pnlPct>=0?'badge-ok':'badge-sell'}">${pnlPct>=0?'수익 중':'손실 중'}</span>`;

  return `<div class="card" style="position:relative;" onclick="openHoldingDetail('${h.code}', '${h.name}')">
    <button onclick="event.stopPropagation();confirmDeleteHolding('${h.code}','${h.name.replace(/'/g,"\\'")}');"
      style="position:absolute;top:10px;right:10px;background:none;border:none;cursor:pointer;padding:2px;line-height:1;z-index:1;">
      <i class="ti ti-trash" style="font-size:16px;color:#8E8E9A;"></i>
    </button>
    <div class="card-top" style="padding-right:28px;">
      <div class="stock-icon ${iconColors(h.name)}">${iconText(h.name)}</div>
      <div>
        <div class="stock-name">${h.name}</div>
        <div class="stock-sub">평단 ${fmtNum(h.avg_price)}원 · ${h.qty}주</div>
      </div>
      <div class="stock-right">
        <div class="stock-price">${fmtNum(cur)}원</div>
        <div class="stock-change ${pnlClass(pnlPct)}">${pnlPct>=0?'▲':'▼'} ${fmtPct(Math.abs(pnlPct))}</div>
      </div>
    </div>
    <div class="mini-grid">
      <div class="mini-item"><div class="mini-label">평가손익</div><div class="mini-val ${pnlClass(h.pnl)}">${fmtPnl(h.pnl)}</div></div>
      <div class="mini-item"><div class="mini-label">RSI</div><div class="mini-val" style="color:${rsiColor};">${rsi.toFixed(0)}</div></div>
      <div class="mini-item"><div class="mini-label">이격도</div><div class="mini-val">${gap20.toFixed(0)}%</div></div>
    </div>
    <div class="pnl-bar-wrap"><div class="pnl-bar" style="width:${barWidth}%;background:${barColor};"></div></div>
    ${supChips ? `<div class="support-mini">${supChips}</div>` : ''}
    <div class="card-bottom">
      <div class="signal-badges">${badgesHtml}</div>
      <i class="ti ti-chevron-right" style="color:#C7C7CC;font-size:18px;"></i>
    </div>
  </div>`;
}
function openHoldingDetail(code, name) {
  _prevScreen = 'holdings';
  showScreen('holding-detail');
  loadHoldingDetail(code, name);
}

async function loadHoldingDetail(code, name) {
  const el = document.getElementById('holding-detail-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 분석 중...</div>';
  try {
    const d = await api('GET', `/api/holdings/${code}/detail`);
    renderHoldingDetail(d, el);
    // 차트는 DOM 삽입 후 그려야 함
    const a = d.analysis || {};
    const t = a.targets || {};
    setTimeout(() => drawPriceChart(
      a.ohlcv, d.holding?.avg_price, t.target_price, t.stop_price
    ), 50);
    // 뉴스 비동기 로드
    loadHoldingDetailNews(code, d.holding?.name || name, el);
  } catch(e) {
    el.innerHTML = `<div class="loading">분석 데이터를 불러오지 못했습니다<br><small>${e.message||''}</small></div>`;
  }
}

function renderHoldingDetail(d, el) {
  const h = d.holding || {};
  const a = d.analysis || {};
  const curPrice = a.cur_price || a.current_price || h.avg_price;
  const chgPct = a.cur_change_pct || 0;
  const chg = a.cur_change || 0;
  const pnl = a.pnl_amount !== undefined ? a.pnl_amount : (curPrice - h.avg_price) * h.qty;
  const pnlPct = a.pnl_pct !== undefined ? a.pnl_pct : ((curPrice - h.avg_price) / h.avg_price * 100);
  const pnlCls = pnlPct >= 0 ? 'up' : 'down';

  const rsiVal = a.rsi ? Math.round(a.rsi) : null;
  const boll = a.bollinger || {};
  const bollPos = boll.position !== undefined ? boll.position : 0.5;
  const ma20Val = a.ma20;
  const ma60Val = a.ma60;
  const gap20Raw = a.gap20; // 비율 (1.05 = 105%)
  const gap20 = gap20Raw ? (gap20Raw * 100).toFixed(1) : null;
  const targets = a.targets || {};
  const invList = Array.isArray(a.inv_list) ? a.inv_list : [];
  const foreignNet = a.foreign_net_3d || 0;
  const instNet = a.institution_net_3d || 0;
  const badges = Array.isArray(a.badges) ? a.badges : [];
  const verdict = a.verdict || '';

  // ── RSI 해석 ──
  const rsiColor = rsiVal >= 70 ? '#E24B4A' : rsiVal <= 30 ? '#185FA5' : rsiVal >= 60 ? '#BA7517' : '#30D158';
  let rsiInterp = '', rsiIcon = '🟢';
  if (rsiVal !== null) {
    if (rsiVal >= 70)      { rsiInterp = `RSI ${rsiVal}으로 <b>과열 구간</b>이에요. 너무 빠르게 올라온 상태예요. 추가 상승보다 숨 고르기 가능성이 높아요.`; rsiIcon='🔴'; }
    else if (rsiVal <= 30) { rsiInterp = `RSI ${rsiVal}으로 <b>과매도 구간</b>이에요. 너무 많이 떨어진 상태예요. 단기 반등 시도가 나올 수 있어요.`; rsiIcon='🟢'; }
    else if (rsiVal >= 60) { rsiInterp = `RSI ${rsiVal}으로 <b>정상 범위 상단</b>이에요. 과열도 침체도 아닌 건강한 상승세예요.`; rsiIcon='🟡'; }
    else if (rsiVal <= 40) { rsiInterp = `RSI ${rsiVal}으로 <b>정상 범위 하단</b>이에요. 힘이 빠지는 구간이지만 아직 위험하진 않아요.`; rsiIcon='🟡'; }
    else                   { rsiInterp = `RSI ${rsiVal}으로 <b>정상 범위</b>예요. 과열도 침체도 아닌 건강한 상태예요.`; rsiIcon='🟢'; }
  }

  // ── 이격도 해석 ──
  const g = gap20 ? parseFloat(gap20) : 100;
  let gapInterp = '', gapIcon = '🟢';
  if (g >= 115)     { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(g-100).toFixed(0)}% 위</b>에 있어요. 용수철처럼 평균으로 되돌아오려는 힘이 강해요.`; gapIcon='⚠️'; }
  else if (g >= 105){ gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(g-100).toFixed(0)}% 위</b>에 있어요. 약간 올라온 상태지만 아직 과열은 아니에요.`; gapIcon='🟡'; }
  else if (g <= 85) { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(100-g).toFixed(0)}% 아래</b>에 있어요. 많이 떨어진 상태로 반등 가능성이 있어요.`; gapIcon='🟢'; }
  else if (g <= 95) { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(100-g).toFixed(0)}% 아래</b>에 있어요. 평균선 아래지만 크게 이탈한 건 아니에요.`; gapIcon='🟡'; }
  else              { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균 근처에 있어요. 안정적인 위치예요.`; gapIcon='🟢'; }

  // ── 볼린저 해석 ──
  let bollInterp = '', bollIcon = '🟡';
  if (bollPos >= 0.8)     { bollInterp = '볼린저밴드 <b>상단 근처</b>에요. 주가가 터널 천장에 닿아있어요. 여기서 저항을 받으면 단기 조정이 올 수 있어요.'; bollIcon='⚠️'; }
  else if (bollPos <= 0.2){ bollInterp = '볼린저밴드 <b>하단 근처</b>예요. 주가가 터널 바닥에 있어요. 여기서 지지를 받으면 반등이 나올 수 있어요.'; bollIcon='🟢'; }
  else                    { bollInterp = '볼린저밴드 <b>중간 구간</b>에 있어요. 상단 또는 하단 돌파 방향을 지켜보세요.'; bollIcon='🟡'; }
  const bollLbl = bollPos <= 0.2 ? '하단 근처' : bollPos >= 0.8 ? '상단 근처' : '중간';

  // ── 기술 지표 섹션 ──
  const rsiBarW = rsiVal || 50;
  const rsiStatus = rsiVal >= 70 ? '과매수' : rsiVal <= 30 ? '과매도' : '정상';
  const rsiStatusCls = rsiVal >= 70 || rsiVal <= 30 ? 'badge-sell' : 'badge-buy';
  const gapStatus = g >= 95 && g <= 115 ? '평균선 근처' : '이격 과대';
  const gapStatusCls = g >= 95 && g <= 115 ? 'badge-ok' : 'badge-sell';
  const bollStatusCls = bollPos <= 0.3 ? 'badge-buy' : bollPos >= 0.8 ? 'badge-sell' : 'badge-ok';

  let ma20Row = '', ma60Row = '';
  if (ma20Val) {
    const d20 = (curPrice - ma20Val) / ma20Val * 100;
    const scls = d20 >= 0 ? 'badge-ok' : 'badge-sell';
    ma20Row = `<div class="ind-row"><span class="ind-label">20일선</span><div class="ind-right"><span class="ind-val">${fmtNum(Math.round(ma20Val))}</span><span class="badge ${scls}" style="font-size:10px;">${d20>=0?'위':'아래'} ${Math.abs(d20).toFixed(1)}%</span></div></div>`;
  }
  if (ma60Val) {
    const d60 = (curPrice - ma60Val) / ma60Val * 100;
    const scls = d60 >= 0 ? 'badge-ok' : 'badge-sell';
    ma60Row = `<div class="ind-row"><span class="ind-label">60일선</span><div class="ind-right"><span class="ind-val">${fmtNum(Math.round(ma60Val))}</span><span class="badge ${scls}" style="font-size:10px;">${d60>=0?'위':'아래'} ${Math.abs(d60).toFixed(1)}%</span></div></div>`;
  }

  // ── 지지선 ──
  let supRows = '';
  if (ma20Val) {
    const d = (curPrice - ma20Val) / ma20Val * 100;
    const cls = d >= 0 ? 'up' : 'down';
    supRows += `<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma20Val))}</span><span class="sup-dist ${cls}">${d>=0?'+':''}${d.toFixed(1)}%</span><span class="sup-note">${d>=0?'현재 위':'이탈'}</span></div></div>`;
  }
  if (boll.lower) {
    const d = (curPrice - boll.lower) / boll.lower * 100;
    const cls = d >= 0 ? 'up' : 'down';
    supRows += `<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(boll.lower))}</span><span class="sup-dist ${cls}">${d>=0?'+':''}${d.toFixed(1)}%</span><span class="sup-note">지지선</span></div></div>`;
  }
  if (ma60Val) {
    const d = (curPrice - ma60Val) / ma60Val * 100;
    const cls = d >= 0 ? 'up' : 'down';
    supRows += `<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma60Val))}</span><span class="sup-dist ${cls}">${d>=0?'+':''}${d.toFixed(1)}%</span><span class="sup-note">주요 지지</span></div></div>`;
  }

  // ── 수급 ──
  const fMax = Math.max(Math.abs(foreignNet), Math.abs(instNet), 1);
  const fBarW = Math.min(Math.abs(foreignNet) / fMax * 80, 80);
  const iBarW = Math.min(Math.abs(instNet) / fMax * 80, 80);
  const fCls = foreignNet >= 0 ? 'up' : 'down';
  const iCls = instNet >= 0 ? 'up' : 'down';
  const fBarCls = foreignNet >= 0 ? 'bar-buy' : 'bar-sell';
  const iBarCls = instNet >= 0 ? 'bar-buy' : 'bar-sell';
  const fChips = invList.map(r => {
    const v = r.foreign; const c = v >= 0 ? 'chip-buy' : 'chip-sell';
    return `<span class="day-chip ${c}">${v>=0?'+':''}${Math.round(v/1000)}K</span>`;
  }).join('');
  const iChips = invList.map(r => {
    const v = r.inst; const c = v >= 0 ? 'chip-buy' : 'chip-sell';
    return `<span class="day-chip ${c}">${v>=0?'+':''}${Math.round(v/1000)}K</span>`;
  }).join('');

  // ── 배지 & verdict ──
  const badgesHtml = (badges||[]).filter(b => typeof b === 'string').map(b => {
    const cls = b.includes('매도')||b.includes('과열')||b.includes('손절') ? 'badge-sell' :
                b.includes('매수')||b.includes('정배열')||b.includes('지지') ? 'badge-buy' :
                b.includes('주의')||b.includes('경고') ? 'badge-warn' : 'badge-ok';
    return `<span class="badge ${cls}">${b}</span>`;
  }).join('');

  // ── 목표가/손절가 ──
  const tp = targets.target_price, sp2 = targets.stop_price;
  const tu = targets.target_upside, sd = targets.stop_downside;
  const tb = targets.target_basis, sb = targets.stop_basis;
  const rr = targets.risk_reward || 0;
  const avs = targets.avg_vs_stop;
  const rrCls = rr >= 2 ? '#27500A' : rr >= 1 ? '#BA7517' : '#A32D2D';
  const rrLbl = rr >= 2 ? '✅ 양호' : rr >= 1 ? '⚠️ 보통' : '❌ 불리';

  // 뉴스는 비동기 로드 (loadHoldingDetailNews)
  const newsHtml = '';

  // 바닥 지지선 배지 (현재위/근접/주요지지)
  const supBadge = (dist) => {
    if (dist >= 0)  return `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EAF3DE;color:#27500A;">현재위</span>`;
    if (dist >= -5) return `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#FAEEDA;color:#633806;">근접</span>`;
    return             `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EEEDFE;color:#3C3489;">주요지지</span>`;
  };

  let supRowsNew = '';
  if (ma20Val) {
    const d = (curPrice - ma20Val) / ma20Val * 100;
    supRowsNew += `<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma20Val))}원</span><span class="sup-dist ${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span>${supBadge(d)}</div></div>`;
  }
  if (boll.lower) {
    const d = (curPrice - boll.lower) / boll.lower * 100;
    supRowsNew += `<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(boll.lower))}원</span><span class="sup-dist ${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span>${supBadge(d)}</div></div>`;
  }
  if (ma60Val) {
    const d = (curPrice - ma60Val) / ma60Val * 100;
    supRowsNew += `<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma60Val))}원</span><span class="sup-dist ${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span>${supBadge(d)}</div></div>`;
  }

  const pnlBarW = Math.min(Math.abs(pnlPct) * 2, 100);
  const pnlBarColor = pnlPct >= 0 ? '#E24B4A' : '#185FA5';

  el.innerHTML = `
    <!-- 히어로 카드 (흰색) -->
    <div class="section" style="margin-top:0;">
      <div class="card" style="padding:16px;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:2px;">
          <div>
            <div style="font-size:18px;font-weight:700;color:#1A1A2E;">${h.name}</div>
            <div style="font-size:11px;color:#8E8E9A;margin-top:2px;">${h.code}</div>
          </div>
          <span class="badge ${pnlCls==='up'?'badge-buy':'badge-sell'}" style="font-size:11px;padding:4px 10px;">${pnlCls==='up'?'수익':'손실'} ${pnlPct>=0?'+':''}${pnlPct.toFixed(2)}%</span>
        </div>
        <div style="font-size:28px;font-weight:800;color:#1A1A2E;margin-top:10px;">${fmtNum(curPrice)}원</div>
        <div style="font-size:13px;margin-top:3px;color:${chgPct>=0?'#E24B4A':'#185FA5'};">
          ${chgPct>=0?'▲':'▼'} ${Math.abs(chg).toLocaleString()}원 (${Math.abs(chgPct).toFixed(2)}%)
        </div>
        ${a.cur_high || a.cur_low ? `<div style="font-size:11px;color:#8E8E9A;margin-top:6px;">
          고가 ${fmtNum(a.cur_high||0)}원 &nbsp;저가 ${fmtNum(a.cur_low||0)}원 &nbsp;거래량 ${(a.cur_volume||0).toLocaleString()}
        </div>` : ''}

        <div style="border-top:1px solid #F0F0F5;margin:14px 0 10px;"></div>
        <div style="font-size:11px;font-weight:600;color:#8E8E9A;margin-bottom:10px;">내 보유 현황</div>
        <div style="display:flex;gap:8px;">
          <div style="flex:1;background:#F8F8FA;border-radius:10px;padding:10px 12px;"><div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">평단가</div><div style="font-size:13px;font-weight:600;color:#1A1A2E;">${fmtNum(h.avg_price)}원</div></div>
          <div style="flex:1;background:#F8F8FA;border-radius:10px;padding:10px 12px;"><div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">보유 수량</div><div style="font-size:13px;font-weight:600;color:#1A1A2E;">${h.qty}주</div></div>
          <div style="flex:1;background:#F8F8FA;border-radius:10px;padding:10px 12px;"><div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">평가손익</div><div style="font-size:13px;font-weight:600;" class="${pnlCls}">${pnl>=0?'+':''}${Math.round(pnl/10000)}만원</div></div>
        </div>
        <div style="height:4px;background:#F0F0F5;border-radius:2px;margin-top:10px;overflow:hidden;">
          <div style="height:4px;width:${pnlBarW}%;background:${pnlBarColor};border-radius:2px;"></div>
        </div>
      </div>
    </div>

    <!-- 가격 차트 -->
    ${(a.ohlcv||[]).length > 0 ? `<div class="section">
      <div class="sec-title"><i class="ti ti-chart-candle" style="font-size:15px;color:#5B5BD6;"></i>가격 차트 <span style="font-size:10px;color:#8E8E9A;font-weight:400;">(주황선=평단가)</span></div>
      <div class="card" style="padding:12px 8px;">
        <canvas id="price-chart" style="width:100%;height:200px;"></canvas>
      </div>
    </div>` : ''}

    <!-- 기술 지표 -->
    <div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>기술적 지표</div>
      <div class="card">
        ${rsiVal !== null ? `<div class="ind-row">
          <span class="ind-label">RSI (14일)</span>
          <div class="ind-right">
            <div style="width:80px;height:6px;background:#F0F0F5;border-radius:3px;margin-right:8px;">
              <div style="width:${rsiBarW}%;height:6px;background:${rsiColor};border-radius:3px;"></div>
            </div>
            <span class="ind-val">${rsiVal}</span>
            <span class="badge ${rsiStatusCls}" style="font-size:10px;margin-left:4px;">${rsiStatus}</span>
          </div>
        </div>` : ''}
        ${gap20 ? `<div class="ind-row">
          <span class="ind-label">이격도 (20일)</span>
          <div class="ind-right"><span class="ind-val">${parseFloat(gap20).toFixed(0)}%</span><span class="badge ${gapStatusCls}" style="font-size:10px;margin-left:4px;">${gapStatus}</span></div>
        </div>` : ''}
        <div class="ind-row">
          <span class="ind-label">볼린저밴드</span>
          <div class="ind-right"><span class="ind-val">${bollLbl}</span><span class="badge ${bollStatusCls}" style="font-size:10px;margin-left:4px;">${bollPos<=0.3?'지지 시도':bollPos>=0.8?'과열':'보통'}</span></div>
        </div>
        ${ma20Row}${ma60Row}
      </div>
    </div>

    <!-- 지표 해석 -->
    ${rsiVal !== null ? `<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:0 16px 12px;">
      <div style="font-size:12px;font-weight:700;color:#3C3489;margin-bottom:12px;display:flex;align-items:center;gap:6px;">
        <i class="ti ti-microscope" style="font-size:14px;"></i> 지금 이 숫자가 의미하는 것
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">${rsiIcon} RSI (상대강도지수)</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">${rsiInterp}</div>
        </div>
        ${gap20 ? `<div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">${gapIcon} 이격도 (20일 평균 기준)</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">${gapInterp}</div>
        </div>` : ''}
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">${bollIcon} 볼린저밴드</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">${bollInterp}</div>
        </div>
      </div>
    </div>` : ''}

    <!-- 지지선 -->
    ${supRowsNew ? `<div class="section">
      <div class="sec-title"><i class="ti ti-barrier-block" style="font-size:15px;color:#5B5BD6;"></i>바닥 지지선</div>
      <div class="card">${supRowsNew}</div>
    </div>` : ''}

    <!-- 거래량 + 수급 SVG 차트 -->
    ${invList.length ? `<div class="section">
      <div class="sec-title"><i class="ti ti-chart-bar" style="font-size:15px;color:#5B5BD6;"></i>5일 거래량 · 수급 흐름</div>
      <div class="card" style="padding:14px;">
        ${_buildFlowChart(a.vol_list || [], invList)}
        <div style="display:flex;gap:16px;margin-top:10px;font-size:12px;">
          <span style="color:${foreignNet>=0?'#E24B4A':'#185FA5'};font-weight:600;">외국인 3일 ${foreignNet>=0?'+':''}${foreignNet.toLocaleString()}주</span>
          <span style="color:${instNet>=0?'#F5A623':'#30D158'};font-weight:600;">기관 3일 ${instNet>=0?'+':''}${instNet.toLocaleString()}주</span>
        </div>
      </div>
    </div>` : ''}

    <!-- 배지 -->
    ${badgesHtml ? `<div class="section">
      <div style="padding:0 16px 8px;"><div class="signal-badges">${badgesHtml}</div></div>
    </div>` : ''}

    <!-- 목표가/손절가 -->
    ${tp ? `<div class="section">
      <div class="sec-title"><i class="ti ti-target" style="font-size:15px;color:#5B5BD6;"></i>목표가 / 손절가 분석</div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
          <div>
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">추천 목표가</div>
            <div style="font-size:18px;font-weight:700;color:#27500A;">${fmtNum(tp)}</div>
            <div style="font-size:11px;color:#27500A;">+${tu}%</div>
            <div style="font-size:10px;color:#8E8E9A;margin-top:2px;">기준: ${tb}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">추천 손절가</div>
            <div style="font-size:18px;font-weight:700;color:#A32D2D;">${fmtNum(sp2)}</div>
            <div style="font-size:11px;color:#A32D2D;">${sd}%</div>
            <div style="font-size:10px;color:#8E8E9A;margin-top:2px;">기준: ${sb}${avs!==null?` · 평단 대비 ${avs>0?'+':''}${avs}%`:''}</div>
          </div>
        </div>
        <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">리스크/리워드 비율</div>
          <div style="font-size:13px;font-weight:600;color:${rrCls};">1 : ${rr} ${rrLbl}</div>
          <div style="font-size:10px;color:#8E8E9A;margin-top:3px;">손실 1원 대비 수익 ${rr}원 기대 — 2 이상이면 진입 적합</div>
        </div>
      </div>
    </div>` : ''}

    <!-- 최근 공시 -->
    ${(a.disclosures||[]).length > 0 ? `<div class="section">
      <div class="sec-title"><i class="ti ti-file-text" style="font-size:15px;color:#5B5BD6;"></i>최근 공시 (30일)</div>
      ${(a.disclosures||[]).map(dis => `
        <div class="card" style="margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:10px;padding:2px 8px;border-radius:5px;background:#EEEDFE;color:#3C3489;font-weight:600;">${dis.type||'기타공시'}</span>
            <span style="font-size:10px;color:#8E8E9A;">${dis.date||''}</span>
          </div>
          <div style="font-size:13px;font-weight:600;color:#1A1A2E;margin-bottom:10px;line-height:1.5;">${dis.title||''}</div>
          <div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;margin-bottom:8px;">
            <div style="font-size:10px;font-weight:700;color:#5B5BD6;margin-bottom:5px;">💡 이 공시가 의미하는 것</div>
            <div style="font-size:11px;color:#3C3C43;line-height:1.6;">${dis.meaning||''}</div>
          </div>
          ${(dis.impact||[]).length > 0 ? `<div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
            <div style="font-size:10px;font-weight:700;color:#5B5BD6;margin-bottom:5px;">↗ 추가 영향 흐름</div>
            ${(dis.impact||[]).map(pt => `<div style="font-size:11px;color:#3C3C43;line-height:1.8;">- ${pt}</div>`).join('')}
          </div>` : ''}
        </div>
      `).join('')}
    </div>` : ''}

    <!-- 뉴스 (비동기 로드) -->
    <div class="section" id="holding-news-section">
      <div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>${h.name} 뉴스</div>
    </div>

    <!-- 손절 기준 확인 -->
    ${(() => {
      const stopRef = Math.round(h.avg_price * 0.97);
      const instSellDays = invList.filter(r => r.inst < 0).length;
      const foreignSellDays = invList.filter(r => r.foreign < 0).length;
      let lines = [];
      if (pnlPct < 0) {
        lines.push(`평단 ${fmtNum(h.avg_price)}원 기준 현재 <b>${pnlPct.toFixed(2)}%</b> 손실 중이에요.`);
      } else {
        lines.push(`평단 ${fmtNum(h.avg_price)}원 기준 현재 <b>+${pnlPct.toFixed(2)}%</b> 수익 중이에요.`);
      }
      if (instSellDays >= 3) lines.push(`기관이 ${instSellDays}일 연속 순매도 중으로 추세 회복까지 시간이 필요해요.`);
      else if (instNet > 0) lines.push(`기관이 최근 순매수로 전환하며 긍정적인 수급 신호가 나타나고 있어요.`);
      if (foreignSellDays >= 3) lines.push(`외국인도 ${foreignSellDays}일 연속 순매도 중이에요.`);
      lines.push(`손절 기준(-3% 추가 하락 = <b>${fmtNum(stopRef)}원</b>)을 명확히 설정해두는 게 좋아요.`);
      return `<div class="section">
        <div class="card" style="background:#FFF8F8;border:1px solid #F5C5C5;">
          <div style="font-size:13px;font-weight:700;color:#791F1F;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
            <i class="ti ti-alert-triangle" style="font-size:15px;"></i> 손절 기준 확인
          </div>
          <div style="font-size:13px;color:#3C3C43;line-height:1.8;">${lines.join('<br>')}</div>
        </div>
      </div>`;
    })()}

    <!-- 시스템 판단 -->
    ${(() => {
      let lines = [];
      if (rsiVal !== null) {
        const rsiStr = rsiVal <= 30 ? `RSI ${rsiVal}로 과매도 근접` : rsiVal >= 70 ? `RSI ${rsiVal}로 과열 구간` : `RSI ${rsiVal}로 정상 범위`;
        lines.push(rsiStr + (bollPos <= 0.2 ? ', 볼린저 하단 지지 시도 중이에요.' : bollPos >= 0.8 ? ', 볼린저 상단 저항 구간이에요.' : ', 볼린저 중간 구간이에요.'));
      }
      if (foreignNet < 0 && instNet < 0) lines.push(`외국인은 소량 매수 중이나 기관은 ${invList.filter(r=>r.inst<0).length}일 연속 매도 중으로 수급 신호는 혼조세요.`);
      else if (foreignNet > 0 && instNet > 0) lines.push('외국인·기관 모두 순매수로 수급이 우호적이에요.');
      else if (foreignNet > 0) lines.push('외국인 순매수, 기관은 관망세예요.');
      else if (instNet > 0) lines.push('기관 순매수, 외국인은 관망세예요.');
      if (ma20Val) {
        const d20 = (curPrice - ma20Val) / ma20Val * 100;
        lines.push(`20일선(${fmtNum(Math.round(ma20Val))}원) ${d20 >= 0 ? '위에서 유지된다면 단기 반등 가능성이 있어요.' : '아래로 이탈해 추세 회복 여부를 지켜봐야 해요.'}`);
      }
      if (verdict) lines.push(verdict);
      if (!lines.length) return '';
      return `<div class="section">
        <div class="card" style="background:#FFFBF0;border:1px solid #F5E6B2;">
          <div style="font-size:13px;font-weight:700;color:#8B6914;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
            <span style="font-size:15px;">☀️</span> 시스템 판단
          </div>
          <div style="font-size:13px;color:#3C3C43;line-height:1.8;">${lines.join('<br>')}</div>
        </div>
      </div>`;
    })()}

    <div style="padding:0 16px 16px;">
      <div class="warn-box" style="margin-bottom:10px;"><i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>투자 결정은 본인 책임입니다. 이 정보는 참고용이며 투자 권유가 아닙니다.</div>
      <button class="btn-danger" onclick="deleteHolding('${h.code}', '${h.name}')">
        <i class="ti ti-trash" style="font-size:16px;"></i> 종목 삭제하기
      </button>
    </div>`;
}

function drawPriceChart(ohlcv, avgPrice, targetPrice, stopPrice) {
  const canvas = document.getElementById('price-chart');
  if (!canvas || !ohlcv || ohlcv.length === 0) return;
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.offsetWidth || 340;
  const H = 200;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width  = W + 'px';
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const PAD = { top: 16, right: 12, bottom: 28, left: 52 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top  - PAD.bottom;

  // 가격 범위
  const allPrices = ohlcv.flatMap(c => [c.high, c.low]);
  if (avgPrice)   allPrices.push(avgPrice);
  if (targetPrice)allPrices.push(targetPrice);
  if (stopPrice)  allPrices.push(stopPrice);
  const minP = Math.min(...allPrices) * 0.995;
  const maxP = Math.max(...allPrices) * 1.005;
  const scaleY = v => PAD.top + cH - (v - minP) / (maxP - minP) * cH;
  const n = ohlcv.length;
  const barW = Math.max(2, Math.floor(cW / n) - 1);
  const scaleX = i => PAD.left + (i + 0.5) * (cW / n);

  // 배경
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, W, H);

  // Y축 레이블
  ctx.fillStyle = '#C7C7CC';
  ctx.font = '9px -apple-system,sans-serif';
  ctx.textAlign = 'right';
  const steps = 4;
  for (let i = 0; i <= steps; i++) {
    const v = minP + (maxP - minP) * (i / steps);
    const y = scaleY(v);
    ctx.fillText((v/10000).toFixed(0) + '만', PAD.left - 4, y + 3);
    ctx.strokeStyle = '#F0F0F5';
    ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
  }

  // 수평선 그리기 함수
  const drawLine = (price, color, label, dash) => {
    if (!price) return;
    const y = scaleY(price);
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;
    if (dash) ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color;
    ctx.font = 'bold 9px -apple-system,sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(label, W - PAD.right - 2, y - 2);
    ctx.restore();
  };

  // 캔들스틱
  ohlcv.forEach((c, i) => {
    const x = scaleX(i);
    const yH = scaleY(c.high);
    const yL = scaleY(c.low);
    const yO = scaleY(c.open);
    const yC = scaleY(c.close);
    const isUp = c.close >= c.open;
    const color = isUp ? '#E24B4A' : '#185FA5';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, yH); ctx.lineTo(x, yL); ctx.stroke();
    ctx.fillStyle = color;
    const top  = Math.min(yO, yC);
    const body = Math.max(Math.abs(yO - yC), 1);
    ctx.fillRect(x - barW/2, top, barW, body);
  });

  // X축 날짜 (첫·중간·마지막)
  ctx.fillStyle = '#C7C7CC';
  ctx.font = '9px -apple-system,sans-serif';
  ctx.textAlign = 'center';
  [0, Math.floor(n/2), n-1].forEach(i => {
    const d = ohlcv[i]?.date?.slice(5) || '';
    ctx.fillText(d, scaleX(i), H - PAD.bottom + 12);
  });

  // 수평선: 손절가→목표가→평단가 순으로 그려서 평단가가 위에 표시
  drawLine(stopPrice,   '#E24B4A', '손절가', true);
  drawLine(targetPrice, '#27500A', '목표가', true);
  drawLine(avgPrice,    '#FF9F0A', '평단가', false);
}

function confirmDeleteHolding(code, name) {
  showConfirm({
    title: '보유종목 삭제',
    message: `<b>${name}</b>을(를) 삭제할까요?<br>삭제하면 되돌릴 수 없어요.`,
    confirmText: '삭제',
    onConfirm: async () => {
      try {
        await api('DELETE', `/api/holdings/${code}`);
        _holdingsLoaded = false;
        loadHoldings(true);
      } catch(e) { alert(e.message); }
    }
  });
}

async function deleteHolding(code, name) {
  if (!confirm(`${name}을(를) 보유종목에서 삭제할까요?`)) return;
  try {
    await api('DELETE', `/api/holdings/${code}`);
    _holdingsLoaded = false;
    goBack();
  } catch(e) {
    alert(e.message);
  }
}

// ─────────────────────────────────────────────────────────
// 종목 추가 폼
// ─────────────────────────────────────────────────────────
function toggleAddHolding() {
  const el = document.getElementById('holding-add-form');
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
  if (el.style.display === 'block') {
    document.getElementById('h-search').value = '';
    document.getElementById('h-code').value = '';
    document.getElementById('h-price').value = '';
    document.getElementById('h-qty').value = '';
  }
}

function toggleAddWatchlist() {
  const el = document.getElementById('watchlist-add-form');
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
  if (el.style.display === 'block') {
    document.getElementById('w-search').value = '';
    document.getElementById('w-code').value = '';
  }
}

let _searchTimeout = null;
function searchStock(prefix) {
  clearTimeout(_searchTimeout);
  const q = document.getElementById(prefix + '-search').value.trim();
  const resEl = document.getElementById(prefix + '-search-results');
  if (!q) { resEl.style.display = 'none'; return; }
  _searchTimeout = setTimeout(async () => {
    try {
      const d = await api('GET', `/api/stock/search?q=${encodeURIComponent(q)}`);
      const results = d.results || [];
      if (!results.length) { resEl.style.display = 'none'; return; }
      resEl.innerHTML = results.map(r =>
        `<div class="search-result-item" onclick="selectStock('${prefix}', '${r.code}', '${r.name.replace(/'/g,"\\'")}')">
          ${r.name}<span>${r.code}</span>
        </div>`
      ).join('');
      resEl.style.display = 'block';
    } catch(e) {}
  }, 300);
}

function selectStock(prefix, code, name) {
  document.getElementById(prefix + '-search').value = name;
  document.getElementById(prefix + '-code').value = code;
  document.getElementById(prefix + '-search-results').style.display = 'none';
}

async function addHolding() {
  const code = document.getElementById('h-code').value;
  const name = document.getElementById('h-search').value.trim();
  const avg_price = parseFloat(document.getElementById('h-price').value);
  const qty = parseInt(document.getElementById('h-qty').value);
  if (!code || !name || !avg_price || !qty) { alert('모든 항목을 입력하세요'); return; }
  try {
    await api('POST', '/api/holdings', { code, name, avg_price, qty });
    toggleAddHolding();
    _holdingsLoaded = false;
    loadHoldings(true);
  } catch(e) { alert(e.message); }
}

async function addWatchlist() {
  const code = document.getElementById('w-code').value;
  const name = document.getElementById('w-search').value.trim();
  if (!code || !name) { alert('종목을 검색해서 선택하세요'); return; }
  const sel = document.getElementById('w-group-select').value;
  const newG = document.getElementById('w-group-new').value.trim();
  const group_name = (sel === '__new__' ? newG : sel) || '기본';
  if (sel === '__new__' && !newG) { alert('새 그룹명을 입력하세요'); return; }
  try {
    await api('POST', '/api/watchlist', { code, name, group_name });
    toggleAddWatchlist();
    _watchlistLoaded = false;
    loadWatchlist(true);
  } catch(e) { alert(e.message); }
}

function onWatchlistGroupSelect(val) {
  const inp = document.getElementById('w-group-new');
  inp.style.display = val === '__new__' ? '' : 'none';
}

// ─────────────────────────────────────────────────────────
// 관심종목 탭
// ─────────────────────────────────────────────────────────
function renderWatchlistFromData(d) {
  _allWatchlist = d.watchlist || [];
  _watchlistAlertCount = d.alert_count || 0;
  _renderGroupTabs(d.groups || []);
  _updateAlertBadge();
  renderWatchlist();
}

let _watchlistLoaded = false;
let _watchlistFilter = '전체';
let _watchlistGroupFilter = '전체';
let _watchlistAlertCount = 0;

function _updateAlertBadge() {
  const badge = document.getElementById('watchlist-alert-badge');
  if (!badge) return;
  badge.style.display = _watchlistAlertCount > 0 ? '' : 'none';
}

function _renderGroupTabs(groups) {
  const el = document.getElementById('watchlist-group-tabs');
  if (!el) return;
  const all = ['전체', ...groups.filter(g => g && g !== '기본').concat(groups.includes('기본') ? ['기본'] : [])];
  // deduplicate
  const uniq = [...new Set(all)];
  el.innerHTML = uniq.map((g, i) =>
    `<button class="tab ${i === 0 && _watchlistGroupFilter === '전체' ? 'active' : (_watchlistGroupFilter === g ? 'active' : 'inactive')}"
      onclick="filterWatchlistGroup('${g}', this)">${g}</button>`
  ).join('');

  // 그룹 추가 폼 select 업데이트
  const sel = document.getElementById('w-group-select');
  if (sel) {
    const existing = uniq.filter(g => g !== '전체');
    sel.innerHTML = existing.map(g => `<option value="${g}">${g}</option>`).join('')
      + '<option value="__new__">+ 새 그룹 만들기</option>';
  }
}

function filterWatchlistGroup(group, btn) {
  _watchlistGroupFilter = group;
  document.querySelectorAll('#watchlist-group-tabs .tab').forEach(b => {
    b.className = 'tab ' + (b === btn ? 'active' : 'inactive');
  });
  renderWatchlist();
}

async function loadWatchlist(force) {
  if (_watchlistLoaded && !force) return;
  _watchlistLoaded = true;
  const el = document.getElementById('watchlist-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 불러오는 중...</div>';
  try {
    const d = await api('GET', '/api/watchlist');
    _allWatchlist = d.watchlist || [];
    _watchlistAlertCount = d.alert_count || 0;
    _renderGroupTabs(d.groups || []);
    _updateAlertBadge();
    renderWatchlist();
  } catch(e) {
    el.innerHTML = `<div class="loading" style="flex-direction:column;gap:8px;">
      <span>불러오지 못했습니다</span>
      <span style="font-size:11px;color:#C7C7CC;">${e.message||''}</span>
      <button class="btn-secondary" style="margin-top:8px;" onclick="loadWatchlist(true)">다시 시도</button>
    </div>`;
  }
}

function filterWatchlist(filter, btn) {
  _watchlistFilter = filter;
  document.querySelectorAll('#screen-watchlist .tabs:last-of-type .tab').forEach(b => {
    b.className = 'tab ' + (b === btn ? 'active' : 'inactive');
  });
  renderWatchlist();
}

function renderWatchlist() {
  const el = document.getElementById('watchlist-content');
  let list = _allWatchlist;
  const filt = _watchlistFilter || '전체';
  const gFilt = _watchlistGroupFilter || '전체';

  // 그룹 필터
  if (gFilt !== '전체') {
    list = list.filter(w => (w.group_name || '기본') === gFilt);
  }

  // 타이밍 필터
  if (filt !== '전체') {
    list = list.filter(w => {
      const st = w.timing?.status;
      if (filt === '매수검토') return st === 'buy_ok';
      if (filt === '추격금지') return st === 'chase_no';
      if (filt === '관망')   return st === 'watch';
      return true;
    });
  }

  if (!list.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-star"></i>관심종목을 추가해보세요</div>';
    return;
  }

  // 그룹핑
  const groups = { buy_ok: [], chase_no: [], watch: [], none: [] };
  list.forEach(w => {
    const st = w.timing?.status || 'none';
    (groups[st] || groups.none).push(w);
  });

  const groupMeta = {
    buy_ok:   { label: '매수 검토 가능', color: '#27500A' },
    chase_no: { label: '추격매수 금지',  color: '#791F1F' },
    watch:    { label: '관망 중',        color: '#633806' },
    none:     { label: '기타',           color: '#8E8E9A' },
  };

  function buildCard(w) {
    const rsi    = w.rsi != null ? Math.round(w.rsi) : null;
    const gap20  = w.gap20 != null ? w.gap20 : null;
    const chgPct = w.change_pct || 0;
    const chgCls = chgPct >= 0 ? 'up' : 'down';
    const chgTxt = (chgPct >= 0 ? '▲ +' : '▼ ') + Math.abs(chgPct).toFixed(2) + '%';

    // RSI 색상
    let rsiColor = '#5B5BD6', rsiLabel = '보통';
    if (rsi != null) {
      if (rsi >= 70) { rsiColor = '#E24B4A'; rsiLabel = '과열'; }
      else if (rsi <= 35) { rsiColor = '#3B6D11'; rsiLabel = '저점'; }
    }

    // 배지 (문자열만 필터)
    const timing = w.timing || {};
    const bdgType = timing.badge_type || 'neutral';
    const bdgCls  = bdgType === 'buy' ? 'badge-buy' : bdgType === 'sell' ? 'badge-sell' : 'badge-ok';
    const extraBadges = (w.badges || []).filter(b => typeof b === 'string').slice(0, 3)
      .map(b => `<span class="badge badge-ok">${b}</span>`).join('');

    // 시장 구분 (코드 앞자리로 추정)
    const market = w.market || (w.code && w.code.length === 6 && w.code[0] === '0' ? '코스닥' : '코스피');
    const codeSub = `${market} · ${w.code}`;

    const cur = w.cur_price || 0;

    // AI 목표가·손절가
    let targetRow = '';
    const tg = w.targets || {};
    const tp = tg.target_price, sp2 = tg.stop_price;
    if (tp && cur) {
      const tu = tg.target_upside != null ? (tg.target_upside >= 0 ? '+' : '') + tg.target_upside.toFixed(1) : '';
      const sd = tg.stop_downside != null ? tg.stop_downside.toFixed(1) : '';
      targetRow = `<div style="display:flex;gap:10px;align-items:center;margin:8px 0 4px;flex-wrap:wrap;">
        <span style="color:#8E8E9A;font-size:12px;">목표가</span>
        <span style="font-weight:600;color:#27500A;font-size:13px;">${fmtNum(tp)}원</span>
        ${tu ? `<span style="color:#27500A;font-size:12px;">(${tu}%)</span>` : ''}
        ${sp2 ? `<span style="color:#8E8E9A;font-size:12px;margin-left:4px;">손절가</span>
        <span style="font-weight:600;color:#A32D2D;font-size:13px;">${fmtNum(sp2)}원</span>
        ${sd ? `<span style="color:#A32D2D;font-size:12px;">(${sd}%)</span>` : ''}` : ''}
      </div>`;
    }

    const isAlert = (timing.score || 0) >= 70;
    return `<div class="card" style="position:relative;" onclick="openWatchlistDetail('${w.code}','${w.name.replace(/'/g,"\\'")}')">
      <button onclick="event.stopPropagation();confirmDeleteWatchlist('${w.code}','${w.name.replace(/'/g,"\\'")}');"
        style="position:absolute;top:10px;right:10px;background:none;border:none;cursor:pointer;padding:2px;line-height:1;z-index:1;">
        <i class="ti ti-trash" style="font-size:16px;color:#8E8E9A;"></i>
      </button>
      ${isAlert ? `<div style="position:absolute;top:10px;right:38px;width:7px;height:7px;border-radius:50%;background:#E24B4A;"></div>` : ''}
      <div class="card-top" style="padding-right:28px;">
        <div class="stock-icon ${iconColors(w.name)}">${iconText(w.name)}</div>
        <div>
          <div class="stock-name">${w.name}</div>
          <div class="stock-sub" style="color:#8E8E9A;">${codeSub}</div>
        </div>
        <div class="stock-right">
          ${cur ? `<div class="stock-price">${fmtNum(cur)}원</div>` : ''}
          ${chgPct !== 0 ? `<div class="stock-change ${chgCls}">${chgTxt}</div>` : ''}
        </div>
      </div>
      ${rsi != null ? `
      <div class="rsi-mini">
        <span class="rsi-label">RSI ${rsi}</span>
        <div class="rsi-bar"><div class="rsi-fill" style="width:${rsi}%;background:${rsiColor};"></div></div>
        <span class="rsi-val" style="color:${rsiColor};">${rsiLabel}</span>
      </div>` : ''}
      ${timing.reason ? `<div class="watch-reason ${bdgType === 'buy' ? 'reason-buy' : 'reason-sell'}">${timing.reason}</div>` : ''}
      ${targetRow}
      <div class="card-bottom">
        <div class="badges">
          ${timing.label ? `<span class="badge ${bdgCls}">${timing.label}</span>` : ''}
          ${extraBadges}
        </div>
        <i class="ti ti-chevron-right" style="color:#C7C7CC;font-size:18px;"></i>
      </div>
    </div>`;
  }

  const order = ['buy_ok', 'chase_no', 'watch', 'none'];
  let html = '';
  order.forEach(key => {
    if (!groups[key].length) return;
    if (filt === '전체') {
      html += `<div class="section"><div class="sec-label" style="color:${groupMeta[key].color};">${groupMeta[key].label}</div>`;
    } else {
      html += `<div class="section">`;
    }
    html += groups[key].map(buildCard).join('') + '</div>';
  });

  el.innerHTML = html;
}

function openWatchlistDetail(code, name) {
  _prevScreen = 'watchlist';
  showScreen('watchlist-detail');
  loadWatchlistDetail(code, name);
}

async function loadWatchlistDetail(code, name) {
  const el = document.getElementById('watchlist-detail-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 분석 중...</div>';
  try {
    const d = await api('GET', `/api/watchlist/${code}/detail`);
    renderWatchlistDetail(d, el, code, name);
    // 뉴스는 별도로 비동기 로드
    loadWatchlistDetailNews(code, name, el);
  } catch(e) {
    el.innerHTML = `<div class="loading" style="flex-direction:column;gap:6px;padding:32px 16px;">
      <span style="color:#E24B4A;">데이터 조회 실패</span>
      <span style="font-size:11px;color:#8E8E9A;">${e.message||''}</span>
    </div>`;
  }
}

async function loadHoldingDetailNews(code, name, containerEl) {
  const newsEl = containerEl.querySelector('#holding-news-section');
  if (!newsEl) return;
  newsEl.innerHTML += '<div style="text-align:center;padding:8px;color:#8E8E9A;font-size:12px;">뉴스 로딩 중...</div>';
  try {
    const r = await api('GET', `/api/stock/${code}/news`);
    const items = (r.news || []).slice(0, 3);
    const secTitle = `<div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>${name} 뉴스</div>`;
    if (!items.length) { newsEl.innerHTML = secTitle; return; }
    newsEl.innerHTML = secTitle + items.map(n => {
      const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
      return `<div class="news-card">
        <div class="news-card-top"><span class="badge ${bdg}">${n.label||'중립'}</span><span class="news-source">${n.source||''} · ${n.published||''}</span></div>
        <div class="news-title">${n.title||''}</div>
      </div>`;
    }).join('');
  } catch(e) {
    newsEl.innerHTML = '';
  }
}

async function loadWatchlistDetailNews(code, name, containerEl) {
  const newsEl = containerEl.querySelector('#watchlist-news-section');
  if (!newsEl) return;
  newsEl.innerHTML = '<div style="text-align:center;padding:12px;color:#8E8E9A;font-size:12px;">뉴스 로딩 중...</div>';
  try {
    const r = await api('GET', `/api/stock/${code}/news`);
    const items = (r.news || []).slice(0, 3);
    if (!items.length) { newsEl.innerHTML = ''; return; }
    newsEl.innerHTML = items.map(n => {
      const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
      return `<div class="news-card">
        <div class="news-card-top"><span class="badge ${bdg}">${n.label||'중립'}</span><span class="news-source">${n.source||''} · ${n.published||''}</span></div>
        <div class="news-title">${n.title||''}</div>
      </div>`;
    }).join('');
  } catch(e) {
    newsEl.innerHTML = '';
  }
}

function renderWatchlistDetail(d, el, code, name) {
  const item = d.item || { code, name };
  const a = d.analysis || {};
  if (a.error) {
    el.innerHTML = `<div class="loading" style="flex-direction:column;gap:6px;padding:32px 16px;">
      <span style="color:#E24B4A;">데이터 조회 실패</span>
      <span style="font-size:11px;color:#8E8E9A;word-break:break-all;">${a.error}</span>
    </div>`;
    return;
  }
  const timing = a.timing || {};
  const curPrice = a.cur_price || a.current_price || 0;
  const chgPct = a.cur_change_pct || 0;
  const chg = a.cur_change || 0;

  const rsiVal = a.rsi ? Math.round(a.rsi) : null;
  const boll = a.bollinger || {};
  const bollPos = boll.position !== undefined ? boll.position : 0.5;
  const ma20Val = a.ma20;
  const ma60Val = a.ma60;
  const gap20Raw = a.gap20;
  const gap20 = gap20Raw ? (gap20Raw * 100).toFixed(1) : null;
  const invList = Array.isArray(a.inv_list) ? a.inv_list : [];
  const foreignNet = a.foreign_net_3d || 0;
  const instNet = a.institution_net_3d || 0;
  const badges = Array.isArray(a.badges) ? a.badges : [];
  const verdict = a.verdict || '';

  // RSI 해석
  const rsiColor = rsiVal >= 70 ? '#E24B4A' : rsiVal <= 30 ? '#185FA5' : rsiVal >= 60 ? '#BA7517' : '#30D158';
  let rsiInterp = '', rsiIcon = '🟢';
  if (rsiVal !== null) {
    if (rsiVal >= 70)      { rsiInterp = `RSI ${rsiVal}으로 <b>과열 구간</b>이에요. 너무 빠르게 올라온 상태예요. 추가 상승보다 숨 고르기 가능성이 높아요.`; rsiIcon='🔴'; }
    else if (rsiVal <= 30) { rsiInterp = `RSI ${rsiVal}으로 <b>과매도 구간</b>이에요. 너무 많이 떨어진 상태예요. 단기 반등 시도가 나올 수 있어요.`; rsiIcon='🟢'; }
    else if (rsiVal >= 60) { rsiInterp = `RSI ${rsiVal}으로 <b>정상 범위 상단</b>이에요. 과열도 침체도 아닌 건강한 상승세예요.`; rsiIcon='🟡'; }
    else if (rsiVal <= 40) { rsiInterp = `RSI ${rsiVal}으로 <b>정상 범위 하단</b>이에요. 힘이 빠지는 구간이지만 아직 위험하진 않아요.`; rsiIcon='🟡'; }
    else                   { rsiInterp = `RSI ${rsiVal}으로 <b>정상 범위</b>예요. 과열도 침체도 아닌 건강한 상태예요.`; rsiIcon='🟢'; }
  }

  // 이격도 해석
  const g = gap20 ? parseFloat(gap20) : 100;
  let gapInterp = '', gapIcon = '🟢';
  if (g >= 115)     { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(g-100).toFixed(0)}% 위</b>에 있어요. 용수철처럼 평균으로 되돌아오려는 힘이 강해요.`; gapIcon='⚠️'; }
  else if (g >= 105){ gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(g-100).toFixed(0)}% 위</b>에 있어요. 약간 올라온 상태지만 아직 과열은 아니에요.`; gapIcon='🟡'; }
  else if (g <= 85) { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(100-g).toFixed(0)}% 아래</b>에 있어요. 많이 떨어진 상태로 반등 가능성이 있어요.`; gapIcon='🟢'; }
  else if (g <= 95) { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균보다 <b>${(100-g).toFixed(0)}% 아래</b>에 있어요. 평균선 아래지만 크게 이탈한 건 아니에요.`; gapIcon='🟡'; }
  else              { gapInterp = `이격도 ${g.toFixed(0)}%로 20일 평균 근처에 있어요. 안정적인 위치예요.`; gapIcon='🟢'; }

  // 볼린저 해석
  let bollInterp = '', bollIcon = '🟡';
  if (bollPos >= 0.8)     { bollInterp = '볼린저밴드 <b>상단 근처</b>에요. 주가가 터널 천장에 닿아있어요. 여기서 저항을 받으면 단기 조정이 올 수 있어요.'; bollIcon='⚠️'; }
  else if (bollPos <= 0.2){ bollInterp = '볼린저밴드 <b>하단 근처</b>예요. 주가가 터널 바닥에 있어요. 여기서 지지를 받으면 반등이 나올 수 있어요.'; bollIcon='🟢'; }
  else                    { bollInterp = '볼린저밴드 <b>중간 구간</b>에 있어요. 상단 또는 하단 돌파 방향을 지켜보세요.'; bollIcon='🟡'; }
  const bollLbl = bollPos <= 0.2 ? '하단 근처' : bollPos >= 0.8 ? '상단 근처' : '중간';

  // 기술 지표 배지
  const rsiBarW = rsiVal || 50;
  const rsiStatus = rsiVal >= 70 ? '과매수' : rsiVal <= 30 ? '과매도' : '정상';
  const rsiStatusCls = rsiVal >= 70 || rsiVal <= 30 ? 'badge-sell' : 'badge-buy';
  const gapStatus = g >= 95 && g <= 115 ? '평균선 근처' : '이격 과대';
  const gapStatusCls = g >= 95 && g <= 115 ? 'badge-ok' : 'badge-sell';
  const bollStatusCls = bollPos <= 0.3 ? 'badge-buy' : bollPos >= 0.8 ? 'badge-sell' : 'badge-ok';

  let ma20Row = '', ma60Row = '';
  if (ma20Val) {
    const d20 = (curPrice - ma20Val) / ma20Val * 100;
    const scls = d20 >= 0 ? 'badge-ok' : 'badge-sell';
    ma20Row = `<div class="ind-row"><span class="ind-label">20일선</span><div class="ind-right"><span class="ind-val">${fmtNum(Math.round(ma20Val))}</span><span class="badge ${scls}" style="font-size:10px;">${d20>=0?'위':'아래'} ${Math.abs(d20).toFixed(1)}%</span></div></div>`;
  }
  if (ma60Val) {
    const d60 = (curPrice - ma60Val) / ma60Val * 100;
    const scls = d60 >= 0 ? 'badge-ok' : 'badge-sell';
    ma60Row = `<div class="ind-row"><span class="ind-label">60일선</span><div class="ind-right"><span class="ind-val">${fmtNum(Math.round(ma60Val))}</span><span class="badge ${scls}" style="font-size:10px;">${d60>=0?'위':'아래'} ${Math.abs(d60).toFixed(1)}%</span></div></div>`;
  }

  // 지지선 배지
  const supBadgeW = (dist) => {
    if (dist >= 0)  return `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EAF3DE;color:#27500A;">현재위</span>`;
    if (dist >= -5) return `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#FAEEDA;color:#633806;">근접</span>`;
    return             `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EEEDFE;color:#3C3489;">주요지지</span>`;
  };
  let supRowsNew = '';
  if (ma20Val) {
    const dv = (curPrice - ma20Val) / ma20Val * 100;
    supRowsNew += `<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma20Val))}원</span><span class="sup-dist ${dv>=0?'up':'down'}">${dv>=0?'+':''}${dv.toFixed(1)}%</span>${supBadgeW(dv)}</div></div>`;
  }
  if (boll.lower) {
    const dv = (curPrice - boll.lower) / boll.lower * 100;
    supRowsNew += `<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(boll.lower))}원</span><span class="sup-dist ${dv>=0?'up':'down'}">${dv>=0?'+':''}${dv.toFixed(1)}%</span>${supBadgeW(dv)}</div></div>`;
  }
  if (ma60Val) {
    const dv = (curPrice - ma60Val) / ma60Val * 100;
    supRowsNew += `<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma60Val))}원</span><span class="sup-dist ${dv>=0?'up':'down'}">${dv>=0?'+':''}${dv.toFixed(1)}%</span>${supBadgeW(dv)}</div></div>`;
  }

  // 수급
  const fMax = Math.max(Math.abs(foreignNet), Math.abs(instNet), 1);
  const fBarW = Math.min(Math.abs(foreignNet) / fMax * 80, 80);
  const iBarW = Math.min(Math.abs(instNet) / fMax * 80, 80);
  const fCls = foreignNet >= 0 ? 'up' : 'down';
  const iCls = instNet >= 0 ? 'up' : 'down';
  const fBarCls = foreignNet >= 0 ? 'bar-buy' : 'bar-sell';
  const iBarCls = instNet >= 0 ? 'bar-buy' : 'bar-sell';
  const fChips = invList.map(r => {
    const v = r.foreign; const c = v >= 0 ? 'chip-buy' : 'chip-sell';
    return `<span class="day-chip ${c}">${v>=0?'+':''}${Math.round(v/1000)}K</span>`;
  }).join('');
  const iChips = invList.map(r => {
    const v = r.inst; const c = v >= 0 ? 'chip-buy' : 'chip-sell';
    return `<span class="day-chip ${c}">${v>=0?'+':''}${Math.round(v/1000)}K</span>`;
  }).join('');

  // 배지 & verdict
  const badgesHtml = (badges||[]).filter(b => typeof b === 'string').map(b => {
    const cls = b.includes('매도')||b.includes('과열')||b.includes('손절') ? 'badge-sell' :
                b.includes('매수')||b.includes('정배열')||b.includes('지지') ? 'badge-buy' :
                b.includes('주의')||b.includes('경고') ? 'badge-warn' : 'badge-ok';
    return `<span class="badge ${cls}">${b}</span>`;
  }).join('');

  // 타이밍 판정 섹션
  let timingHtml = '';
  if (timing.label) {
    const tc = timing.badge_type === 'buy' ? 'badge-buy' : timing.badge_type === 'sell' ? 'badge-sell' : 'badge-warn';
    timingHtml = `<div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-clock-check" style="font-size:15px;color:#5B5BD6;"></i>매수 타이밍 판정</div>
      <div class="card">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span class="badge ${tc}" style="font-size:13px;padding:5px 12px;flex-shrink:0;">${timing.label}</span>
          ${timing.reason ? `<span style="font-size:12px;color:#3C3C43;">${timing.reason}</span>` : ''}
        </div>
      </div>
    </div>`;
  }

  // AI 추천 목표가/손절가
  const targets = a.targets || {};
  const tp = targets.target_price;
  const sp2 = targets.stop_price;
  let priceTargetHtml = '';
  if (tp && sp2 && curPrice) {
    const tu = targets.target_upside;
    const sd = targets.stop_downside;
    const tb = targets.target_basis || '';
    const sb = targets.stop_basis || '';
    const rr = targets.risk_reward || 0;
    const rrCls = rr >= 2 ? '#27500A' : rr >= 1 ? '#BA7517' : '#A32D2D';
    const rrLbl = rr >= 2 ? '✅ 양호' : rr >= 1 ? '⚠️ 보통' : '❌ 불리';
    priceTargetHtml = `<div class="section">
      <div class="sec-title"><i class="ti ti-target" style="font-size:15px;color:#5B5BD6;"></i>목표가 / 손절가 분석</div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
          <div>
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">추천 목표가</div>
            <div style="font-size:18px;font-weight:700;color:#27500A;">${fmtNum(tp)}</div>
            <div style="font-size:11px;color:#27500A;">+${tu}%</div>
            <div style="font-size:10px;color:#8E8E9A;margin-top:2px;">기준: ${tb}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">추천 손절가</div>
            <div style="font-size:18px;font-weight:700;color:#A32D2D;">${fmtNum(sp2)}</div>
            <div style="font-size:11px;color:#A32D2D;">${sd}%</div>
            <div style="font-size:10px;color:#8E8E9A;margin-top:2px;">기준: ${sb}</div>
          </div>
        </div>
        ${rr ? `<div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">리스크/리워드 비율</div>
          <div style="font-size:13px;font-weight:600;color:${rrCls};">1 : ${rr} ${rrLbl}</div>
          <div style="font-size:10px;color:#8E8E9A;margin-top:3px;">손실 1원 대비 수익 ${rr}원 기대 — 2 이상이면 진입 적합</div>
        </div>` : ''}
      </div>
    </div>`;
  }

  // 뉴스는 비동기 로드 (loadWatchlistDetailNews)
  const newsHtml = '';

  // 시스템 판단 텍스트 (보유종목과 동일한 상세 분석)
  const systemLines = [];
  if (rsiVal !== null) {
    const rsiStr = rsiVal <= 30 ? `RSI ${rsiVal}로 과매도 근접` : rsiVal >= 70 ? `RSI ${rsiVal}로 과열 구간` : `RSI ${rsiVal}로 정상 범위`;
    systemLines.push(rsiStr + (bollPos <= 0.2 ? ', 볼린저 하단 지지 시도 중이에요.' : bollPos >= 0.8 ? ', 볼린저 상단 저항 구간이에요.' : ', 볼린저 중간 구간이에요.'));
  }
  if (foreignNet < 0 && instNet < 0) systemLines.push('외국인·기관 모두 매도 중으로 수급 신호가 부정적이에요.');
  else if (foreignNet > 0 && instNet > 0) systemLines.push('외국인·기관 모두 순매수로 수급이 우호적이에요.');
  else if (foreignNet > 0) systemLines.push('외국인 순매수, 기관은 관망세예요.');
  else if (instNet > 0) systemLines.push('기관 순매수, 외국인은 관망세예요.');
  if (ma20Val && curPrice) {
    const d20 = (curPrice - ma20Val) / ma20Val * 100;
    systemLines.push(`20일선(${fmtNum(Math.round(ma20Val))}원) ${d20 >= 0 ? '위에서 유지된다면 단기 반등 가능성이 있어요.' : '아래로 이탈해 추세 회복 여부를 지켜봐야 해요.'}`);
  }
  if (verdict) systemLines.push(verdict);

  el.innerHTML = `
    <!-- 히어로 카드 (흰색) -->
    <div class="section" style="margin-top:0;">
      <div class="card" style="padding:16px;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:2px;">
          <div>
            <div style="font-size:18px;font-weight:700;color:#1A1A2E;">${item.name}</div>
            <div style="font-size:11px;color:#8E8E9A;margin-top:2px;">${item.code}</div>
          </div>
          ${timing.label ? `<span class="badge ${timing.badge_type==='buy'?'badge-buy':timing.badge_type==='sell'?'badge-sell':'badge-warn'}" style="font-size:11px;padding:4px 10px;">${timing.label}</span>` : ''}
        </div>
        <div style="display:flex;align-items:baseline;gap:8px;margin-top:10px;">
          <div style="font-size:28px;font-weight:800;color:#1A1A2E;">${fmtNum(curPrice)}원</div>
          ${(!chgPct&&!chg)?'<span style="font-size:10px;color:#8E8E9A;background:#F0F0F5;border-radius:4px;padding:2px 6px;">최근 종가</span>':''}
        </div>
        ${(chgPct||chg) ? `<div style="font-size:13px;margin-top:3px;color:${chgPct>=0?'#E24B4A':'#185FA5'};">
          ${chgPct>=0?'▲':'▼'} ${Math.abs(chg).toLocaleString()}원 (${Math.abs(chgPct).toFixed(2)}%)
        </div>` : '<div style="font-size:12px;color:#8E8E9A;margin-top:3px;">장 마감 · 전일 종가 기준</div>'}
        ${a.cur_high || a.cur_low ? `<div style="font-size:11px;color:#8E8E9A;margin-top:6px;">
          고가 ${fmtNum(a.cur_high||0)}원 &nbsp;저가 ${fmtNum(a.cur_low||0)}원 &nbsp;거래량 ${(a.cur_volume||0).toLocaleString()}
        </div>` : ''}
        ${timing.reason ? `<div style="border-top:1px solid #F0F0F5;margin:12px 0 8px;"></div>
        <div style="font-size:12px;color:#3C3C43;line-height:1.6;background:#F8F8FA;border-radius:10px;padding:10px 12px;">${timing.reason}</div>` : ''}
      </div>
    </div>

    <!-- TradingView 차트 -->
    <div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-chart-candle" style="font-size:15px;color:#5B5BD6;"></i>차트</div>
      <div style="border-radius:16px;overflow:hidden;background:#131722;">
        <div id="tv-chart-${code}"></div>
      </div>
    </div>

    <!-- 타이밍 판정 -->
    ${timingHtml}

    <!-- 기술 지표 -->
    <div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>기술적 지표</div>
      <div class="card">
        ${rsiVal !== null ? `<div class="ind-row">
          <span class="ind-label">RSI (14일)</span>
          <div class="ind-right">
            <div style="width:80px;height:6px;background:#F0F0F5;border-radius:3px;margin-right:8px;">
              <div style="width:${rsiBarW}%;height:6px;background:${rsiColor};border-radius:3px;"></div>
            </div>
            <span class="ind-val">${rsiVal}</span>
            <span class="badge ${rsiStatusCls}" style="font-size:10px;margin-left:4px;">${rsiStatus}</span>
          </div>
        </div>` : ''}
        ${gap20 ? `<div class="ind-row">
          <span class="ind-label">이격도 (20일)</span>
          <div class="ind-right"><span class="ind-val">${parseFloat(gap20).toFixed(0)}%</span><span class="badge ${gapStatusCls}" style="font-size:10px;margin-left:4px;">${gapStatus}</span></div>
        </div>` : ''}
        <div class="ind-row">
          <span class="ind-label">볼린저밴드</span>
          <div class="ind-right"><span class="ind-val">${bollLbl}</span><span class="badge ${bollStatusCls}" style="font-size:10px;margin-left:4px;">${bollPos<=0.3?'지지 시도':bollPos>=0.8?'과열':'보통'}</span></div>
        </div>
        ${ma20Row}${ma60Row}
      </div>
    </div>

    <!-- 지표 해석 -->
    ${rsiVal !== null ? `<div style="background:#EEEDFE;border-radius:16px;padding:16px 18px;margin:0 16px 12px;">
      <div style="font-size:12px;font-weight:700;color:#3C3489;margin-bottom:12px;display:flex;align-items:center;gap:6px;">
        <i class="ti ti-microscope" style="font-size:14px;"></i> 지금 이 숫자가 의미하는 것
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">${rsiIcon} RSI (상대강도지수)</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">${rsiInterp}</div>
        </div>
        ${gap20 ? `<div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">${gapIcon} 이격도 (20일 평균 기준)</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">${gapInterp}</div>
        </div>` : ''}
        <div style="background:rgba(255,255,255,0.6);border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;color:#534AB7;margin-bottom:4px;">${bollIcon} 볼린저밴드</div>
          <div style="font-size:11px;color:#3C3489;line-height:1.6;">${bollInterp}</div>
        </div>
      </div>
    </div>` : ''}

    <!-- 지지선 -->
    ${supRowsNew ? `<div class="section">
      <div class="sec-title"><i class="ti ti-barrier-block" style="font-size:15px;color:#5B5BD6;"></i>바닥 지지선</div>
      <div class="card">${supRowsNew}</div>
    </div>` : ''}

    <!-- 거래량 + 수급 SVG 차트 -->
    ${invList.length ? `<div class="section">
      <div class="sec-title"><i class="ti ti-chart-bar" style="font-size:15px;color:#5B5BD6;"></i>5일 거래량 · 수급 흐름</div>
      <div class="card" style="padding:14px;">
        ${_buildFlowChart(a.vol_list || [], invList)}
        <div style="display:flex;gap:16px;margin-top:10px;font-size:12px;">
          <span style="color:${foreignNet>=0?'#E24B4A':'#185FA5'};font-weight:600;">외국인 3일 ${foreignNet>=0?'+':''}${foreignNet.toLocaleString()}주</span>
          <span style="color:${instNet>=0?'#F5A623':'#30D158'};font-weight:600;">기관 3일 ${instNet>=0?'+':''}${instNet.toLocaleString()}주</span>
        </div>
      </div>
    </div>` : ''}

    <!-- 배지 -->
    ${badgesHtml ? `<div class="section">
      <div style="padding:0 16px 8px;"><div class="signal-badges">${badgesHtml}</div></div>
    </div>` : ''}

    <!-- 목표가/손절가 -->
    ${priceTargetHtml}

    <!-- 뉴스 (비동기 로드) -->
    <div class="section" id="watchlist-news-section">
      <div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>${item.name} 뉴스</div>
    </div>

    <!-- 시스템 판단 -->
    ${systemLines.length ? `<div class="section">
      <div class="card" style="background:#FFFBF0;border:1px solid #F5E6B2;">
        <div style="font-size:13px;font-weight:700;color:#8B6914;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
          <span style="font-size:15px;">☀️</span> 시스템 판단
        </div>
        <div style="font-size:13px;color:#3C3C43;line-height:1.8;">${systemLines.join('<br>')}</div>
      </div>
    </div>` : ''}

    <div style="padding:0 16px 16px;">
      <div class="warn-box" style="margin-bottom:10px;"><i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>투자 결정은 본인 책임입니다. 이 정보는 참고용이며 투자 권유가 아닙니다.</div>
      <button class="btn-danger" onclick="deleteWatchlist('${item.code}', '${item.name}')">
        <i class="ti ti-trash" style="font-size:16px;"></i> 관심종목 삭제
      </button>
    </div>`;

  _initTradingViewChart(code, `tv-chart-${code}`);
}

function _initTradingViewChart(stockCode, containerId) {
  const symbol = `KRX:${stockCode}`;
  const container = document.getElementById(containerId);
  if (!container) return;

  function _doInit() {
    container.innerHTML = '';
    new TradingView.widget({
      container_id: containerId,
      symbol: symbol,
      interval: 'D',
      timezone: 'Asia/Seoul',
      theme: 'dark',
      style: '1',
      locale: 'kr',
      toolbar_bg: '#131722',
      enable_publishing: false,
      hide_side_toolbar: true,
      hide_top_toolbar: false,
      save_image: false,
      height: 360,
      width: '100%',
      studies: ['RSI@tv-basicstudies', 'MACD@tv-basicstudies'],
      show_popup_button: false,
      allow_symbol_change: false,
    });
  }

  if (typeof TradingView !== 'undefined') {
    _doInit();
  } else {
    const s = document.createElement('script');
    s.src = 'https://s3.tradingview.com/tv.js';
    s.onload = _doInit;
    document.head.appendChild(s);
  }
}

function confirmDeleteWatchlist(code, name) {
  showConfirm({
    title: '관심종목 삭제',
    message: `<b>${name}</b>을(를) 삭제할까요?<br>삭제하면 되돌릴 수 없어요.`,
    confirmText: '삭제',
    onConfirm: async () => {
      try {
        await api('DELETE', `/api/watchlist/${code}`);
        _watchlistLoaded = false;
        loadWatchlist(true);
      } catch(e) { alert(e.message); }
    }
  });
}

async function deleteWatchlist(code, name) {
  if (!confirm(`${name}을(를) 관심종목에서 삭제할까요?`)) return;
  try {
    await api('DELETE', `/api/watchlist/${code}`);
    _watchlistLoaded = false;
    goBack();
  } catch(e) { alert(e.message); }
}

// ─────────────────────────────────────────────────────────
// 매집 스캐너
// ─────────────────────────────────────────────────────────
let _scannerLoaded = false;
async function loadScanner(force) {
  if (_scannerLoaded && !force) return;
  _scannerLoaded = true;
  const el = document.getElementById('scanner-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 스캔 중...</div>';
  try {
    const d = await api('GET', '/api/scanner');
    if (d.loading) {
      // 백그라운드 계산 중 — 10초 후 재시도
      el.innerHTML = '<div class="loading"><div class="spinner"></div> 종목 분석 중... (1~2분 소요)</div>';
      clearTimeout(_scannerPollTimer);
      _scannerPollTimer = setTimeout(() => { _scannerLoaded = false; loadScanner(true); }, 10000);
      return;
    }
    renderScanner(d, el);
  } catch(e) {
    el.innerHTML = `<div class="loading">스캔 데이터를 불러오지 못했습니다</div>`;
  }
}

let _scannerFilter = '전체';
let _scannerItems = [];

function renderScanner(d, el) {
  _scannerItems = d.results || d.stocks || [];
  if (!_scannerItems.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-chart-bar"></i>매집 신호 종목 없음</div>';
    return;
  }
  renderScannerList(el);
}

function renderScannerList(el) {
  el = el || document.getElementById('scanner-content');
  const items = _scannerItems;
  const filt = _scannerFilter;

  // 필터 적용
  let filtered = items;
  if (filt === '신뢰도 높음') filtered = items.filter(s => s.confidence === 'high');
  else if (filt === '거래량급증') filtered = items.filter(s => s.signals?.vol_surge);
  else if (filt === '수급연속') filtered = items.filter(s => s.signals?.foreign_buy && s.signals?.inst_buy);
  else if (filt === 'OBV상승') filtered = items.filter(s => s.signals?.obv_up);

  // 요약 카운트
  const highCnt = items.filter(s => s.confidence === 'high').length;
  const midCnt  = items.filter(s => s.confidence === 'mid').length;

  function buildCard(s, rank) {
    const sig = s.signals || {};
    const rsiVal = s.rsi ? Math.round(s.rsi) : null;
    const rsiColor = rsiVal >= 70 ? '#E24B4A' : rsiVal <= 35 ? '#30D158' : '#5B5BD6';
    const volRatio = s.volume_ratio ? (s.volume_ratio * 100).toFixed(0) : null;
    const obvTrend = s.obv?.trend === 'up';
    const chgPct = s.change_pct || 0;
    const confCls = s.confidence === 'high' ? 'high' : 'mid';
    const badgeLbl = s.confidence === 'high' ? `신뢰도 높음 ${s.score}/5` : `신뢰도 보통 ${s.score}/5`;
    const badgeCls = s.confidence === 'high' ? 'badge-ok' : 'badge-warn';
    const market = s.code && s.code[0] === '0' ? '코스닥' : '코스피';

    return `<div class="scanner-card ${confCls}" onclick="openScannerDetail(${rank})">
      <div class="sc-top">
        <span class="sc-rank">${rank+1}</span>
        <div class="stock-icon ${iconColors(s.name)}">${iconText(s.name)}</div>
        <div>
          <div class="stock-name">${s.name}</div>
          <div class="stock-sub" style="color:#8E8E9A;">${market} · ${s.code}</div>
        </div>
        <div class="stock-right">
          <div class="stock-price">${fmtNum(s.price||s.cur_price)}원</div>
          <div class="stock-change ${chgPct>=0?'up':'down'}">${chgPct>=0?'▲ +':'▼ '}${Math.abs(chgPct).toFixed(2)}%</div>
        </div>
      </div>
      <div class="sc-signal-dots">
        <div class="sc-sig-item"><div class="sc-sig-dot ${sig.vol_surge?'on':'off'}"></div><span class="sc-sig-text">거래량</span></div>
        <div class="sc-sig-item"><div class="sc-sig-dot ${sig.obv_up?'on':'off'}"></div><span class="sc-sig-text">OBV</span></div>
        <div class="sc-sig-item"><div class="sc-sig-dot ${sig.foreign_buy?'on':'off'}"></div><span class="sc-sig-text">외국인</span></div>
        <div class="sc-sig-item"><div class="sc-sig-dot ${sig.inst_buy?'on':'off'}"></div><span class="sc-sig-text">기관</span></div>
        <div class="sc-sig-item"><div class="sc-sig-dot ${sig.sideways?'on':'off'}"></div><span class="sc-sig-text">횡보</span></div>
      </div>
      ${rsiVal !== null ? `<div class="sc-rsi-row">
        <span class="sc-rsi-label">RSI</span>
        <div class="sc-rsi-bar"><div class="sc-rsi-fill" style="width:${rsiVal}%;background:${rsiColor};"></div></div>
        <span class="sc-rsi-val" style="color:${rsiColor};">${rsiVal}</span>
      </div>` : ''}
      ${volRatio ? `<div class="sc-obv-row">
        <span class="sc-obv-label">거래량 평균 대비</span>
        <span class="sc-obv-val"><i class="ti ti-trending-up" style="font-size:12px;"></i>+${volRatio}%</span>
      </div>` : ''}
      <div class="sc-card-bottom">
        <span class="badge ${badgeCls}">${badgeLbl}</span>
        <span class="sc-detail-btn">상세보기 <i class="ti ti-chevron-right" style="font-size:13px;"></i></span>
      </div>
    </div>`;
  }

  const highItems = filtered.filter(s => s.confidence === 'high');
  const midItems  = filtered.filter(s => s.confidence === 'mid');
  let allRanked = [...highItems, ...midItems];

  const filterBtns = ['전체','신뢰도 높음','거래량급증','수급연속','OBV상승'].map(f =>
    `<button class="scanner-filter-btn ${f===filt?'active':'inactive'}" onclick="_scannerFilter='${f}';renderScannerList();">${f}</button>`
  ).join('');

  el.innerHTML = `
    <div class="scanner-sum-row">
      <div class="scanner-sum-card"><div class="scanner-sum-label">신뢰도 높음</div><div class="scanner-sum-val" style="color:#3C3489;">${highCnt}</div></div>
      <div class="scanner-sum-card"><div class="scanner-sum-label">신뢰도 보통</div><div class="scanner-sum-val" style="color:#854F0B;">${midCnt}</div></div>
      <div class="scanner-sum-card"><div class="scanner-sum-label">전체 감지</div><div class="scanner-sum-val" style="color:#3B6D11;">${items.length}</div></div>
    </div>
    <div class="scanner-filter-row">${filterBtns}</div>
    ${highItems.length ? `<div class="section">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:12px;font-weight:600;color:#6B6B8A;display:flex;align-items:center;gap:5px;"><span style="width:6px;height:6px;border-radius:50%;background:#5B5BD6;display:inline-block;"></span>신뢰도 높음 (4~5/5)</span>
        <span style="font-size:11px;color:#5B5BD6;">점수순</span>
      </div>
      ${highItems.map((s,i) => buildCard(s,i)).join('')}
    </div>` : ''}
    ${midItems.length ? `<div class="section">
      <div style="margin-bottom:8px;">
        <span style="font-size:12px;font-weight:600;color:#6B6B8A;display:flex;align-items:center;gap:5px;"><span style="width:6px;height:6px;border-radius:50%;background:#BA7517;display:inline-block;"></span>신뢰도 보통 (3/5)</span>
      </div>
      ${midItems.map((s,i) => buildCard(s, highItems.length+i)).join('')}
    </div>` : ''}
    ${!filtered.length ? '<div class="empty-state"><i class="ti ti-filter-off"></i>해당 조건의 종목이 없습니다</div>' : ''}`;
}

function openScannerDetail(idx) {
  const s = _scannerItems[idx];
  if (!s) return;
  _prevScreen = 'scanner';
  document.getElementById('scanner-detail-name').textContent = s.name;
  document.getElementById('scanner-detail-code').textContent = `${s.code && s.code[0]==='0'?'코스닥':'코스피'} · ${s.code}`;
  const badgeEl = document.getElementById('scanner-detail-badge');
  badgeEl.textContent = `신뢰도 ${s.confidence==='high'?'높음':'보통'} ${s.score}/5`;
  badgeEl.className = `badge ${s.confidence==='high'?'badge-ok':'badge-warn'}`;
  showScreen('scanner-detail');
  renderScannerDetail(s);
}

function renderScannerDetail(s) {
  const el = document.getElementById('scanner-detail-content');
  const sig = s.signals || {};
  const rsiVal = s.rsi ? Math.round(s.rsi) : null;
  const rsiColor = rsiVal >= 70 ? '#E24B4A' : rsiVal <= 35 ? '#30D158' : '#5B5BD6';
  const boll = s.bollinger || {};
  const bollPos = boll.position !== undefined ? boll.position : 0.5;
  const bollLbl = bollPos <= 0.2 ? '하단 근처' : bollPos >= 0.8 ? '상단 근처' : '중간';
  const ma20 = s.ma20, ma60 = s.ma60;
  const cur = s.price || s.cur_price || 0;
  const chgPct = s.change_pct || 0;
  const volRatio = s.volume_ratio ? (s.volume_ratio * 100).toFixed(0) : null;
  const obvTrend = s.obv?.trend === 'up';
  const foreignNet = s.foreign_net_3d || 0;
  const instNet = s.institution_net_3d || 0;
  const invList = Array.isArray(s.inv_list) ? s.inv_list : [];

  // 기술 지표 상태
  const rsiStatus = rsiVal >= 70 ? '과매수' : rsiVal <= 30 ? '과매도' : '정상';
  const rsiStatusCls = rsiVal >= 70 || rsiVal <= 30 ? 'status-danger' : 'status-ok';
  const gap20 = s.gap20 ? (s.gap20 * 100).toFixed(1) : null;
  const gapStatus = gap20 && Math.abs(parseFloat(gap20)-100) <= 5 ? '정상' : '이격';
  const gapStatusCls = gapStatus === '정상' ? 'status-ok' : 'status-danger';

  let ma20Row = '', ma60Row = '';
  if (ma20 && cur) {
    const d = (cur - ma20) / ma20 * 100;
    ma20Row = `<div class="ind-row"><span class="ind-label">20일선</span><div class="ind-right"><span class="ind-val">${fmtNum(Math.round(ma20))}원</span><span class="ind-status ${d>=0?'status-ok':'status-danger'}">${d>=0?'위':'아래'}</span></div></div>`;
  }
  if (ma60 && cur) {
    const d = (cur - ma60) / ma60 * 100;
    ma60Row = `<div class="ind-row"><span class="ind-label">60일선</span><div class="ind-right"><span class="ind-val">${fmtNum(Math.round(ma60))}원</span><span class="ind-status ${d>=0?'status-ok':'status-danger'}">${d>=0?'위':'아래'}</span></div></div>`;
  }

  // 수급
  const fMax = Math.max(Math.abs(foreignNet), Math.abs(instNet), 1);
  const fBarW = Math.min(Math.abs(foreignNet)/fMax*80, 80);
  const iBarW = Math.min(Math.abs(instNet)/fMax*80, 80);
  const fChips = invList.map(r => { const v=r.foreign; return `<span class="day-chip ${v>=0?'chip-buy':'chip-sell'}">${v>=0?'+':''}${Math.round(v/1000)}K</span>`; }).join('');
  const iChips = invList.map(r => { const v=r.inst;    return `<span class="day-chip ${v>=0?'chip-buy':'chip-sell'}">${v>=0?'+':''}${Math.round(v/1000)}K</span>`; }).join('');

  // 지지선
  const supBadge = d => d>=0 ? `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EAF3DE;color:#27500A;">현재위</span>`
    : d>=-5 ? `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#FAEEDA;color:#633806;">근접</span>`
    : `<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EEEDFE;color:#3C3489;">주요지지</span>`;
  let supRows = '';
  if (ma20 && cur) { const d=(cur-ma20)/ma20*100; supRows+=`<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma20))}원</span><span class="sup-dist ${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span>${supBadge(d)}</div></div>`; }
  if (boll.lower && cur) { const d=(cur-boll.lower)/boll.lower*100; supRows+=`<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(boll.lower))}원</span><span class="sup-dist ${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span>${supBadge(d)}</div></div>`; }
  if (ma60 && cur) { const d=(cur-ma60)/ma60*100; supRows+=`<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma60))}원</span><span class="sup-dist ${d>=0?'up':'down'}">${d>=0?'+':''}${d.toFixed(1)}%</span>${supBadge(d)}</div></div>`; }

  el.innerHTML = `
    <!-- 현재가 -->
    <div class="scanner-price-section">
      <div class="scanner-current-price">${fmtNum(cur)}원</div>
      <div style="display:flex;gap:8px;margin-top:4px;">
        <span class="${chgPct>=0?'up':'down'}" style="font-size:14px;font-weight:600;">${chgPct>=0?'▲':'▼'} ${Math.abs(chgPct).toFixed(2)}%</span>
      </div>
      ${s.cur_high||s.cur_low ? `<div class="scanner-price-meta">
        <div class="scanner-pm-item">고가 <span>${fmtNum(s.cur_high||0)}원</span></div>
        <div class="scanner-pm-item">저가 <span>${fmtNum(s.cur_low||0)}원</span></div>
        <div class="scanner-pm-item">거래량 <span>${(s.cur_volume||0).toLocaleString()}</span></div>
      </div>` : ''}
    </div>

    <!-- TradingView 차트 -->
    <div class="section" style="margin-top:8px;">
      <div class="sec-title"><i class="ti ti-chart-candle" style="font-size:15px;color:#5B5BD6;"></i>차트</div>
      <div style="border-radius:16px;overflow:hidden;background:#131722;">
        <div id="tv-sc-${s.code}"></div>
      </div>
    </div>

    <!-- 매집 신호 점수 투명화 -->
    <div class="section" style="margin-top:8px;">
      <div class="sec-title"><i class="ti ti-radar" style="font-size:15px;color:#5B5BD6;"></i>매집신호 상세 <span style="font-size:11px;color:#8E8E9A;font-weight:400;">(5개 조건 충족 시 신뢰도 높음)</span></div>
      <div class="card" style="padding:14px;">
        ${[
          { key:'vol_surge',   label:'거래량 급증',  desc: volRatio ? `평균 대비 +${volRatio}% 거래량 폭발 (기준: 평균의 2배↑)` : '평균 거래량 2배 이상 조건', icon:'ti-chart-bar' },
          { key:'obv_up',      label:'OBV 상승',     desc: `매수세 누적 지표 상승 중 (거래량·가격 방향 동일)`, icon:'ti-trending-up' },
          { key:'foreign_buy', label:'외국인 순매수', desc: foreignNet ? `최근 3일 +${Math.abs(foreignNet).toLocaleString()}주 순매수` : '최근 3일 외국인 순매수 조건', icon:'ti-world' },
          { key:'inst_buy',    label:'기관 순매수',   desc: instNet ? `최근 3일 +${Math.abs(instNet).toLocaleString()}주 순매수` : '최근 3일 기관 순매수 조건', icon:'ti-building-bank' },
          { key:'sideways',    label:'가격 횡보',     desc: '박스권 눌림 — 매집 후 급등 전 전형적 패턴', icon:'ti-arrows-horizontal' },
        ].map(item => {
          const ok = sig[item.key];
          return `<div style="display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid #F0F0F5;">
            <div style="width:28px;height:28px;border-radius:50%;background:${ok?'#3B6D11':'#8E8E9A'};display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;">
              <i class="ti ${item.icon}" style="font-size:14px;color:#fff;"></i>
            </div>
            <div style="flex:1;">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
                <span style="font-size:13px;font-weight:600;color:${ok?'#1A1A2E':'#8E8E9A'};">${item.label}</span>
                <span style="font-size:10px;padding:2px 7px;border-radius:5px;background:${ok?'#EAF3DE':'#F0F0F5'};color:${ok?'#27500A':'#8E8E9A'};">${ok?'✅ 충족':'❌ 미충족'}</span>
              </div>
              <div style="font-size:11px;color:#8E8E9A;line-height:1.5;">${item.desc}</div>
            </div>
          </div>`;
        }).join('')}
        <div style="display:flex;align-items:center;justify-content:space-between;padding-top:10px;">
          <span style="font-size:13px;color:#3C3C43;">종합 점수</span>
          <div style="display:flex;gap:4px;">
            ${[1,2,3,4,5].map(i => `<div style="width:18px;height:18px;border-radius:50%;background:${i<=s.score?'#5B5BD6':'#F0F0F5'};"></div>`).join('')}
            <span style="font-size:13px;font-weight:700;color:#5B5BD6;margin-left:6px;">${s.score}/5</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 기술 지표 -->
    <div class="section">
      <div class="sec-title"><i class="ti ti-activity" style="font-size:15px;color:#5B5BD6;"></i>기술적 지표</div>
      <div class="card">
        ${rsiVal !== null ? `<div class="ind-row"><span class="ind-label">RSI (14일)</span><div class="ind-right"><div class="rsi-bar-wrap"><div class="rsi-bar-fill" style="width:${rsiVal}%;background:${rsiColor};"></div></div><span class="ind-val">${rsiVal}</span><span class="ind-status ${rsiStatusCls}">${rsiStatus}</span></div></div>` : ''}
        ${gap20 ? `<div class="ind-row"><span class="ind-label">이격도 (20일)</span><div class="ind-right"><span class="ind-val">${gap20}%</span><span class="ind-status ${gapStatusCls}">${gapStatus}</span></div></div>` : ''}
        <div class="ind-row"><span class="ind-label">볼린저밴드</span><div class="ind-right"><span class="ind-val">${bollLbl}</span><span class="ind-status ${bollPos<=0.3?'status-ok':bollPos>=0.8?'status-danger':'status-ok'}">${bollPos<=0.3?'지지권':bollPos>=0.8?'과열':'정상'}</span></div></div>
        ${ma20Row}${ma60Row}
      </div>
    </div>

    <!-- 거래량 + 수급 SVG 차트 -->
    ${(invList.length || s.vol_list?.length) ? `<div class="section">
      <div class="sec-title"><i class="ti ti-chart-bar" style="font-size:15px;color:#5B5BD6;"></i>5일 거래량 · 수급 흐름</div>
      <div class="card" style="padding:14px;">
        ${_buildFlowChart(s.vol_list || [], invList)}
      </div>
    </div>` : ''}

    <!-- 지지선 -->
    ${supRows ? `<div class="section">
      <div class="sec-title"><i class="ti ti-barrier-block" style="font-size:15px;color:#5B5BD6;"></i>바닥 지지선</div>
      <div class="card">${supRows}</div>
    </div>` : ''}

    <!-- 시스템 판단 -->
    ${s.verdict ? `<div class="advice-box">
      <div class="advice-title"><i class="ti ti-bulb" style="font-size:15px;"></i>시스템 판단</div>
      <div class="advice-text">${s.verdict}</div>
    </div>` : ''}

    <div style="padding:0 16px 20px;">
      <div class="warn-box"><i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>투자 결정은 본인 책임입니다. 이 정보는 참고용이며 투자 권유가 아닙니다.</div>
    </div>`;

  _initTradingViewChart(s.code, `tv-sc-${s.code}`);
}

function _buildFlowChart(volList, invList) {
  const n = Math.max(volList.length, invList.length, 1);
  const W = 280, barW = Math.floor((W - (n-1)*4) / n);
  const H_VOL = 50, H_FLOW = 40;

  // 거래량 바
  const maxVol = Math.max(...volList.map(d => d.volume), 1);
  const volBars = volList.map((d, i) => {
    const h = Math.max(Math.round(d.volume / maxVol * H_VOL), 2);
    const x = i * (barW + 4);
    const label = d.date ? d.date.slice(5) : '';
    return `<rect x="${x}" y="${H_VOL - h}" width="${barW}" height="${h}" rx="2" fill="#5B5BD6" opacity="0.8"/>
      <text x="${x + barW/2}" y="${H_VOL + 11}" text-anchor="middle" font-size="8" fill="#8E8E9A">${label}</text>`;
  }).join('');

  // 외국인·기관 수급 바 (양수=빨강, 음수=파랑)
  const maxFlow = Math.max(...invList.flatMap(d => [Math.abs(d.foreign), Math.abs(d.inst)]), 1);
  const midY = H_FLOW / 2;
  const flowBars = invList.map((d, i) => {
    const x = i * (barW + 4);
    const halfW = Math.floor(barW / 2) - 1;
    const fH = Math.max(Math.round(Math.abs(d.foreign) / maxFlow * midY), 1);
    const iH = Math.max(Math.round(Math.abs(d.inst) / maxFlow * midY), 1);
    const fy = d.foreign >= 0 ? midY - fH : midY;
    const iy = d.inst >= 0 ? midY - iH : midY;
    return `<rect x="${x}" y="${fy}" width="${halfW}" height="${fH}" rx="1" fill="${d.foreign>=0?'#E24B4A':'#185FA5'}"/>
      <rect x="${x+halfW+1}" y="${iy}" width="${halfW}" height="${iH}" rx="1" fill="${d.inst>=0?'#F5A623':'#30D158'}"/>`;
  }).join('');

  return `
    <div style="font-size:11px;font-weight:600;color:#3C3C43;margin-bottom:6px;">거래량 추이</div>
    <svg viewBox="0 0 ${W} ${H_VOL+14}" style="width:100%;overflow:visible;">${volBars}</svg>
    <div style="display:flex;gap:12px;margin:10px 0 6px;font-size:10px;color:#8E8E9A;align-items:center;">
      <span style="font-weight:600;color:#3C3C43;">외국인·기관 수급</span>
      <span><span style="display:inline-block;width:8px;height:8px;background:#E24B4A;border-radius:2px;margin-right:3px;"></span>외국인매수</span>
      <span><span style="display:inline-block;width:8px;height:8px;background:#185FA5;border-radius:2px;margin-right:3px;"></span>외국인매도</span>
      <span><span style="display:inline-block;width:8px;height:8px;background:#F5A623;border-radius:2px;margin-right:3px;"></span>기관매수</span>
    </div>
    <svg viewBox="0 0 ${W} ${H_FLOW}" style="width:100%;overflow:visible;">
      <line x1="0" y1="${midY}" x2="${W}" y2="${midY}" stroke="#F0F0F5" stroke-width="1"/>
      ${flowBars}
    </svg>`;
}

// ─────────────────────────────────────────────────────────
// 앱 초기화
// ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // 엔터키로 로그인
  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });
  document.getElementById('reg-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') doRegister();
  });

  // 검색 결과 외부 클릭 시 닫기
  document.addEventListener('click', e => {
    if (!e.target.closest('.search-wrap')) {
      document.querySelectorAll('.search-results').forEach(el => el.style.display = 'none');
    }
  });

  if (_token) {
    afterLogin();
  } else {
    showScreen('login');
  }
});
