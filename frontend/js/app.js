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
  const noNav = ['login', 'register', 'holding-detail', 'watchlist-detail', 'news-detail', 'index-detail', 'forecast-detail', 'supply-detail'];
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
    const map = {'긍정': 'positive', '부정': 'negative', '혼조': 'mixed'};
    news = news.filter(n => n.sentiment === map[_newsFilter]);
  }
  if (!news.length) {
    el.innerHTML = '<div class="empty-state"><i class="ti ti-news"></i>뉴스가 없습니다</div>';
    return;
  }

  const catLabelMap = {
    '반도체': '💻 반도체·AI 업종 관련',
    '바이오': '🧬 바이오·제약 업종 관련',
    '2차전지': '🔋 2차전지·배터리 업종 관련',
    '금융': '🏦 금융·증권 업종 관련',
    '글로벌': '🌐 글로벌 시장 관련',
    '전체': '📈 전체 시장 관련',
  };
  const briefStrategyMap = {
    'positive': '장 초반 관련 종목 주가 반응을 먼저 확인하고, 상승 추세가 이어지면 분할 매수 진입을 고려하세요.',
    'negative': '장 초반 주가 반응을 보고, 추가 하락이 예상되면 손절 또는 비중 축소를 검토하세요.',
    'mixed':    '장 초반 관련 종목 주가 반응을 먼저 보고, 상승하면 추세 진입, 하락하면 관망을 권장합니다.',
    'neutral':  '직접적 영향이 제한적일 수 있어 시장 전반 흐름을 참고하며 포트폴리오를 점검하세요.',
  };

  // 상대 시간 계산 ("2시간 전", "3일 전" 등)
  function relTime(pub) {
    if (!pub) return '';
    try {
      const now = Date.now();
      // "06/15" 또는 "2026.06.15" 또는 ISO 형식 처리
      let d;
      if (/^\d{2}\/\d{2}$/.test(pub)) {
        const y = new Date().getFullYear();
        d = new Date(`${y}-${pub.replace('/','-')}`);
      } else {
        d = new Date(pub.replace(/\./g, '-'));
      }
      if (isNaN(d)) return pub;
      const diff = now - d.getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 60) return `${mins}분 전`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}시간 전`;
      const days = Math.floor(hrs / 24);
      if (days < 7) return `${days}일 전`;
      return pub;
    } catch { return pub; }
  }

  const html = news.map((n, i) => {
    const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
    const lbl = n.label || (n.sentiment === 'positive' ? '긍정' : n.sentiment === 'negative' ? '부정' : '혼조');
    const borderClass = n.sentiment === 'positive' ? 'positive' : n.sentiment === 'negative' ? 'negative' : 'mixed';
    const catLabel = catLabelMap[n.category] || '📈 전체 시장 관련';
    const timeStr = relTime(n.published);
    const sourceStr = [n.source, n.published ? n.published.slice(0,5) : ''].filter(Boolean).join(' · ');

    // 카드 본문: brief > summary 앞부분
    const summaryText = n.brief || (n.summary ? n.summary.slice(0, 130) + (n.summary.length > 130 ? '...' : '') : '');

    // ai_summary에서 "📋 이 뉴스는?" 이후 텍스트 추출 (<b> 태그 포함 패턴)
    let aiText = '';
    if (n.ai_summary) {
      // 패턴: <b>📋 이 뉴스는?</b><br>텍스트
      const m = n.ai_summary.match(/이 뉴스는\?<\/b><br>([\s\S]+)$/) ||
                n.ai_summary.match(/이 뉴스는\?<br>([\s\S]+)$/);
      if (m) {
        aiText = m[1].trim();
      } else {
        // HTML 태그 제거 후 텍스트만
        aiText = n.ai_summary
          .replace(/<[^>]+>/g, '')
          .replace(/🔍\s*감지된 키워드/g, '')
          .replace(/📋\s*이 뉴스는\?/g, '')
          .trim();
      }
    }

    // 키워드 배지 섹션 (kw_section - <span> 배지들)
    let kwHtml = '';
    if (n.ai_summary) {
      const kwMatch = n.ai_summary.match(/^([\s\S]*?)(?=<b>📋|📋)/);
      if (kwMatch && kwMatch[1].includes('<span')) kwHtml = kwMatch[1].trim();
    }

    const briefStrategy = briefStrategyMap[n.sentiment] || briefStrategyMap['neutral'];

    // 관련 종목 칩
    const stocks = Array.isArray(n.related_stocks) ? n.related_stocks : [];
    const stocksHtml = stocks.slice(0, 3).map(s => {
      const nm = typeof s === 'object' ? (s.name || '') : s;
      return `<span style="padding:3px 10px;border-radius:20px;background:#F0F0F5;color:#3C3C43;font-size:11px;font-weight:500;">${nm}</span>`;
    }).join('');

    return `<div class="news-card ${borderClass}" style="margin-bottom:12px;">
      <!-- 헤더: 감성 배지 + 출처 -->
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
        <span class="badge ${bdg}">${lbl}</span>
        <span style="font-size:11px;color:#8E8E9A;margin-left:auto;">${sourceStr}</span>
      </div>
      <!-- 제목: 줄바꿈 허용 -->
      <div style="font-size:15px;font-weight:700;color:#1C1C1E;line-height:1.5;margin-bottom:8px;">${n.title||''}</div>
      <!-- 기사 요약 -->
      ${summaryText ? `<div style="font-size:12px;color:#8E8E9A;line-height:1.65;margin-bottom:10px;">${summaryText}</div>` : ''}
      <!-- AI 분석 -->
      ${aiText ? `<div style="border-top:1px solid #F0F0F5;padding-top:12px;">
        <div style="display:flex;align-items:center;gap:5px;margin-bottom:8px;">
          <i class="ti ti-sparkles" style="font-size:13px;color:#5B5BD6;"></i>
          <span style="font-size:12px;font-weight:700;color:#5B5BD6;">AI 분석</span>
        </div>
        <div style="font-size:11px;color:#8E8E9A;font-weight:600;margin-bottom:6px;">${catLabel}</div>
        ${kwHtml ? `<div style="margin-bottom:6px;line-height:2;">${kwHtml}</div>` : ''}
        <div style="font-size:13px;color:#3C3C43;line-height:1.7;margin-bottom:10px;">${aiText}</div>
        <div style="margin-bottom:10px;">
          <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px;">
            <span style="font-size:13px;">☀️</span>
            <span style="font-size:12px;font-weight:700;color:#3C3C43;">대응 전략</span>
          </div>
          <div style="font-size:13px;color:#3C3C43;line-height:1.65;">${briefStrategy}</div>
        </div>
      </div>` : ''}
      <!-- 푸터: 시간 + 관련 종목 -->
      <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;${aiText?'':'margin-top:8px;'}">
        <span style="font-size:11px;color:#C7C7CC;">${timeStr}</span>
        <div style="display:flex;gap:5px;flex-wrap:wrap;">${stocksHtml}</div>
      </div>
    </div>`;
  }).join('');

  el.innerHTML = `<div class="section" style="margin-top:12px;">${html}</div>`;
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
      if (streak > 2) {
        streakBox = `<div class="streak-box">
          <div class="streak-icon"><i class="ti ti-flame" style="font-size:20px;"></i></div>
          <div><div class="streak-title">${label} ${streak}일 연속 순매수 중</div><div class="streak-sub">누적 ${total>=0?'+':''}${fmtInv(total,unit)} · ${streak>=5?'강한 매집 신호':'지속 관찰 필요'}</div></div>
        </div>`;
      } else if (streak < -2) {
        streakBox = `<div class="streak-box" style="background:#FCEBEB;">
          <div class="streak-icon" style="background:#E24B4A;"><i class="ti ti-trending-down" style="font-size:20px;"></i></div>
          <div><div class="streak-title" style="color:#A32D2D;">${label} ${Math.abs(streak)}일 연속 순매도 중</div><div class="streak-sub" style="color:#791F1F;">이탈 흐름 · 주의 필요</div></div>
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
  // 기사 기본 정보 먼저 표시
  renderNewsDetailBase(n, el);
  // AI 분석이 없으면 온디맨드로 요청
  if (!n.ai_summary && !n._analyzing) {
    n._analyzing = true;
    const analyzeEl = document.getElementById('news-analyze-placeholder');
    if (analyzeEl) analyzeEl.innerHTML = '<div class="loading" style="padding:16px;"><div class="spinner"></div> AI 분석 생성 중... (최대 10초)</div>';
    try {
      const result = await api('POST', '/api/news/analyze', {
        title: n.title || '',
        summary: n.summary || '',
        sentiment: n.sentiment || 'neutral',
        category: n.category || '전체',
      });
      n.ai_summary = result.ai_summary;
      n.strategy = result.strategy;
      if (result.related_stocks) n.related_stocks = result.related_stocks;
      n._analyzing = false;
      // 분석 영역만 교체
      if (analyzeEl) analyzeEl.innerHTML = buildNewsAnalysisHtml(n);
    } catch(e) {
      n._analyzing = false;
      if (analyzeEl) analyzeEl.innerHTML = '<div style="padding:16px;font-size:13px;color:#8E8E9A;">분석을 불러오지 못했습니다.</div>';
    }
  }
}

function renderNewsDetailBase(n, el) {
  const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
  const lbl = n.label || (n.sentiment === 'positive' ? '긍정' : n.sentiment === 'negative' ? '부정' : '혼조');
  const borderColor = n.sentiment === 'positive' ? '#185FA5' : n.sentiment === 'negative' ? '#E24B4A' : '#F0A500';
  const catChip = n.category && n.category !== '전체' ? `<span class="badge badge-ok" style="font-size:11px;">${n.category}</span>` : '';

  // 원문 요약
  const summaryHtml = n.summary ? `
    <div class="card" style="margin-bottom:12px;">
      <div style="font-size:11px;color:#8E8E9A;margin-bottom:6px;display:flex;align-items:center;gap:4px;">
        <i class="ti ti-file-text" style="font-size:12px;"></i> 기사 요약
      </div>
      <div style="font-size:13px;color:#3C3C43;line-height:1.7;">${n.summary}</div>
    </div>` : '';

  // 외부 링크
  const linkHtml = n.link ? `
    <a href="${n.link}" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:center;gap:6px;padding:12px;border:1px solid #E5E5EA;border-radius:12px;color:#5B5BD6;font-size:14px;font-weight:600;text-decoration:none;margin-bottom:16px;">
      <i class="ti ti-external-link" style="font-size:15px;"></i> 원문 기사 보기
    </a>` : '';

  const alreadyHasAnalysis = !!(n.ai_summary || n.strategy);

  el.innerHTML = `
    <div style="padding:16px 16px 0;">
      <!-- 헤더 -->
      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
        <span class="badge ${bdg}">${lbl}</span>
        ${catChip}
        <span style="font-size:11px;color:#8E8E9A;margin-left:auto;">${n.source||''}</span>
        <span style="font-size:11px;color:#C7C7CC;">${n.published||''}</span>
      </div>
      <!-- 제목 -->
      <div style="font-size:17px;font-weight:700;color:#1C1C1E;line-height:1.5;margin-bottom:10px;border-left:3px solid ${borderColor};padding-left:10px;">${n.title||''}</div>
      ${n.brief ? `<div class="news-brief" style="margin-bottom:12px;">💡 ${n.brief}</div>` : ''}
      ${summaryHtml}
      ${linkHtml}
    </div>
    <!-- AI 분석 영역 (즉시 있으면 바로 렌더, 없으면 로딩) -->
    <div id="news-analyze-placeholder">
      ${alreadyHasAnalysis ? buildNewsAnalysisHtml(n) : ''}
    </div>`;
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

  return `${stocksHtml}
    <div style="padding:0 16px 20px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
        <i class="ti ti-brain" style="font-size:15px;color:#5B5BD6;"></i>
        <span style="font-size:13px;font-weight:700;color:#1C1C1E;">AI 분석</span>
      </div>
      <div style="background:#F5F4FF;border:1px solid #E0DEFF;border-radius:14px;padding:16px;font-size:13px;line-height:1.9;color:#1C1C1E;">
        ${n.ai_summary}
      </div>
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

  return `<div class="card clickable" onclick="openHoldingDetail('${h.code}', '${h.name}')">
    <div class="card-top">
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

  // ── 뉴스 ──
  const newsHtml = (a.news||[]).slice(0,3).map(n => {
    const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
    const briefHtml = n.brief ? `<div class="news-brief">💡 ${n.brief}</div>` : '';
    return `<div class="news-card">
      <div class="news-card-top"><span class="badge ${bdg}">${n.label||'중립'}</span><span class="news-source">${n.source||''} · ${n.published||''}</span></div>
      <div class="news-title">${n.title||''}</div>${briefHtml}
    </div>`;
  }).join('');

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

    <!-- 수급 -->
    <div class="section">
      <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (5일)</div>
      <div class="card">
        <div class="supply-row">
          <span class="supply-who">외국인</span>
          <div class="supply-bar-bg"><div class="supply-bar-fill ${fBarCls}" style="width:${fBarW}%;"></div></div>
          <span class="supply-val ${fCls}">${foreignNet>=0?'+':''}${foreignNet.toLocaleString()}주</span>
        </div>
        ${fChips ? `<div class="days-row">${fChips}</div>` : ''}
        <div class="supply-row">
          <span class="supply-who">기관</span>
          <div class="supply-bar-bg"><div class="supply-bar-fill ${iBarCls}" style="width:${iBarW}%;"></div></div>
          <span class="supply-val ${iCls}">${instNet>=0?'+':''}${instNet.toLocaleString()}주</span>
        </div>
        ${iChips ? `<div class="days-row">${iChips}</div>` : ''}
      </div>
    </div>

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

    <!-- 뉴스 -->
    ${newsHtml ? `<div class="section">
      <div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>${h.name} 뉴스</div>
      ${newsHtml}
    </div>` : ''}

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
  const filt = _watchlistFilter || '전체';

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

    // 목표가·손절가 거리
    const cur = w.cur_price || 0;
    let targetRow = '';
    if (w.target_price && cur) {
      const tDist = ((w.target_price - cur) / cur * 100).toFixed(1);
      const sDist = w.stop_loss ? ((w.stop_loss - cur) / cur * 100).toFixed(1) : null;
      targetRow = `<div class="target-row">
        <span class="target-label">목표가</span>
        <span class="target-val">${fmtNum(w.target_price)}원</span>
        <span class="target-dist">(${tDist >= 0 ? '+' : ''}${tDist}%)</span>
        ${sDist != null ? `<span class="target-label" style="margin-left:8px;">손절가</span>
        <span class="target-val" style="color:#A32D2D;">${fmtNum(w.stop_loss)}원</span>
        <span class="target-dist" style="color:#A32D2D;">(${sDist}%)</span>` : ''}
      </div>`;
    }

    // 배지
    const timing = w.timing || {};
    const bdgType = timing.badge_type || 'neutral';
    const bdgCls  = bdgType === 'buy' ? 'badge-buy' : bdgType === 'sell' ? 'badge-sell' : 'badge-ok';
    const extraBadges = (w.badges || []).slice(0, 3)
      .map(b => `<span class="badge badge-ok">${b}</span>`).join('');

    return `<div class="card clickable" onclick="openWatchlistDetail('${w.code}','${w.name.replace(/'/g,"\\'")}')">
      <div class="card-top">
        <div class="stock-icon ${iconColors(w.name)}">${iconText(w.name)}</div>
        <div>
          <div class="stock-name">${w.name}</div>
          <div class="stock-sub">${w.code}</div>
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
  } catch(e) {
    el.innerHTML = `<div class="loading">분석 데이터를 불러오지 못했습니다</div>`;
  }
}

function renderWatchlistDetail(d, el, code, name) {
  const item = d.item || { code, name };
  const a = d.analysis || {};
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

  // 지지선
  let supRows = '';
  if (ma20Val) {
    const dv = (curPrice - ma20Val) / ma20Val * 100;
    const cls = dv >= 0 ? 'up' : 'down';
    supRows += `<div class="sup-row"><span class="sup-label">20일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma20Val))}</span><span class="sup-dist ${cls}">${dv>=0?'+':''}${dv.toFixed(1)}%</span><span class="sup-note">${dv>=0?'현재 위':'이탈'}</span></div></div>`;
  }
  if (boll.lower) {
    const dv = (curPrice - boll.lower) / boll.lower * 100;
    const cls = dv >= 0 ? 'up' : 'down';
    supRows += `<div class="sup-row"><span class="sup-label">볼린저 하단</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(boll.lower))}</span><span class="sup-dist ${cls}">${dv>=0?'+':''}${dv.toFixed(1)}%</span><span class="sup-note">지지선</span></div></div>`;
  }
  if (ma60Val) {
    const dv = (curPrice - ma60Val) / ma60Val * 100;
    const cls = dv >= 0 ? 'up' : 'down';
    supRows += `<div class="sup-row"><span class="sup-label">60일선</span><div class="sup-right"><span class="sup-price">${fmtNum(Math.round(ma60Val))}</span><span class="sup-dist ${cls}">${dv>=0?'+':''}${dv.toFixed(1)}%</span><span class="sup-note">주요 지지</span></div></div>`;
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
        <span class="badge ${tc}" style="font-size:14px;padding:6px 12px;">${timing.label}</span>
        ${timing.reason ? `<div class="analysis-text" style="margin-top:8px;">${timing.reason}</div>` : ''}
      </div>
    </div>`;
  }

  // 목표가/손절가
  const tp = item.target_price;
  const sp2 = item.stop_loss;
  let priceTargetHtml = '';
  if (tp && curPrice) {
    const tDist = ((tp - curPrice) / curPrice * 100).toFixed(1);
    const sDist = sp2 ? ((sp2 - curPrice) / curPrice * 100).toFixed(1) : null;
    const rr = sp2 ? Math.abs(tDist / ((sp2 - curPrice) / curPrice * 100)).toFixed(1) : null;
    const rrCls = rr >= 2 ? '#27500A' : rr >= 1 ? '#BA7517' : '#A32D2D';
    const rrLbl = rr >= 2 ? '✅ 양호' : rr >= 1 ? '⚠️ 보통' : '❌ 불리';
    priceTargetHtml = `<div class="section">
      <div class="sec-title"><i class="ti ti-target" style="font-size:15px;color:#5B5BD6;"></i>목표가 / 손절가</div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
          <div>
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">내 목표가</div>
            <div style="font-size:18px;font-weight:700;color:#27500A;">${fmtNum(tp)}</div>
            <div style="font-size:11px;color:#27500A;">${tDist >= 0 ? '+' : ''}${tDist}%</div>
          </div>
          ${sp2 ? `<div style="text-align:right;">
            <div style="font-size:10px;color:#8E8E9A;margin-bottom:3px;">내 손절가</div>
            <div style="font-size:18px;font-weight:700;color:#A32D2D;">${fmtNum(sp2)}</div>
            <div style="font-size:11px;color:#A32D2D;">${sDist}%</div>
          </div>` : ''}
        </div>
        ${rr ? `<div style="background:#F8F8FA;border-radius:10px;padding:10px 12px;">
          <div style="font-size:10px;color:#8E8E9A;margin-bottom:4px;">리스크/리워드 비율</div>
          <div style="font-size:13px;font-weight:600;color:${rrCls};">1 : ${rr} ${rrLbl}</div>
          <div style="font-size:10px;color:#8E8E9A;margin-top:3px;">손실 1원 대비 수익 ${rr}원 기대 — 2 이상이면 진입 적합</div>
        </div>` : ''}
      </div>
    </div>`;
  }

  // 뉴스
  const newsHtml = (a.news||[]).slice(0,3).map(n => {
    const bdg = n.sentiment === 'positive' ? 'badge-pos' : n.sentiment === 'negative' ? 'badge-neg' : 'badge-mix';
    const briefHtml = n.brief ? `<div class="news-brief">💡 ${n.brief}</div>` : '';
    return `<div class="news-card">
      <div class="news-card-top"><span class="badge ${bdg}">${n.label||'중립'}</span><span class="news-source">${n.source||''} · ${n.published||''}</span></div>
      <div class="news-title">${n.title||''}</div>${briefHtml}
    </div>`;
  }).join('');

  el.innerHTML = `
    <!-- 히어로 -->
    <div class="detail-hero">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div class="detail-name">${item.name}</div>
        ${timing.label ? `<span class="badge ${timing.badge_type==='buy'?'badge-buy':timing.badge_type==='sell'?'badge-sell':'badge-warn'}">${timing.label}</span>` : ''}
      </div>
      <div class="detail-price">${fmtNum(curPrice)}원</div>
      <div style="font-size:13px;margin-top:2px;opacity:0.85;">
        <span class="${chgPct>=0?'up':'down'}" style="color:#fff;">${chgPct>=0?'▲':'▼'} ${Math.abs(chg).toLocaleString()}원 (${Math.abs(chgPct).toFixed(2)}%)</span>
      </div>
      ${a.cur_high || a.cur_low ? `<div style="font-size:11px;opacity:0.7;margin-top:6px;">
        고가 ${fmtNum(a.cur_high||0)} · 저가 ${fmtNum(a.cur_low||0)} · 거래량 ${(a.cur_volume||0).toLocaleString()}
      </div>` : ''}
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

    <!-- 수급 -->
    <div class="section">
      <div class="sec-title"><i class="ti ti-users" style="font-size:15px;color:#5B5BD6;"></i>외국인·기관 수급 (5일)</div>
      <div class="card">
        <div class="supply-row">
          <span class="supply-who">외국인</span>
          <div class="supply-bar-bg"><div class="supply-bar-fill ${fBarCls}" style="width:${fBarW}%;"></div></div>
          <span class="supply-val ${fCls}">${foreignNet>=0?'+':''}${foreignNet.toLocaleString()}주</span>
        </div>
        ${fChips ? `<div class="days-row">${fChips}</div>` : ''}
        <div class="supply-row">
          <span class="supply-who">기관</span>
          <div class="supply-bar-bg"><div class="supply-bar-fill ${iBarCls}" style="width:${iBarW}%;"></div></div>
          <span class="supply-val ${iCls}">${instNet>=0?'+':''}${instNet.toLocaleString()}주</span>
        </div>
        ${iChips ? `<div class="days-row">${iChips}</div>` : ''}
      </div>
    </div>

    <!-- 배지 -->
    ${badgesHtml ? `<div class="section">
      <div style="padding:0 16px 8px;"><div class="signal-badges">${badgesHtml}</div></div>
    </div>` : ''}

    <!-- 목표가/손절가 -->
    ${priceTargetHtml}

    <!-- 뉴스 -->
    ${newsHtml ? `<div class="section">
      <div class="sec-title"><i class="ti ti-news" style="font-size:15px;color:#5B5BD6;"></i>${item.name} 뉴스</div>
      ${newsHtml}
    </div>` : ''}

    <div style="padding:0 16px 16px;">
      <div class="warn-box" style="margin-bottom:10px;"><i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>투자 결정은 본인 책임입니다. 이 정보는 참고용이며 투자 권유가 아닙니다.</div>
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
