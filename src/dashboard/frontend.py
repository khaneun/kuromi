INDEX_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kuromi Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --accent: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
  --yellow: #d29922;
  --muted: #8b949e;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-width: 320px;
  line-height: 1.5;
}

/* ===== Top Nav ===== */
.topnav {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 56px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.topnav-logo {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  margin-right: 32px;
  letter-spacing: -0.02em;
}
.topnav-tabs {
  display: flex;
  gap: 0;
  height: 100%;
}
.topnav-tab {
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--muted);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  cursor: pointer;
  user-select: none;
  height: 100%;
}
.topnav-tab:hover { color: var(--text); }
.topnav-tab.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}
.topnav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.8rem;
}
#ws-indicator {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--muted);
  display: inline-block;
}
#ws-label { color: var(--muted); }
#clock { color: var(--muted); }

/* ===== Page containers ===== */
.page { display: none; padding: 24px; max-width: 1400px; margin: 0 auto; }
.page.active { display: block; }

/* ===== Cards ===== */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.card-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 12px;
}

/* ===== KPI Cards ===== */
.kpi-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  position: relative;
}
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  flex: 1;
  min-width: 180px;
}
.kpi-label {
  font-size: 0.75rem;
  color: var(--muted);
  margin-bottom: 4px;
}
.kpi-value {
  font-size: 1.3rem;
  font-weight: 700;
}
.system-badge {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  gap: 8px;
}
.badge {
  font-size: 0.7rem;
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 600;
  text-transform: uppercase;
}
.badge-green { background: var(--green); color: #000; }
.badge-red { background: var(--red); color: #fff; }
.badge-yellow { background: var(--yellow); color: #000; }
.badge-blue { background: var(--accent); color: #000; }

/* ===== Tables ===== */
table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
th {
  text-align: left;
  color: var(--muted);
  font-weight: 500;
  padding: 8px;
  border-bottom: 1px solid var(--border);
  font-size: 0.75rem;
}
td {
  padding: 8px;
  border-bottom: 1px solid var(--border);
}
tr:hover td { background: rgba(88,166,255,0.04); }
.pos { color: var(--green); }
.neg { color: var(--red); }

/* ===== Dashboard grid ===== */
.dash-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
.dash-full { grid-column: 1 / -1; }
@media (max-width: 768px) {
  .dash-grid { grid-template-columns: 1fr; }
}

/* ===== Chart ===== */
.chart-container { height: 250px; position: relative; }

/* ===== Event Log ===== */
.event-log {
  max-height: 300px;
  overflow-y: auto;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.72rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px;
  line-height: 1.6;
}
.event-log-entry {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== Agent Grid ===== */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.agent-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.agent-dot {
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0;
}
.dot-ok { background: var(--green); }
.dot-warn { background: var(--yellow); }
.dot-err { background: var(--red); }
.agent-name-ko { font-weight: 700; font-size: 0.95rem; }
.agent-name-en { color: var(--muted); font-size: 0.75rem; margin-left: 4px; }
.agent-role { color: var(--muted); font-size: 0.78rem; margin-bottom: 10px; }
.agent-metrics { font-size: 0.78rem; }
.agent-metric-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  border-bottom: 1px solid var(--border);
}
.agent-metric-row:last-child { border-bottom: none; }
.agent-metric-label { color: var(--muted); }
.success-bar-bg {
  width: 60px; height: 6px; background: var(--border); border-radius: 3px;
  display: inline-block; vertical-align: middle; margin-left: 6px;
}
.success-bar-fill {
  height: 100%; border-radius: 3px; background: var(--green);
}
.agent-error {
  margin-top: 10px;
  background: rgba(248,81,73,0.1);
  border: 1px solid rgba(248,81,73,0.3);
  border-radius: 6px;
  padding: 8px;
  font-size: 0.75rem;
  color: var(--red);
  cursor: pointer;
}
.agent-error-detail {
  display: none;
  margin-top: 6px;
  font-family: monospace;
  font-size: 0.7rem;
  white-space: pre-wrap;
  word-break: break-all;
}
.agent-error.expanded .agent-error-detail { display: block; }

/* ===== Improver Log ===== */
.improver-timeline {
  border-left: 2px solid var(--border);
  margin-left: 8px;
  padding-left: 16px;
}
.improver-entry {
  position: relative;
  padding-bottom: 16px;
  font-size: 0.8rem;
}
.improver-entry::before {
  content: '';
  position: absolute;
  left: -21px;
  top: 4px;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--accent);
  border: 2px solid var(--surface);
}
.improver-ts { color: var(--muted); font-size: 0.72rem; }
.improver-source {
  display: inline-block;
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 8px;
  margin-left: 6px;
  font-weight: 600;
}
.improver-source-seed { background: var(--accent); color: #000; }
.improver-source-llm { background: var(--yellow); color: #000; }
.improver-keys { color: var(--text); margin-top: 2px; }

/* ===== Settings ===== */
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.settings-full { grid-column: 1 / -1; }
@media (max-width: 900px) {
  .settings-grid { grid-template-columns: 1fr; }
}
.form-group { margin-bottom: 14px; }
.form-label {
  display: block;
  font-size: 0.78rem;
  color: var(--muted);
  margin-bottom: 4px;
  font-weight: 500;
}
.form-input, .form-select {
  width: 100%;
  padding: 8px 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.15s;
}
.form-input:focus, .form-select:focus { border-color: var(--accent); }
.form-note {
  font-size: 0.7rem;
  color: var(--muted);
  margin-top: 2px;
}

/* Toggle Switch */
.toggle-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.toggle {
  position: relative;
  width: 44px; height: 24px;
  cursor: pointer;
}
.toggle input { display: none; }
.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--border);
  border-radius: 12px;
  transition: background 0.2s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px; height: 18px;
  border-radius: 50%;
  background: var(--text);
  top: 3px; left: 3px;
  transition: transform 0.2s;
}
.toggle input:checked + .toggle-slider { background: var(--accent); }
.toggle input:checked + .toggle-slider::before { transform: translateX(20px); }
.toggle-label { font-size: 0.85rem; font-weight: 500; }

/* Ticker pills */
.ticker-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.ticker-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 4px 10px;
  font-size: 0.78rem;
  font-weight: 500;
}
.ticker-pill-x {
  cursor: pointer;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1;
}
.ticker-pill-x:hover { color: var(--red); }
.ticker-add-row {
  display: flex;
  gap: 8px;
}
.ticker-add-row input { flex: 1; }

/* System Log */
.sys-log {
  height: 400px;
  overflow-y: auto;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.72rem;
  color: var(--green);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.15s, border-color 0.15s;
}
.btn:hover { background: #21262d; }
.btn-primary { background: var(--accent); color: #000; border-color: var(--accent); }
.btn-primary:hover { background: #79b8ff; }
.btn-green { border-color: var(--green); color: var(--green); }
.btn-green:hover { background: var(--green); color: #000; }
.btn-danger { border-color: var(--red); color: var(--red); }
.btn-danger:hover { background: var(--red); color: #fff; }
.btn-critical { background: #5a0a0a; border-color: var(--red); color: var(--red); }
.btn-critical:hover { background: var(--red); color: #fff; }
.btn-row { display: flex; flex-wrap: wrap; gap: 8px; }

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  z-index: 999;
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
}
.toast.show { opacity: 1; transform: translateY(0); pointer-events: auto; }
.toast-success { background: var(--green); color: #000; }
.toast-error { background: var(--red); color: #fff; }

/* Misc */
.section-gap { margin-bottom: 20px; }
.empty-msg { color: var(--muted); font-size: 0.8rem; text-align: center; padding: 16px; }
</style>
</head>
<body>

<!-- ===== Top Navigation ===== -->
<nav class="topnav">
  <span class="topnav-logo">Kuromi</span>
  <div class="topnav-tabs">
    <a class="topnav-tab active" data-tab="dashboard" onclick="navigate('dashboard')">종합 대시보드</a>
    <a class="topnav-tab" data-tab="agents" onclick="navigate('agents')">Agent 관리</a>
    <a class="topnav-tab" data-tab="settings" onclick="navigate('settings')">설정</a>
  </div>
  <div class="topnav-right">
    <span id="ws-indicator"></span>
    <span id="ws-label">연결 중...</span>
    <span id="clock"></span>
  </div>
</nav>

<!-- ===== Tab 1: 종합 대시보드 ===== -->
<div id="page-dashboard" class="page active">
  <!-- KPI Row -->
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">총 자산</div>
      <div class="kpi-value" id="kpi-equity">-</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">가용 잔고</div>
      <div class="kpi-value" id="kpi-available">-</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">미실현 손익</div>
      <div class="kpi-value" id="kpi-unrealized">-</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">수익률</div>
      <div class="kpi-value" id="kpi-return">-</div>
    </div>
    <div class="system-badge" id="system-badges"></div>
  </div>

  <div class="dash-grid">
    <!-- Positions -->
    <div class="card">
      <div class="card-title">보유 포지션</div>
      <table>
        <thead><tr><th>티커</th><th>진입가</th><th>현재가</th><th>평가손익(%)</th><th>보유량</th></tr></thead>
        <tbody id="positions-body"></tbody>
      </table>
    </div>

    <!-- Equity Curve -->
    <div class="card">
      <div class="card-title">자산 곡선</div>
      <div class="chart-container"><canvas id="equity-chart"></canvas></div>
    </div>

    <!-- Recent Orders -->
    <div class="card">
      <div class="card-title">최근 주문 (10건)</div>
      <table>
        <thead><tr><th>시간</th><th>방향</th><th>티커</th><th>가격</th><th>상태</th></tr></thead>
        <tbody id="orders-body"></tbody>
      </table>
    </div>

    <!-- Recent Trades -->
    <div class="card">
      <div class="card-title">최근 체결 (10건)</div>
      <table>
        <thead><tr><th>시간</th><th>방향</th><th>티커</th><th>가격</th><th>수량</th></tr></thead>
        <tbody id="trades-body"></tbody>
      </table>
    </div>

    <!-- Event Log -->
    <div class="card dash-full">
      <div class="card-title">이벤트 로그</div>
      <div class="event-log" id="event-log"></div>
    </div>
  </div>
</div>

<!-- ===== Tab 2: Agent 관리 ===== -->
<div id="page-agents" class="page">
  <div class="card-title" style="padding:0 0 12px 0">Agent 현황</div>
  <div class="agent-grid" id="agent-grid"></div>

  <div class="card" style="margin-top:8px">
    <div class="card-title">Improver 피드백 로그</div>
    <div class="improver-timeline" id="improver-timeline">
      <div class="empty-msg">피드백 로그가 없습니다.</div>
    </div>
  </div>
</div>

<!-- ===== Tab 3: 설정 ===== -->
<div id="page-settings" class="page">
  <div class="settings-grid">

    <!-- Mode Settings -->
    <div class="card">
      <div class="card-title">모드 설정</div>
      <div class="form-group">
        <div class="toggle-wrap">
          <label class="toggle">
            <input type="checkbox" id="cfg-dryrun">
            <span class="toggle-slider"></span>
          </label>
          <span class="toggle-label" id="cfg-dryrun-label">모의매매</span>
        </div>
      </div>
      <div class="form-group">
        <div class="form-label">시스템 상태</div>
        <span id="cfg-system-status" class="badge badge-green">운영중</span>
      </div>
    </div>

    <!-- LLM Settings -->
    <div class="card">
      <div class="card-title">LLM 설정</div>
      <div class="form-group">
        <label class="form-label">모델 선택</label>
        <select class="form-select" id="cfg-llm-model">
          <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
          <option value="claude-opus-4-6">claude-opus-4-6</option>
          <option value="gpt-4o">gpt-4o</option>
          <option value="gpt-4o-mini">gpt-4o-mini</option>
          <option value="gemini-2.5-pro">gemini-2.5-pro</option>
          <option value="gemini-2.5-flash">gemini-2.5-flash</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Endpoint URL</label>
        <input class="form-input" type="text" id="cfg-llm-endpoint" placeholder="비어있으면 기본 Anthropic/OpenAI/Google">
      </div>
      <div class="form-note">API 키는 Secrets Manager에서 관리됩니다.</div>
    </div>

    <!-- Risk Settings -->
    <div class="card">
      <div class="card-title">리스크 설정</div>
      <div class="form-group">
        <label class="form-label">거래당 자본 비율</label>
        <input class="form-input" type="number" id="cfg-risk-per-trade" min="0.001" max="0.1" step="0.001">
      </div>
      <div class="form-group">
        <label class="form-label">일일 손실 한도</label>
        <input class="form-input" type="number" id="cfg-risk-daily-loss" min="0.01" max="0.2" step="0.01">
      </div>
      <div class="form-group">
        <label class="form-label">최대 동시 포지션</label>
        <input class="form-input" type="number" id="cfg-max-positions" min="1" max="20" step="1">
      </div>
      <div class="form-group">
        <label class="form-label">의사결정 임계값</label>
        <input class="form-input" type="number" id="cfg-decision-threshold" min="0.1" max="1.0" step="0.05">
      </div>
    </div>

    <!-- Trading Tickers -->
    <div class="card">
      <div class="card-title">매매 종목</div>
      <div class="ticker-pills" id="ticker-pills"></div>
      <div class="ticker-add-row">
        <input class="form-input" type="text" id="ticker-input" placeholder="KRW-BTC">
        <button class="btn btn-primary" onclick="addTicker()">추가</button>
      </div>
    </div>

    <!-- System Log -->
    <div class="card settings-full">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        시스템 로그
        <button class="btn" onclick="refreshLogs()">새로고침</button>
      </div>
      <div class="sys-log" id="sys-log">로그를 불러오는 중...</div>
    </div>

    <!-- System Control -->
    <div class="card settings-full">
      <div class="card-title">시스템 제어</div>
      <div class="btn-row" style="margin-bottom:16px">
        <button class="btn btn-danger" onclick="controlAction('halt','매매를 정지하시겠습니까?')">매매 정지</button>
        <button class="btn btn-green" onclick="controlAction('resume','매매를 재개하시겠습니까?')">매매 재개</button>
        <button class="btn btn-danger" onclick="controlAction('liquidate','전체 포지션을 긴급 청산하시겠습니까?\\n이 작업은 되돌릴 수 없습니다.')">긴급 청산</button>
        <button class="btn btn-critical" onclick="systemStop()">시스템 종료</button>
      </div>
    </div>

    <!-- Save Button -->
    <div class="settings-full" style="text-align:right;padding-top:8px">
      <button class="btn btn-primary" onclick="saveConfig()" style="padding:10px 32px;font-size:0.9rem">설정 저장</button>
    </div>
  </div>
</div>

<!-- Toast Notification -->
<div class="toast" id="toast"></div>

<script>
/* ========== Helpers ========== */
function $(id) { return document.getElementById(id); }
function fmt(n) {
  if (n == null || isNaN(n)) return '-';
  return Number(n).toLocaleString('ko-KR', { maximumFractionDigits: 0 });
}
function fmtDec(n, d) {
  if (n == null || isNaN(n)) return '-';
  return Number(n).toLocaleString('ko-KR', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function pct(n) {
  if (n == null || isNaN(n)) return '-';
  var v = (n * 100).toFixed(2);
  return (n >= 0 ? '+' : '') + v + '%';
}
function cls(n) { return n >= 0 ? 'pos' : 'neg'; }
function relTime(ts) {
  if (!ts) return '-';
  var now = Date.now() / 1000;
  var t = typeof ts === 'number' ? ts : new Date(ts).getTime() / 1000;
  var diff = Math.max(0, now - t);
  if (diff < 60) return Math.floor(diff) + '초 전';
  if (diff < 3600) return Math.floor(diff / 60) + '분 전';
  if (diff < 86400) return Math.floor(diff / 3600) + '시간 전';
  return Math.floor(diff / 86400) + '일 전';
}
function fmtUptime(sec) {
  if (sec == null) return '-';
  var s = Math.floor(sec);
  var d = Math.floor(s / 86400); s %= 86400;
  var h = Math.floor(s / 3600); s %= 3600;
  var m = Math.floor(s / 60);
  if (d > 0) return d + '일 ' + h + '시간';
  if (h > 0) return h + '시간 ' + m + '분';
  return m + '분';
}
function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ========== Toast ========== */
var toastTimer = null;
function showToast(msg, type) {
  var t = $('toast');
  t.textContent = msg;
  t.className = 'toast toast-' + (type || 'success') + ' show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function() { t.classList.remove('show'); }, 3000);
}

/* ========== API ========== */
async function api(url, method, body) {
  var opts = { method: method || 'GET', headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  var r = await fetch(url, opts);
  return r.json();
}

/* ========== Navigation / Routing ========== */
var currentTab = 'dashboard';
var intervals = {};

function navigate(tab) {
  currentTab = tab;
  window.location.hash = '#' + tab;
  document.querySelectorAll('.topnav-tab').forEach(function(el) {
    el.classList.toggle('active', el.getAttribute('data-tab') === tab);
  });
  document.querySelectorAll('.page').forEach(function(el) {
    el.classList.toggle('active', el.id === 'page-' + tab);
  });
  stopAllPolling();
  startPolling(tab);
}

function stopAllPolling() {
  Object.keys(intervals).forEach(function(k) {
    clearInterval(intervals[k]);
    delete intervals[k];
  });
}

function startPolling(tab) {
  if (tab === 'dashboard') {
    refreshDashboard();
    intervals.dashboard = setInterval(refreshDashboard, 3000);
  } else if (tab === 'agents') {
    refreshAgents();
    intervals.agents = setInterval(refreshAgents, 5000);
    refreshImproverLog();
    intervals.improver = setInterval(refreshImproverLog, 30000);
  } else if (tab === 'settings') {
    loadConfig();
    refreshLogs();
    intervals.logs = setInterval(refreshLogs, 5000);
  }
}

/* ========== Tab 1: Dashboard ========== */
async function refreshDashboard() {
  try {
    var [st, orders, trades, eq] = await Promise.all([
      api('/api/state'),
      api('/api/orders?limit=10'),
      api('/api/trades?limit=10'),
      api('/api/equity?last=500')
    ]);
    renderKPI(st);
    renderBadges(st);
    renderPositions(st.capital ? st.capital.positions || {} : {});
    renderOrders(orders);
    renderTrades(trades);
    renderEquity(eq);
  } catch (e) {
    console.error('Dashboard refresh error:', e);
  }
}

function renderKPI(st) {
  var c = st.capital || {};
  $('kpi-equity').textContent = fmt(c.total_equity) + ' KRW';
  $('kpi-available').textContent = fmt(c.available_krw) + ' KRW';

  var upnl = c.unrealized_pnl || 0;
  $('kpi-unrealized').textContent = fmt(upnl) + ' KRW';
  $('kpi-unrealized').className = 'kpi-value ' + cls(upnl);

  var ret = c.total_return_pct;
  $('kpi-return').textContent = pct(ret);
  $('kpi-return').className = 'kpi-value ' + cls(ret || 0);
}

function renderBadges(st) {
  var html = '';
  if (st.halted) {
    html += '<span class="badge badge-red">정지</span>';
  } else if (st.dry_run) {
    html += '<span class="badge badge-yellow">DRY-RUN</span>';
  } else {
    html += '<span class="badge badge-green">운영중</span>';
  }
  $('system-badges').innerHTML = html;
}

function renderPositions(positions) {
  var entries = Object.entries(positions);
  if (entries.length === 0) {
    $('positions-body').innerHTML = '<tr><td colspan="5" class="empty-msg">보유 포지션이 없습니다.</td></tr>';
    return;
  }
  $('positions-body').innerHTML = entries.map(function(e) {
    var t = e[0], p = e[1];
    var pnl = p.unrealized_pnl || 0;
    var pnlPct = p.unrealized_pnl_pct;
    return '<tr>' +
      '<td>' + escHtml(t) + '</td>' +
      '<td>' + fmt(p.entry_price) + '</td>' +
      '<td>' + fmt(p.current_price) + '</td>' +
      '<td class="' + cls(pnl) + '">' + fmt(pnl) + ' (' + pct(pnlPct) + ')</td>' +
      '<td>' + fmtDec(p.volume, 6) + '</td>' +
      '</tr>';
  }).join('');
}

function renderOrders(orders) {
  if (!orders || orders.length === 0) {
    $('orders-body').innerHTML = '<tr><td colspan="5" class="empty-msg">최근 주문이 없습니다.</td></tr>';
    return;
  }
  $('orders-body').innerHTML = orders.map(function(o) {
    var side = o.side === 'buy' ? '매수' : '매도';
    var sideClass = o.side === 'buy' ? 'pos' : 'neg';
    return '<tr>' +
      '<td>' + (o.created_at || '').slice(5, 16) + '</td>' +
      '<td class="' + sideClass + '">' + side + '</td>' +
      '<td>' + escHtml(o.ticker) + '</td>' +
      '<td>' + fmt(o.price) + '</td>' +
      '<td>' + escHtml(o.state) + '</td>' +
      '</tr>';
  }).join('');
}

function renderTrades(trades) {
  if (!trades || trades.length === 0) {
    $('trades-body').innerHTML = '<tr><td colspan="5" class="empty-msg">최근 체결이 없습니다.</td></tr>';
    return;
  }
  $('trades-body').innerHTML = trades.map(function(t) {
    var side = t.side === 'buy' ? '매수' : '매도';
    var sideClass = t.side === 'buy' ? 'pos' : 'neg';
    return '<tr>' +
      '<td>' + (t.ts || '').slice(5, 16) + '</td>' +
      '<td class="' + sideClass + '">' + side + '</td>' +
      '<td>' + escHtml(t.ticker) + '</td>' +
      '<td>' + fmt(t.price) + '</td>' +
      '<td>' + fmtDec(t.volume, 6) + '</td>' +
      '</tr>';
  }).join('');
}

/* ===== Equity Chart ===== */
var eqChart = null;
function initChart() {
  var ctx = $('equity-chart').getContext('2d');
  eqChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: '총 자산',
        data: [],
        borderColor: '#58a6ff',
        borderWidth: 1.5,
        fill: false,
        pointRadius: 0,
        tension: 0.3
      }, {
        label: '미실현 손익',
        data: [],
        borderColor: '#d29922',
        borderWidth: 1,
        fill: false,
        pointRadius: 0,
        tension: 0.3,
        borderDash: [4, 2]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: {
          ticks: {
            callback: function(v) { return fmt(v); },
            color: '#8b949e',
            font: { size: 11 }
          },
          grid: { color: '#21262d' }
        }
      },
      plugins: {
        legend: {
          labels: {
            color: '#8b949e',
            boxWidth: 12,
            font: { size: 11 }
          }
        }
      }
    }
  });
}

function renderEquity(eq) {
  if (!eq || !eq.length || !eqChart) return;
  eqChart.data.labels = eq.map(function(p) {
    return new Date(p.ts * 1000).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  });
  eqChart.data.datasets[0].data = eq.map(function(p) { return p.equity; });
  eqChart.data.datasets[1].data = eq.map(function(p) { return p.unrealized_pnl; });
  eqChart.update('none');
}

/* ========== Tab 2: Agent Management ========== */
async function refreshAgents() {
  try {
    var agents = await api('/api/agents');
    renderAgentGrid(agents);
  } catch (e) {
    console.error('Agent refresh error:', e);
  }
}

function renderAgentGrid(agents) {
  if (!agents || agents.length === 0) {
    $('agent-grid').innerHTML = '<div class="empty-msg">등록된 Agent가 없습니다.</div>';
    return;
  }
  $('agent-grid').innerHTML = agents.map(function(a) {
    var dotClass = a.task_exception ? 'dot-err' : (a.stopping ? 'dot-warn' : 'dot-ok');
    var m = a.metrics || {};
    var successPct = m.success_rate != null ? (m.success_rate * 100).toFixed(1) : '0.0';
    var successWidth = m.success_rate != null ? Math.min(100, m.success_rate * 100) : 0;
    var errClass = (m.events_failed || 0) > 0 ? 'neg' : '';

    var errorSection = '';
    if (a.last_error) {
      errorSection = '<div class="agent-error" onclick="this.classList.toggle(\'expanded\')">' +
        '<strong>최근 에러</strong> (클릭하여 펼치기)' +
        '<div class="agent-error-detail">' + escHtml(a.last_error) + '</div>' +
        '</div>';
    }

    return '<div class="agent-card">' +
      '<div class="agent-header">' +
        '<span class="agent-dot ' + dotClass + '"></span>' +
        '<span class="agent-name-ko">' + escHtml(a.display_name || a.name) + '</span>' +
        '<span class="agent-name-en">' + escHtml(a.name) + '</span>' +
      '</div>' +
      '<div class="agent-role">' + escHtml(a.role || '') + '</div>' +
      '<div class="agent-metrics">' +
        '<div class="agent-metric-row"><span class="agent-metric-label">처리 이벤트</span><span>' + (m.events_processed || 0) + '</span></div>' +
        '<div class="agent-metric-row"><span class="agent-metric-label">성공률</span><span>' + successPct + '% <span class="success-bar-bg"><span class="success-bar-fill" style="width:' + successWidth + '%"></span></span></span></div>' +
        '<div class="agent-metric-row"><span class="agent-metric-label">에러 수</span><span class="' + errClass + '">' + (m.events_failed || 0) + '</span></div>' +
        '<div class="agent-metric-row"><span class="agent-metric-label">가동시간</span><span>' + fmtUptime(m.uptime_sec) + '</span></div>' +
        '<div class="agent-metric-row"><span class="agent-metric-label">마지막 활동</span><span>' + relTime(m.last_activity_ts) + '</span></div>' +
      '</div>' +
      errorSection +
      '</div>';
  }).join('');
}

async function refreshImproverLog() {
  try {
    var logs = await api('/api/improver/log');
    renderImproverLog(logs);
  } catch (e) {
    console.error('Improver log error:', e);
  }
}

function renderImproverLog(logs) {
  if (!logs || logs.length === 0) {
    $('improver-timeline').innerHTML = '<div class="empty-msg">피드백 로그가 없습니다.</div>';
    return;
  }
  $('improver-timeline').innerHTML = logs.map(function(entry) {
    var sourceClass = entry.source === 'seed' ? 'improver-source-seed' : 'improver-source-llm';
    var sourceLabel = entry.source === 'seed' ? 'SEED' : 'LLM';
    var keys = Array.isArray(entry.updated_keys) ? entry.updated_keys.join(', ') : (entry.updated_keys || '-');
    return '<div class="improver-entry">' +
      '<div class="improver-ts">' + escHtml(entry.timestamp || '') +
        '<span class="improver-source ' + sourceClass + '">' + sourceLabel + '</span>' +
      '</div>' +
      '<div class="improver-keys">변경: ' + escHtml(keys) + '</div>' +
      '</div>';
  }).join('');
}

/* ========== Tab 3: Settings ========== */
var currentConfig = {};
var currentTickers = [];

async function loadConfig() {
  try {
    var cfg = await api('/api/config');
    currentConfig = cfg;
    $('cfg-dryrun').checked = !!cfg.dry_run;
    updateDryRunLabel();

    if (cfg.halted) {
      $('cfg-system-status').textContent = '정지';
      $('cfg-system-status').className = 'badge badge-red';
    } else if (cfg.dry_run) {
      $('cfg-system-status').textContent = 'DRY-RUN';
      $('cfg-system-status').className = 'badge badge-yellow';
    } else {
      $('cfg-system-status').textContent = '운영중';
      $('cfg-system-status').className = 'badge badge-green';
    }

    if (cfg.llm_model) $('cfg-llm-model').value = cfg.llm_model;
    $('cfg-llm-endpoint').value = cfg.llm_endpoint || '';

    $('cfg-risk-per-trade').value = cfg.per_trade_risk_pct || 0.02;
    $('cfg-risk-daily-loss').value = cfg.daily_loss_limit_pct || 0.05;
    $('cfg-max-positions').value = cfg.max_concurrent_positions || 5;
    $('cfg-decision-threshold').value = cfg.decision_threshold || 0.5;

    currentTickers = cfg.tickers || [];
    renderTickers();
  } catch (e) {
    console.error('Config load error:', e);
  }
}

function updateDryRunLabel() {
  $('cfg-dryrun-label').textContent = $('cfg-dryrun').checked ? '모의매매' : '실매매';
}

function renderTickers() {
  $('ticker-pills').innerHTML = currentTickers.map(function(t, i) {
    return '<span class="ticker-pill">' + escHtml(t) +
      '<span class="ticker-pill-x" onclick="removeTicker(' + i + ')">&times;</span></span>';
  }).join('');
}

function addTicker() {
  var input = $('ticker-input');
  var val = input.value.trim().toUpperCase();
  if (!val) return;
  if (!/^KRW-[A-Z0-9]+$/.test(val)) {
    showToast('형식이 올바르지 않습니다. (예: KRW-BTC)', 'error');
    return;
  }
  if (currentTickers.indexOf(val) !== -1) {
    showToast('이미 추가된 종목입니다.', 'error');
    return;
  }
  currentTickers.push(val);
  renderTickers();
  input.value = '';
}

function removeTicker(idx) {
  currentTickers.splice(idx, 1);
  renderTickers();
}

async function refreshLogs() {
  try {
    var data = await api('/api/logs?lines=200');
    var logEl = $('sys-log');
    var text = Array.isArray(data) ? data.join('\\n') : (data.logs || data.text || JSON.stringify(data));
    logEl.textContent = text;
    logEl.scrollTop = logEl.scrollHeight;
  } catch (e) {
    $('sys-log').textContent = '로그를 불러올 수 없습니다.';
  }
}

async function saveConfig() {
  var payload = {
    dry_run: $('cfg-dryrun').checked,
    llm_model: $('cfg-llm-model').value,
    llm_endpoint: $('cfg-llm-endpoint').value || null,
    per_trade_risk_pct: parseFloat($('cfg-risk-per-trade').value),
    daily_loss_limit_pct: parseFloat($('cfg-risk-daily-loss').value),
    max_concurrent_positions: parseInt($('cfg-max-positions').value),
    decision_threshold: parseFloat($('cfg-decision-threshold').value),
    tickers: currentTickers
  };
  try {
    await api('/api/config', 'PUT', payload);
    showToast('설정이 저장되었습니다.', 'success');
  } catch (e) {
    showToast('설정 저장에 실패했습니다.', 'error');
  }
}

/* ===== System Control ===== */
async function controlAction(action, msg) {
  if (!confirm(msg)) return;
  try {
    await api('/api/control/' + action, 'POST');
    showToast('명령이 실행되었습니다.', 'success');
  } catch (e) {
    showToast('명령 실행에 실패했습니다.', 'error');
  }
}

function systemStop() {
  if (!confirm('시스템을 종료하시겠습니까?')) return;
  if (!confirm('정말로 시스템을 종료하시겠습니까?\\n이 작업은 모든 Agent를 중단합니다.')) return;
  api('/api/control/system-stop', 'POST').then(function() {
    showToast('시스템 종료 명령이 전송되었습니다.', 'success');
  }).catch(function() {
    showToast('시스템 종료에 실패했습니다.', 'error');
  });
}

/* ========== WebSocket ========== */
var ws = null;
var wsReconnectTimer = null;

function connectWS() {
  var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
  ws = new WebSocket(proto + location.host + '/ws');

  ws.onopen = function() {
    $('ws-indicator').style.background = 'var(--green)';
    $('ws-label').textContent = '연결됨';
    $('ws-label').style.color = 'var(--green)';
  };

  ws.onclose = function() {
    $('ws-indicator').style.background = 'var(--red)';
    $('ws-label').textContent = '연결 끊김';
    $('ws-label').style.color = 'var(--red)';
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = setTimeout(connectWS, 3000);
  };

  ws.onerror = function() {
    ws.close();
  };

  ws.onmessage = function(e) {
    try {
      var d = JSON.parse(e.data);
      if (d.topic === 'heartbeat') return;
      var log = $('event-log');
      var time = new Date().toLocaleTimeString('ko-KR');
      var entry = document.createElement('div');
      entry.className = 'event-log-entry';
      entry.innerHTML = '<span style="color:var(--muted)">' + time + '</span> ' +
        '<span style="color:var(--accent)">[' + escHtml(d.topic) + ']</span> ' +
        escHtml(JSON.stringify(d.payload || '').slice(0, 200));
      log.insertBefore(entry, log.firstChild);
      while (log.children.length > 50) {
        log.removeChild(log.lastChild);
      }
    } catch (err) { /* ignore parse errors */ }
  };
}

/* ========== Init ========== */
function initApp() {
  initChart();
  connectWS();

  $('cfg-dryrun').addEventListener('change', updateDryRunLabel);

  $('ticker-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') addTicker();
  });

  /* Clock */
  setInterval(function() {
    $('clock').textContent = new Date().toLocaleTimeString('ko-KR');
  }, 1000);

  /* Hash routing */
  var hash = window.location.hash.replace('#', '') || 'dashboard';
  if (['dashboard', 'agents', 'settings'].indexOf(hash) === -1) hash = 'dashboard';
  navigate(hash);

  window.addEventListener('hashchange', function() {
    var h = window.location.hash.replace('#', '') || 'dashboard';
    if (['dashboard', 'agents', 'settings'].indexOf(h) !== -1 && h !== currentTab) {
      navigate(h);
    }
  });
}

initApp();
</script>
</body>
</html>
"""
