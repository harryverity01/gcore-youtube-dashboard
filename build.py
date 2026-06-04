#!/usr/bin/env python3
"""Render docs/index.html from docs/data.json + strategy.json.

The page is fully static and self-contained: the data is injected inline,
Chart.js is pulled from a CDN, and video thumbnails load from i.ytimg.com
at view-time. No server, no build step beyond this script.
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
    --good:#39d98a; --bad:#ff5d5d;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 22px 80px}
  /* header */
  .head{display:flex;align-items:center;gap:16px;flex-wrap:wrap;
    border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:26px}
  .head img{width:60px;height:60px;border-radius:50%;border:2px solid var(--accent)}
  .head h1{margin:0;font-size:22px;letter-spacing:.2px}
  .head .sub{color:var(--mut);font-size:13px;margin-top:3px}
  .head .right{margin-left:auto;text-align:right;font-size:12px;color:var(--mut)}
  .pill{display:inline-block;background:var(--accent);color:#000;font-weight:700;
    font-size:11px;padding:4px 10px;border-radius:999px;letter-spacing:.3px}
  /* section */
  h2.sec{font-size:13px;letter-spacing:1.4px;text-transform:uppercase;color:var(--mut);
    margin:38px 0 14px;font-weight:700}
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
  .chart h3{margin:0 0 12px;font-size:14px;font-weight:700}
  .chart .cv{position:relative;height:230px}
  .full{grid-column:1 / -1}
  /* video wall */
  .wall{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
  .vid{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;
    transition:transform .12s ease,border-color .12s ease}
  .vid:hover{transform:translateY(-3px);border-color:var(--accent)}
  .vid .thumb{position:relative;aspect-ratio:16/9;background:#000;overflow:hidden}
  .vid .thumb img{width:100%;height:100%;object-fit:cover;display:block}
  .vid .badge{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.8);
    font-size:11px;padding:2px 6px;border-radius:5px;font-weight:600}
  .vid .rank{position:absolute;top:8px;left:8px;background:var(--accent);color:#000;
    font-size:11px;font-weight:800;padding:2px 8px;border-radius:6px}
  .vid .body{padding:12px 14px}
  .vid .t{font-size:13px;font-weight:700;line-height:1.35;height:54px;overflow:hidden}
  .vid .m{display:flex;gap:14px;color:var(--mut);font-size:12px;margin-top:10px;flex-wrap:wrap}
  .vid .m b{color:var(--txt)}
  /* strategy */
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
    .wall{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}}
  @media(max-width:560px){.wall{grid-template-columns:1fr}.head .right{margin-left:0;text-align:left}}
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
      <span id="built"></span><br>
      <span id="window"></span>
    </div>
  </div>

  <h2 class="sec">Channel Snapshot</h2>
  <div class="cards" id="cards"></div>

  <h2 class="sec">Phase 2 — Progress to Targets</h2>
  <div id="targets"></div>

  <h2 class="sec">Audience &amp; Reach · Last 28 Days</h2>
  <div class="grid">
    <div class="chart full"><h3>Daily views (28-day window)</h3><div class="cv"><canvas id="cTrend"></canvas></div></div>
    <div class="chart"><h3>Traffic sources</h3><div class="cv"><canvas id="cTraffic"></canvas></div></div>
    <div class="chart"><h3>Top geographies (views)</h3><div class="cv"><canvas id="cGeo"></canvas></div></div>
    <div class="chart"><h3>Audience by age</h3><div class="cv"><canvas id="cAge"></canvas></div></div>
    <div class="chart"><h3>Content type · views share</h3><div class="cv"><canvas id="cContent"></canvas></div></div>
  </div>

  <h2 class="sec">Top Videos · Last 28 Days</h2>
  <div class="wall" id="wall"></div>

  <h2 class="sec">Strategy</h2>
  <div class="two">
    <div class="box">
      <h3>What's working</h3>
      <div class="formula" id="formula"></div>
      <ul class="ins" id="insights"></ul>
    </div>
    <div class="box">
      <h3>Next up</h3>
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

const fmt = n => (n==null?"—":Number(n).toLocaleString("en-US"));
const fmtDur = s => { s=Math.round(s||0); const m=Math.floor(s/60); return m+"m "+String(s%60).padStart(2,"0")+"s"; };
const iso2dur = d => { if(!d) return ""; const m=d.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/)||[];
  const h=+(m[1]||0),mi=+(m[2]||0),se=+(m[3]||0);
  return (h?h+":"+String(mi).padStart(2,"0"):mi)+":"+String(se).padStart(2,"0"); };
const pct = (cur,prev) => { if(!prev) return null; return (cur-prev)/prev*100; };
const deltaHTML = (cur,prev,invert=false) => {
  const p = pct(cur,prev); if(p==null) return "";
  const good = invert ? p<0 : p>0;
  const cls = Math.abs(p)<0.5 ? "flat" : (good?"up":"down");
  const arr = p>0?"▲":(p<0?"▼":"•");
  return `<div class="d ${cls}">${arr} ${Math.abs(p).toFixed(1)}% vs prev 28d</div>`;
};

// ---- unpack overview rows ----
const ov = (DATA.overview&&DATA.overview[0])||[0,0,0,0,0,0,0,0];
const pv = (DATA.overview_prev&&DATA.overview_prev[0])||[0,0,0,0,0,0,0,0];
const O = {views:ov[0],mins:ov[1],avg:ov[2],sg:ov[3],sl:ov[4],likes:ov[5],comments:ov[6],shares:ov[7]};
const P = {views:pv[0],mins:pv[1],avg:pv[2],sg:pv[3],sl:pv[4],likes:pv[5],comments:pv[6],shares:pv[7]};
const netSubs = O.sg-O.sl, netPrev = P.sg-P.sl;

// ---- header ----
const snap = DATA.snapshot||{};
document.getElementById("avatar").src = snap.avatar || "https://yt3.ggpht.com/ytc/default";
document.getElementById("handle").textContent = "@gcoreofficial · channel created "+(snap.created||"").slice(0,4);
document.getElementById("phase").textContent = STRATEGY.phase;
document.getElementById("built").textContent = "Updated "+BUILT;
document.getElementById("window").textContent = "Window "+(DATA.window||[]).join(" → ");

// ---- stat cards ----
const cards = [
  {k:"Subscribers",v:fmt(snap.subs)},
  {k:"Total Views",v:fmt(snap.total_views)},
  {k:"Videos",v:fmt(snap.videos)},
  {k:"Net Subs · 28d",v:(netSubs>=0?"+":"")+fmt(netSubs),d:deltaHTML(netSubs,netPrev)},
  {k:"Views · 28d",v:fmt(O.views),d:deltaHTML(O.views,P.views)},
  {k:"Watch Time · 28d",v:fmt(Math.round(O.mins/60))+" hrs",d:deltaHTML(O.mins,P.mins)},
  {k:"Avg View Duration",v:fmtDur(O.avg),d:deltaHTML(O.avg,P.avg)},
  {k:"Engagement · 28d",v:fmt(O.likes+O.comments+O.shares),d:`<div class="d flat">${fmt(O.likes)} likes · ${fmt(O.shares)} shares</div>`},
];
document.getElementById("cards").innerHTML = cards.map(c=>
  `<div class="card"><div class="k">${c.k}</div><div class="v">${c.v}</div>${c.d||""}</div>`).join("");

// ---- targets ----
const topViews = Math.max(0,...(DATA.top_videos||[]).map(v=>v.views||0));
const live = {subscribers:snap.subs||0, top_video_views:topViews, monthly_5k:topViews};
document.getElementById("targets").innerHTML = STRATEGY.targets.map(t=>{
  const cur = live[t.key]||0, p = Math.min(100, cur/t.goal*100);
  return `<div class="prog"><div class="top"><span class="lab">${t.label}</span>
    <span class="num">${fmt(cur)} / ${fmt(t.goal)} · ${p.toFixed(0)}%</span></div>
    <div class="bar"><i style="width:${Math.max(2,p)}%"></i></div>
    <div class="note">${t.note||""}</div></div>`;
}).join("");

// ---- chart defaults ----
Chart.defaults.color="#9a9a9a"; Chart.defaults.borderColor="#2a2a2a";
Chart.defaults.font.family=getComputedStyle(document.body).fontFamily;
const ACC="#FFA500", ACC2="#FF7A00";
const palette=["#FFA500","#FF7A00","#ff5d5d","#39d98a","#4d9fff","#b366ff","#ffd24d","#5ad1c9","#8a8a8a","#e06bff"];

// trend
const daily = DATA.daily||[];
new Chart(cTrend,{type:"line",data:{labels:daily.map(r=>r[0].slice(5)),
  datasets:[{label:"Views",data:daily.map(r=>r[1]),borderColor:ACC,backgroundColor:"rgba(255,165,0,.12)",
    fill:true,tension:.3,pointRadius:0,borderWidth:2}]},
  options:{plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{beginAtZero:true}},
    maintainAspectRatio:false}});

// traffic
const TRAFFIC_LABELS={SUBSCRIBER:"Subscriber feed",YT_SEARCH:"YouTube search",EXT_URL:"External URLs",
  RELATED_VIDEO:"Suggested videos",NO_LINK_OTHER:"Direct / other",NO_LINK_EMBEDDED:"Embedded player",
  YT_CHANNEL:"Channel page",PLAYLIST:"Playlists",NOTIFICATION:"Notifications",YT_OTHER_PAGE:"Other YouTube",
  ADVERTISING:"Advertising",CAMPAIGN_CARD:"Cards / end screens",HASHTAGS:"Hashtags",SHORTS:"Shorts feed"};
const traffic=(DATA.traffic||[]).slice(0,8);
new Chart(cTraffic,{type:"doughnut",data:{labels:traffic.map(r=>TRAFFIC_LABELS[r[0]]||r[0]),
  datasets:[{data:traffic.map(r=>r[1]),backgroundColor:palette,borderColor:"#141414",borderWidth:2}]},
  options:{plugins:{legend:{position:"right",labels:{boxWidth:10,font:{size:11}}}},
    maintainAspectRatio:false,cutout:"58%"}});

// geography
const COUNTRY={US:"United States",DE:"Germany",GB:"United Kingdom",AU:"Australia",CA:"Canada",
  SE:"Sweden",FR:"France",NL:"Netherlands",IN:"India",ES:"Spain",IT:"Italy",CH:"Switzerland",
  PL:"Poland",BR:"Brazil",JP:"Japan",SG:"Singapore",AE:"UAE",IE:"Ireland",NO:"Norway",FI:"Finland"};
const geo=(DATA.geography||[]).slice(0,10);
new Chart(cGeo,{type:"bar",data:{labels:geo.map(r=>COUNTRY[r[0]]||r[0]),
  datasets:[{data:geo.map(r=>r[1]),backgroundColor:ACC,borderRadius:5}]},
  options:{indexAxis:"y",plugins:{legend:{display:false}},
    scales:{x:{beginAtZero:true,grid:{display:false}},y:{grid:{display:false}}},maintainAspectRatio:false}});

// age (aggregate genders)
const ageMap={};
(DATA.demographics||[]).forEach(r=>{const a=String(r[0]).replace("age","");ageMap[a]=(ageMap[a]||0)+ (+r[2]||0);});
const ageKeys=Object.keys(ageMap).sort();
new Chart(cAge,{type:"bar",data:{labels:ageKeys,
  datasets:[{data:ageKeys.map(k=>+ageMap[k].toFixed(1)),backgroundColor:ACC2,borderRadius:5}]},
  options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y+"%"}}},
    scales:{x:{grid:{display:false}},y:{beginAtZero:true,ticks:{callback:v=>v+"%"}}},maintainAspectRatio:false}});

// content type
const CT={creatorContentTypeUnspecified:"Other",videoOnDemand:"Long-form (VOD)",shorts:"Shorts",
  liveStream:"Live",story:"Story"};
const content=(DATA.by_content||[]);
new Chart(cContent,{type:"doughnut",data:{labels:content.map(r=>CT[r[0]]||r[0]),
  datasets:[{data:content.map(r=>r[1]),backgroundColor:[ACC,ACC2,"#4d9fff","#8a8a8a"],borderColor:"#141414",borderWidth:2}]},
  options:{plugins:{legend:{position:"right",labels:{boxWidth:10,font:{size:11}}}},
    maintainAspectRatio:false,cutout:"58%"}});

// ---- video wall ----
const vids=(DATA.top_videos||[]).slice(0,12);
document.getElementById("wall").innerHTML = vids.map((v,i)=>{
  const thumb=`https://i.ytimg.com/vi/${v.id}/mqdefault.jpg`;
  return `<a class="vid" href="https://youtu.be/${v.id}" target="_blank" rel="noopener">
    <div class="thumb"><span class="rank">#${i+1}</span>
      <img loading="lazy" src="${thumb}" onerror="this.src='https://i.ytimg.com/vi/${v.id}/hqdefault.jpg'" alt="">
      <span class="badge">${iso2dur(v.dur)}</span></div>
    <div class="body"><div class="t">${(v.title||v.id).replace(/</g,"&lt;")}</div>
      <div class="m"><span><b>${fmt(v.views)}</b> views</span>
        <span><b>${fmtDur(v.avg_dur)}</b> avg</span>
        <span><b>${fmt(v.likes)}</b> likes</span></div>
      <div class="m"><span>${v.published||""}</span></div></div></a>`;
}).join("");

// ---- strategy ----
document.getElementById("formula").textContent = STRATEGY.formula;
document.getElementById("insights").innerHTML = STRATEGY.insights.map(i=>`<li>${i}</li>`).join("");
document.getElementById("next").innerHTML = (STRATEGY.next_up||[]).map(i=>`<li>${i}</li>`).join("");
document.getElementById("mission").textContent = STRATEGY.mission;

document.getElementById("foot").innerHTML =
  `Data: YouTube Data &amp; Analytics API (channel==MINE, @gcoreofficial) · 28-day rolling window · `+
  `auto-refreshed daily via GitHub Actions. Thumbnail CTR / impressions are Studio-only and not shown. `+
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
