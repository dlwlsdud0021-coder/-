// ─────────────────────────────────────────────────────────
// 포켓주식 앱 JS
// ─────────────────────────────────────────────────────────

const API = '';  // 같은 서버에서 서빙되므로 빈 문자열

// ─────────────────────────────────────────────────────────
// 상태
// ─────────────────────────────────────────────────────────
let _token = localStorage.getItem('pk_token') || '';
let _username = localStorage.getItem('pk_user') || '';
let _currentTab = 'home';
let _prevScreen = '';
let _allNews = [];
let _allHoldings = [];
let _allWatchlist = [];

// ─────────────────────────────────────────────────────────
// API 유틸
// ─────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (_token) opts.headers['Authorization'] = 'Bearer ' + _token;
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || '오류가 발생했습니다');
  return data;
}

// ─────────────────────────────────────────────────────────
// 화면 전환
// ─────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-' + id).classList.add('active');
  const nav = document.getElementById('bottom-nav');
  const noNav = ['login', 'register', 'holding-detail', 'watchlist-detail', 'news-detail', 'index-detail'];
  nav.style.display = noNav.includes(id) ? 'none' : 'flex';
}

function switchTab(tab) {
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
}

function goBack() {
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
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 시장 분석 중...</div>';
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
      <div class="forecast-card">
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
        <div class="warn-box"><i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>${fWarn}</div>
      </div>
    </div>
    ${investorHtml}`;
}

function buildInvestorSection(investor) {
  if (!investor || !investor.length) return '';
  // 최근 5일 합계로 방향 판단
  const total5 = investor.reduce((acc, r) => ({
    foreign: acc.foreign + (r.foreign || 0),
    inst: acc.inst + (r.inst || 0),
  }), { foreign: 0, inst: 0 });
  const fDir = total5.foreign > 0 ? '순매수' : '순매도';
  const iDir = total5.inst > 0 ? '순매수' : '순매도';
  const fCls = total5.foreign > 0 ? 'up' : 'down';
  const iCls = total5.inst > 0 ? 'up' : 'down';

  const rows = [...investor].reverse().map(r => {
    const fc = r.foreign > 0 ? 'up' : 'down';
    const ic = r.inst > 0 ? 'up' : 'down';
    const f = (r.foreign / 1e8).toFixed(0);
    const i = (r.inst / 1e8).toFixed(0);
    return `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:0.5px solid #F0F0F5;font-size:13px;">
      <span style="color:#8E8E9A;min-width:56px;">${r.date.slice(5)}</span>
      <span class="${fc}" style="flex:1;text-align:center;">외국인<br><b>${r.foreign>0?'+':''}${f}억</b></span>
      <span class="${ic}" style="flex:1;text-align:center;">기관<br><b>${r.inst>0?'+':''}${i}억</b></span>
    </div>`;
  }).join('');

  return `
    <div class="section">
      <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (5일)</div>
      <div class="card">
        <div style="display:flex;gap:10px;margin-bottom:12px;">
          <div style="flex:1;text-align:center;padding:10px 6px;background:#F8F8FA;border-radius:10px;">
            <div style="font-size:11px;color:#8E8E9A;margin-bottom:4px;">외국인 5일 합계</div>
            <div class="${fCls}" style="font-size:16px;font-weight:700;">${total5.foreign>0?'+':''}${(total5.foreign/1e8).toFixed(0)}억</div>
            <div class="${fCls}" style="font-size:11px;">${fDir}</div>
          </div>
          <div style="flex:1;text-align:center;padding:10px 6px;background:#F8F8FA;border-radius:10px;">
            <div style="font-size:11px;color:#8E8E9A;margin-bottom:4px;">기관 5일 합계</div>
            <div class="${iCls}" style="font-size:16px;font-weight:700;">${total5.inst>0?'+':''}${(total5.inst/1e8).toFixed(0)}억</div>
            <div class="${iCls}" style="font-size:11px;">${iDir}</div>
          </div>
        </div>
        ${rows}
      </div>
    </div>`;
}

// ─────────────────────────────────────────────────────────
// 뉴스 탭
// ─────────────────────────────────────────────────────────
let _newsLoaded = false;
let _newsFilter = '전체';
async function loadNews(force) {
  if (_newsLoaded && !force) return;
  _newsLoaded = true;
  const el = document.getElementById('news-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 뉴스 불러오는 중...</div>';
  try {
    const d = await api('GET', '/api/news');
    _allNews = d.news || [];
    renderNews();
  } catch(e) {
    el.innerHTML = `<div class="loading">뉴스를 불러오지 못했습니다</div>`;
  }
}

function filterNews(filter, btn) {
  _newsFilter = filter;
  document.querySelectorAll('#news-filter-row .filter-btn').forEach(b => {
    b.className = 'filter-btn ' + (b === btn ? 'active' : 'inactive');
  });
  renderNews();
}

function renderNews() {
  const el = document.getElementById('news-content');
  let news = _allNews;
  if (_newsFilter !== '전체') {
    const map = { '긍정': 'positive', '부정': 'negative', '혼조': 'mixed' };
    news = news.filter(n => n.sentiment === map[_newsFilter]);
  }
  if (!news.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-news"></i>뉴스가 없습니다</div>';
    return;
  }
  const html = news.map((n, i) => {
    const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
    const lbl = n.label || (n.sentiment === 'positive' ? '긍정' : n.sentiment === 'negative' ? '부정' : '혼조');
    const borderClass = n.sentiment === 'positive' ? 'important' : n.sentiment === 'negative' ? 'negative' : '';
    const briefHtml = n.brief ? `<div class="news-brief">💡 ${n.brief}</div>` : '';
    const hasDetail = !!(n.ai_summary || n.strategy || n.summary);
    const chevron = hasDetail ? `<i class="ti ti-chevron-right" style="color:#C7C7CC;font-size:18px;flex-shrink:0;"></i>` : '';
    return `<div class="news-card ${borderClass} ${hasDetail?'clickable':''}" ${hasDetail?`onclick="openNewsDetail(${i})"`:''}>
      <div class="news-card-top">
        <span class="badge ${bdg}">${lbl}</span>
        <span class="news-source">${n.source||''} · ${n.published||''}</span>
        ${chevron}
      </div>
      <div class="news-title">${n.title||''}</div>
      ${briefHtml}
    </div>`;
  }).join('');
  el.innerHTML = `<div class="section" style="margin-top:12px;">${html}</div>`;
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

function renderIndexDetail(d, el) {
  const name = d.name || 'KOSPI';
  const info = d.info || {};
  const ma = d.ma || {};
  const investor = d.investor || [];
  const sectors = d.sectors || [];
  const analysis = d.analysis || [];

  const cur = info.current || 0;
  const chg = info.change || 0;
  const chgPct = info.change_pct || 0;
  const isUp = chgPct >= 0;

  // 이동평균선 카드
  const ma20 = ma.ma20 ? ma.ma20.toFixed(2) : '-';
  const ma60 = ma.ma60 ? ma.ma60.toFixed(2) : '-';
  const dist20 = ma.ma20_dist_pct !== undefined ? (ma.ma20_dist_pct > 0 ? '+' : '') + ma.ma20_dist_pct.toFixed(2) + '%' : '-';
  const dist60 = ma.ma60_dist_pct !== undefined ? (ma.ma60_dist_pct > 0 ? '+' : '') + ma.ma60_dist_pct.toFixed(2) + '%' : '-';
  const trend = ma.trend || '-';
  const trendColor = trend.includes('상승') ? '#E24B4A' : trend.includes('하락') ? '#185FA5' : '#8E8E9A';
  const gcBadge = ma.golden_cross
    ? `<span class="badge badge-buy">정배열 ✓</span>`
    : `<span class="badge badge-sell">역배열</span>`;
  const a20Badge = ma.above_ma20
    ? `<span class="badge badge-ok">20일선 위</span>`
    : `<span class="badge badge-sell">20일선 아래</span>`;
  const a60Badge = ma.above_ma60
    ? `<span class="badge badge-ok">60일선 위</span>`
    : `<span class="badge badge-sell">60일선 아래</span>`;

  // 외국인/기관 수급 (최근 5일)
  let investorHtml = '';
  if (investor.length) {
    const rows = investor.slice().reverse().map(r => {
      const fCls = r.foreign > 0 ? 'up' : 'down';
      const iCls = r.inst > 0 ? 'up' : 'down';
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:0.5px solid #F0F0F5;font-size:13px;">
        <span style="color:#8E8E9A;min-width:70px;">${r.date.slice(5)}</span>
        <span class="${fCls}" style="min-width:80px;text-align:right;">외국인 ${r.foreign > 0 ? '+' : ''}${(r.foreign/1e8).toFixed(0)}억</span>
        <span class="${iCls}" style="min-width:80px;text-align:right;">기관 ${r.inst > 0 ? '+' : ''}${(r.inst/1e8).toFixed(0)}억</span>
      </div>`;
    }).join('');
    investorHtml = `
      <div class="section">
        <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (최근 5일)</div>
        <div class="card">${rows}</div>
      </div>`;
  }

  // 섹터 퍼포먼스
  let sectorHtml = '';
  if (sectors.length) {
    const bars = sectors.map(s => {
      const cls = s.pct >= 0 ? 'up' : 'down';
      const barW = Math.min(Math.abs(s.pct) * 10, 100);
      const barColor = s.pct >= 0 ? '#E24B4A' : '#185FA5';
      return `<div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px;">
          <span style="font-weight:500;">${s.name}</span>
          <span class="${cls}">${s.pct >= 0 ? '+' : ''}${s.pct}%</span>
        </div>
        <div style="height:5px;background:#F0F0F5;border-radius:3px;">
          <div style="height:5px;width:${barW}%;background:${barColor};border-radius:3px;"></div>
        </div>
      </div>`;
    }).join('');
    sectorHtml = `
      <div class="section">
        <div class="sec-title"><i class="ti ti-chart-bar" style="font-size:15px;color:#5B5BD6;"></i>섹터별 등락률</div>
        <div class="card">${bars}</div>
      </div>`;
  }

  // AI 시장 분석
  let aiHtml = '';
  if (analysis.length) {
    const dotColors = ['dot-blue', 'dot-green', 'dot-orange'];
    const items = analysis.map((a, i) => `
      <div class="analysis-item">
        <div class="analysis-label"><div class="dot ${dotColors[i] || 'dot-blue'}"></div>${a.label || '분석'}</div>
        <div class="analysis-text">${a.text || ''}</div>
      </div>`).join('');
    aiHtml = `
      <div class="section">
        <div class="sec-title"><i class="ti ti-search" style="font-size:15px;color:#5B5BD6;"></i>AI 시장 분석</div>
        <div class="card">${items}</div>
      </div>`;
  }

  el.innerHTML = `
    <div class="detail-hero">
      <div class="detail-name">${name}</div>
      <div class="detail-price" style="${isUp ? '' : 'color:#fff;'}">${cur.toLocaleString('ko-KR', {minimumFractionDigits:2, maximumFractionDigits:2})}</div>
      <div style="font-size:15px;margin-top:4px;opacity:0.9;">${isUp ? '▲' : '▼'} ${Math.abs(chg).toFixed(2)} (${isUp ? '+' : ''}${chgPct.toFixed(2)}%)</div>
    </div>
    <div class="section" style="margin-top:12px;">
      <div class="sec-title"><i class="ti ti-trending-up" style="font-size:15px;color:#5B5BD6;"></i>이동평균선 분석</div>
      <div class="card">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
          ${gcBadge} ${a20Badge} ${a60Badge}
        </div>
        <div style="font-size:15px;font-weight:700;color:${trendColor};margin-bottom:12px;">현재 추세: ${trend}</div>
        <div class="mini-grid" style="grid-template-columns:1fr 1fr;">
          <div class="mini-item">
            <div class="mini-label">20일 이동평균</div>
            <div class="mini-val">${ma20}</div>
            <div style="font-size:11px;color:#8E8E9A;margin-top:2px;">이격도 ${dist20}</div>
          </div>
          <div class="mini-item">
            <div class="mini-label">60일 이동평균</div>
            <div class="mini-val">${ma60}</div>
            <div style="font-size:11px;color:#8E8E9A;margin-top:2px;">이격도 ${dist60}</div>
          </div>
        </div>
      </div>
    </div>
    ${investorHtml}
    ${sectorHtml}
    ${aiHtml}`;
}

// ─────────────────────────────────────────────────────────
// 뉴스 상세
// ─────────────────────────────────────────────────────────
function openNewsDetail(idx) {
  const n = _allNews[idx];
  if (!n) return;
  _currentTab = 'news'; // goBack()이 뉴스탭으로 돌아오도록
  showScreen('news-detail');
  renderNewsDetail(n);
}

function renderNewsDetail(n) {
  const el = document.getElementById('news-detail-content');
  const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
  const lbl = n.label || (n.sentiment === 'positive' ? '긍정' : n.sentiment === 'negative' ? '부정' : '혼조');

  // 카테고리 칩
  const catChip = n.category ? `<span class="badge badge-ok" style="font-size:11px;">${n.category}</span>` : '';

  // 관련 종목
  const stocks = Array.isArray(n.related_stocks) ? n.related_stocks : [];
  const stocksHtml = stocks.length ? `
    <div style="margin-bottom:16px;">
      <div style="font-size:12px;color:#8E8E9A;margin-bottom:6px;">관련 종목</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;">
        ${stocks.map(s => `<span class="badge badge-ok">${s}</span>`).join('')}
      </div>
    </div>` : '';

  // 원문 요약
  const summaryHtml = n.summary ? `
    <div class="card" style="margin-bottom:12px;">
      <div style="font-size:12px;color:#8E8E9A;margin-bottom:6px;display:flex;align-items:center;gap:4px;">
        <i class="ti ti-file-text" style="font-size:13px;"></i> 내용
      </div>
      <div style="font-size:14px;color:#3C3C43;line-height:1.6;">${n.summary}</div>
    </div>` : '';

  // AI 분석 (무슨 뉴스 / 영향 / 대응)
  const aiHtml = n.ai_summary ? `
    <div class="card" style="margin-bottom:12px;background:linear-gradient(135deg,#F5F4FF 0%,#fff 100%);border:1px solid #E8E7FF;">
      <div style="font-size:14px;line-height:1.8;color:#3C3C43;">${n.ai_summary}</div>
    </div>` : '';

  // 투자 전략 (strategy)
  const strategyHtml = n.strategy ? `
    <div class="card" style="margin-bottom:12px;background:linear-gradient(135deg,#FFF8EC 0%,#fff 100%);border:1px solid #FFE0A0;">
      <div style="font-size:13px;font-weight:700;color:#FF9F0A;margin-bottom:8px;display:flex;align-items:center;gap:4px;">
        <i class="ti ti-target" style="font-size:15px;"></i> 투자 전략
      </div>
      <div style="font-size:14px;line-height:1.8;color:#3C3C43;">${n.strategy}</div>
    </div>` : '';

  // 외부 링크
  const linkHtml = n.link ? `
    <a href="${n.link}" target="_blank" rel="noopener" style="display:block;text-align:center;padding:12px;border:1px solid #E5E5EA;border-radius:12px;color:#5B5BD6;font-size:14px;font-weight:600;text-decoration:none;margin-bottom:12px;">
      <i class="ti ti-external-link" style="font-size:15px;"></i> 원문 기사 보기
    </a>` : '';

  el.innerHTML = `
    <div style="padding:16px 16px 0;">
      <div style="display:flex;gap:6px;align-items:center;margin-bottom:10px;">
        <span class="badge ${bdg}">${lbl}</span>
        ${catChip}
        <span style="font-size:11px;color:#8E8E9A;margin-left:auto;">${n.source||''} · ${n.published||''}</span>
      </div>
      <div style="font-size:17px;font-weight:700;color:#1C1C1E;line-height:1.5;margin-bottom:12px;">${n.title||''}</div>
      ${n.brief ? `<div class="news-brief" style="margin-bottom:16px;">💡 ${n.brief}</div>` : ''}
      ${stocksHtml}
      ${summaryHtml}
      ${aiHtml}
      ${strategyHtml}
      ${linkHtml}
    </div>`;
}

// ─────────────────────────────────────────────────────────
// 보유종목 탭
// ─────────────────────────────────────────────────────────
let _holdingsLoaded = false;
let _holdingsFilter = '전체';
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
  const el = document.getElementById('holdings-content');
  let list = _allHoldings;
  if (_holdingsFilter === '수익') list = list.filter(h => h.pnl >= 0);
  else if (_holdingsFilter === '손실') list = list.filter(h => h.pnl < 0);
  if (!list.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-briefcase"></i>종목을 추가해보세요</div>';
    return;
  }
  const profit = list.filter(h => h.pnl >= 0);
  const loss = list.filter(h => h.pnl < 0);
  let html = '';
  if (profit.length) html += `<div class="section"><div class="sec-label">수익 중인 종목</div>${profit.map(holdingCard).join('')}</div>`;
  if (loss.length) html += `<div class="section"><div class="sec-label">손실 중인 종목</div>${loss.map(holdingCard).join('')}</div>`;
  el.innerHTML = html;
}

function holdingCard(h) {
  const pnlPct = h.pnl_pct || 0;
  const barWidth = Math.min(Math.abs(pnlPct) * 2, 100);
  const barColor = pnlPct >= 0 ? '#E24B4A' : '#185FA5';
  return `<div class="card clickable" onclick="openHoldingDetail('${h.code}', '${h.name}')">
    <div class="card-top">
      <div class="stock-icon ${iconColors(h.name)}">${iconText(h.name)}</div>
      <div>
        <div class="stock-name">${h.name}</div>
        <div class="stock-sub">평단 ${fmtNum(h.avg_price)}원 · ${h.qty}주</div>
      </div>
      <div class="stock-right">
        <div class="stock-price">${fmtNum(h.value)}원</div>
        <div class="stock-change ${pnlClass(pnlPct)}">${pnlPct>=0?'▲':'▼'} ${fmtPct(Math.abs(pnlPct))}</div>
      </div>
    </div>
    <div class="mini-grid">
      <div class="mini-item"><div class="mini-label">평가손익</div><div class="mini-val ${pnlClass(h.pnl)}">${fmtPnl(h.pnl)}</div></div>
      <div class="mini-item"><div class="mini-label">현재가</div><div class="mini-val">${fmtNum(h.cur_price)}</div></div>
      <div class="mini-item"><div class="mini-label">수익률</div><div class="mini-val ${pnlClass(pnlPct)}">${fmtPct(pnlPct)}</div></div>
    </div>
    <div class="pnl-bar-wrap"><div class="pnl-bar" style="width:${barWidth}%;background:${barColor};"></div></div>
    <div class="card-bottom">
      <div class="signal-badges"><span class="badge ${pnlPct>=0?'badge-ok':'badge-sell'}">${pnlPct>=0?'수익 중':'손실 중'}</span></div>
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
  } catch(e) {
    el.innerHTML = `<div class="loading">분석 데이터를 불러오지 못했습니다</div>`;
  }
}

function renderHoldingDetail(d, el) {
  const h = d.holding || {};
  const a = d.analysis || {};
  // analyze_stock 반환: current_price, rsi, gap20, gap60, ma20, ma60, badges, verdict, pnl_pct, pnl_amount, eval_amount
  const curPrice = a.cur_price || a.current_price || h.avg_price;
  const pnl = a.pnl_amount !== undefined ? a.pnl_amount : (curPrice - h.avg_price) * h.qty;
  const pnlPct = a.pnl_pct !== undefined ? a.pnl_pct : ((curPrice - h.avg_price) / h.avg_price * 100);

  const rsi = a.rsi ? Math.round(a.rsi) : '-';
  const gap20 = a.gap20 ? (a.gap20 * 100).toFixed(1) + '%' : '-';
  const gap60 = a.gap60 ? (a.gap60 * 100).toFixed(1) + '%' : '-';
  const ma20 = a.ma20 ? fmtNum(Math.round(a.ma20)) : '-';
  const ma60 = a.ma60 ? fmtNum(Math.round(a.ma60)) : '-';
  const volRatio = a.volume_ratio ? a.volume_ratio.toFixed(1) + 'x' : '-';
  const foreignNet = a.foreign_net_3d !== undefined ? fmtPnl(a.foreign_net_3d) : '-';
  const instNet = a.institution_net_3d !== undefined ? fmtPnl(a.institution_net_3d) : '-';

  const badges = Array.isArray(a.badges) ? a.badges : [];
  const verdict = a.verdict || '';

  // 지지선 칩
  const boll = a.bollinger || {};
  let supportChips = '';
  if (a.ma20) supportChips += `<div class="sup-chip">20일선 <span class="${pnlClass(a.gap20||0)}">${gap20}</span></div>`;
  if (a.ma60) supportChips += `<div class="sup-chip">60일선 <span class="${pnlClass(a.gap60||0)}">${gap60}</span></div>`;
  if (boll.lower) supportChips += `<div class="sup-chip">볼하단 ${fmtNum(Math.round(boll.lower))}</div>`;

  const badgesHtml = badges.map(b => {
    const cls = b.includes('매도') || b.includes('과열') || b.includes('손절') ? 'badge-sell' :
                b.includes('매수') || b.includes('정배열') || b.includes('지지') ? 'badge-buy' :
                b.includes('주의') || b.includes('경고') ? 'badge-warn' : 'badge-ok';
    return `<span class="badge ${cls}">${b}</span>`;
  }).join('');

  const newsHtml = (a.news||[]).slice(0,3).map(n => {
    const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
    const lbl = n.label || '중립';
    const briefHtml = n.brief ? `<div class="news-brief">💡 ${n.brief}</div>` : '';
    return `<div class="news-card">
      <div class="news-card-top"><span class="badge ${bdg}">${lbl}</span><span class="news-source">${n.source||''}</span></div>
      <div class="news-title">${n.title||''}</div>${briefHtml}
    </div>`;
  }).join('');

  el.innerHTML = `
    <div class="detail-hero">
      <div class="detail-name">${h.name}</div>
      <div class="detail-price">${fmtNum(curPrice)}원 <span style="font-size:16px;opacity:0.85;">${pnlPct>=0?'▲':'▼'} ${fmtPct(Math.abs(pnlPct))}</span></div>
      <div class="detail-meta">${h.code} · 평단 ${fmtNum(h.avg_price)}원 · ${h.qty}주</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-item-label">평가손익</div><div class="detail-item-val">${fmtPnl(pnl)}원</div></div>
        <div class="detail-item"><div class="detail-item-label">수익률</div><div class="detail-item-val">${fmtPct(pnlPct)}</div></div>
        <div class="detail-item"><div class="detail-item-label">RSI</div><div class="detail-item-val">${rsi}</div></div>
        <div class="detail-item"><div class="detail-item-label">거래량비</div><div class="detail-item-val">${volRatio}</div></div>
      </div>
    </div>
    <div class="section" style="margin-top:12px;">
      <div class="card">
        <div class="mini-grid" style="grid-template-columns:1fr 1fr 1fr;">
          <div class="mini-item"><div class="mini-label">20일선</div><div class="mini-val">${ma20}</div></div>
          <div class="mini-item"><div class="mini-label">60일선</div><div class="mini-val">${ma60}</div></div>
          <div class="mini-item"><div class="mini-label">이격도(20일)</div><div class="mini-val">${gap20}</div></div>
        </div>
        <div class="mini-grid" style="grid-template-columns:1fr 1fr;margin-top:6px;">
          <div class="mini-item"><div class="mini-label">외국인 3일순매수</div><div class="mini-val ${foreignNet>0?'up':'down'}">${foreignNet}</div></div>
          <div class="mini-item"><div class="mini-label">기관 3일순매수</div><div class="mini-val ${instNet>0?'up':'down'}">${instNet}</div></div>
        </div>
        ${supportChips ? `<div class="support-mini" style="margin-top:10px;">${supportChips}</div>` : ''}
        ${badgesHtml ? `<div class="signal-badges" style="margin-top:10px;">${badgesHtml}</div>` : ''}
        ${verdict ? `<div class="analysis-text" style="margin-top:10px;padding-top:10px;border-top:0.5px solid #F0F0F5;">${verdict}</div>` : ''}
      </div>
    </div>
    ${newsHtml ? `<div class="section"><div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>관련 뉴스</div>${newsHtml}</div>` : ''}
    <div style="padding:0 16px 16px;">
      <button class="btn-danger" onclick="deleteHolding('${h.code}', '${h.name}')">
        <i class="ti ti-trash" style="font-size:16px;"></i> 종목 삭제하기
      </button>
    </div>`;
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
    document.getElementById('w-target').value = '';
    document.getElementById('w-stop').value = '';
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
  const target_price = parseFloat(document.getElementById('w-target').value) || null;
  const stop_loss = parseFloat(document.getElementById('w-stop').value) || null;
  if (!code || !name) { alert('종목을 검색해서 선택하세요'); return; }
  try {
    await api('POST', '/api/watchlist', { code, name, target_price, stop_loss });
    toggleAddWatchlist();
    _watchlistLoaded = false;
    loadWatchlist(true);
  } catch(e) { alert(e.message); }
}

// ─────────────────────────────────────────────────────────
// 관심종목 탭
// ─────────────────────────────────────────────────────────
let _watchlistLoaded = false;
let _watchlistFilter = '전체';
async function loadWatchlist(force) {
  if (_watchlistLoaded && !force) return;
  _watchlistLoaded = true;
  const el = document.getElementById('watchlist-content');
  el.innerHTML = '<div class="loading"><div class="spinner"></div> 불러오는 중...</div>';
  try {
    const d = await api('GET', '/api/watchlist');
    _allWatchlist = d.watchlist || [];
    renderWatchlist();
  } catch(e) {
    el.innerHTML = `<div class="loading">불러오지 못했습니다</div>`;
  }
}

function filterWatchlist(filter, btn) {
  _watchlistFilter = filter;
  document.querySelectorAll('#screen-watchlist .tab').forEach(b => {
    b.className = 'tab ' + (b === btn ? 'active' : 'inactive');
  });
  renderWatchlist();
}

function renderWatchlist() {
  const el = document.getElementById('watchlist-content');
  let list = _allWatchlist;
  if (!list.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-star"></i>관심종목을 추가해보세요</div>';
    return;
  }
  el.innerHTML = `<div class="section" style="margin-top:8px;">
    ${list.map(w => `
      <div class="card clickable" onclick="openWatchlistDetail('${w.code}', '${w.name}')">
        <div class="card-top">
          <div class="stock-icon ${iconColors(w.name)}">${iconText(w.name)}</div>
          <div>
            <div class="stock-name">${w.name}</div>
            <div class="stock-sub">${w.code}</div>
          </div>
          <div style="margin-left:auto;">
            <i class="ti ti-chevron-right" style="color:#C7C7CC;font-size:18px;"></i>
          </div>
        </div>
        ${w.target_price ? `
          <div class="target-row">
            <span class="target-label">목표가</span><span class="target-val">${fmtNum(w.target_price)}원</span>
            ${w.stop_loss ? `<span class="target-label" style="margin-left:8px;">손절가</span><span class="target-val" style="color:#A32D2D;">${fmtNum(w.stop_loss)}원</span>` : ''}
          </div>` : ''}
      </div>`).join('')}
  </div>`;
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
  } catch(e) {
    el.innerHTML = `<div class="loading">분석 데이터를 불러오지 못했습니다</div>`;
  }
}

function renderWatchlistDetail(d, el, code, name) {
  const item = d.item || { code, name };
  const a = d.analysis || {};
  const timing = a.timing || {};
  const curPrice = a.cur_price || a.current_price || 0;

  const rsi = a.rsi ? Math.round(a.rsi) : '-';
  const gap20 = a.gap20 ? (a.gap20 * 100).toFixed(1) + '%' : '-';
  const ma20 = a.ma20 ? fmtNum(Math.round(a.ma20)) : '-';
  const ma60 = a.ma60 ? fmtNum(Math.round(a.ma60)) : '-';
  const volRatio = a.volume_ratio ? a.volume_ratio.toFixed(1) + 'x' : '-';
  const foreignNet = a.foreign_net_3d !== undefined ? fmtPnl(a.foreign_net_3d) : '-';
  const instNet = a.institution_net_3d !== undefined ? fmtPnl(a.institution_net_3d) : '-';

  const badges = Array.isArray(a.badges) ? a.badges : [];
  const verdict = a.verdict || '';

  // 타이밍 배지
  let timingBadge = '';
  if (timing.label) {
    const tc = timing.badge_type === 'buy' ? 'badge-buy' : timing.badge_type === 'sell' ? 'badge-sell' : 'badge-warn';
    timingBadge = `<span class="badge ${tc}" style="font-size:14px;padding:6px 12px;">${timing.label}</span>`;
    if (timing.reason) timingBadge += `<div class="analysis-text" style="margin-top:6px;">${timing.reason}</div>`;
  }

  const badgesHtml = badges.map(b => {
    const cls = b.includes('매도') || b.includes('과열') || b.includes('손절') ? 'badge-sell' :
                b.includes('매수') || b.includes('정배열') || b.includes('지지') ? 'badge-buy' :
                b.includes('주의') || b.includes('경고') ? 'badge-warn' : 'badge-ok';
    return `<span class="badge ${cls}">${b}</span>`;
  }).join('');

  const boll = a.bollinger || {};
  let supportChips = '';
  if (a.ma20) supportChips += `<div class="sup-chip">20일선 <span>${gap20}</span></div>`;
  if (a.ma60) supportChips += `<div class="sup-chip">60일선 ${ma60}</div>`;
  if (boll.lower) supportChips += `<div class="sup-chip">볼하단 ${fmtNum(Math.round(boll.lower))}</div>`;

  // 목표가 달성률
  let targetHtml = '';
  if (item.target_price && curPrice) {
    const targetPct = ((curPrice - item.target_price) / item.target_price * 100);
    const barW = Math.min(Math.abs(curPrice / item.target_price * 100), 100);
    targetHtml = `<div class="card" style="margin-bottom:12px;">
      <div style="font-size:13px;color:#8E8E9A;margin-bottom:6px;">목표가 달성률</div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-weight:600;">${fmtNum(curPrice)}원</span>
        <span style="font-size:12px;color:#8E8E9A;">목표 ${fmtNum(item.target_price)}원</span>
      </div>
      <div class="pnl-bar-wrap" style="margin-top:8px;"><div class="pnl-bar" style="width:${barW}%;background:#5B5BD6;"></div></div>
      <div style="font-size:12px;color:${targetPct<=0?'#E24B4A':'#185FA5'};margin-top:4px;">${fmtPct(targetPct)}</div>
    </div>`;
  }

  el.innerHTML = `
    <div class="detail-hero">
      <div class="detail-name">${item.name}</div>
      <div class="detail-price">${fmtNum(curPrice)}원</div>
      <div class="detail-meta">${item.code}</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-item-label">RSI</div><div class="detail-item-val">${rsi}</div></div>
        <div class="detail-item"><div class="detail-item-label">이격도(20일)</div><div class="detail-item-val">${gap20}</div></div>
        <div class="detail-item"><div class="detail-item-label">거래량비</div><div class="detail-item-val">${volRatio}</div></div>
        <div class="detail-item"><div class="detail-item-label">매집점수</div><div class="detail-item-val">${a.score !== undefined ? a.score + '/5' : '-'}</div></div>
      </div>
    </div>
    <div class="section" style="margin-top:12px;">
      ${timingBadge ? `<div class="card" style="margin-bottom:12px;">${timingBadge}</div>` : ''}
      ${targetHtml}
      <div class="card">
        <div class="mini-grid" style="grid-template-columns:1fr 1fr 1fr;">
          <div class="mini-item"><div class="mini-label">20일선</div><div class="mini-val">${ma20}</div></div>
          <div class="mini-item"><div class="mini-label">60일선</div><div class="mini-val">${ma60}</div></div>
          <div class="mini-item"><div class="mini-label">20일이격</div><div class="mini-val">${gap20}</div></div>
        </div>
        <div class="mini-grid" style="grid-template-columns:1fr 1fr;margin-top:6px;">
          <div class="mini-item"><div class="mini-label">외국인 3일순매수</div><div class="mini-val">${foreignNet}</div></div>
          <div class="mini-item"><div class="mini-label">기관 3일순매수</div><div class="mini-val">${instNet}</div></div>
        </div>
        ${supportChips ? `<div class="support-mini" style="margin-top:10px;">${supportChips}</div>` : ''}
        ${badgesHtml ? `<div class="signal-badges" style="margin-top:10px;">${badgesHtml}</div>` : ''}
        ${verdict ? `<div class="analysis-text" style="margin-top:10px;padding-top:10px;border-top:0.5px solid #F0F0F5;">${verdict}</div>` : ''}
      </div>
    </div>
    <div style="padding:0 16px 16px;">
      <button class="btn-danger" onclick="deleteWatchlist('${item.code}', '${item.name}')">
        <i class="ti ti-trash" style="font-size:16px;"></i> 관심종목 삭제
      </button>
    </div>`;
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
    renderScanner(d, el);
  } catch(e) {
    el.innerHTML = `<div class="loading">스캔 데이터를 불러오지 못했습니다</div>`;
  }
}

function renderScanner(d, el) {
  const items = d.results || d.stocks || [];
  if (!items.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-chart-bar"></i>오늘 매집 신호 없음</div>';
    return;
  }
  el.innerHTML = `<div class="section" style="margin-top:12px;">
    ${items.map((s, i) => `
      <div class="scanner-card">
        <div class="scanner-rank">#${i+1}</div>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
          <div><div class="scanner-name">${s.name}</div><div class="scanner-code">${s.code}</div></div>
          <div style="text-align:right;">
            <div class="stock-price">${fmtNum(s.price||s.cur_price)}원</div>
            <div class="stock-change ${pnlClass(s.change_pct||0)}">${(s.change_pct||0)>=0?'▲':'▼'} ${fmtPct(Math.abs(s.change_pct||0))}</div>
          </div>
        </div>
        <div class="scanner-signals">
          ${(s.signals||[]).map(sig => `<span class="badge badge-ok">${sig}</span>`).join('')}
          ${s.foreign_buy ? `<span class="badge badge-buy">외국인 매수</span>` : ''}
          ${s.inst_buy ? `<span class="badge badge-buy">기관 매수</span>` : ''}
        </div>
        <div class="scanner-metrics">
          ${s.rsi !== undefined ? `<div class="metric-item"><div class="metric-label">RSI</div><div class="metric-val">${s.rsi}</div></div>` : ''}
          ${s.volume_ratio !== undefined ? `<div class="metric-item"><div class="metric-label">거래량비</div><div class="metric-val">${s.volume_ratio}x</div></div>` : ''}
          ${s.foreign_net !== undefined ? `<div class="metric-item"><div class="metric-label">외국인</div><div class="metric-val up">${fmtPnl(s.foreign_net)}</div></div>` : ''}
          ${s.inst_net !== undefined ? `<div class="metric-item"><div class="metric-label">기관</div><div class="metric-val up">${fmtPnl(s.inst_net)}</div></div>` : ''}
        </div>
      </div>`).join('')}
  </div>`;
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
