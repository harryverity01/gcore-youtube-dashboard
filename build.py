#!/usr/bin/env python3
"""Render docs/index.html from docs/data.json + strategy.json.

The page is fully static and self-contained: the granular data is injected
inline, Chart.js is pulled from a CDN, thumbnails load from i.ytimg.com.

All panels are driven by an active date range chosen in the browser. Because
the page can't call the API live, fetch_gcore_stats.py bakes day-level rows and
this page aggregates whatever range the user picks entirely client-side.
"""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "docs", "data.json")))
STRATEGY = json.load(open(os.path.join(HERE, "strategy.json")))
BUILT = datetime.datetime.utcnow().strftime("%-d %b %Y, %H:%M UTC")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Gcore · YouTube Performance Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0a0a0a; --panel:#141414; --panel2:#1b1b1b; --line:#2a2a2a;
    --txt:#f2f2f2; --mut:#9a9a9a; --accent:#FFA500; --accent2:#FF7A00;
    --good:#39d98a; --bad:#ff5d5d; --blue:#4d9fff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 22px 80px}
  .head{display:flex;align-items:center;gap:16px;flex-wrap:wrap;
    border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:8px}
  .head img{width:60px;height:60px;border-radius:50%;border:2px solid var(--accent)}
  .head h1{margin:0;font-size:22px;letter-spacing:.2px}
  .head .sub{color:var(--mut);font-size:13px;margin-top:3px}
  .head .right{margin-left:auto;text-align:right;font-size:12px;color:var(--mut)}
  .pill{display:inline-block;background:var(--accent);color:#000;font-weight:700;
    font-size:11px;padding:4px 10px;border-radius:999px;letter-spacing:.3px}
  h2.sec{font-size:13px;letter-spacing:1.4px;text-transform:uppercase;color:var(--mut);
    margin:38px 0 14px;font-weight:700}
  h2.sec .hint{text-transform:none;letter-spacing:0;font-weight:500;color:#6f6f6f;font-size:12px;margin-left:8px}
  /* date range controls */
  .controls{position:sticky;top:0;z-index:20;background:rgba(10,10,10,.92);
    backdrop-filter:blur(6px);border-bottom:1px solid var(--line);
    padding:14px 0 14px;margin-bottom:6px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .presets{display:flex;gap:6px;flex-wrap:wrap}
  .presets button{background:var(--panel2);color:var(--txt);border:1px solid var(--line);
    border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;transition:.12s}
  .presets button:hover{border-color:var(--accent)}
  .presets button.on{background:var(--accent);color:#000;border-color:var(--accent)}
  .daterange{display:flex;gap:8px;align-items:center;margin-left:auto;flex-wrap:wrap}
  .daterange label{color:var(--mut);font-size:12px}
  .daterange input[type=date]{background:var(--panel2);color:var(--txt);border:1px solid var(--line);
    border-radius:8px;padding:6px 9px;font-size:12.5px;color-scheme:dark}
  .daterange .apply{background:var(--accent2);color:#000;border:0;border-radius:8px;
    padding:7px 13px;font-weight:700;font-size:12.5px;cursor:pointer}
  .rangelabel{font-size:12px;color:var(--mut);margin:0 0 18px}
  .rangelabel b{color:var(--txt)}
  /* stat cards */
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
  .card .k{color:var(--mut);font-size:12px;letter-spacing:.4px;text-transform:uppercase}
  .card .v{font-size:28px;font-weight:800;margin-top:6px;line-height:1}
  .card .d{font-size:12px;margin-top:8px;font-weight:600}
  .up{color:var(--good)} .down{color:var(--bad)} .flat{color:var(--mut)}
  /* progress */
  .prog{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:12px}
  .prog .top{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
  .prog .lab{font-weight:700;font-size:15px}
  .prog .num{color:var(--mut);font-size:13px}
  .bar{height:10px;background:var(--panel2);border-radius:999px;margin-top:12px;overflow:hidden}
  .bar > i{display:block;height:100%;background:linear-gradient(90deg,var(--accent2),var(--accent));border-radius:999px}
  .prog .note{color:var(--mut);font-size:12px;margin-top:8px}
  /* charts */
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
  .chart{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
  .chart h3{margin:0 0 4px;font-size:14px;font-weight:700}
  .chart .cap{color:var(--mut);font-size:11.5px;margin:0 0 10px}
  .chart .cv{position:relative;height:230px}
  .full{grid-column:1 / -1}
  /* tables */
  .tablewrap{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
  .tablescroll{max-height:520px;overflow:auto}
  table{border-collapse:collapse;width:100%;font-size:13px}
  thead th{position:sticky;top:0;background:var(--panel2);text-align:right;padding:10px 12px;
    font-size:11.5px;letter-spacing:.4px;text-transform:uppercase;color:var(--mut);white-space:nowrap;
    border-bottom:1px solid var(--line);cursor:pointer;user-select:none}
  thead th.l{text-align:left}
  thead th.sortable:hover{color:var(--txt)}
  thead th .arr{color:var(--accent);margin-left:3px}
  tbody td{padding:9px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
  tbody td.l{text-align:left}
  tbody tr:hover{background:#181818}
  tbody tr:last-child td{border-bottom:0}
  .vtitle{display:flex;gap:10px;align-items:center;max-width:380px}
  .vtitle img{width:64px;height:36px;object-fit:cover;border-radius:4px;background:#000;flex:none}
  .vtitle .tt{font-weight:600;line-height:1.3;overflow:hidden;display:-webkit-box;
    -webkit-line-clamp:2;-webkit-box-orient:vertical;white-space:normal}
  .vtitle .pub{color:var(--mut);font-size:11px;font-weight:400}
  .tag{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:5px;margin-left:6px;vertical-align:middle}
  .tag.live{background:rgba(57,217,138,.16);color:var(--good)}
  .tag.imp{background:rgba(77,159,255,.16);color:var(--blue)}
  .na{color:#5f5f5f}
  .totrow td{font-weight:800;background:var(--panel2);border-top:2px solid var(--line)}
  .tabletools{display:flex;align-items:center;gap:14px;padding:12px 14px;flex-wrap:wrap;border-bottom:1px solid var(--line)}
  .switch{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--mut);cursor:pointer}
  .switch input{accent-color:var(--accent)}
  .mode{color:var(--mut);font-size:12px;margin-left:auto}
  /* import panel */
  .imp{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px;display:grid;
    grid-template-columns:1.3fr 1fr;gap:18px}
  .imp h3{margin:0 0 8px;font-size:14px}
  .imp p{color:var(--mut);font-size:12.5px;line-height:1.55;margin:6px 0}
  .imp code{background:var(--panel2);padding:1px 5px;border-radius:4px;font-size:11.5px;color:#d8d8d8}
  .impbtns{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}
  .filebtn{background:var(--accent);color:#000;font-weight:700;font-size:12.5px;padding:9px 14px;
    border-radius:8px;cursor:pointer;border:0}
  .ghost{background:transparent;color:var(--mut);border:1px solid var(--line);border-radius:8px;
    padding:9px 14px;font-size:12.5px;cursor:pointer}
  .jobcard{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-size:12.5px;line-height:1.6}
  .jobcard .st{font-weight:700}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
  .dot.g{background:var(--good)} .dot.y{background:var(--accent)} .dot.r{background:var(--bad)}
  /* video wall */
  .two{display:grid;grid-template-columns:1.1fr .9fr;gap:14px}
  .box{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
  .box h3{margin:0 0 12px;font-size:14px;font-weight:700}
  .formula{background:var(--panel2);border-left:3px solid var(--accent);padding:12px 14px;
    border-radius:8px;font-size:14px;font-weight:600;margin-bottom:16px}
  ul.ins{margin:0;padding:0;list-style:none}
  ul.ins li{font-size:13px;color:#d8d8d8;padding:9px 0;border-bottom:1px solid var(--line);line-height:1.5}
  ul.ins li:last-child{border-bottom:0}
  ul.next li{font-size:13px;padding:8px 0 8px 20px;position:relative;color:#d8d8d8}
  ul.next li:before{content:"→";position:absolute;left:0;color:var(--accent);font-weight:700}
  .foot{color:var(--mut);font-size:12px;margin-top:40px;border-top:1px solid var(--line);
    padding-top:18px;line-height:1.6}
  @media(max-width:880px){.cards{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}
    .two{grid-template-columns:1fr}.imp{grid-template-columns:1fr}.daterange{margin-left:0}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <img id="avatar" alt="Gcore">
    <div>
      <h1>Gcore · YouTube Performance</h1>
      <div class="sub" id="handle"></div>
    </div>
    <div class="right">
      <span class="pill" id="phase"></span><br>
      <span id="built"></span>
    </div>
  </div>

  <!-- DATE RANGE CONTROLS — drive every panel below -->
  <div class="controls">
    <div class="presets" id="presets"></div>
    <div class="daterange">
      <label>From <input type="date" id="d0"></label>
      <label>To <input type="date" id="d1"></label>
      <button class="apply" id="apply">Apply</button>
    </div>
  </div>
  <div class="rangelabel" id="rangelabel"></div>

  <h2 class="sec">Channel Snapshot <span class="hint">lifetime totals · not range-dependent</span></h2>
  <div class="cards" id="snapcards"></div>

  <h2 class="sec" id="targetsHdr">Progress to Targets</h2>
  <div id="targets"></div>

  <h2 class="sec">Performance <span class="hint" id="ovhint"></span></h2>
  <div class="cards" id="ovcards"></div>

  <h2 class="sec">Daily Breakdown</h2>
  <div class="chart full" style="margin-bottom:14px"><h3>Views · watch time · avg view duration</h3>
    <p class="cap" id="dailycap"></p><div class="cv" style="height:280px"><canvas id="cDaily"></canvas></div></div>
  <div class="tablewrap"><div class="tablescroll"><table id="dailyTable"></table></div></div>

  <h2 class="sec">Top Videos <span class="hint" id="tvhint"></span></h2>
  <div class="tablewrap">
    <div class="tabletools">
      <label class="switch"><input type="checkbox" id="edOnly"> Editorial only</label>
      <span class="mode" id="tvmode"></span>
    </div>
    <div class="tablescroll"><table id="tvTable"></table></div>
  </div>

  <h2 class="sec">Impressions &amp; CTR <span class="hint">auto-updated daily via the YouTube Reporting API — no action needed</span></h2>
  <div class="imp">
    <div>
      <h3>Updates automatically every day</h3>
      <p>Thumbnail <b>impressions</b> and <b>CTR</b> come from the YouTube <b>Reporting API</b>
        (<code>channel_reach_basic_a1</code>) and refresh on the <b>same daily schedule as every other metric</b> —
        you don't have to do anything. Each new day shows up as <span class="tag live">live</span> on its own.</p>
      <p>The one API limit: this report is job-based, so it begins ~24–48h after the job is first created and
        carries ~30 days of backfill. Dates before that show <span class="na">n/a</span> until they fill in going forward.</p>
      <details>
        <summary>Optional · one-time — load older CTR history (you never <i>need</i> to)</summary>
        <p>Only if you want CTR/impressions for dates from <i>before</i> the job existed: YouTube Studio →
          Analytics → Advanced mode → Content tab → <b>Export → Comma-separated values (.csv)</b>, then drop the
          <code>Table data.csv</code> below (columns <code>Video</code>, <code>Impressions</code>,
          <code>Impressions click-through rate (%)</code>). Live daily data always wins — an import only fills gaps,
          it never overrides the automatic numbers.</p>
        <div class="impbtns">
          <label class="filebtn">Import Studio CSV<input type="file" id="csv" accept=".csv,text/csv" hidden></label>
          <button class="ghost" id="csvClear">Clear import</button>
          <span id="impStatus" style="font-size:12px;color:var(--mut)"></span>
        </div>
      </details>
    </div>
    <div>
      <h3>Reach reporting job</h3>
      <div class="jobcard" id="jobcard"></div>
    </div>
  </div>

  <h2 class="sec">Audience &amp; Reach</h2>
  <div class="grid">
    <div class="chart"><h3>Traffic sources</h3><p class="cap" id="capTraffic"></p><div class="cv"><canvas id="cTraffic"></canvas></div></div>
    <div class="chart"><h3>Content type · views share</h3><p class="cap" id="capContent"></p><div class="cv"><canvas id="cContent"></canvas></div></div>
    <div class="chart"><h3>Top geographies (views)</h3><p class="cap" id="capGeo"></p><div class="cv"><canvas id="cGeo"></canvas></div></div>
    <div class="chart"><h3>Audience by age</h3><p class="cap" id="capAge"></p><div class="cv"><canvas id="cAge"></canvas></div></div>
  </div>

  <h2 class="sec">Strategy</h2>
  <div class="two">
    <div class="box">
      <h3>What's working</h3>
      <div class="formula" id="formula"></div>
      <ul class="ins" id="insights"></ul>
    </div>
    <div class="box">
      <h3 id="nextHdr">Next up</h3>
      <ul class="next" id="next"></ul>
      <p style="color:var(--mut);font-size:12px;margin-top:18px;line-height:1.5" id="mission"></p>
    </div>
  </div>

  <div class="foot" id="foot"></div>
</div>

<script>
const DATA = __DATA__;
const STRATEGY = __STRATEGY__;
const BUILT = "__BUILT__";

/* ============================ formatting ============================ */
const fmt = n => (n==null||isNaN(n)?"—":Math.round(n).toLocaleString("en-US"));
const fmt1 = n => (n==null||isNaN(n)?"—":Number(n).toLocaleString("en-US",{maximumFractionDigits:1}));
const fmtDur = s => { s=Math.round(s||0); const m=Math.floor(s/60); return m+"m "+String(s%60).padStart(2,"0")+"s"; };
const fmtHrs = m => fmt1((m||0)/60)+" h";
const iso2dur = d => { if(!d) return ""; const m=d.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/)||[];
  const h=+(m[1]||0),mi=+(m[2]||0),se=+(m[3]||0);
  return (h?h+":"+String(mi).padStart(2,"0"):mi)+":"+String(se).padStart(2,"0"); };
const esc = s => String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ============================ date helpers ============================ */
const D   = s => new Date(s+"T00:00:00Z");
const isod= d => d.toISOString().slice(0,10);
const addDays = (s,n)=>{const d=D(s);d.setUTCDate(d.getUTCDate()+n);return isod(d);};
const between = (a,b)=>Math.round((D(b)-D(a))/864e5)+1;          // inclusive day count
const TODAY = DATA.today;
const DAILY = DATA.daily||[];
const MINDATE = DAILY.length ? DAILY[0][0] : (DATA.gran_days||[TODAY])[0];
const MAXDATE = DAILY.length ? DAILY[DAILY.length-1][0] : TODAY;
const GRAN = DATA.gran_days||[];
const GRAN_START = GRAN.length ? GRAN[0] : TODAY;

/* ============================ index the baked data ============================ */
// channel daily -> date keyed object
const C = {};   // col name -> index
(DATA.daily_cols||[]).forEach((c,i)=>C[c]=i);
const dailyByDate = {};
DAILY.forEach(r=>{ dailyByDate[r[0]] = {
  views:r[C.views], minutes:r[C.minutes], avgDur:r[C.avgDur],
  subsGained:r[C.subsGained], subsLost:r[C.subsLost],
  likes:r[C.likes], comments:r[C.comments], shares:r[C.shares] }; });

// reach: vid -> [{date, imp, clk}]
const reachByVid = {};
(DATA.reach_daily||[]).forEach(([idx,vid,imp,clk])=>{
  (reachByVid[vid]=reachByVid[vid]||[]).push({date:GRAN[idx], imp, clk});
});
const REACH_DATES = (DATA.reach_job&&DATA.reach_job.dates)||null;

/* ============================ manual Studio import (localStorage) ============================ */
const LS_KEY="gcore_studio_v1";
let STUDIO = {};   // vid -> {imp, ctr}
let STUDIO_META = null;
(function(){ try{ const j=JSON.parse(localStorage.getItem(LS_KEY)||"null");
  if(j){ STUDIO=j.map||{}; STUDIO_META=j.meta||null; } }catch(e){} })();

/* ============================ range state ============================ */
const PRESETS = [
  ["7","Last 7d"],["28","Last 28d"],["90","Last 90d"],
  ["thismonth","This month"],["lastmonth","Last month"],["all","All time"]
];
function presetRange(p){
  if(p==="all")  return {start:MINDATE, end:MAXDATE};
  if(p==="thismonth"){ const d=D(TODAY); return {start:TODAY.slice(0,8)+"01", end:TODAY}; }
  if(p==="lastmonth"){ const d=D(TODAY); d.setUTCDate(1); const end=addDays(isod(d),-1);
    const start=end.slice(0,8)+"01"; return {start,end}; }
  return {start:addDays(TODAY, -(+p-1)), end:TODAY};
}
function clampRange(r){
  let s=r.start<MINDATE?MINDATE:r.start, e=r.end>MAXDATE?MAXDATE:r.end;
  if(s>e) s=e; return {start:s, end:e};
}
let RANGE = (function(){
  try{ const j=JSON.parse(localStorage.getItem("gcore_range_v1")||"null"); if(j&&j.start&&j.end) return j; }catch(e){}
  return {preset:"90", ...presetRange("90")};
})();
RANGE = {...RANGE, ...clampRange(RANGE)};

/* ============================ aggregation ============================ */
function inRange(date,r){ return date>=r.start && date<=r.end; }

function aggOverview(r){
  let o={views:0,minutes:0,subsGained:0,subsLost:0,likes:0,comments:0,shares:0,days:0};
  for(const d in dailyByDate){ if(!inRange(d,r)) continue; const x=dailyByDate[d];
    o.views+=x.views; o.minutes+=x.minutes; o.subsGained+=x.subsGained; o.subsLost+=x.subsLost;
    o.likes+=x.likes; o.comments+=x.comments; o.shares+=x.shares; o.days++; }
  o.avgDur = o.views ? (o.minutes*60)/o.views : 0;     // exact: total watch seconds / views
  o.netSubs = o.subsGained - o.subsLost;
  return o;
}
function prevRange(r){ const len=between(r.start,r.end); const end=addDays(r.start,-1); return {start:addDays(end,-(len-1)), end}; }

function dailyRows(r){
  const rows=[];
  DAILY.forEach(row=>{ if(inRange(row[0],r)) rows.push({date:row[0], views:row[C.views], minutes:row[C.minutes], avgDur:row[C.avgDur]}); });
  return rows;
}

// reach impressions+clicks for a video over a range -> {imp, ctr} or null
function reachFor(vid,r){
  const arr=reachByVid[vid]; if(!arr) return null;
  let imp=0, clk=0, n=0;
  arr.forEach(x=>{ if(inRange(x.date,r)){ imp+=x.imp; clk+=x.clk; n++; } });
  if(!n||!imp) return null;
  return {imp, ctr: imp? clk/imp*100 : 0};
}
// resolve impressions/CTR for a video+range with precedence: live > imported > n/a
function ctrCell(vid,r){
  const live=reachFor(vid,r);
  if(live) return {imp:live.imp, ctr:live.ctr, src:"live"};
  const st=STUDIO[vid];
  if(st && (st.imp!=null||st.ctr!=null)) return {imp:st.imp, ctr:st.ctr, src:"imp"};
  return {imp:null, ctr:null, src:"na"};
}

// is the active range fully inside the per-video baked window?
function rangeInGran(r){ return r.start>=GRAN_START; }

// build top-video rows for the range
function topVideos(r){
  const ed = document.getElementById("edOnly").checked;
  const since = STRATEGY.editorial_since || "0000-00-00";
  const meta = DATA.videos||{};
  let rows=[], mode;
  if(rangeInGran(r)){
    mode="range";
    const vd=DATA.video_daily||{};
    for(const vid in vd){
      const s=vd[vid]; let views=0,minutes=0,wsec=0,apw=0;
      for(let k=0;k<s.i.length;k++){ const date=GRAN[s.i[k]]; if(!inRange(date,r)) continue;
        views+=s.v[k]; minutes+=s.w[k]; apw+=s.ap[k]*s.v[k]; }
      if(views<=0) continue;
      rows.push({vid, views, minutes, avgDur:(minutes*60)/views, avgPct: views?apw/views:0});
    }
  } else {
    mode="alltime";
    (DATA.top_all_time||[]).forEach(v=>rows.push({vid:v.id, views:v.views, minutes:v.minutes, avgDur:v.avgDur, avgPct:v.avgPct}));
  }
  rows.forEach(row=>{ const m=meta[row.vid]||{}; row.title=m.title||row.vid; row.published=m.published||"";
    row.dur=m.dur||""; const cc=ctrCell(row.vid,r); row.imp=cc.imp; row.ctr=cc.ctr; row.csrc=cc.src; });
  if(ed) rows=rows.filter(row=>(row.published||"")>=since);
  return {rows, mode};
}

/* window picker for geo/demographics (cannot be sliced per arbitrary day) */
function windowName(r,preset){
  if(preset==="all") return "all";
  const L=between(r.start,r.end);
  for(const n of ["7","28","90","365"]) if(+n>=L) return n;
  return "all";
}
function windowLabel(name){ return name==="all" ? "all-time" : "last "+name+"d"; }

/* distributions from per-day flat rows [idx,key,views,minutes] within range */
function distAgg(rows,r){
  const g={};
  (rows||[]).forEach(([idx,key,v,m])=>{ const date=GRAN[idx]; if(!inRange(date,r)) return;
    g[key]=g[key]||{views:0,minutes:0}; g[key].views+=v; g[key].minutes+=m; });
  return Object.entries(g).map(([k,x])=>[k,x.views,x.minutes]).sort((a,b)=>b[1]-a[1]);
}
function distCoverage(r){
  // per-day traffic/content only cover the granular window
  if(r.start>=GRAN_START) return "selected range";
  return "last "+DATA.granular_days+"d (max baked) — range extends earlier";
}

/* ============================ charts registry ============================ */
Chart.defaults.color="#9a9a9a"; Chart.defaults.borderColor="#2a2a2a";
const ACC="#FFA500", ACC2="#FF7A00", BLUE="#4d9fff", GOOD="#39d98a";
const PALETTE=["#FFA500","#FF7A00","#ff5d5d","#39d98a","#4d9fff","#b366ff","#ffd24d","#5ad1c9","#8a8a8a","#e06bff"];
const charts={};
function mkChart(id,cfg){ if(charts[id]) charts[id].destroy(); charts[id]=new Chart(document.getElementById(id),cfg); }

/* downsample daily series to <=140 points for the chart (weekly buckets) */
function bucket(rows){
  if(rows.length<=140) return rows;
  const step=Math.ceil(rows.length/140), out=[];
  for(let i=0;i<rows.length;i+=step){ const slice=rows.slice(i,i+step);
    let v=0,m=0,ws=0; slice.forEach(x=>{v+=x.views;m+=x.minutes;ws+=x.avgDur*x.views;});
    out.push({date:slice[0].date, views:v, minutes:m, avgDur:v?ws/v:0}); }
  return out;
}

const TRAFFIC_LABELS={SUBSCRIBER:"Subscriber feed",YT_SEARCH:"YouTube search",EXT_URL:"External URLs",
  RELATED_VIDEO:"Suggested videos",NO_LINK_OTHER:"Direct / other",NO_LINK_EMBEDDED:"Embedded player",
  YT_CHANNEL:"Channel page",PLAYLIST:"Playlists",NOTIFICATION:"Notifications",YT_OTHER_PAGE:"Other YouTube",
  ADVERTISING:"Advertising",CAMPAIGN_CARD:"Cards / end screens",HASHTAGS:"Hashtags",SHORTS:"Shorts feed"};
const CT={creatorContentTypeUnspecified:"Other",videoOnDemand:"Long-form (VOD)",shorts:"Shorts",liveStream:"Live",story:"Story"};
const COUNTRY={US:"United States",DE:"Germany",GB:"United Kingdom",AU:"Australia",CA:"Canada",
  SE:"Sweden",FR:"France",NL:"Netherlands",IN:"India",ES:"Spain",IT:"Italy",CH:"Switzerland",
  PL:"Poland",BR:"Brazil",JP:"Japan",SG:"Singapore",AE:"UAE",IE:"Ireland",NO:"Norway",FI:"Finland",
  KR:"South Korea",RU:"Russia",UA:"Ukraine",TR:"Turkey",MX:"Mexico"};

/* ============================ rendering ============================ */
let SORT={key:"views", dir:-1};

function deltaHTML(cur,prev,invert){
  if(!prev) return "";
  const p=(cur-prev)/prev*100, good=invert?p<0:p>0;
  const cls=Math.abs(p)<0.5?"flat":(good?"up":"down"), arr=p>0?"▲":(p<0?"▼":"•");
  return `<div class="d ${cls}">${arr} ${Math.abs(p).toFixed(1)}% vs prev ${between(RANGE.start,RANGE.end)}d</div>`;
}

function renderSnapshot(){
  const s=DATA.snapshot||{};
  document.getElementById("avatar").src=s.avatar||"https://yt3.ggpht.com/ytc/default";
  document.getElementById("handle").textContent="@gcoreofficial · channel created "+(s.created||"").slice(0,4);
  document.getElementById("phase").textContent=STRATEGY.phase||"";
  document.getElementById("built").textContent="Updated "+BUILT;
  const cards=[{k:"Subscribers",v:fmt(s.subs)},{k:"Total Views",v:fmt(s.total_views)},
    {k:"Videos",v:fmt(s.videos)},{k:"Channel age",v:(s.created?Math.floor((Date.now()-Date.parse(s.created))/3.15e10):"—")+" yrs"}];
  document.getElementById("snapcards").innerHTML=cards.map(c=>`<div class="card"><div class="k">${c.k}</div><div class="v">${c.v}</div></div>`).join("");
}

function renderOverview(){
  const o=aggOverview(RANGE), p=aggOverview(prevRange(RANGE));
  document.getElementById("ovhint").textContent=between(RANGE.start,RANGE.end)+" days · vs previous equal period";
  const cards=[
    {k:"Views",v:fmt(o.views),d:deltaHTML(o.views,p.views)},
    {k:"Watch time",v:fmtHrs(o.minutes),d:deltaHTML(o.minutes,p.minutes)},
    {k:"Avg view duration",v:fmtDur(o.avgDur),d:deltaHTML(o.avgDur,p.avgDur)},
    {k:"Net subs",v:(o.netSubs>=0?"+":"")+fmt(o.netSubs),d:deltaHTML(o.netSubs,p.netSubs)},
    {k:"Likes",v:fmt(o.likes),d:deltaHTML(o.likes,p.likes)},
    {k:"Comments",v:fmt(o.comments),d:deltaHTML(o.comments,p.comments)},
    {k:"Shares",v:fmt(o.shares),d:deltaHTML(o.shares,p.shares)},
    {k:"Subs gained / lost",v:fmt(o.subsGained)+" / "+fmt(o.subsLost),d:""},
  ];
  document.getElementById("ovcards").innerHTML=cards.map(c=>`<div class="card"><div class="k">${c.k}</div><div class="v">${c.v}</div>${c.d||""}</div>`).join("");
}

function renderDaily(){
  const rows=dailyRows(RANGE);
  document.getElementById("dailycap").textContent=`${rows.length} days · ${RANGE.start} → ${RANGE.end}`+
    (rows.length>140?` · chart bucketed (${Math.ceil(rows.length/140)}d) for readability`:``);
  const br=bucket(rows);
  mkChart("cDaily",{type:"line",data:{labels:br.map(r=>r.date.slice(5)),datasets:[
    {label:"Views",data:br.map(r=>r.views),borderColor:ACC,backgroundColor:"rgba(255,165,0,.12)",fill:true,tension:.3,pointRadius:0,borderWidth:2,yAxisID:"y"},
    {label:"Watch time (min)",data:br.map(r=>r.minutes),borderColor:BLUE,backgroundColor:"transparent",fill:false,tension:.3,pointRadius:0,borderWidth:2,yAxisID:"y1"},
    {label:"Avg view duration (s)",data:br.map(r=>Math.round(r.avgDur)),borderColor:GOOD,backgroundColor:"transparent",fill:false,tension:.3,pointRadius:0,borderWidth:1.5,borderDash:[5,4],yAxisID:"y2",hidden:true}
  ]},options:{maintainAspectRatio:false,interaction:{mode:"index",intersect:false},
    plugins:{legend:{labels:{boxWidth:12,font:{size:11}}}},
    scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12}},
      y:{position:"left",beginAtZero:true,title:{display:true,text:"Views"}},
      y1:{position:"right",beginAtZero:true,grid:{display:false},title:{display:true,text:"Watch min"}},
      y2:{display:false,beginAtZero:true}}}});
  // table (latest first, capped)
  const CAP=800; const desc=rows.slice().reverse();
  const shown=desc.slice(0,CAP);
  let tot={views:0,minutes:0,wsec:0}; rows.forEach(r=>{tot.views+=r.views;tot.minutes+=r.minutes;tot.wsec+=r.avgDur*r.views;});
  let h=`<thead><tr><th class="l">Date</th><th>Views</th><th>Watch time</th><th>Avg view duration</th></tr></thead><tbody>`;
  h+=shown.map(r=>`<tr><td class="l">${r.date}</td><td>${fmt(r.views)}</td><td>${fmtHrs(r.minutes)}</td><td>${fmtDur(r.avgDur)}</td></tr>`).join("");
  if(desc.length>CAP) h+=`<tr><td class="l na" colspan="4">+${fmt(desc.length-CAP)} earlier days — narrow the range to see them</td></tr>`;
  h+=`</tbody><tfoot><tr class="totrow"><td class="l">Total · ${rows.length}d</td><td>${fmt(tot.views)}</td><td>${fmtHrs(tot.minutes)}</td><td>${fmtDur(tot.views?tot.wsec/tot.views:0)}</td></tr></tfoot>`;
  document.getElementById("dailyTable").innerHTML=h;
}

const TVCOLS=[
  {k:"rank",l:"#",cls:"",sortable:false},
  {k:"title",l:"Video",cls:"l",sortable:false},
  {k:"views",l:"Views",fmt:r=>fmt(r.views)},
  {k:"minutes",l:"Watch time",fmt:r=>fmtHrs(r.minutes)},
  {k:"avgDur",l:"Avg duration",fmt:r=>fmtDur(r.avgDur)},
  {k:"avgPct",l:"Avg % viewed",fmt:r=>fmt1(r.avgPct)+"%"},
  {k:"imp",l:"Impressions",fmt:r=>r.imp==null?`<span class="na">n/a</span>`:fmt(r.imp)},
  {k:"ctr",l:"CTR",fmt:r=>r.ctr==null?`<span class="na">n/a</span>`:fmt1(r.ctr)+"%"+(
    r.csrc==="live"?`<span class="tag live" title="Live Reporting API reach data for the selected range">live</span>`:
    r.csrc==="imp"?`<span class="tag imp" title="Imported Studio total — reflects your export's range, not sliced to the selected range">imp</span>`:``)},
];
function renderTopVideos(){
  const {rows,mode}=topVideos(RANGE);
  rows.sort((a,b)=>{ let x=a[SORT.key], y=b[SORT.key];
    if(x==null) x=-Infinity; if(y==null) y=-Infinity;
    if(typeof x==="string") return SORT.dir*x.localeCompare(y);
    return SORT.dir*(x-y); });
  const reachNote = REACH_DATES ? `live reach ${REACH_DATES[0]}→${REACH_DATES[1]}` : `no live reach data yet`;
  document.getElementById("tvmode").textContent = (mode==="range"
    ? `Measured over ${RANGE.start} → ${RANGE.end}`
    : `All-time totals (range extends before the ${DATA.granular_days}d per-video window)`) + ` · ${reachNote}`;
  document.getElementById("tvhint").textContent = mode==="range" ? "re-ranked for the selected range" : "all-time";
  let h=`<thead><tr>`+TVCOLS.map(c=>{
    const arr=(c.sortable!==false&&SORT.key===c.k)?`<span class="arr">${SORT.dir<0?"▼":"▲"}</span>`:"";
    return `<th class="${c.cls||""} ${c.sortable!==false?"sortable":""}" data-k="${c.k}" data-sortable="${c.sortable!==false}">${c.l}${arr}</th>`;
  }).join("")+`</tr></thead><tbody>`;
  h+=rows.map((r,i)=>{
    const thumb=`https://i.ytimg.com/vi/${r.vid}/mqdefault.jpg`;
    const tcell=`<div class="vtitle"><a href="https://youtu.be/${r.vid}" target="_blank" rel="noopener"><img loading="lazy" src="${thumb}" onerror="this.style.visibility='hidden'"></a><div><div class="tt">${esc(r.title)}</div><div class="pub">${r.published||""} · ${iso2dur(r.dur)}</div></div></div>`;
    return `<tr><td>${i+1}</td><td class="l">${tcell}</td>`+
      TVCOLS.slice(2).map(c=>`<td>${c.fmt(r)}</td>`).join("")+`</tr>`;
  }).join("");
  if(!rows.length) h+=`<tr><td class="l na" colspan="${TVCOLS.length}">No videos with views in this range.</td></tr>`;
  h+=`</tbody>`;
  const t=document.getElementById("tvTable"); t.innerHTML=h;
  t.querySelectorAll("th[data-sortable='true']").forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; if(SORT.key===k) SORT.dir*=-1; else {SORT.key=k; SORT.dir=-1;} renderTopVideos();
  });
}

function renderDistributions(){
  const traffic=distAgg(DATA.traffic_daily,RANGE).slice(0,8);
  document.getElementById("capTraffic").textContent="Coverage: "+distCoverage(RANGE);
  mkChart("cTraffic",{type:"doughnut",data:{labels:traffic.map(r=>TRAFFIC_LABELS[r[0]]||r[0]),
    datasets:[{data:traffic.map(r=>r[1]),backgroundColor:PALETTE,borderColor:"#141414",borderWidth:2}]},
    options:{plugins:{legend:{position:"right",labels:{boxWidth:10,font:{size:11}}}},maintainAspectRatio:false,cutout:"58%"}});

  const content=distAgg(DATA.content_daily,RANGE);
  document.getElementById("capContent").textContent="Coverage: "+distCoverage(RANGE);
  mkChart("cContent",{type:"doughnut",data:{labels:content.map(r=>CT[r[0]]||r[0]),
    datasets:[{data:content.map(r=>r[1]),backgroundColor:[ACC,ACC2,BLUE,"#8a8a8a","#b366ff"],borderColor:"#141414",borderWidth:2}]},
    options:{plugins:{legend:{position:"right",labels:{boxWidth:10,font:{size:11}}}},maintainAspectRatio:false,cutout:"58%"}});

  const wn=windowName(RANGE,RANGE.preset);
  const geo=((DATA.geo_by_window||{})[wn]||[]).slice(0,10);
  document.getElementById("capGeo").textContent="Window: "+windowLabel(wn)+(wn!=="all"&&RANGE.preset==="custom"?" (nearest preset)":"");
  mkChart("cGeo",{type:"bar",data:{labels:geo.map(r=>COUNTRY[r[0]]||r[0]),
    datasets:[{data:geo.map(r=>r[1]),backgroundColor:ACC,borderRadius:5}]},
    options:{indexAxis:"y",plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{display:false}},y:{grid:{display:false}}},maintainAspectRatio:false}});

  const ageMap={}; ((DATA.demo_by_window||{})[wn]||[]).forEach(r=>{const a=String(r[0]).replace("age","");ageMap[a]=(ageMap[a]||0)+(+r[2]||0);});
  const ageKeys=Object.keys(ageMap).sort();
  document.getElementById("capAge").textContent="Window: "+windowLabel(wn)+" · viewerPercentage can't be sliced by exact date";
  mkChart("cAge",{type:"bar",data:{labels:ageKeys,datasets:[{data:ageKeys.map(k=>+ageMap[k].toFixed(1)),backgroundColor:ACC2,borderRadius:5}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y+"%"}}},
      scales:{x:{grid:{display:false}},y:{beginAtZero:true,ticks:{callback:v=>v+"%"}}},maintainAspectRatio:false}});
}

function renderTargets(){
  const meta=DATA.videos||{};
  const topLifetime=Math.max(0,...Object.values(meta).map(v=>v.lifetime_views||0));
  const {rows}=topVideos(RANGE); const topRange=rows.length?Math.max(...rows.map(r=>r.views)):0;
  const live={subscribers:(DATA.snapshot||{}).subs||0, top_video_views:topLifetime, monthly_5k:topRange};
  document.getElementById("targets")&&(document.getElementById("targets").innerHTML=(STRATEGY.targets||[]).map(t=>{
    const cur=live[t.key]||0, p=Math.min(100,cur/t.goal*100);
    return `<div class="prog"><div class="top"><span class="lab">${t.label}</span>
      <span class="num">${fmt(cur)} / ${fmt(t.goal)} · ${p.toFixed(0)}%</span></div>
      <div class="bar"><i style="width:${Math.max(2,p)}%"></i></div><div class="note">${t.note||""}</div></div>`;}).join(""));
}

function renderStrategy(){
  document.getElementById("formula").textContent=STRATEGY.formula||"";
  document.getElementById("insights").innerHTML=(STRATEGY.insights||[]).map(i=>`<li>${esc(i)}</li>`).join("");
  const nx=STRATEGY.next_up||[]; document.getElementById("next").innerHTML=nx.map(i=>`<li>${esc(i)}</li>`).join("");
  if(!nx.length) document.getElementById("nextHdr").style.display="none";
  document.getElementById("mission").textContent=STRATEGY.mission||"";
}

function renderJobCard(){
  const j=DATA.reach_job||{}; let dot="r", st="Unknown";
  if(j.dates){ dot="g"; st="Live — data "+j.dates[0]+" → "+j.dates[1]; }
  else if(j.api_enabled===false){ dot="r"; st="Reporting API not enabled"; }
  else if(j.created_now){ dot="y"; st="Job created this run — first data "+(j.first_data_expected||"~24-48h"); }
  else if(j.exists){ dot="y"; st="Job exists, awaiting first reports — "+(j.first_data_expected||"~24-48h"); }
  else if(j.error){ dot="r"; st="Error: "+j.error; }
  document.getElementById("jobcard").innerHTML=
    `<div class="st"><span class="dot ${dot}"></span>${esc(st)}</div>`+
    `<div style="color:var(--mut);margin-top:6px">Report type <code>${esc(j.report_type||"")}</code>`+
    (j.job_id?` · job <code>${esc(j.job_id)}</code>`:``)+
    (j.reports!=null?` · ${j.reports} report files`:``)+`</div>`;
  // import status
  const n=Object.keys(STUDIO).length;
  document.getElementById("impStatus").textContent = n
    ? `${n} videos imported${STUDIO_META&&STUDIO_META.at?" · "+STUDIO_META.at:""}` : "no manual import loaded";
}

/* ============================ controls ============================ */
function renderControls(){
  document.getElementById("presets").innerHTML=PRESETS.map(([k,l])=>
    `<button data-p="${k}" class="${RANGE.preset===k?"on":""}">${l}</button>`).join("");
  document.querySelectorAll("#presets button").forEach(b=>b.onclick=()=>{
    const p=b.dataset.p; RANGE={preset:p, ...clampRange(presetRange(p))}; syncInputs(); renderAll(); });
  document.getElementById("apply").onclick=()=>{
    const s=document.getElementById("d0").value, e=document.getElementById("d1").value;
    if(!s||!e) return; RANGE={preset:"custom", ...clampRange({start:s,end:e})}; syncInputs(); renderAll(); };
}
function syncInputs(){
  const d0=document.getElementById("d0"), d1=document.getElementById("d1");
  d0.min=MINDATE; d0.max=MAXDATE; d1.min=MINDATE; d1.max=MAXDATE;
  d0.value=RANGE.start; d1.value=RANGE.end;
  document.querySelectorAll("#presets button").forEach(b=>b.classList.toggle("on",b.dataset.p===RANGE.preset));
  const lab=RANGE.preset==="custom"?"Custom":PRESETS.find(p=>p[0]===RANGE.preset)?.[1]||"";
  document.getElementById("rangelabel").innerHTML=`Showing <b>${RANGE.start}</b> → <b>${RANGE.end}</b> · ${between(RANGE.start,RANGE.end)} days${lab?` · ${lab}`:""}`;
}

/* ============================ CSV import ============================ */
function parseCSV(text){
  const rows=[]; let row=[],cur="",q=false;
  for(let i=0;i<text.length;i++){ const c=text[i];
    if(q){ if(c==='"'){ if(text[i+1]==='"'){cur+='"';i++;} else q=false; } else cur+=c; }
    else { if(c==='"') q=true; else if(c===","){row.push(cur);cur="";}
      else if(c==="\n"){row.push(cur);rows.push(row);row=[];cur="";}
      else if(c==="\r"){} else cur+=c; } }
  if(cur.length||row.length){ row.push(cur); rows.push(row); }
  return rows.filter(r=>r.length>1||(r.length===1&&r[0].trim()));
}
function importStudio(text){
  const rows=parseCSV(text); if(!rows.length) return {ok:false,msg:"empty file"};
  const header=rows[0].map(h=>h.trim()); const low=header.map(h=>h.toLowerCase());
  const findCol=(pred)=>low.findIndex(pred);
  let vi=low.findIndex(h=>h==="video"||h==="content"||h==="video id");
  if(vi<0) vi=low.findIndex(h=>h.includes("video")&&!h.includes("title")&&!h.includes("publish")&&!h.includes("duration"));
  let ii=findCol(h=>h.includes("impression")&&!h.includes("click")&&!h.includes("ctr"));
  let ci=findCol(h=>h.includes("click-through")||h.includes("click through")||h.includes("ctr"));
  if(vi<0||ii<0) return {ok:false,msg:"couldn't find Video/Impressions columns. Header: "+header.join(" | ")};
  const map={}; let count=0;
  for(let k=1;k<rows.length;k++){ const r=rows[k]; if(!r||r.length<=Math.max(vi,ii)) continue;
    const vid=(r[vi]||"").trim(); if(!vid||/^total/i.test(vid)) continue;
    const imp=parseFloat((r[ii]||"").replace(/[, ]/g,""));
    let ctr=ci>=0?parseFloat((r[ci]||"").replace(/[%, ]/g,"")):null;
    if(isNaN(imp)) continue;
    map[vid]={imp:imp, ctr:(ctr==null||isNaN(ctr))?null:ctr}; count++; }
  if(!count) return {ok:false,msg:"no data rows parsed"};
  return {ok:true, map, count, cols:{video:header[vi],imp:header[ii],ctr:ci>=0?header[ci]:null}};
}
function wireImport(){
  document.getElementById("csv").onchange=ev=>{ const f=ev.target.files[0]; if(!f) return;
    const rd=new FileReader(); rd.onload=()=>{ const res=importStudio(rd.result);
      if(!res.ok){ alert("Import failed: "+res.msg); return; }
      STUDIO=res.map; STUDIO_META={at:new Date().toISOString().slice(0,16).replace("T"," "),count:res.count,cols:res.cols};
      try{ localStorage.setItem(LS_KEY,JSON.stringify({map:STUDIO,meta:STUDIO_META})); }catch(e){}
      renderJobCard(); renderTopVideos();
      alert(`Imported ${res.count} videos (Video=“${res.cols.video}”, Impressions=“${res.cols.imp}”, CTR=“${res.cols.ctr||"—"}”).`);
    }; rd.readAsText(f); ev.target.value=""; };
  document.getElementById("csvClear").onclick=()=>{ STUDIO={}; STUDIO_META=null;
    try{ localStorage.removeItem(LS_KEY); }catch(e){} renderJobCard(); renderTopVideos(); };
  document.getElementById("edOnly").checked = (STRATEGY.editorial_since? true:false);
  document.getElementById("edOnly").onchange=renderTopVideos;
}

/* ============================ orchestration ============================ */
function renderAll(){
  try{ localStorage.setItem("gcore_range_v1",JSON.stringify(RANGE)); }catch(e){}
  syncInputs(); renderOverview(); renderDaily(); renderTopVideos(); renderDistributions(); renderTargets();
}
renderSnapshot(); renderStrategy(); renderJobCard(); renderControls(); wireImport(); renderAll();

document.getElementById("foot").innerHTML =
  `Data: YouTube Data API (lifetime snapshot + video metadata), Analytics API v2 (day-granular views, `+
  `estimatedMinutesWatched, averageViewDuration, averageViewPercentage, subs, likes/comments/shares, traffic, geography, demographics), `+
  `and Reporting API v1 reach reports (video_thumbnail_impressions + video_thumbnail_impressions_ctr). `+
  `Every panel is computed in-browser for the active range from data refreshed daily via GitHub Actions. `+
  `Built ${BUILT}. Internal — please don't share the URL publicly.`;
</script>
</body>
</html>
"""

out = (HTML
       .replace("__DATA__", json.dumps(DATA))
       .replace("__STRATEGY__", json.dumps(STRATEGY))
       .replace("__BUILT__", BUILT))
open(os.path.join(HERE, "docs", "index.html"), "w").write(out)
print("Wrote docs/index.html (" + str(len(out)) + " bytes)")
