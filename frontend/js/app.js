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
  const noNav = ['login', 'register', 'holding-detail', 'watchlist-detail'];
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

  const analysis = d.analysis || [];
  const forecast = d.forecast || {};

  const heroTitle = kpPct >= 1.5 ? '강한 상승장' : kpPct >= 0.3 ? '상승장' : kpPct <= -1.5 ? '하락장' : kpPct <= -0.3 ? '약세장' : '보합장';
  const heroIcon = kpPct >= 0 ? 'ti-trending-up' : 'ti-trending-down';

  let analysisHtml = '';
  const dotColors = ['dot-blue','dot-green','dot-orange'];
  (analysis.slice(0,3)).forEach((a, i) => {
    const warnHtml = a.warning ? `<div class="warn-text"><i class="ti ti-alert-triangle" style="font-size:13px;flex-shrink:0;"></i>${a.warning}</div>` : '';
    analysisHtml += `
      <div class="analysis-item">
        <div class="analysis-label"><div class="dot ${dotColors[i]||'dot-blue'}"></div>${a.label||a.title||'분석'}</div>
        <div class="analysis-text">${a.text||a.content||''}</div>
        ${warnHtml}
      </div>`;
  });
  if (!analysisHtml) {
    analysisHtml = `<div class="analysis-item"><div class="analysis-text">KOSPI ${fmtNum(kospi)} (${fmtPct(kpPct)}) · KOSDAQ ${fmtNum(kosdaq)} (${fmtPct(kdPct)})</div></div>`;
  }

  const fDir = forecast.direction || (kpPct >= 0 ? '상승' : '하락');
  const fConf = forecast.confidence || 55;
  const fBasis = forecast.basis || [];
  const fPoints = forecast.points || [];

  let basisHtml = (fBasis.slice(0,2)).map(b => `<div class="forecast-item">${b}</div>`).join('');
  let pointsHtml = (fPoints.slice(0,2)).map(p => `<div class="forecast-item">${p}</div>`).join('');
  if (!basisHtml) basisHtml = `<div class="forecast-item">전일 미국 S&P500 ${fmtPct(spPct)} 참고</div>`;
  if (!pointsHtml) pointsHtml = `<div class="forecast-item">장 초반 외국인 매매 방향 확인</div>`;

  const fWarn = forecast.warning || '예측은 참고용이며 투자 결정은 본인 판단으로 하세요';

  el.innerHTML = `
    <div class="hero">
      <div class="hero-badge"><i class="ti ${heroIcon}" style="font-size:13px;"></i>${heroTitle}</div>
      <div class="hero-status">KOSPI ${fmtNum(kospi)} ${kpPct>=0?'▲':'▼'} ${Math.abs(kpPct).toFixed(2)}%</div>
      <div class="hero-desc">KOSPI ${fmtPct(kpPct)} · KOSDAQ ${fmtPct(kdPct)} · S&P500 ${fmtPct(spPct)} / 나스닥 ${fmtPct(ndPct)}</div>
      <div class="hero-tip"><i class="ti ti-bulb" style="font-size:14px;flex-shrink:0;"></i>${forecast.tip||'보유 종목 동향을 확인하세요'}</div>
    </div>

    <div class="index-row">
      <div class="index-card ${kpPct>=0?'up-border':'down-border'}">
        <div class="index-name">KOSPI</div>
        <div class="index-val">${fmtNum(kospi)}</div>
        <div class="index-change ${pnlClass(kpPct)}">${kpPct>=0?'▲':'▼'} ${fmtPct(Math.abs(kpPct))}</div>
      </div>
      <div class="index-card ${kdPct>=0?'up-border':'down-border'}">
        <div class="index-name">KOSDAQ</div>
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
          <div class="forecast-title"><i class="ti ti-trending-up" style="color:#E24B4A;"></i>${fDir} 예상</div>
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
  const html = news.map(n => {
    const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
    const lbl = n.label || (n.sentiment === 'positive' ? '긍정' : n.sentiment === 'negative' ? '부정' : '혼조');
    const borderClass = n.sentiment === 'positive' ? 'important' : n.sentiment === 'negative' ? 'negative' : '';
    const briefHtml = n.brief ? `<div class="news-brief">💡 ${n.brief}</div>` : '';
    return `<div class="news-card ${borderClass}">
      <div class="news-card-top">
        <span class="badge ${bdg}">${lbl}</span>
        <span class="news-source">${n.source||''} · ${n.published||''}</span>
      </div>
      <div class="news-title">${n.title||''}</div>
      ${briefHtml}
    </div>`;
  }).join('');
  el.innerHTML = `<div class="section" style="margin-top:12px;">${html}</div>`;
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
  const pnlPct = ((a.cur_price||h.avg_price) - h.avg_price) / h.avg_price * 100;
  const curPrice = a.cur_price || h.avg_price;
  const pnl = (curPrice - h.avg_price) * h.qty;

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
      <div class="detail-price ${pnlClass(pnlPct)}">${fmtNum(curPrice)}원</div>
      <div class="detail-meta">${h.code} · 평단 ${fmtNum(h.avg_price)}원 · ${h.qty}주</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-item-label">평가손익</div><div class="detail-item-val">${fmtPnl(pnl)}원</div></div>
        <div class="detail-item"><div class="detail-item-label">수익률</div><div class="detail-item-val">${fmtPct(pnlPct)}</div></div>
        <div class="detail-item"><div class="detail-item-label">RSI</div><div class="detail-item-val">${a.rsi||'-'}</div></div>
        <div class="detail-item"><div class="detail-item-label">이격도</div><div class="detail-item-val">${a.disparity||'-'}</div></div>
      </div>
    </div>
    ${a.signal_text ? `<div class="section" style="margin-top:12px;"><div class="card"><div class="analysis-text">${a.signal_text}</div></div></div>` : ''}
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
  const curPrice = a.cur_price || 0;

  el.innerHTML = `
    <div class="detail-hero">
      <div class="detail-name">${item.name}</div>
      <div class="detail-price">${fmtNum(curPrice)}원</div>
      <div class="detail-meta">${item.code}</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-item-label">RSI</div><div class="detail-item-val">${a.rsi||'-'}</div></div>
        <div class="detail-item"><div class="detail-item-label">이격도</div><div class="detail-item-val">${a.disparity||'-'}</div></div>
        ${item.target_price ? `<div class="detail-item"><div class="detail-item-label">목표가</div><div class="detail-item-val">${fmtNum(item.target_price)}</div></div>` : ''}
        ${item.stop_loss ? `<div class="detail-item"><div class="detail-item-label">손절가</div><div class="detail-item-val" style="color:rgba(255,255,255,0.7);">${fmtNum(item.stop_loss)}</div></div>` : ''}
      </div>
    </div>
    ${a.signal_text ? `<div class="section" style="margin-top:12px;"><div class="card"><div class="analysis-text">${a.signal_text}</div></div></div>` : ''}
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
