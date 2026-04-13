INDEX_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kuromi Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --accent: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
  --blue: #388bfd;
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

/* ===== App Header ===== */
.appheader {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-title {
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 48px;
  border-bottom: 1px solid var(--border);
}
.header-logo {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.8rem;
}
.header-tabs {
  display: flex;
  gap: 0;
  padding: 0 24px;
  height: 40px;
}
.header-tab {
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
.header-tab:hover { color: var(--text); }
.header-tab.active {
  color: var(--text);
  border-bottom-color: var(--accent);
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
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
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
/* 한국 증권 컨벤션: 상승/매수/이익=빨강, 하락/매도/손실=파랑, 보합=회색 */
.pos { color: var(--red); }
.neg { color: var(--blue); }
.neutral { color: var(--muted); }

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

/* Mode Switch */
.mode-switch { display:flex; border:1px solid var(--border); border-radius:8px; overflow:hidden; }
.mode-btn { flex:1; padding:14px; background:var(--bg); border:none; color:var(--muted); font-size:0.9rem; font-weight:600; cursor:pointer; transition:all 0.2s; text-align:center; }
.mode-btn:first-child { border-right:1px solid var(--border); }
.mode-btn.sel-dry { background:var(--yellow); color:#000; }
.mode-btn.sel-live { background:rgba(248,81,73,0.15); color:var(--red); font-weight:700; }
.mode-desc { font-size:0.8rem; color:var(--muted); margin-top:10px; padding:8px 10px; background:var(--bg); border-radius:6px; line-height:1.5; }

/* Range Sliders */
.slider-group { margin-bottom:20px; }
.slider-header { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px; }
.slider-label { font-size:0.82rem; color:var(--text); }
.slider-val { font-size:1.05rem; font-weight:700; color:var(--accent); min-width:40px; text-align:right; }
input[type=range] { -webkit-appearance:none; width:100%; height:6px; background:var(--border); border-radius:3px; outline:none; cursor:pointer; margin:4px 0; }
input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:20px; height:20px; border-radius:50%; background:var(--accent); cursor:pointer; box-shadow:0 0 0 3px var(--surface); }
input[type=range]::-moz-range-thumb { width:20px; height:20px; border-radius:50%; background:var(--accent); cursor:pointer; border:3px solid var(--surface); }
.slider-ticks { display:flex; justify-content:space-between; font-size:0.65rem; color:var(--muted); margin-top:2px; padding:0 2px; }
.slider-range-hint { display:flex; justify-content:space-between; font-size:0.68rem; color:var(--muted); margin-top:3px; padding:0 1px; }
.slider-note { font-size:0.72rem; color:var(--muted); margin-top:6px; font-style:italic; }

/* Ticker Chips */
.ticker-chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.ticker-chip { display:inline-flex; align-items:center; gap:6px; padding:8px 14px; background:var(--bg); border:1.5px solid var(--border); border-radius:20px; cursor:pointer; transition:all 0.15s; font-size:0.82rem; user-select:none; }
.ticker-chip:hover { border-color:var(--muted); }
.ticker-chip.active { border-color:var(--accent); background:rgba(88,166,255,0.08); font-weight:600; }
.chip-dot { width:6px; height:6px; border-radius:50%; background:var(--border); flex-shrink:0; }
.ticker-chip.active .chip-dot { background:var(--green); }
.ticker-chip-price { font-size:0.7rem; color:var(--muted); margin-left:2px; }
.ticker-note { font-size:0.78rem; color:var(--muted); margin-bottom:8px; line-height:1.5; }

/* LLM Row */
.llm-row { display:flex; align-items:center; gap:10px; }
.llm-badge { font-size:0.7rem; padding:2px 8px; border-radius:10px; font-weight:600; white-space:nowrap; }
.llm-on { background:rgba(63,185,80,0.15); color:var(--green); }

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

<!-- ===== App Header ===== -->
<header class="appheader">
  <div class="header-title">
    <span class="header-logo"><img src="data:image/png;base64,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" style="width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:6px">Kuromi</span>
    <div class="header-right">
      <span id="ws-indicator"></span>
      <span id="ws-label">연결 중...</span>
      <span id="clock"></span>
    </div>
  </div>
  <nav class="header-tabs">
    <a class="header-tab active" data-tab="dashboard" onclick="navigate('dashboard')">종합 대시보드</a>
    <a class="header-tab" data-tab="agents" onclick="navigate('agents')">Agent 관리</a>
    <a class="header-tab" data-tab="settings" onclick="navigate('settings')">설정</a>
    <a class="header-tab" data-tab="system" onclick="navigate('system')">시스템</a>
  </nav>
</header>

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
      <div class="kpi-sub" id="kpi-locked" style="font-size:0.72rem;color:#94a3b8;margin-top:2px"></div>
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

    <!-- 매매 모드 -->
    <div class="card">
      <div class="card-title">매매 모드</div>
      <div class="mode-switch">
        <button class="mode-btn sel-dry" id="mode-dry" onclick="setMode(true)">모의매매</button>
        <button class="mode-btn" id="mode-live" onclick="setMode(false)">실매매</button>
      </div>
      <div class="mode-desc" id="mode-desc">모의매매 모드입니다. 실제 주문이 실행되지 않습니다.</div>
    </div>

    <!-- LLM 설정 -->
    <div class="card">
      <div class="card-title">LLM 설정</div>
      <div class="form-group">
        <label class="form-label">Improver 모델</label>
        <div id="llm-active-display" style="display:flex;align-items:center;gap:8px;padding:10px;background:rgba(63,185,80,0.08);border:1px solid rgba(63,185,80,0.3);border-radius:6px;margin-bottom:8px">
          <span style="width:8px;height:8px;border-radius:50%;background:var(--green);flex-shrink:0"></span>
          <span style="font-size:0.88rem;font-weight:600;color:var(--green)" id="llm-active-name">-</span>
          <span style="font-size:0.72rem;color:var(--muted);margin-left:auto">현재 사용 중</span>
        </div>
        <select class="form-select" id="cfg-llm-model">
          <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
          <option value="claude-opus-4-6">Claude Opus 4.6</option>
          <option value="gpt-4o">GPT-4o</option>
          <option value="gpt-4o-mini">GPT-4o Mini</option>
          <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
          <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
        </select>
        <div class="form-note" style="margin-top:4px">다른 모델 선택 후 저장 버튼으로 적용</div>
      </div>
      <div class="form-group">
        <label class="form-label">Endpoint URL</label>
        <input class="form-input" type="text" id="cfg-llm-endpoint" placeholder="비어있으면 기본 Anthropic/OpenAI/Google API">
      </div>
      <div class="form-note">API 키는 AWS Secrets Manager에서 관리됩니다.</div>
    </div>

    <!-- 리스크 설정 -->
    <div class="card settings-full">
      <div class="card-title">리스크 설정</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px 36px">
        <div class="slider-group">
          <div class="slider-header">
            <span class="slider-label">거래당 투자 비율</span>
            <span class="slider-val" id="risk-per-trade-val">1%</span>
          </div>
          <input type="range" id="cfg-risk-per-trade" min="1" max="20" step="1" value="1">
          <div class="slider-range-hint"><span>1%</span><span>20%</span></div>
          <div class="slider-note">한 번의 매매에 투입하는 총 자본 대비 비율</div>
        </div>
        <div class="slider-group">
          <div class="slider-header">
            <span class="slider-label">일일 손실 한도</span>
            <span class="slider-val" id="risk-daily-loss-val">3%</span>
          </div>
          <input type="range" id="cfg-risk-daily-loss" min="1" max="20" step="1" value="3">
          <div class="slider-range-hint"><span>1%</span><span>20%</span></div>
          <div class="slider-note">초과 시 매매 자동 중단</div>
        </div>
        <div class="slider-group">
          <div class="slider-header">
            <span class="slider-label">최대 동시 포지션</span>
            <span class="slider-val" id="max-positions-val">3개</span>
          </div>
          <input type="range" id="cfg-max-positions" min="1" max="10" step="1" value="3">
          <div class="slider-range-hint"><span>1개</span><span>10개</span></div>
        </div>
        <div class="slider-group">
          <div class="slider-header">
            <span class="slider-label">매매 신호 임계값</span>
            <span class="slider-val" id="decision-threshold-val">50%</span>
          </div>
          <input type="range" id="cfg-decision-threshold" min="10" max="90" step="5" value="50">
          <div class="slider-range-hint"><span>10%</span><span>90%</span></div>
          <div class="slider-note">높을수록 보수적 — 강한 시그널에서만 매매 실행</div>
        </div>
      </div>
    </div>

    <!-- 매매 종목 -->
    <div class="card settings-full">
      <div class="card-title">매매 종목</div>
      <div class="ticker-note">StrategyAgent가 아래 종목들의 시그널을 분석합니다. 권장: 5개 이하 (많을수록 연산 부하 증가).</div>

      <div class="form-label" style="margin-bottom:6px">선택된 종목 <span id="ticker-count-badge" style="font-size:0.75rem;color:var(--accent)"></span></div>
      <div class="ticker-chips" id="ticker-selected"></div>

      <div style="margin-top:18px;margin-bottom:8px;display:flex;gap:8px;align-items:center">
        <input class="form-input" type="text" id="ticker-search" placeholder="종목 검색 (BTC, 비트코인...)" style="flex:1;font-size:0.82rem">
        <button class="btn" onclick="selectRecommended()" style="white-space:nowrap">⭐ 추천 선택</button>
        <button class="btn" onclick="clearAllTickers()" style="white-space:nowrap;color:var(--muted)">초기화</button>
      </div>
      <div class="ticker-note" style="margin-bottom:8px" id="ticker-search-hint">Upbit KRW 전체 종목 로딩 중...</div>
      <div class="ticker-chips" id="ticker-available" style="max-height:180px;overflow-y:auto;padding:4px 0"></div>
    </div>

    <!-- 저장 -->
    <div class="settings-full" style="display:flex;justify-content:flex-end;align-items:center;gap:16px;padding-top:8px">
      <span style="font-size:0.75rem;color:var(--muted)">LLM 모델 · 리스크 · 종목 저장 &nbsp;|&nbsp; 매매 모드는 버튼 클릭 시 즉시 반영</span>
      <button class="btn btn-primary" onclick="saveConfig()" style="padding:10px 28px;font-size:0.9rem">저장</button>
    </div>
  </div>
</div>

<!-- ===== Tab 4: 시스템 ===== -->
<div id="page-system" class="page">
  <!-- 이벤트 로그 -->
  <div class="card" style="margin-bottom:16px">
    <div class="card-title">이벤트 로그</div>
    <div class="event-log" id="event-log"></div>
  </div>

  <!-- 시스템 제어 -->
  <div class="card" style="margin-bottom:16px">
    <div class="card-title">시스템 제어</div>
    <div class="btn-row" style="margin-bottom:16px">
      <button class="btn btn-danger" onclick="controlAction('halt','매매를 정지하시겠습니까?')">매매 정지</button>
      <button class="btn btn-green" onclick="controlAction('resume','매매를 재개하시겠습니까?')">매매 재개</button>
      <button class="btn btn-danger" onclick="controlAction('liquidate','전체 포지션을 긴급 청산하시겠습니까?\\n이 작업은 되돌릴 수 없습니다.')">긴급 청산</button>
      <button class="btn btn-critical" onclick="systemStop()">시스템 종료</button>
    </div>
  </div>

  <!-- 시스템 로그 -->
  <div class="card">
    <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
      시스템 로그 <span style="font-size:0.65rem;color:var(--muted);font-weight:400;text-transform:none">logs/kuromi.log</span>
      <button class="btn" onclick="refreshLogs()">새로고침</button>
    </div>
    <div class="sys-log" id="sys-log">로그를 불러오는 중...</div>
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
function cls(n) { return n > 0 ? 'pos' : n < 0 ? 'neg' : 'neutral'; }
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
  document.querySelectorAll('.header-tab').forEach(function(el) {
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
  } else if (tab === 'system') {
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
    // A·C: 전역 캐시 업데이트 (설정 탭 종목 추천용)
    if (st.last_signals) lastSignals = st.last_signals;
    if (st.capital) lastCapital = st.capital;
    if (st.last_prices) lastPrices = st.last_prices;
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

  var locked = c.locked_krw || 0;
  var lockedEl = $('kpi-locked');
  if (lockedEl) {
    lockedEl.textContent = locked > 0 ? ('주문 중 ' + fmt(locked) + ' KRW') : '';
  }

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
  var STATE_KO = {
    'submitted': '제출됨', 'accepted': '접수됨', 'partially_filled': '부분체결',
    'filled': '체결완료', 'cancelled': '취소됨', 'failed': '실패'
  };
  $('orders-body').innerHTML = orders.map(function(o) {
    var side = o.side === 'buy' ? '매수' : '매도';
    var sideClass = o.side === 'buy' ? 'pos' : 'neg';
    var stateLabel = STATE_KO[o.state] || o.state;
    var stateClass = o.state === 'failed' ? 'neg' : o.state === 'filled' ? 'pos' : '';
    return '<tr>' +
      '<td>' + (o.created_at || '').slice(5, 16) + '</td>' +
      '<td class="' + sideClass + '">' + side + '</td>' +
      '<td>' + escHtml(o.ticker) + '</td>' +
      '<td>' + fmt(o.price) + '</td>' +
      '<td class="' + stateClass + '">' + stateLabel + '</td>' +
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
    var sideClass = t.side === 'buy' ? 'pos' : 'neg';  /* 매수=빨강, 매도=파랑 */
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

    var lastError = m.last_error || null;
    var errorSection = '';
    if (lastError) {
      errorSection = '<div class="agent-error" onclick="this.classList.toggle(\\'expanded\\')">' +
        '<strong>최근 에러</strong> (클릭하여 펼치기)' +
        '<div class="agent-error-detail">' + escHtml(lastError) + '</div>' +
        '</div>';
    }

    return '<div class="agent-card">' +
      '<div class="agent-header">' +
        '<span class="agent-dot ' + dotClass + '"></span>' +
        '<span class="agent-name-ko">' + escHtml(a.label || a.name) + '</span>' +
        '<span class="agent-name-en">' + escHtml(a.name) + '</span>' +
      '</div>' +
      '<div class="agent-role">' + escHtml(a.description || '') + '</div>' +
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
var lastPrices = {};
var lastSignals = {};    // C: 티커별 시그널 요약 {avg, momentum, ...}
var lastCapital = {};    // A: 최신 capital snapshot (포지션 손익 포함)
var tickerAdvice = {add: [], remove: []};  // B: ImproverAgent 편입/편출 추천
var allUpbitMarkets = [];  // {code, name} fetched from Upbit
var RECOMMENDED = ['KRW-BTC','KRW-ETH','KRW-XRP','KRW-SOL','KRW-DOGE','KRW-ADA','KRW-AVAX'];
var LLM_NAMES = {
  'claude-sonnet-4-6': 'Claude Sonnet 4.6',
  'claude-opus-4-6': 'Claude Opus 4.6',
  'gpt-4o': 'GPT-4o',
  'gpt-4o-mini': 'GPT-4o Mini',
  'gemini-2.5-pro': 'Gemini 2.5 Pro',
  'gemini-2.5-flash': 'Gemini 2.5 Flash'
};

function setMode(dryRun) {
  if (!dryRun) {
    if (!confirm('실매매 모드로 전환하시겠습니까?\\n실제 자금으로 거래가 실행됩니다.')) return;
  }
  api('/api/config', 'PUT', {dry_run: dryRun}).then(function() {
    updateModeUI(dryRun);
    showToast(dryRun ? '모의매매 모드로 전환' : '실매매 모드로 전환 (잔고 동기화까지 약 1분)', 'success');
  }).catch(function() { showToast('모드 전환 실패', 'error'); });
}

function updateModeUI(dryRun) {
  $('mode-dry').className = 'mode-btn' + (dryRun ? ' sel-dry' : '');
  $('mode-live').className = 'mode-btn' + (!dryRun ? ' sel-live' : '');
  $('mode-desc').textContent = dryRun
    ? '모의매매 모드입니다. 실제 주문이 실행되지 않습니다.'
    : '실매매 모드입니다. Upbit 잔고 동기화 후 실제 자금으로 거래가 실행됩니다.';
}

function updateLLMDisplay(modelValue) {
  var name = LLM_NAMES[modelValue] || modelValue;
  $('llm-active-name').textContent = name;
}

function setupSliders() {
  [
    {id:'cfg-risk-per-trade', valId:'risk-per-trade-val', suffix:'%'},
    {id:'cfg-risk-daily-loss', valId:'risk-daily-loss-val', suffix:'%'},
    {id:'cfg-max-positions', valId:'max-positions-val', suffix:'개'},
    {id:'cfg-decision-threshold', valId:'decision-threshold-val', suffix:'%'}
  ].forEach(function(s) {
    var el = $(s.id);
    if (el) el.addEventListener('input', function() {
      $(s.valId).textContent = el.value + s.suffix;
    });
  });
}

async function fetchUpbitMarkets() {
  try {
    var r = await fetch('https://api.upbit.com/v1/market/all?is_details=false');
    var markets = await r.json();
    allUpbitMarkets = markets
      .filter(function(m) { return m.market.startsWith('KRW-'); })
      .map(function(m) { return {code: m.market, name: m.korean_name}; })
      .sort(function(a, b) { return a.code.localeCompare(b.code); });
    $('ticker-search-hint').textContent = 'Upbit KRW 종목 ' + allUpbitMarkets.length + '개 로드됨. 검색어 입력 또는 아래 목록에서 선택.';
    renderAvailableTickers('');
  } catch(e) {
    $('ticker-search-hint').textContent = 'Upbit 종목 로드 실패. 검색이 제한됩니다.';
    allUpbitMarkets = RECOMMENDED.map(function(c) { return {code:c, name:c.replace('KRW-','')}; });
    renderAvailableTickers('');
  }
}

async function loadConfig() {
  try {
    var results = await Promise.all([api('/api/config'), api('/api/state')]);
    var cfg = results[0];
    var stData = results[1];
    currentConfig = cfg;
    lastPrices = stData.last_prices || {};

    updateModeUI(!!cfg.dry_run);

    var model = cfg.llm_model || 'claude-sonnet-4-6';
    $('cfg-llm-model').value = model;
    updateLLMDisplay(model);
    $('cfg-llm-endpoint').value = cfg.llm_endpoint || '';

    var pct1 = Math.round((cfg.per_trade_risk_pct || 0.01) * 100);
    $('cfg-risk-per-trade').value = pct1;
    $('risk-per-trade-val').textContent = pct1 + '%';

    var pct2 = Math.round((cfg.daily_loss_limit_pct || 0.03) * 100);
    $('cfg-risk-daily-loss').value = pct2;
    $('risk-daily-loss-val').textContent = pct2 + '%';

    var mp = cfg.max_concurrent_positions || 3;
    $('cfg-max-positions').value = mp;
    $('max-positions-val').textContent = mp + '개';

    var th = Math.round((cfg.decision_threshold || 0.5) * 100);
    $('cfg-decision-threshold').value = th;
    $('decision-threshold-val').textContent = th + '%';

    currentTickers = cfg.trading_tickers || [];
    // A·C: 최신 신호·자본 업데이트
    if (stData.last_signals) lastSignals = stData.last_signals;
    if (stData.capital) lastCapital = stData.capital;
    renderSelectedTickers();
    fetchUpbitMarkets();
    // B: ImproverAgent 편입/편출 추천 비동기 로드
    api('/api/improver/ticker-advice').then(function(adv) {
      if (adv && (adv.add || adv.remove)) {
        tickerAdvice = {add: adv.add || [], remove: adv.remove || []};
        renderSelectedTickers();
        renderAvailableTickers($('ticker-search') ? $('ticker-search').value : '');
      }
    }).catch(function() {});
  } catch (e) {
    console.error('Config load error:', e);
  }
}

function renderSelectedTickers() {
  var badge = $('ticker-count-badge');
  if (badge) badge.textContent = '(' + currentTickers.length + '개)';
  var el = $('ticker-selected');
  if (!el) return;
  if (currentTickers.length === 0) {
    el.innerHTML = '<span style="font-size:0.78rem;color:var(--muted)">선택된 종목 없음</span>';
    return;
  }
  var SIG_KEYS = ['momentum','zscore','rsi','bollinger_pct_b','macd_hist','stochastic_k','obv_slope'];
  el.innerHTML = currentTickers.map(function(t) {
    var sym = t.replace('KRW-','');
    var price = lastPrices[t];
    var priceHtml = price ? ' <span class="ticker-chip-price">' + fmt(price) + '</span>' : '';

    // (C) 시그널 강도 → chip-dot 색상
    var dotStyle = '';
    var chipTitle = '';
    var sig = lastSignals[t];
    if (sig && sig.avg != null) {
      var avg = sig.avg;
      var dotColor = avg > 0.15 ? 'var(--red)' : avg < -0.15 ? 'var(--blue)' : 'var(--yellow)';
      dotStyle = ' style="background:' + dotColor + '"';
      chipTitle = ' title="시그널 평균: ' + (avg >= 0 ? '+' : '') + (avg * 100).toFixed(0) + '%"';
    }

    // (A) 미실현 손익 배지
    var pnlHtml = '';
    var posData = lastCapital.positions && lastCapital.positions[t];
    if (posData && posData.unrealized_pnl_pct != null) {
      var pp = posData.unrealized_pnl_pct * 100;
      var pnlCls = pp > 0 ? 'pos' : pp < 0 ? 'neg' : 'neutral';
      pnlHtml = ' <span class="' + pnlCls + '" style="font-size:0.7rem">' + (pp >= 0 ? '+' : '') + pp.toFixed(1) + '%</span>';
    }

    // (B) ImproverAgent 편출 추천
    var removeHtml = '';
    if (tickerAdvice.remove && tickerAdvice.remove.indexOf(t) !== -1) {
      removeHtml = ' <span style="font-size:0.62rem;color:var(--yellow);margin-left:1px" title="ImproverAgent 편출 추천">▼편출</span>';
    }

    return '<span class="ticker-chip active" data-t="' + escHtml(t) + '" onclick="toggleTicker(this.dataset.t)"' + chipTitle + '>' +
      '<span class="chip-dot"' + dotStyle + '></span>' + escHtml(sym) + priceHtml + pnlHtml + removeHtml +
      ' <span style="color:var(--muted);font-size:0.9rem;margin-left:4px">&times;</span></span>';
  }).join('');
}

function renderAvailableTickers(search) {
  var el = $('ticker-available');
  if (!el) return;
  var term = search.trim().toLowerCase();
  var adviceAdd = tickerAdvice.add || [];
  var filtered = allUpbitMarkets.filter(function(m) {
    if (currentTickers.indexOf(m.code) !== -1) return false;
    // (B) ImproverAgent 편입 추천도 기본 목록에 포함
    if (!term) return RECOMMENDED.indexOf(m.code) !== -1 || adviceAdd.indexOf(m.code) !== -1;
    return m.code.toLowerCase().indexOf(term) !== -1 || m.name.toLowerCase().indexOf(term) !== -1;
  });
  if (!term && filtered.length === 0 && allUpbitMarkets.length === 0) {
    el.innerHTML = '';
    return;
  }
  function makeChip(m) {
    var sym = m.code.replace('KRW-','');
    // (B) 편입 추천 배지
    var addBadge = adviceAdd.indexOf(m.code) !== -1
      ? ' <span style="font-size:0.62rem;color:var(--red);margin-left:2px" title="ImproverAgent 편입 추천">▲편입</span>'
      : '';
    return '<span class="ticker-chip" data-t="' + escHtml(m.code) + '" onclick="toggleTicker(this.dataset.t)">' +
      '<span class="chip-dot"></span>' + escHtml(sym) +
      ' <span style="font-size:0.7rem;color:var(--muted)">' + escHtml(m.name) + '</span>' + addBadge + '</span>';
  }
  if (!term) {
    el.innerHTML = '<span style="font-size:0.72rem;color:var(--muted);width:100%;margin-bottom:4px">추천 종목 (검색어 입력 시 전체 ' + allUpbitMarkets.length + '개 검색)</span>' +
      filtered.map(makeChip).join('');
  } else {
    el.innerHTML = filtered.slice(0, 30).map(makeChip).join('') +
      (filtered.length > 30 ? '<span style="font-size:0.72rem;color:var(--muted)"> 외 ' + (filtered.length-30) + '개...</span>' : '');
  }
}

function toggleTicker(ticker) {
  var idx = currentTickers.indexOf(ticker);
  if (idx === -1) {
    currentTickers.push(ticker);
  } else {
    currentTickers.splice(idx, 1);
  }
  renderSelectedTickers();
  renderAvailableTickers($('ticker-search') ? $('ticker-search').value : '');
}

function selectRecommended() {
  currentTickers = RECOMMENDED.filter(function(t) {
    return allUpbitMarkets.length === 0 || allUpbitMarkets.some(function(m) { return m.code === t; });
  });
  renderSelectedTickers();
  renderAvailableTickers('');
  showToast('추천 종목 7개 선택됨', 'success');
}

function clearAllTickers() {
  currentTickers = [];
  renderSelectedTickers();
  renderAvailableTickers($('ticker-search') ? $('ticker-search').value : '');
}

async function refreshLogs() {
  try {
    var data = await api('/api/logs?lines=200');
    var logEl = $('sys-log');
    var text = data.lines ? data.lines.join('\\n') : JSON.stringify(data);
    logEl.textContent = text;
    logEl.scrollTop = logEl.scrollHeight;
  } catch (e) {
    $('sys-log').textContent = '로그를 불러올 수 없습니다.';
  }
}

async function saveConfig() {
  var payload = {
    llm_model: $('cfg-llm-model').value,
    llm_endpoint: $('cfg-llm-endpoint').value || '',
    per_trade_risk_pct: parseInt($('cfg-risk-per-trade').value) / 100,
    daily_loss_limit_pct: parseInt($('cfg-risk-daily-loss').value) / 100,
    max_concurrent_positions: parseInt($('cfg-max-positions').value),
    decision_threshold: parseInt($('cfg-decision-threshold').value) / 100,
    trading_tickers: currentTickers
  };
  try {
    await api('/api/config', 'PUT', payload);
    updateLLMDisplay(payload.llm_model);
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
  try { initChart(); } catch(e) { console.warn('Chart.js init failed:', e); }
  connectWS();

  setupSliders();

  /* Ticker search */
  var tsEl = $('ticker-search');
  if (tsEl) tsEl.addEventListener('input', function() { renderAvailableTickers(tsEl.value); });

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
