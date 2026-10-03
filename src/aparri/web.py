"""Phase 8: static, offline-capable interactive defense map -> ``outputs/web/``.

No server and no build step: open ``outputs/web/index.html`` from a USB stick, or host the folder on GitHub Pages.
Leaflet is vendored in ``outputs/web/vendor`` (works without internet); the data are plain ``.js`` files
(``window.APARRI = {...}``) rather than fetched JSON, because browsers refuse ``fetch()`` on ``file://`` pages.
Optional online basemaps are offered but the map is fully usable without them.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import pandas as pd

from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport

PROPS_SEG = ["transect_id", "barangay", "risk_class", "trend", "confidence", "EPR_m_yr", "lrr", "lrr_ci_low", "lrr_ci_high", "NSM_m", "SCE_m",
             "n_dates", "unc_status", "unc_epr_used_m_yr", "unc_basis", "class_may_flip", "class_lower_bound", "class_upper_bound",
             "quality_flag", "multi_hit_years", "missing", "axis_km", "length_m", "valid_epr", "risk_class_raw", "T_source"]


def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if (v != v) else round(float(v), 3)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if v is pd.NA or v is None:
        return None
    return v


def to_geojson(gdf: gpd.GeoDataFrame, props: list[str] | None = None, simplify_m: float = 0.0, extra: dict | None = None) -> dict:
    g = gdf.copy()
    if simplify_m:
        g["geometry"] = g.geometry.simplify(simplify_m, preserve_topology=True)
    g = g.to_crs(4326)
    cols = [c for c in (props or [c for c in g.columns if c != "geometry"]) if c in g.columns]
    feats = []
    for _, r in g.iterrows():
        geom = json.loads(gpd.GeoSeries([r.geometry]).to_json())["features"][0]["geometry"]
        geom = json.loads(json.dumps(geom), parse_float=lambda s: round(float(s), 6))
        feats.append({"type": "Feature", "properties": {c: _clean(r[c]) for c in cols}, "geometry": geom})
    return {"type": "FeatureCollection", "features": feats}


def js(name: str, obj) -> str:
    return f"window.APARRI = window.APARRI || {{}};\nwindow.APARRI.{name} = " + json.dumps(obj, separators=(",", ":"), ensure_ascii=False, default=_clean) + ";\n"


def build_data(cfg: dict) -> dict:
    work = cfg["crs_work"]; P = cfg["paths"]
    name = cfg["shoreline_set"]
    seg = gpd.read_file(repo_path(f"data/processed/{name}/risk_segments.gpkg"))
    tr = gpd.read_file(repo_path(f"data/processed/{name}/risk_transects.gpkg"))
    from .transects import SET_FILES
    parts = gpd.read_file(repo_path(SET_FILES[name]), layer="shoreline_parts")
    study = read_vector(P["barangays_study"], work)
    allb = read_vector(P["barangays_all"], work)
    legacy = read_vector(P["risk_legacy"], work)
    legacy["risk"] = legacy.Risk_Level.astype(str).str[:3].replace({"Hig": "High", "Med": "Medium", "LOW": "Low"})
    ext = pd.read_csv(repo_path("outputs/tables/Table_4_2_extended.csv"))
    th = pd.read_csv(repo_path("outputs/tables/Table_4_2_barangay_results.csv"))
    seg_cols = [c for c in PROPS_SEG if c in seg.columns]
    segj = to_geojson(seg, seg_cols, 0.5)
    trj = to_geojson(tr, ["transect_id", "barangay", "EPR_m_yr", "lrr", "risk_class", "confidence", "quality_flag", "flagged", "axis_km"], 0.0)
    shj = to_geojson(parts[["year", "scope", "part_id", "geometry"]], ["year", "scope", "part_id"], 2.0)
    brj = to_geojson(study[["ADM4_EN", "geometry"]].rename(columns={"ADM4_EN": "name"}), ["name"], 5.0)
    allj = to_geojson(allb[["ADM4_EN", "geometry"]].rename(columns={"ADM4_EN": "name"}), ["name"], 30.0)
    lgj = to_geojson(legacy[["risk", "geometry"]], ["risk"], 2.0)
    meta = {
        "title": "Aparri coastal erosion risk, 1990–2025",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "shoreline_set": name, "years": cfg["years"], "spacing_m": cfg["transects"]["spacing_m"],
        "thresholds": {"low_max": cfg["risk"]["low_max"], "medium_max": cfg["risk"]["medium_max"]},
        "strip_width_m": cfg["risk"]["strip_width_m"],
        "what_if_unc_m": cfg["risk"]["confidence_scenario_unc_m"],
        "acquisition_dates_known": all(cfg["acquisition_dates"].values()),
        "uncertainty_provided": {k: v is not None for k, v in cfg["uncertainty_m"].items()},
        "order": cfg["table_4_2_order"],
    }
    table = {"thesis": th.to_dict("records"), "extended": ext.to_dict("records")}
    return {"segments": segj, "transects": trj, "shorelines": shj, "barangays": brj, "context": allj, "legacy": lgj, "table42": table, "meta": meta,
            "seg_cols": seg_cols}


def write_site(out, data: dict) -> None:
    (out / "data").mkdir(exist_ok=True)
    for k in ("segments", "transects", "shorelines", "barangays", "context", "legacy", "table42", "meta"):
        (out / "data" / f"{k}.js").write_text(js(k, data[k]), encoding="utf-8")
    (out / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (out / "app.js").write_text(APP_JS, encoding="utf-8")
    (out / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (out / "README.md").write_text(README, encoding="utf-8")


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("web", cfg)
    out = ensure_dir("outputs/web")
    data = build_data(cfg)
    write_site(out, data)
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    rep.count("segments", len(data["segments"]["features"])); rep.count("transects", len(data["transects"]["features"])); rep.count("site_kB", round(size / 1024))
    rep.add_output(out / "index.html")
    rep.write()
    print(f"web map written to {out} ({size/1024:.0f} kB)")


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aparri Erosion Map</title>
<link rel="stylesheet" href="vendor/leaflet.css">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>Coastal erosion along eight Aparri barangays, 1990–2025</h1>
  <p class="disclaimer" role="note"><strong>Academic use.</strong> Classification is based on the shoreline change rate only; it is not a full exposure/vulnerability assessment.
  Rates come from 30&nbsp;m Landsat-based shorelines, with no measured positional error or image dates supplied (see “Limits”).</p>
</header>
<main>
  <section id="map-wrap" aria-label="Map">
    <div id="map" role="application" aria-label="Interactive map of shoreline change; use the panel on the right for keyboard access"></div>
    <div id="yearbar" aria-live="polite">
      <button id="play" type="button" aria-label="Play the shorelines from 1990 to 2025">▶ Play</button>
      <label for="year">Shoreline year: <output id="yearout">2025</output></label>
      <input id="year" type="range" min="0" max="4" step="1" value="4" aria-label="Shoreline year">
      <label class="chk"><input type="checkbox" id="cumul"> show all earlier years too</label>
    </div>
  </section>
  <aside id="panel" aria-label="Controls and information">
    <details open><summary>How to read this map</summary>
      <p>Each coloured line piece is 50&nbsp;m of the open sea-facing shoreline. Its colour is the <b>erosion rate</b> from 1990 to 2025: <span class="sw low"></span>Low (&lt; 2&nbsp;m/yr) · <span class="sw med"></span>Medium (2–5) · <span class="sw high"></span>High (&gt; 5). Blue triangles mark pieces that <em>grew</em> seaward. Grey = not classified (transect fans at the river mouth). A dotted line = low confidence.</p>
      <p>Click any piece for its numbers. Use the slider or ▶ to see how the shoreline moved; the 1990 line is the reference.</p>
    </details>
    <fieldset><legend>Layers</legend>
      <label><input type="checkbox" id="l-seg" checked> Risk classes (rebuilt)</label>
      <label><input type="checkbox" id="l-shore" checked> Shorelines by year</label>
      <label><input type="checkbox" id="l-brgy" checked> Study barangays</label>
      <label><input type="checkbox" id="l-ctx"> Other barangays</label>
      <label><input type="checkbox" id="l-tr"> Transects (50&nbsp;m)</label>
      <label><input type="checkbox" id="l-leg"> Legacy risk polygons <em>(NOT valid, comparison only)</em></label>
      <label><input type="checkbox" id="l-banks" checked> River banks (not classified)</label>
    </fieldset>
    <fieldset><legend>Display</legend>
      <label for="basemap">Background</label>
      <select id="basemap"><option value="none">None (works offline)</option><option value="osm">OpenStreetMap (needs internet)</option><option value="sat">Esri satellite (needs internet)</option></select>
      <label><input type="checkbox" id="cb"> Colour-blind-safe palette</label>
    </fieldset>
    <fieldset><legend>Barangay</legend>
      <label for="brgy">Zoom to</label>
      <select id="brgy"><option value="">— all —</option></select>
      <div id="brgy-card" aria-live="polite"></div>
    </fieldset>
    <div id="legend" aria-label="Legend"></div>
    <h2>Kilometres of shoreline per class</h2>
    <div id="chart" role="img" aria-label="Stacked bar chart of shoreline kilometres per class and barangay"></div>
    <details><summary>Table 4.2 (accessible table)</summary><div id="table42"></div></details>
    <details><summary>Limits — read before quoting a number</summary>
      <ul id="limits"></ul>
    </details>
    <p class="small" id="foot"></p>
  </aside>
</main>
<script src="vendor/leaflet.js"></script>
<script src="data/meta.js"></script><script src="data/segments.js"></script><script src="data/shorelines.js"></script>
<script src="data/barangays.js"></script><script src="data/context.js"></script><script src="data/transects.js"></script>
<script src="data/legacy.js"></script><script src="data/table42.js"></script>
<script src="app.js"></script>
</body>
</html>
"""

STYLE_CSS = """:root{--low:#2e8b57;--med:#ffa500;--high:#e31a1c;--ink:#1c2733;--bg:#f6f8fa;--panel:#fff;--line:#d0d7de}
@media (prefers-color-scheme:dark){:root{--ink:#e6edf3;--bg:#0d1117;--panel:#161b22;--line:#30363d}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{padding:10px 16px;border-bottom:1px solid var(--line);background:var(--panel)}h1{font-size:1.15rem;margin:0 0 4px}
.disclaimer{margin:0;font-size:.82rem;background:#fff4ce;color:#3d2e00;padding:6px 10px;border-radius:6px}
main{display:grid;grid-template-columns:1fr 380px;height:calc(100vh - 92px);min-height:560px}
#map-wrap{position:relative;min-height:420px}#map{position:absolute;inset:0;background:#dbe9f4}
#yearbar{position:absolute;left:10px;right:10px;bottom:22px;z-index:900;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#yearbar input[type=range]{flex:1;min-width:140px}#yearout{font-weight:700;font-size:1.1rem}
button{font:inherit;padding:4px 12px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);cursor:pointer}button:focus-visible,select:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #1f6feb}
#panel{overflow:auto;padding:10px 14px;background:var(--panel);border-left:1px solid var(--line)}fieldset{border:1px solid var(--line);border-radius:6px;margin:8px 0;padding:6px 10px}legend{font-weight:600;padding:0 4px}
fieldset label{display:block}select{width:100%;margin:2px 0 6px;padding:4px;background:var(--panel);color:var(--ink)}
.sw{display:inline-block;width:14px;height:8px;margin:0 4px 0 6px;border-radius:2px}.sw.low{background:var(--low)}.sw.med{background:var(--med)}.sw.high{background:var(--high)}
h2{font-size:.95rem;margin:12px 0 4px}details{margin:6px 0}summary{cursor:pointer;font-weight:600}.small{font-size:.75rem;opacity:.75}
#brgy-card table,#table42 table{border-collapse:collapse;width:100%;font-size:.8rem}#brgy-card td,#brgy-card th,#table42 td,#table42 th{border:1px solid var(--line);padding:2px 5px;text-align:right}th{background:rgba(127,127,127,.12)}td:first-child,th:first-child{text-align:left}
#legend{font-size:.85rem;margin:6px 0}#legend span.k{display:inline-block;width:22px;height:5px;margin:0 6px 2px 0;vertical-align:middle}
.leaflet-popup-content{font-size:13px;min-width:230px}.leaflet-popup-content table{border-collapse:collapse}.leaflet-popup-content td{padding:1px 6px 1px 0;vertical-align:top}
.lbl{background:rgba(255,255,255,.75);border:none;box-shadow:none;font-weight:600;font-size:11px;padding:1px 4px;color:#222}
@media (max-width:820px){main{grid-template-columns:1fr;grid-template-rows:60vh auto;height:auto}#panel{border-left:none;border-top:1px solid var(--line)}}
@media print{header .disclaimer{background:none;border:1px solid #000}main{display:block;height:auto}#map-wrap{height:560px;position:relative}#panel{border:none;overflow:visible}#yearbar button,#yearbar input,.leaflet-control-zoom,fieldset,details summary{display:none}details{display:block}details>*{display:block}}
"""

README = """# Interactive defense map (static)

**Open locally:** double-click `index.html` (works from a USB stick, no internet, no server). Chrome, Edge, Firefox and Safari are supported.
**Host online (GitHub Pages):** push this folder, then Settings -> Pages -> deploy from the branch/folder that contains `index.html`.

Contents: `index.html`, `app.js`, `style.css`, `vendor/` (Leaflet 1.9.4, BSD-2), `data/*.js` (the layers; regenerate with `make web`).
The optional OpenStreetMap / Esri backgrounds need internet; everything else works offline.

Layers: rebuilt risk segments (50 m), shorelines 1990/2000/2010/2020/2025, study barangays, other barangays, transects, legacy risk polygons (marked NOT valid; for the "why did the map change?" question).

Known limitations: classification uses erosion rate only (not exposure/vulnerability); positional error and image dates were not supplied (a +-30 m what-if is used for the confidence label); the Cagayan River banks are not classified; the shoreline set is `vector_clean` (provenance of the original lines unknown).
"""

APP_JS = r"""(function(){
'use strict';
var A = window.APARRI, M = A.meta, YEARS = M.years;
var PAL = {std:{Low:'#2e8b57',Medium:'#ffa500',High:'#e31a1c'}, cb:{Low:'#4575b4',Medium:'#fdae61',High:'#d73027'}};
var YCOL = {1990:'#6a3d9a',2000:'#2171b5',2010:'#00868b',2020:'#636363',2025:'#000000'};  /* no red/orange/green: those mean risk classes */
var pal = 'std';
var map = L.map('map',{preferCanvas:true,zoomSnap:0.25,keyboard:true,attributionControl:true});
map.attributionControl.addAttribution('Rebuilt analysis, CE thesis CSU-Carig · Leaflet');
L.control.scale({metric:true,imperial:false}).addTo(map);
var base = null;
function setBase(v){ if(base){map.removeLayer(base);base=null;}
  if(v==='osm'){base=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'});}
  if(v==='sat'){base=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:18,attribution:'Esri'});}
  if(base){base.addTo(map);base.bringToBack();}}
function fmt(v,d){return (v===null||v===undefined)?'–':Number(v).toFixed(d===undefined?2:d);}
function col(c){return PAL[pal][c]||'#7f7f7f';}

/* ---------- layers ---------- */
var ctx = L.geoJSON(A.context,{style:{color:'#c9c4b2',weight:.6,fillColor:'#f1efe6',fillOpacity:.8},interactive:false});
var brgyLabelLayer = L.layerGroup();
var brgy = L.geoJSON(A.barangays,{style:{color:'#555',weight:1,dashArray:'4 3',fillColor:'#d9d9d9',fillOpacity:.55},onEachFeature:function(f,l){
  l.bindTooltip(f.properties.name,{permanent:true,direction:'center',className:'lbl'});
  l.on('click',function(){selectBrgy(f.properties.name);});}});
var legacy = L.geoJSON(A.legacy,{style:function(f){return {color:'#000',weight:.5,fillColor:col(f.properties.risk),fillOpacity:.55};},
  onEachFeature:function(f,l){l.bindPopup('<b>Legacy polygon (NOT valid)</b><br>Label in the old file: '+f.properties.risk+'<br>See docs/01_data_audit.md');}});
var trans = L.geoJSON(A.transects,{style:function(f){return {color:f.properties.flagged?'#d62728':'#6b7280',weight:.7,opacity:.8};},
  onEachFeature:function(f,l){var p=f.properties;l.bindPopup('<b>'+p.transect_id+'</b><br>'+(p.barangay||'—')+'<br>EPR '+fmt(p.EPR_m_yr)+' m/yr · LRR '+fmt(p.lrr)+' m/yr<br>flags: '+(p.quality_flag||'none'));}});
var shoreLayer = L.layerGroup();
var banks = L.layerGroup();
var seg;
function segStyle(f){var p=f.properties;var c=p.risk_class;var grey=!c;
  return {color:grey?'#7f7f7f':col(c),weight:grey?4:5,opacity:.95,dashArray:(p.confidence==='low')?'2 4':null,lineCap:'butt'};}
function popup(p){
  var flip = p.class_may_flip? 'Yes — the class could change inside the ±'+fmt(p.unc_epr_used_m_yr,2)+' m/yr error band' : 'No';
  var cls = p.risk_class? p.risk_class : 'Not classified ('+(p.quality_flag||'invalid transect')+')';
  return '<table><tr><td colspan=2><b>'+(p.barangay||'—')+'</b> · '+p.transect_id+'</td></tr>'+
  '<tr><td>Risk class</td><td><b>'+cls+'</b> ('+(p.trend||'')+')</td></tr>'+
  '<tr><td>EPR 1990–2025</td><td>'+fmt(p.EPR_m_yr)+' m/yr (negative = erosion)</td></tr>'+
  '<tr><td>NSM</td><td>'+fmt(p.NSM_m,1)+' m</td></tr>'+
  '<tr><td>LRR (all years)</td><td>'+fmt(p.lrr)+' m/yr (95% CI '+fmt(p.lrr_ci_low)+' … '+fmt(p.lrr_ci_high)+'; '+p.n_dates+' dates)</td></tr>'+
  '<tr><td>Uncertainty</td><td>'+p.unc_status+' — class bounds use '+p.unc_basis+'</td></tr>'+
  '<tr><td>Class may flip?</td><td>'+flip+'</td></tr>'+
  '<tr><td>Confidence</td><td>'+p.confidence+'</td></tr>'+
  '<tr><td>Flags</td><td>'+([p.quality_flag,p.multi_hit_years?'multi-hit '+p.multi_hit_years:'',p.missing].filter(Boolean).join('; ')||'none')+'</td></tr>'+
  '<tr><td>Along coast</td><td>'+fmt(p.axis_km,2)+' km from NW end</td></tr></table>';}
function buildSeg(){ if(seg){map.removeLayer(seg);}
  seg = L.geoJSON(A.segments,{style:segStyle,onEachFeature:function(f,l){l.bindPopup(popup(f.properties));l.on('mouseover',function(){l.setStyle({weight:8});});l.on('mouseout',function(){seg.resetStyle(l);});}});
  if(document.getElementById('l-seg').checked){seg.addTo(map);} accMarks(); legend(); chart();}
var acc = L.layerGroup();
function accMarks(){acc.clearLayers();A.segments.features.forEach(function(f){if(f.properties.trend==='accreting'){var c=f.geometry.coordinates;var m=c[Math.floor(c.length/2)];
  L.circleMarker([m[1],m[0]],{radius:3,color:'#08519c',fillColor:'#08519c',fillOpacity:1,weight:1,interactive:false}).addTo(acc);}});}

/* ---------- shorelines by year ---------- */
var yearIdx=4;
function drawShore(){shoreLayer.clearLayers();banks.clearLayers();var cum=document.getElementById('cumul').checked;var yr=YEARS[yearIdx];
  A.shorelines.features.forEach(function(f){var y=f.properties.year;var isBank=f.properties.scope!=='open_coast';
    var show=cum?(y<=yr):(y===yr||y===YEARS[0]);
    if(!show) return;
    var cur=(y===yr);
    var ln=L.geoJSON(f,{style:{color:YCOL[y],weight:cur?2:1.4,opacity:cur?1:.55,dashArray:isBank?'5 4':null},interactive:false});
    (isBank?banks:shoreLayer).addLayer(ln);});
  if(!document.getElementById('l-banks').checked){map.removeLayer(banks);}else if(document.getElementById('l-shore').checked){banks.addTo(map);}
  document.getElementById('yearout').textContent=yr;
  if(seg&&map.hasLayer(seg)){seg.eachLayer(function(l){l.bringToFront();});}}
/* ---------- panel ---------- */
function legend(){var el=document.getElementById('legend');var P=PAL[pal];
  el.innerHTML='<b>Erosion rate class</b><br>'+['Low','Medium','High'].map(function(c){var t={Low:'< 2 m/yr',Medium:'2–5 m/yr',High:'> 5 m/yr'}[c];return '<span class="k" style="background:'+P[c]+'"></span>'+c+' ('+t+')';}).join('<br>')+
  '<br><span class="k" style="background:#7f7f7f"></span>Not classified<br><span class="k" style="background:#08519c;height:8px;width:8px;border-radius:4px"></span>accreting piece';
  el.innerHTML+='<br><b>Shoreline year</b><br>'+YEARS.map(function(y){return '<span class="k" style="background:'+YCOL[y]+'"></span>'+y;}).join(' &nbsp; ')+'<br><em>dashed = river banks</em>';
  document.querySelectorAll('.sw.low').forEach(function(s){s.style.background=P.Low;});document.querySelectorAll('.sw.med').forEach(function(s){s.style.background=P.Medium;});document.querySelectorAll('.sw.high').forEach(function(s){s.style.background=P.High;});}
function kmByBrgy(){var o={};M.order.forEach(function(b){o[b]={Low:0,Medium:0,High:0,No:0};});
  A.segments.features.forEach(function(f){var p=f.properties;if(!o[p.barangay])return;var c=p.risk_class||'No';o[p.barangay][c]+=p.length_m/1000;});return o;}
function chart(sel){var d=kmByBrgy();var W=350,H=190,L0=28,B=48;var mx=0;M.order.forEach(function(b){var t=d[b].Low+d[b].Medium+d[b].High+d[b].No;mx=Math.max(mx,t);});
  var bw=(W-L0)/M.order.length;var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" xmlns="http://www.w3.org/2000/svg" font-size="9">';
  for(var t=0;t<=mx;t+=1){var y=H-B-(t/mx)*(H-B-8);s+='<line x1="'+L0+'" x2="'+W+'" y1="'+y+'" y2="'+y+'" stroke="#999" stroke-opacity=".3"/><text x="2" y="'+(y+3)+'" fill="currentColor">'+t+'</text>';}
  M.order.forEach(function(b,i){var x=L0+i*bw+3;var y=H-B;[['Low',col('Low')],['Medium',col('Medium')],['High',col('High')],['No','#7f7f7f']].forEach(function(k){var h=(d[b][k[0]]/mx)*(H-B-8);y-=h;s+='<rect x="'+x+'" y="'+y+'" width="'+(bw-6)+'" height="'+h+'" fill="'+k[1]+'"'+(sel===b?' stroke="#000" stroke-width="2"':'')+'/>';});
    s+='<text transform="translate('+(x+bw/2-3)+','+(H-B+8)+') rotate(40)" fill="currentColor">'+b+'</text>';});
  s+='<text x="2" y="9" fill="currentColor">km</text></svg>';document.getElementById('chart').innerHTML=s;}
function table42(){var rows=A.table42.thesis;var h='<table><tr>'+Object.keys(rows[0]).map(function(k){return '<th>'+k.replace(' (m/year)','').replace(' Risk','')+'</th>';}).join('')+'</tr>';
  rows.forEach(function(r){h+='<tr>'+Object.keys(r).map(function(k,i){var v=r[k];return '<td>'+(i===0?v:(v===null?'–':Number(v).toFixed(2)))+'</td>';}).join('')+'</tr>';});document.getElementById('table42').innerHTML=h+'</table>';}
function selectBrgy(name){var sel=document.getElementById('brgy');sel.value=name||'';chart(name);var card=document.getElementById('brgy-card');
  if(!name){card.innerHTML='';map.fitBounds(bounds,{padding:[20,20]});return;}
  var e=A.table42.extended.filter(function(r){return r.Barangay===name;})[0];
  var sub={type:'FeatureCollection',features:A.segments.features.filter(function(f){return f.properties.barangay===name;})};
  if(sub.features.length){map.fitBounds(L.geoJSON(sub).getBounds().pad(.25));}else{brgy.eachLayer(function(l){if(l.feature.properties.name===name){map.fitBounds(l.getBounds());}});}
  var keys=Object.keys(e).filter(function(k){return ['Barangay','data quality'].indexOf(k)<0;});
  card.innerHTML='<table><tr><th colspan=2>'+name+' — Table 4.2 row</th></tr>'+keys.map(function(k){var v=e[k];return '<tr><td>'+k+'</td><td>'+(v===null?'–':(typeof v==='number'?v.toFixed(2):v))+'</td></tr>';}).join('')+'<tr><td colspan=2>'+e['data quality']+'</td></tr></table>';}
/* ---------- wire up ---------- */
var bounds=L.geoJSON(A.segments).getBounds().pad(.08);
map.fitBounds(bounds);
M.order.slice().sort().forEach(function(b){var o=document.createElement('option');o.value=b;o.textContent=b;document.getElementById('brgy').appendChild(o);});
document.getElementById('brgy').addEventListener('change',function(){selectBrgy(this.value);});
function toggle(id,layer){document.getElementById(id).addEventListener('change',function(){this.checked?layer.addTo(map):map.removeLayer(layer);if(layer===acc||layer===seg){}});}
brgy.addTo(map);shoreLayer.addTo(map);banks.addTo(map);acc.addTo(map);
toggle('l-brgy',brgy);toggle('l-ctx',ctx);toggle('l-tr',trans);toggle('l-leg',legacy);
document.getElementById('l-seg').addEventListener('change',function(){if(this.checked){seg.addTo(map);acc.addTo(map);}else{map.removeLayer(seg);map.removeLayer(acc);}});
document.getElementById('l-shore').addEventListener('change',function(){if(this.checked){shoreLayer.addTo(map);drawShore();}else{map.removeLayer(shoreLayer);map.removeLayer(banks);}});
document.getElementById('l-banks').addEventListener('change',drawShore);
document.getElementById('cumul').addEventListener('change',drawShore);
document.getElementById('year').addEventListener('input',function(){yearIdx=+this.value;drawShore();});
document.getElementById('basemap').addEventListener('change',function(){setBase(this.value);});
document.getElementById('cb').addEventListener('change',function(){pal=this.checked?'cb':'std';buildSeg();legacy.setStyle(function(f){return {color:'#000',weight:.5,fillColor:col(f.properties.risk),fillOpacity:.55};});});
var timer=null;document.getElementById('play').addEventListener('click',function(){var b=this;
  if(timer){clearInterval(timer);timer=null;b.textContent='▶ Play';return;}
  yearIdx=0;b.textContent='⏸ Pause';document.getElementById('year').value=0;drawShore();
  timer=setInterval(function(){yearIdx++;if(yearIdx>=YEARS.length){clearInterval(timer);timer=null;b.textContent='▶ Play';yearIdx=YEARS.length-1;}document.getElementById('year').value=yearIdx;drawShore();},1800);});
buildSeg();drawShore();table42();
setTimeout(function(){map.invalidateSize();map.fitBounds(bounds);},60);window.addEventListener('resize',function(){map.invalidateSize();});
document.getElementById('limits').innerHTML=[
 'Classes use the <b>erosion rate only</b> (EPR 1990–2025). Exposure and vulnerability were not assessed.',
 'Shorelines are 30&nbsp;m Landsat-based; one pixel at both dates = ±'+(Math.sqrt(2)*M.what_if_unc_m/35).toFixed(2)+' m/yr. <b>No measured positional error or image dates were supplied</b>; the confidence labels use a ±'+M.what_if_unc_m+' m what-if.',
 'Most of the coast sits within that error of the 2 m/yr class boundary, so “Low” versus “Medium” is partly a matter of convention (see “Class may flip?” in the pop-up).',
 'The Cagayan River banks and the Linao spit hook are not classified (transects cross there).',
 'Shoreline set: '+M.shoreline_set+' (origin of the original lines unknown; cleaned and cross-checked against an independent raster-derived set).',
 'Hectares in Table 4.2 are kilometres × a '+M.strip_width_m+' m strip (an assumption).'].map(function(t){return '<li>'+t+'</li>';}).join('');
document.getElementById('foot').textContent='Generated '+M.generated+' · '+A.segments.features.length+' shoreline pieces · '+A.transects.features.length+' transects';
window.__APARRI_READY__=true;
})();
"""


if __name__ == "__main__":  # pragma: no cover
    run()
