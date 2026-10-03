(function(){
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
