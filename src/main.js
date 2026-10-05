import {installRecordImport} from './import-records.js';
import {installCoverage} from './coverage.js';
import {resolveAttributes} from './attributes.js';
import {resolveTemporal} from './temporal.js';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './style.css';
import { levels, attributes, parseYear, formatYear, yearToTick, tickToYear, categoryColor, populationColor } from './model.js';
import {presentedAttribute} from './reference-context.js';
import {categoryPresentationKey} from './category-presentation.js';
import { loadGeography, loadSnapshot, ensureGeometry } from './data-client.js';
import { pointInGeometry } from './geometry.js';
import { PixelLayer } from './pixel-layer.js';
import {installWheelZoom} from './wheel-zoom.js';
import {locationInventoryChanged,boundaryFootprintsChanged} from './pixel-metadata.js';
import { GRID_ZOOM } from './pixel-grid.js';
const $ = selector => document.querySelector(selector);
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = { owner:'Political', culture:'Culture', religion:'Religion', population:'Population', rank:'Location rank', topography:'Topography', vegetation:'Vegetation', climate:'Climate', ...Object.fromEntries(levels.map(l => [l,l[0].toUpperCase()+l.slice(1)])) };
const icons = ['⚑','◈','✧','▥','♜','△','♧','☀'];
$('#app').innerHTML = `
  <header><a class="brand" href="/" aria-label="WorldAtlas home"><span class="brand-mark">◎</span> WorldAtlas<span class="edition">THE LIVING ATLAS</span></a><button id="about" class="quiet">About the data <span>↗</span></button></header>
  <main><aside class="sidebar"><div class="eyebrow">EXPLORE / 01</div><h1>A world<br>through time.</h1><p class="intro">Every border, a story.<br>Every place, a different perspective.</p>
    <label class="search-label" for="search">FIND A LOCATION</label><div class="search-wrap"><span>⌕</span><input id="search" type="search" placeholder="Search the world…" autocomplete="off"></div><div id="results" aria-live="polite"></div>
    <div class="section-heading">MAP LAYERS <span>08</span></div><div class="modes">${attributes.map((key,i) => `<button data-mode="${key}" class="mode ${key==='owner'?'active':''}" aria-pressed="${key==='owner'}"><span class="mode-icon">${icons[i]}</span>${labels[key]}<span class="mode-dot"></span></button>`).join('')}</div>
    <div class="section-heading geography-heading">GEOGRAPHIC HIERARCHY <span>06</span></div><div class="hierarchy-modes">${levels.map(key => `<button data-mode="${key}" class="mode" aria-pressed="false">${labels[key]}</button>`).join('')}</div>
    <div class="sidebar-footer"><span class="status-dot"></span> An atlas in the making <small>Public geography · Open history</small></div>
  </aside><section class="workspace" aria-label="World map explorer"><div class="map-heading"><div><span class="eyebrow">WORLD VIEW</span><h2 id="map-title">The political world</h2></div><div class="year-badge" id="map-year">2026 AD</div></div>
    <div class="map-stage"><div id="map" aria-label="Interactive world map"></div><div id="loading" role="status">Preparing your atlas…</div>
      <div class="map-actions"><button id="home" title="Fit world" aria-label="Fit world">⌖</button><button id="zoom-in" aria-label="Zoom in">+</button><button id="zoom-out" aria-label="Zoom out">−</button></div>
      <div class="map-note" id="map-note">Named geographic territories · Modern reference</div>
      <div id="details" class="details"><div class="eyebrow">A CLOSER LOOK</div><h3>Every place<br>has a past.</h3><p>Select a region on the map to explore its people, landscape, and place in the world.</p><button id="london" class="text-button">Explore London <span>→</span></button></div>
      <div class="legend"><div class="legend-heading"><span id="legend-title">POLITICAL</span><span id="legend-count"></span></div><div id="legend-items"></div></div><div class="map-coordinate">N ↑ <span>WORLDATLAS / EXPLORER</span></div>
    </div><div class="coverage"><span id="coverage" aria-live="polite">Loading geographic coverage…</span><button id="example-tour">Try 1444 examples →</button></div>
    <section class="timeline" aria-label="Historical timeline"><div class="timeline-top"><div><div class="eyebrow">TRAVEL THROUGH TIME</div><div class="timeline-caption">Choose a year. Discover a world.</div></div><form id="year-form"><label for="year-input">Go to year</label><input id="year-input" value="2026 AD" aria-describedby="year-error" autocomplete="off"><button type="submit" aria-label="Go to year">→</button></form></div>
      <div id="year-error" role="alert"></div><div class="slider-row"><button id="previous" aria-label="Previous year">‹</button><input id="year-slider" type="range" min="0" max="5025" value="5025" aria-label="Year"><button id="next" aria-label="Next year">›</button></div>
      <div class="timeline-ticks">${[-3000,-2000,-1000,1,1000,2026].map(y=>`<button data-year="${y}">${formatYear(y)}</button>`).join('')}</div><div class="timeline-footer"><span>Historical gaps are shown as unknown.</span><label class="check"><input type="checkbox" id="examples"> Include illustrative examples</label></div>
    </section>
  </section></main>
  <dialog id="data-dialog"><button id="close-dialog" class="dialog-close" aria-label="Close data information">×</button><div class="eyebrow">KNOW YOUR SOURCES</div><h2>Real boundaries.<br>Documented history.</h2>
  <p><strong>Locations use city territories, districts, or named physical regions.</strong> Country-specific source choices replace the previous average-area rule. Compact territories such as Hong Kong are single locations. The worldwide semantic review remains open; its complete ledger is available in Coverage and review. Published metropolitan territories combine their constituent wards. Named rural groupings come from IBGE in Brazil, MAPA in Spain, and Statistics Canada / AAFC in Canada. Each change records its source members; no unit counts are forced. Source dates vary and these are reference territories, not reconstructed historical boundaries.</p>
  <p id="framework-status"></p>
  <p><strong>Every location has a complete six-level geographic hierarchy.</strong> Location → Province → Area → Region → Subcontinent → Continent. The framework combines named Natural Earth regions, Chinese prefectures, Italian local labour systems and retained WGSRPD groups. Geographic membership is independent of political ownership. Some atlas groups adapt published geography; they are not claims about historical jurisdictions. Structural validation covers every location, while outstanding semantic reviews are listed in the geographic crosswalk report.</p>
  <p>New source evidence: <a href="https://www.geoboundaries.org/api/current/gbHumanitarian/CHN/ADM2/" target="_blank" rel="noreferrer">China prefectures (2020)</a>, CC BY 3.0 IGO; <a href="https://maps.regione.umbria.it/server/rest/services/Hosted/Sistemi_Locali_del_Lavoro_2011_2018/FeatureServer/2" target="_blank" rel="noreferrer">ISTAT local labour systems (2011/2018), Regione Umbria SIAT</a>, CC BY 3.0; <a href="https://www.bayarea.gov.hk/filemanager/en/share/pdf/Outline_Development_Plan.pdf" target="_blank" rel="noreferrer">Greater Bay Area plan (2019), Chapter 3</a>, geographic cooperation groups. Source dates describe reference geography, not evidence for every selected year.</p>
  <p><strong>A fixed geographic grid.</strong> Each land cell has one location ID and inherits its full parent chain. Colors and clicks use the same integer ID buffer. Zooming out displays the same fixed cells, which become smaller than a screen pixel. Local borders fade out; province borders remain visible. The grid stays about 153 m at the equator at every zoom. All current locations are represented; the coverage report records pixel distortion and source geometry remains available. Rendering runs in a background worker.</p>
  <p><strong>Locations form a single display coverage.</strong> Duplicate territory collections are removed. Overlapping source boundaries are reconciled using Natural Earth reference borders where supported, then the finer source polygon for remaining shared coverage. This display convention does not resolve territorial disputes. Historical source polygons are retained as evidence; disputed coverage produces an unresolved location record.</p>
  <p><strong>Historical ownership uses Cliopatria.</strong> Bennett et al. (2025), Seshat Global History Databank, reconstruct political territories from 3400 BC to 2024 AD. We include POLITY records, exclude composite RELATION records, simplify geometry, and filter their dated intervals. Coverage and precision vary; uncolored areas are not evidence that a place was uninhabited or ungoverned. Location borders shown underneath are modern.</p>
  <p>Political mode assigns each location one owner when a reconstructed polity covers more than half its land. WGS84 area, unioned same-polity footprints and conflicting claims are checked during preparation. Missing majorities and overlapping claims remain unresolved. Every map mode colors whole locations; source polygons do not paint partial locations.</p>
  <p><strong>Names change; identity persists.</strong> Names, habitation, rank, existence and parent membership can have sourced, dated records at every level. Settlements are separate entities associated with polygon locations. Renames retain an ID; splits and mergers link distinct IDs. Unknown does not mean uninhabited. Historical boundary versions reassign the fixed grid; higher boundaries follow their members.</p>
  <p><a href="https://github.com/tdwg/wgsrpd" target="_blank" rel="noreferrer">WGSRPD geographic scheme, TDWG / Royal Botanic Gardens, Kew</a> · R. K. Brummitt (2001); GIS: Justin Moat. Source GIS metadata credits ESRI / GMi underlying boundaries. Atlas macro-groups adapt the scheme to six continents. Coastline mismatch and low-overlap classifications are recorded in the downloadable hierarchy report.</p>
  <p>2026 uses modern ownership references with varying source dates, not a verified 2026 snapshot. Cliopatria has no 2025–2026 coverage.</p>
  <p><a href="https://www.geoboundaries.org/" target="_blank" rel="noreferrer">geoBoundaries / William & Mary</a> · Per-country dates and licenses appear in the inspector. <a href="https://www.naturalearthdata.com/about/terms-of-use/" target="_blank" rel="noreferrer">Natural Earth: public domain</a>.</p>
  <p><a href="https://doi.org/10.1038/s41597-025-04516-9" target="_blank" rel="noreferrer">Bennett et al., Cliopatria (2025)</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>. Geographic islands classifications also use <a href="https://github.com/datasets/country-codes" target="_blank" rel="noreferrer">country-codes / GeoNames continent codes</a>.</p><p>Physical subdivisions: AAFC, RESOLVE and Australia DCCEEW / IBRA. Name crosswalks: MLIT / Geolonia and <a href="https://www.geonames.org/" target="_blank" rel="noreferrer">GeoNames (CC BY 4.0)</a>. Turkmenistan district adaptations: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors (ODbL)</a>. Source years and coverage vary; retained coarse territories are listed in the audit.</p><p><a href="./semantic-report.json" target="_blank">Location crosswalk</a> · <a href="./granularity-audit.json" target="_blank">Full location audit</a> · <a href="./coverage-report.json" target="_blank">Coverage review</a> · <a href="./location-policy.json" target="_blank">Country policies</a> · <a href="./granularity-report.json" target="_blank">Source-level audit</a> · <a href="./hierarchy-report.json" target="_blank">Geographic crosswalk report</a></p></dialog>`;
const map = L.map('map', { zoomControl:false, attributionControl:true, minZoom:1, maxZoom:13, zoomSnap:0, scrollWheelZoom:false, preferCanvas:true, maxBounds:[[-89,-210],[89,210]], maxBoundsViscosity:0.7 });
installWheelZoom(map);
map.attributionControl.setPrefix(false);
map.attributionControl.addAttribution('<a href="https://www.geoboundaries.org/">geoBoundaries</a> · <a href="https://www.naturalearthdata.com/">Natural Earth</a> · <a href="https://doi.org/10.1038/s41597-025-04516-9">Cliopatria, CC BY 4.0</a>');
const worldBounds = [[-57,-174],[80,179]];
map.fitBounds(worldBounds);
let year = 2026, desiredYear = year, mode = 'owner', selected = null, data, referenceData, temporal, geoLayer, polities=[], states = new Map(), boundaries = new Map(), parents = new Map(), features = new Map(), layers = new Map(), maxPopulation = 0, controller, timer;
const emptyPolities=[];
const displayName=f=>f.properties.temporal?.display_name || f.properties.name;
const unitName=u=>u.display_name || u.name;
const trail = feature => {
  const result = [{...feature.properties.temporal,id:feature.id, level:'location', name:feature.properties.name}];
  let parent = parents.get(feature.properties.parent_id);
  while (parent) { result.push(parent); parent = parents.get(parent.parent_id); }
  return result;
};
function state(feature) {return states.get(feature.id)||{};}
function value(feature) { return levels.includes(mode) ? trail(feature).find(u=>u.level===mode)?.id : presentedAttribute(state(feature),mode).value; }
function categoryKey(feature) {return categoryPresentationKey(mode,presentedAttribute(state(feature),mode),value(feature));}
function color(feature) {return mode==='population'?populationColor(value(feature),maxPopulation):categoryColor(categoryKey(feature));}
function style(feature) { return { fillColor:color(feature), fillOpacity:mode==='owner'&&polities.length?0.12:0.87, color:feature.id===selected?'#fff9db':'#344f45', weight:feature.id===selected?2.5:0.45 }; }
function renderLegend() {
  $('#legend-title').textContent = labels[mode].toUpperCase();
  const categories = new Map(); let unknown = 0;
  let referenceContexts=0;
  for (const feature of data.features) { const v = value(feature),shown=presentedAttribute(state(feature),mode),key=categoryKey(feature); if (v == null) unknown++; else categories.set(key, levels.includes(mode) ? unitName(trail(feature).find(u=>u.id===v)) : v);if(v!=null&&shown.reference_context)referenceContexts++; }
  if(mode==='owner' && polities.length){categories.clear();polities.forEach(f=>categories.set(f.properties.name,f.properties.name));unknown=0;}
  $('#legend-count').textContent = mode==='population' ? 'LOG SCALE' : `${categories.size.toLocaleString()} ${levels.includes(mode)?'UNITS':'GROUPS'}`;
  if (mode==='population') $('#legend-items').innerHTML = `<div class="gradient"></div><div class="scale"><span>0</span><span>${maxPopulation.toLocaleString()}</span></div>`;
  else $('#legend-items').innerHTML = [...categories].sort((a,b)=>String(a[1]).localeCompare(String(b[1]))).slice(0,100).map(([key,name])=>`<div class="legend-item"><i style="background:${categoryColor(key)}"></i><span>${escape(name)}</span></div>`).join('') + (categories.size>100?'<div class="legend-item">First 100 shown · Select a region to inspect</div>':'');
  if (unknown) $('#legend-items').insertAdjacentHTML('beforeend', `<div class="legend-item unknown"><i style="background:#53615c"></i>Unknown <small>${unknown.toLocaleString()} locations</small></div>`);
  if (referenceContexts) $('#legend-items').insertAdjacentHTML('beforeend', `<div class="legend-item"><small>${referenceContexts.toLocaleString()} locations show reference context</small></div>`);
  if(mode==='owner' && polities.length) $('#legend-items').insertAdjacentHTML('beforeend','<div class="legend-item unknown">Gray land: no mapped polity</div>');
}
function renderHistory(feature){
  const e=feature.properties.temporal;
  const settlements=[...(temporal?.entities.values()||[])].filter(s=>s.kind==='settlement'&&s.parent_id===feature.id&&s.status!=='not_exists');
  const names=(temporal?.history||[]).filter(r=>r.entity_id===feature.id&&r.field==='name').sort((a,b)=>a.valid_from-b.valid_from);
  const links=(temporal?.links||[]).filter(r=>r.predecessor_id===feature.id||r.successor_id===feature.id);
  return `${e?.name_record?`<p class="record-source"><strong>Dated name:</strong> ${escape(e.name_record.source)}</p>`:''}
    ${settlements.length?`<div class="political-estimate"><strong>Settlements within this location</strong>${settlements.map(s=>`<p>${escape(s.display_name||s.reference_name||s.name||'Unnamed settlement')} · ${escape(s.attributes.rank||'Rank unknown')}${s.attributes.population!=null?` · ${s.attributes.population.toLocaleString()} people (settlement estimate)`:''}<br><small>${!s.display_name?`Reference name; no dated name covers this year.<br>`:''}${escape(s.attributes.source||'No dated settlement attributes')}${s.is_example?' · Illustrative example':''}</small></p>`).join('')}</div>`:''}
    ${names.length?`<section class="name-history"><h4>Recorded names over time</h4>${names.map(r=>`<p><strong>${escape(r.value)}</strong> · ${escape(r.language)} · ${escape(r.name_role)}<br>${formatYear(r.valid_from)} to before ${formatYear(r.valid_to)}${r.is_example?' · Example':''}<br><small>${escape(r.source)}</small></p>`).join('')}</section>`:''}
    ${links.length?`<div class="record-source"><strong>Identity changes</strong>${links.map(r=>`<p>${escape(r.kind)} · ${formatYear(r.year)}<br>${escape(temporal.entities.get(r.predecessor_id)?.name||r.predecessor_id)} → ${escape(temporal.entities.get(r.successor_id)?.name||r.successor_id)}<br>${escape(r.source)}</p>`).join('')}</div>`:''}`;
}
function renderDetails() {
  if (!selected) return;
  const feature = features.get(selected);
  if(!feature){$('#details').innerHTML=`<div class="detail-top"><span class="eyebrow">LOCATION PROFILE</span><button id="close-details" aria-label="Close location profile">×</button></div><div class="profile-main"><h3>Not present in this year</h3><div class="profile-year">${formatYear(year)}</div></div><details class="profile-evidence"><summary>Evidence & sources</summary><p>A sourced existence interval excludes this location. Its identity and history are retained.</p></details>`;$('#close-details').onclick=()=>{selected=null;$('#details').hidden=true;geoLayer.setStyle(style);};return;}
  const record = state(feature), boundary = boundaries.get(selected);
  const provenance=feature.properties.metadata || {}, chain=trail(feature);
  const reviewFile=provenance.semantic_review?.evidence_file==='geographic-decisions'?`geographic-decisions/${String(provenance.semantic_review.continent||'').toLowerCase().replaceAll(' ','-')}.json`:provenance.semantic_review?.evidence_file;
  const history=renderHistory(feature).trim(),profileKey=`${feature.id}:${year}`,sameProfile=$('#details').dataset.profileKey===profileKey,evidenceOpen=sameProfile&&$('#details .profile-evidence')?.open;
  const attributeLabel=key=>key==='owner'?'Owner':key==='culture'?'Primary culture':key==='religion'?'Primary religion':key==='habitation'?'Habitation':labels[key];
  const sourceLink=(source,url)=>url&&/^https?:\/\//i.test(url)?`<a href="${escape(url)}" target="_blank" rel="noreferrer">${escape(source)}</a>`:escape(source);
  const hierarchyContext='Geographic hierarchy';
  const nameContext=`Present-day reference: ${feature.properties.name}`;
  const sourceQuality=referenceData.sourceQualityReviews?.[feature.id];
  $('#details').innerHTML = `<div class="detail-top"><span class="eyebrow">LOCATION PROFILE</span><button id="close-details" aria-label="Close location profile">×</button></div>
    <div class="profile-main"><h3>${escape(displayName(feature))}</h3>${nameContext?`<div class="profile-name-context">${escape(nameContext)}</div>`:''}<div class="profile-year">${formatYear(year)}</div>
    <div class="profile-subheading">${hierarchyContext}</div><div class="breadcrumbs" aria-label="${hierarchyContext}">${[...levels].reverse().map(level=>{const u=chain.find(u=>u.level===level);return `<button data-unit="${escape(u.id)}"><small>${u.level}</small><span>${escape(u.display_name||u.name)}</span></button>`;}).join('')}</div>
    <dl class="profile-attributes">${attributes.map(key=>{const shown=presentedAttribute(record,key);return `<div><dt>${attributeLabel(key)}</dt><dd>${shown.value==null?'<span class="muted">Unknown</span>':escape(key==='population'?shown.value.toLocaleString():shown.value)}${shown.reference_context&&shown.value!=null?'<small class="reference-badge">Reference</small>':''}</dd></div>`;}).join('')}</dl></div>
    <details class="profile-evidence"${evidenceOpen?' open':''}><summary>Evidence & sources</summary><div class="profile-evidence-content">
    <section><h4>Geography</h4>${sourceQuality?`<p><strong>Reference source under review:</strong> ${escape(sourceQuality.summary)} ${escape(sourceQuality.individual_correspondence||'')}${(sourceQuality.public_evidence_files??[]).filter(file=>/^[\w./-]+$/.test(file.path)&&!file.path.split('/').includes('..')).map(file=>`<br><a href="./${escape(file.path)}" download>${escape(file.title)}</a>`).join('')}</p>`:''}${year!==2026&&!feature.properties.temporal?.display_name?`<p>No dated location name covers ${formatYear(year)}; the reference name ${escape(feature.properties.name)} is shown.</p>`:''}<p>${year===2026?'Reference parent chain.':feature.properties.temporal?.parent_record||chain.some(u=>u.parent_record)?'Includes sourced membership for the selected year; other parent links use reference geography.':`Reference parent chain; historical membership for ${formatYear(year)} is unknown.`}</p>
    ${referenceData.pixelMissing?.includes(feature.id)?'<p>This sourced territory currently has no interior pixel at the fixed resolution. Its geographic identity and records remain available; grid representation is awaiting review.</p>':''}
    ${chain.some(u=>u.metadata?.kind==='whole_territory')?'<p>A whole-territory group uses the named source territory at this atlas level. Adjacent levels may share a footprint; this is not a separate administrative division.</p>':''}
    <p><strong>Boundary:</strong> ${sourceLink(boundary?boundary.source:`${provenance.source_name||'Reference'} · ${provenance.administrative_level||''}`,boundary?.source_url||provenance.source_url)}${provenance.topology_reconciled?'<br><strong>Display boundary:</strong> Reconciled shared coverage; original source geometry may differ.':''}${provenance.location_basis?`<br><strong>Location basis:</strong> ${escape(provenance.location_basis)}`:''}${provenance.scale_review?`<br><strong>Scale review:</strong> ${escape(provenance.scale_review.decision)}`:''}<br><strong>Source date:</strong> ${escape(provenance.reference_year||'Unknown')}<br><strong>Parent match:</strong> ${escape(provenance.parent_match||'Source geography')}<br><strong>License:</strong> ${escape(provenance.license||'See source')}</p>
    ${chain.filter(u=>u.metadata?.review_reasons?.length||u.metadata?.semantic_review?.rationale).map(u=>{const m=u.metadata,review=m.semantic_review;return `<p><strong>${escape(u.name)} review:</strong> ${escape(review?.rationale||m.review_reasons.join('; '))}${review?.remaining_reasons?.length?`<br>${review.remaining_reasons.map(escape).join('; ')}`:''}${review?.evidence?.length?`<br>${review.evidence.map(e=>`${sourceLink(e.title||'Geographic review source',e.url)}${e.inspected_fact?`<br><small>${escape(e.inspected_fact)}</small>`:''}`).join('<br>')}`:''}<br>${escape(m.basis||'')}<br>Original source: ${sourceLink(m.source||'Reference geography',m.source_url)}</p>`;}).join('')}
    ${reviewFile&&/^[\w./-]+\.json(?:\.gz)?$/.test(reviewFile)?`<p><a href="./${escape(reviewFile.replace(/\.gz$/,'')+'.gz')}" target="_blank" rel="noreferrer">Full location geographic review</a></p>`:''}
    <p>Geographic groups are independent of political ownership. Dated membership is used where supplied; otherwise this is reference geography.</p></section>
    <section><h4>Attributes</h4><p class="record-tag">${record.is_example?'ILLUSTRATIVE EXAMPLE ATTRIBUTES':record.reference?'MODERN REFERENCE':record.provenance?.owner?.method==='majority-area'?'DERIVED OWNERSHIP':record.source?'SOURCED RECORD':'NO DATED RECORD'}</p><p>${escape(record.source||'No location-level attribute record covers this year.')}</p><p><strong>Habitation:</strong> ${escape(record.habitation||'Unknown')}</p>
    ${[...attributes,'habitation'].map(key=>{const p=presentedAttribute(record,key).provenance||{},m=p.metadata||{},url=p.source_url||m.source_url;return `<p><strong>${escape(attributeLabel(key))}</strong> · ${escape(p.status||'unknown')}<br>${sourceLink(p.source||'No supported record',url)}${p.valid_from!=null?`<br>${formatYear(p.valid_from)}${p.valid_to!=null?` to before ${formatYear(p.valid_to)}`:' onward'}`:''}${p.context_only?'<br>Reference context; the historical state for this year remains unknown.':''}${p.method?`<br>Method: ${escape(p.method)}`:''}${Array.isArray(m.normal_period)?`<br>Climate normal: ${escape(m.normal_period.join('–'))}`:''}${m.note?`<br>${escape(m.note)}`:''}${p.metadata_truncated||p.source_metadata_truncated?`<br><a href="/api/evidence/records/${encodeURIComponent(p.id)}" target="_blank" rel="noreferrer">Full evidence</a>`:''}${m.share!=null?`<br>Dominant source share: ${(m.share*100).toFixed(1)}%${key==='owner'?' of location land':''}`:''}${m.coverage!=null?`<br>Source coverage: ${(m.coverage*100).toFixed(1)}% of location land`:''}${key==='owner'&&p.method==='majority-area'?`<br>Assignment requires more than 50% of the entire location. Contradictory claims remain unresolved.${m.candidates?.length>1?`<br>Candidate land shares: ${m.candidates.map(([,share])=>(share*100).toFixed(1)+'%').join(', ')}`:''}${m.source_record_ids?.length?`<br>${m.source_record_ids.length} dated source ${m.source_record_ids.length===1?'boundary':'boundaries'} considered.`:''}`:''}${p.uncertainty||m.uncertainty?`<br>Uncertainty: ${escape(p.uncertainty||m.uncertainty)}`:''}${m.precision?`<br>Precision: ${escape(m.precision)}`:''}</p>`;}).join('')}</section>
    ${history?`<section><h4>Names, settlements & identity</h4>${history}</section>`:''}</div></details>`;
  $('#details').dataset.profileKey=profileKey;if(!sameProfile)$('#details').scrollTop=0;
  $('#close-details').onclick = () => { selected=null; $('#details').hidden=true; geoLayer.setStyle(style); };
  document.querySelectorAll('[data-unit]').forEach(button => button.onclick = () => {
    const unit = trail(feature).find(u=>u.id===button.dataset.unit); setMode(unit.level);
    const bounds = L.latLngBounds([]);
    data.features.filter(f=>trail(f).some(u=>u.id===unit.id)).forEach(f=>bounds.extend(layers.get(f.id).getBounds()));
    map.fitBounds(bounds, {padding:[35,35], maxZoom:10});
  });
}
function select(id, zoom = false) {
  if (!features.has(id)) return;
  selected=id; $('#details').hidden=false; renderDetails(); geoLayer.setStyle(style);
  layers.get(id)?.bringToFront();
  if (zoom) map.fitBounds(layers.get(id).getBounds(), {padding:[60,60], maxZoom:13});
}
function rebuildGeometry() {
  if (geoLayer) map.removeLayer(geoLayer);
  geoLayer=new PixelLayer(data.features.map(f=>({...f,geometry:boundaries.get(f.id)?.geometry || f.geometry})),{
    ownership:!boundaries.size&&data.features.length===referenceData.features.length?referenceData.ownership:null,
    color,selected:()=>selected,select:id=>select(id),locationBorders:()=>true,
    politicalColor:f=>categoryColor(f.properties.name),
    borderKey:f=>mode==='owner'?(state(f).category_ids?.owner??null):['area','region','subcontinent','continent'].includes(mode)?value(f):null,
    label:displayName
  }).addTo(map);
  layers=new Map(geoLayer.index.map(item=>[item.feature.id,{
    getBounds:()=>L.latLngBounds(map.unproject(L.point(item.bounds[0],item.bounds[1]),GRID_ZOOM),map.unproject(L.point(item.bounds[2],item.bounds[3]),GRID_ZOOM)),
    bringToFront(){}
  }]));
}
function render() {
  geoLayer.setPolitical(emptyPolities);
  maxPopulation = Math.max(0, ...[...states.values()].map(s=>s.population ?? 0));
  geoLayer.setStyle(style); renderLegend(); renderDetails();
  $('#map-title').textContent = mode==='owner'?'The political world':`${labels[mode]} of the world`;
  $('#map-year').textContent = formatYear(year);
  const exampleCount = [...states.values()].filter(s=>s.is_example).length;
  $('#coverage').textContent = `${data.features.length.toLocaleString()} geographic locations · ${[...states.values()].filter(s=>s.owner!=null).length.toLocaleString()} locations with ownership${exampleCount?` · ${exampleCount} example records`:''}${year===2026?' · Modern ownership reference':''}`;
  $('#map-note').textContent = boundaries.size?`${boundaries.size} dated local boundaries · Others are modern reference`:mode==='owner'?'Whole-location ownership · Fixed pixel grid':'Geographic regions · Thin local borders, bold parent borders';
}
function setMode(next) {
  mode=next; document.querySelectorAll('[data-mode]').forEach(b=>{b.classList.toggle('active',b.dataset.mode===mode); b.setAttribute('aria-pressed',String(b.dataset.mode===mode));});
  if (data) render();
}
async function loadYear(next) {
  desiredYear=next; clearTimeout(timer); controller?.abort(); controller=new AbortController();
  $('#year-input').value=formatYear(next).replaceAll(',',''); $('#year-slider').value=yearToTick(next); $('#year-slider').setAttribute('aria-valuetext',formatYear(next)); $('#year-error').textContent='';
  if (!data) return;
  const signal=controller.signal;
  $('#loading').hidden=false; $('#loading').textContent=`Loading ${formatYear(next)}…`;
  try {
    const result=await loadSnapshot(next, $('#examples').checked, signal);
    const temporalReference=result.evidenceUnavailable?{...referenceData,temporal:{...referenceData.temporal,history:[]}}:result.temporalHistoryComplete?{...referenceData,temporal:{...referenceData.temporal,history:result.temporal_history}}:result.temporal_history?.length?{...referenceData,temporal:{...referenceData.temporal,history:[...(referenceData.temporal.history||[]),...result.temporal_history]}}:referenceData;
    let resolved=resolveTemporal(temporalReference,next,$('#examples').checked);
    if(result.boundaries.length||resolved.features.length!==referenceData.features.length){await ensureGeometry(referenceData,signal);resolved=resolveTemporal(temporalReference,next,$('#examples').checked);}
    signal.throwIfAborted();year=next;temporal=resolved;
    const previousFeatures=data.features;
    data={...referenceData,units:temporal.units,features:temporal.features};
    parents=new Map(data.units.map(u=>[u.id,u]));features=new Map(data.features.map(f=>[f.id,f]));
    for(const e of temporal.entities.values())if(e.kind==='settlement'&&features.has(e.parent_id)){const p=features.get(e.parent_id).properties;p.settlement_search=[...(p.settlement_search||[]),...e.search_names];}
    polities=[];
    states=resolveAttributes(data.features,year,{states:result.states,records:result.attributes||[],temporal,examples:$('#examples').checked,evidenceAvailable:!result.evidenceUnavailable,referenceBaselines:result.referenceBaselines||[],referenceContexts:result.referenceContexts});
    const nextBoundaries=new Map(result.boundaries.map(b=>[b.location_id,b]));
    const changed=boundaryFootprintsChanged(boundaries,nextBoundaries)||locationInventoryChanged(previousFeatures,data.features);
    boundaries=nextBoundaries;
    if(changed)rebuildGeometry();
    else geoLayer.updateMetadata(data.features);
    $('#results').innerHTML='';
    render(); $('#loading').hidden=true;
    if(result.storage&&!result.storage.available)$('#year-error').textContent=result.evidenceUnavailable?'Historical content could not load. Dated attribute values are unavailable; labeled reference context and geography remain browsable. Select the year again to retry.':'Historical content could not refresh. Showing the last complete snapshot for this year. Select the year again to retry.';
  } catch(error) { if (error.name!=='AbortError') { $('#loading').textContent='Could not load this year. Submit the year again to retry.'; $('#year-error').textContent='Map unavailable. Check the server connection and retry.'; } }
}
$('#year-form').onsubmit = event => { event.preventDefault(); const next=parseYear($('#year-input').value); if (next===null) $('#year-error').textContent='Enter a year from 3000 BC to 2026 AD. There is no year zero.'; else loadYear(next); };
$('#year-slider').oninput = event => { desiredYear=tickToYear(Number(event.target.value)); $('#year-input').value=formatYear(desiredYear).replaceAll(',',''); event.target.setAttribute('aria-valuetext',formatYear(desiredYear)); clearTimeout(timer); controller?.abort(); timer=setTimeout(()=>loadYear(desiredYear),100); };
$('#previous').onclick = () => loadYear(tickToYear(Math.max(0,yearToTick(desiredYear)-1)));
$('#next').onclick = () => loadYear(tickToYear(Math.min(5025,yearToTick(desiredYear)+1)));
document.querySelectorAll('[data-year]').forEach(b=>b.onclick=()=>loadYear(Number(b.dataset.year)));
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
$('#examples').onchange = ()=>loadYear(desiredYear);
$('#example-tour').onclick = async () => { $('#examples').checked=true; await loadYear(1444); select('atlas:city:GBR-Greater London'); map.fitBounds([[35,-13],[60,35]],{padding:[15,15]}); };
$('#home').onclick = ()=>map.fitBounds(worldBounds);
$('#zoom-in').onclick = ()=>map.zoomIn(); $('#zoom-out').onclick = ()=>map.zoomOut();
$('#london').onclick = ()=>select('atlas:city:GBR-Greater London',true);
$('#about').onclick = ()=>$('#data-dialog').showModal(); $('#close-dialog').onclick = ()=>$('#data-dialog').close();
$('#search').oninput = event => {
  const query=event.target.value.trim().toLocaleLowerCase();
  const matches=query&&data?data.features.filter(f=>`${f.properties.name} ${f.properties.reference_owner} ${(f.properties.temporal?.search_names || []).join(' ')} ${(f.properties.metadata?.search_aliases || []).join(' ')} ${(f.properties.settlement_search || []).join(' ')}`.toLocaleLowerCase().includes(query)).slice(0,20):[];
  $('#results').innerHTML=matches.map(f=>`<button data-result="${escape(f.id)}">${escape(displayName(f))}<small>${escape(f.properties.reference_owner || '')}</small></button>`).join('') || (query?'<p>No matching locations.</p>':'');
  document.querySelectorAll('[data-result]').forEach(b=>b.onclick=()=>{select(b.dataset.result,true); $('#results').innerHTML='';});
};
async function start() {
  try {
    data=await loadGeography({year:desiredYear,examples:$('#examples').checked});referenceData=data; $('#framework-status').textContent=`Framework research in progress: ${data.units.filter(u=>u.metadata?.review_reasons?.length).length.toLocaleString()} geographic groups have open review notes. Complete parent chains do not mean every grouping is semantically verified.`; parents=new Map(data.units.map(u=>[u.id,u])); features=new Map(data.features.map(f=>[f.id,f]));
    rebuildGeometry(); await loadYear(desiredYear);
  } catch { $('#loading').textContent='Atlas could not load. Check the server and reload the page.'; }
}
installCoverage(()=>({data,states,year,parents}));
installRecordImport({getContext:()=>({year,selected,feature:features.get(selected)}),refresh:async()=>{await loadYear(desiredYear);if($('#year-error').textContent)throw Error('Map refresh failed');}});
start();
