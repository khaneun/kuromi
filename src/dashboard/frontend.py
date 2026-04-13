INDEX_HTML = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kuromi Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--muted:#8b949e;
--green:#3fb950;--red:#f85149;--blue:#58a6ff;--yellow:#d29922;--purple:#bc8cff}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);padding:0}
header{background:var(--card);border-bottom:1px solid var(--border);padding:.75rem 1.5rem;display:flex;align-items:center;gap:1rem;position:sticky;top:0;z-index:10}
header h1{font-size:1.1rem;font-weight:700;letter-spacing:-.02em}
.badge{font-size:.7rem;padding:2px 8px;border-radius:12px;font-weight:600;text-transform:uppercase}
.badge-green{background:var(--green);color:#000}.badge-red{background:var(--red);color:#fff}
.badge-yellow{background:var(--yellow);color:#000}.badge-blue{background:var(--blue);color:#000}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem;padding:1rem 1.5rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:1rem}
.card h2{font-size:.85rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:.75rem}
.kpi{display:grid;grid-template-columns:repeat(2,1fr);gap:.5rem}
.kpi-item{display:flex;flex-direction:column}.kpi-label{font-size:.7rem;color:var(--muted)}.kpi-value{font-size:1.1rem;font-weight:600}
.pos{color:var(--green)}.neg{color:var(--red)}
table{width:100%;border-collapse:collapse;font-size:.78rem}
th{text-align:left;color:var(--muted);font-weight:500;padding:4px 6px;border-bottom:1px solid var(--border)}
td{padding:4px 6px;border-bottom:1px solid var(--border)}
.agent-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.dot-ok{background:var(--green)}.dot-err{background:var(--red)}.dot-stop{background:var(--yellow)}
.chart-wrap{height:200px;position:relative}
.ctrl-section{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.75rem}
.btn{padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:var(--card);color:var(--text);
cursor:pointer;font-size:.78rem;font-weight:500;transition:background .15s}
.btn:hover{background:#21262d}.btn-danger{border-color:var(--red);color:var(--red)}
.btn-danger:hover{background:var(--red);color:#fff}
.btn-green{border-color:var(--green);color:var(--green)}
.btn-green:hover{background:var(--green);color:#000}
textarea{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--border);
border-radius:6px;padding:.5rem;font-family:monospace;font-size:.78rem;resize:vertical;min-height:80px}
.event-log{max-height:200px;overflow-y:auto;font-family:monospace;font-size:.72rem;
background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:.5rem}
.full-width{grid-column:1/-1}
.status-bar{margin-left:auto;display:flex;gap:.75rem;align-items:center;font-size:.78rem}
</style></head>
<body>
<header>
  <h1>Kuromi</h1>
  <span id="mode-badge" class="badge badge-yellow">DRY RUN</span>
  <span id="halt-badge" class="badge badge-green" style="display:none">HALTED</span>
  <div class="status-bar">
    <span id="ws-status" style="color:var(--muted)">connecting…</span>
    <span id="clock" style="color:var(--muted)"></span>
  </div>
</header>
<div class="grid">

  <!-- KPI -->
  <div class="card">
    <h2>Portfolio</h2>
    <div class="kpi" id="kpi"></div>
  </div>

  <!-- Positions -->
  <div class="card">
    <h2>Positions</h2>
    <table><thead><tr><th>Ticker</th><th>Entry</th><th>Current</th><th>PnL</th><th>Value</th></tr></thead>
    <tbody id="positions-body"></tbody></table>
  </div>

  <!-- Equity Chart -->
  <div class="card full-width">
    <h2>Equity Curve</h2>
    <div class="chart-wrap"><canvas id="equity-chart"></canvas></div>
  </div>

  <!-- Agents -->
  <div class="card">
    <h2>Agents</h2>
    <div id="agents-list"></div>
  </div>

  <!-- Control Panel -->
  <div class="card">
    <h2>Control</h2>
    <div class="ctrl-section">
      <button class="btn btn-green" onclick="api('/api/control/resume','POST')">Resume</button>
      <button class="btn btn-danger" onclick="api('/api/control/halt','POST')">Halt</button>
      <button class="btn btn-danger" onclick="if(confirm('전체 포지션 긴급 청산?'))api('/api/control/liquidate','POST')">Emergency Liquidate</button>
      <button class="btn" id="dry-btn" onclick="api('/api/control/dry-run','POST')">Toggle Dry Run</button>
    </div>
    <h2>Strategy Params</h2>
    <textarea id="params-input" placeholder='{"decision_threshold":0.5}'></textarea>
    <button class="btn" style="margin-top:.4rem" onclick="sendParams()">Apply Params</button>
    <h2 style="margin-top:.75rem">Improver Prompt</h2>
    <textarea id="prompt-input" placeholder="System prompt for Improver LLM agent"></textarea>
    <button class="btn" style="margin-top:.4rem" onclick="sendPrompt()">Update Prompt</button>
  </div>

  <!-- Recent Orders -->
  <div class="card">
    <h2>Recent Orders</h2>
    <table><thead><tr><th>Time</th><th>Side</th><th>Ticker</th><th>Price</th><th>State</th></tr></thead>
    <tbody id="orders-body"></tbody></table>
  </div>

  <!-- Recent Trades -->
  <div class="card">
    <h2>Recent Trades</h2>
    <table><thead><tr><th>Time</th><th>Side</th><th>Ticker</th><th>Price</th><th>Vol</th></tr></thead>
    <tbody id="trades-body"></tbody></table>
  </div>

  <!-- Event Log -->
  <div class="card full-width">
    <h2>Event Log</h2>
    <div class="event-log" id="event-log"></div>
  </div>

</div>
<script>
const $ = s => document.getElementById(s);
const fmt = (n,d=0) => n==null?'-':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct = n => n==null?'-':(n>=0?'+':'')+( (n*100).toFixed(2))+'%';
const cls = n => n>=0?'pos':'neg';

/* ---------- Equity Chart ---------- */
const ctx = $('equity-chart').getContext('2d');
const eqChart = new Chart(ctx, {
  type:'line',
  data:{labels:[],datasets:[
    {label:'Equity',data:[],borderColor:'#58a6ff',borderWidth:1.5,fill:false,pointRadius:0,tension:.3},
    {label:'Unrealized',data:[],borderColor:'#d29922',borderWidth:1,fill:false,pointRadius:0,tension:.3,borderDash:[4,2]}
  ]},
  options:{responsive:true,maintainAspectRatio:false,animation:false,
    scales:{x:{display:false},y:{ticks:{callback:v=>fmt(v)},grid:{color:'#21262d'}}},
    plugins:{legend:{labels:{color:'#8b949e',boxWidth:12,font:{size:11}}}}}
});

/* ---------- API helpers ---------- */
async function api(url,method='GET',body){
  const opts = {method,headers:{'Content-Type':'application/json'}};
  if(body) opts.body = JSON.stringify(body);
  const r = await fetch(url,opts); return r.json();
}
function sendParams(){
  try{ const p=JSON.parse($('params-input').value); api('/api/control/params','POST',{params:p}).then(r=>alert(JSON.stringify(r))); }
  catch(e){ alert('Invalid JSON'); }
}
function sendPrompt(){
  const p=$('prompt-input').value.trim();
  if(!p){alert('Empty');return;}
  api('/api/control/improver-prompt','POST',{system_prompt:p}).then(r=>alert(JSON.stringify(r)));
}

/* ---------- Polling ---------- */
async function refresh(){
  try{
    const [st,agents,eq,orders,trades] = await Promise.all([
      api('/api/state'),api('/api/agents'),api('/api/equity?last=500'),
      api('/api/orders?limit=10'),api('/api/trades?limit=10')
    ]);
    renderKPI(st);
    renderPositions(st.capital?.positions||{});
    renderAgents(agents);
    renderEquity(eq);
    renderOrders(orders);
    renderTrades(trades);
    $('mode-badge').textContent = st.dry_run?'DRY RUN':'LIVE';
    $('mode-badge').className = 'badge '+(st.dry_run?'badge-yellow':'badge-blue');
    $('halt-badge').style.display = st.halted?'inline':'none';
  }catch(e){console.error(e);}
}

function renderKPI(st){
  const c = st.capital||{};
  const items = [
    ['Equity',fmt(c.total_equity)],['Available KRW',fmt(c.available_krw)],
    ['Unrealized PnL','<span class="'+cls(c.unrealized_pnl)+'">'+fmt(c.unrealized_pnl)+'</span>'],
    ['Realized PnL','<span class="'+cls(c.realized_pnl)+'">'+fmt(c.realized_pnl)+'</span>'],
    ['Total Return','<span class="'+cls(c.total_return_pct)+'">'+pct(c.total_return_pct)+'</span>'],
    ['Trades',c.trade_count||0],
    ['Positions',Object.keys(c.positions||{}).length],
    ['Daily PnL','<span class="'+cls(st.daily_pnl)+'">'+pct(st.daily_pnl)+'</span>'],
  ];
  $('kpi').innerHTML = items.map(([l,v])=>'<div class="kpi-item"><span class="kpi-label">'+l+'</span><span class="kpi-value">'+v+'</span></div>').join('');
}

function renderPositions(positions){
  const rows = Object.entries(positions).map(([t,p])=>{
    const pnl = p.unrealized_pnl||0;
    return '<tr><td>'+t+'</td><td>'+fmt(p.entry_price)+'</td><td>'+fmt(p.current_price)+'</td>'
      +'<td class="'+cls(pnl)+'">'+fmt(pnl)+' ('+pct(p.unrealized_pnl_pct)+')</td>'
      +'<td>'+fmt(p.market_value)+'</td></tr>';
  });
  $('positions-body').innerHTML = rows.join('')||'<tr><td colspan="5" style="color:var(--muted)">No positions</td></tr>';
}

function renderAgents(agents){
  $('agents-list').innerHTML = agents.map(a=>{
    const dot = a.task_exception?'dot-err':a.stopping?'dot-stop':'dot-ok';
    const extra = a.task_exception?' <span style="color:var(--red);font-size:.7rem">'+a.task_exception+'</span>':'';
    return '<div style="padding:3px 0"><span class="agent-dot '+dot+'"></span><strong>'+a.name+'</strong>'+extra+'</div>';
  }).join('');
}

function renderEquity(eq){
  if(!eq.length)return;
  eqChart.data.labels = eq.map(p=>new Date(p.ts*1000).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'}));
  eqChart.data.datasets[0].data = eq.map(p=>p.equity);
  eqChart.data.datasets[1].data = eq.map(p=>p.unrealized_pnl);
  eqChart.update('none');
}

function renderOrders(orders){
  $('orders-body').innerHTML = orders.map(o=>'<tr><td>'+(o.created_at||'').slice(5,16)+'</td>'
    +'<td class="'+(o.side==='buy'?'pos':'neg')+'">'+o.side+'</td><td>'+o.ticker+'</td>'
    +'<td>'+fmt(o.price)+'</td><td>'+o.state+'</td></tr>').join('')
    ||'<tr><td colspan="5" style="color:var(--muted)">No orders</td></tr>';
}

function renderTrades(trades){
  $('trades-body').innerHTML = trades.map(t=>'<tr><td>'+(t.ts||'').slice(5,16)+'</td>'
    +'<td class="'+(t.side==='buy'?'pos':'neg')+'">'+t.side+'</td><td>'+t.ticker+'</td>'
    +'<td>'+fmt(t.price)+'</td><td>'+t.volume?.toFixed(6)+'</td></tr>').join('')
    ||'<tr><td colspan="5" style="color:var(--muted)">No trades</td></tr>';
}

/* ---------- WebSocket ---------- */
let ws;
function connectWS(){
  ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');
  ws.onopen = ()=>{ $('ws-status').textContent='connected'; $('ws-status').style.color='var(--green)'; };
  ws.onclose = ()=>{ $('ws-status').textContent='disconnected'; $('ws-status').style.color='var(--red)'; setTimeout(connectWS,3000); };
  ws.onmessage = (e)=>{
    try{
      const d = JSON.parse(e.data);
      if(d.topic==='heartbeat')return;
      const log = $('event-log');
      const time = new Date().toLocaleTimeString('ko-KR');
      log.innerHTML = '<div><span style="color:var(--muted)">'+time+'</span> <span style="color:var(--blue)">['+d.topic+']</span> '
        +JSON.stringify(d.payload||'').slice(0,200)+'</div>'+log.innerHTML;
      if(log.children.length>200)log.removeChild(log.lastChild);
    }catch(e){}
  };
}
connectWS();
setInterval(refresh,3000); refresh();
setInterval(()=>{ $('clock').textContent=new Date().toLocaleTimeString('ko-KR'); },1000);
</script>
</body></html>"""
