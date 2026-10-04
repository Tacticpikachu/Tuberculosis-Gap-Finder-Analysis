TB.nav("explore");
const METRICS = {
  smoothed_rate: { label: "Reported TB rate", badge: ["real", "REAL"], unit: " /100k", note: "Empirical Bayes-smoothed notification rate per 100,000 (bulletins, DOSM population)." },
  gap: { label: "Hidden gap", badge: ["est", "EST"], unit: " /100k", note: "Expected minus reported rate. Score B currently shares the WHO estimate by population only." },
  desert_level: { label: "Diagnostic desert", badge: ["est", "EST"], cat: { strong: "#e11d48", possible: "#f59e0b", none: "#cbd5e1" },
                  note: "Points: low-high cluster + gap above median + travel above median. 3 = strong, 2 = possible." },
  moran_quadrant: { label: "Clustering", badge: ["exp", "EXP"], cat: { HH: "#e11d48", LH: "#7c3aed", LL: "#0ea5e9", HL: "#f59e0b" },
                    note: "Local Moran's I quadrant. Exploratory: only 10 districts. HH = high near high, LH = low near high." },
};
const RAMP = ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"];
let S, GEO, GRID, map, layer, metric = "smoothed_rate", selected;

const ramp = (v, lo, hi) => v == null ? "#e5e7eb" : RAMP[Math.min(RAMP.length - 1, Math.floor((v - lo) / ((hi - lo) || 1) * RAMP.length))];
const byCode = (c) => S.districts.find((d) => d.code === c);

function panel(d) {
  const row = (k, v, b) => `<div class="kv"><span>${k} ${b ? `<span class="badge ${b[0]}">${b[1]}</span>` : ""}</span><b>${v}</b></div>`;
  const act = { "portable X-ray unit": "Send a portable X-ray unit", "trusted-messenger campaign": "Run a trusted-messenger campaign", monitor: "Monitor" };
  document.getElementById("dpanel").innerHTML = `
    <div style="font-size:1.5rem;font-weight:800;letter-spacing:-.02em">${d.district}</div>
    <div style="margin:8px 0 10px;padding:10px 12px;border-radius:12px;background:var(--bg);font-weight:700">${act[d.action] || TB.fmt(d.action)}</div>
    ${row("Reported rate", TB.fmt(d.smoothed_rate, 1, " /100k"), ["real", "REAL"])}
    ${row("TB cases " + S.year, TB.fmt(d.cases, 0), ["real", "REAL"])}
    ${row("Expected rate", TB.fmt(d.expected_rate, 1, " /100k"), ["est", "EST"])}
    ${row("Hidden gap", TB.fmt(d.gap, 1, " /100k"), ["est", "EST"])}
    ${row("Travel to clinic", TB.fmt(d.travel_min_approx, 1, " min"), ["est", "≈"])}
    ${row("Clustering", d.moran_quadrant ? `${d.moran_quadrant} (p ${TB.fmt(d.moran_p, 2)})` : "No data", ["exp", "EXP"])}
    ${row("Desert points", d.desert_points == null ? "No data" : `${d.desert_points} / 3`, ["est", "EST"])}
    <p style="font-size:12px;color:var(--muted);margin:10px 0 0">Sources: Johor epidemiological bulletins, DOSM, WHO, OpenStreetMap, WorldPop.</p>`;
}

function style(f) {
  const d = byCode(f.properties.code), m = METRICS[metric];
  let fill;
  if (m.cat) fill = m.cat[d[metric]] || "#e5e7eb";
  else { const vs = S.districts.map((x) => x[metric]).filter((x) => x != null); fill = ramp(d[metric], Math.min(...vs), Math.max(...vs)); }
  const on = selected === d.code;
  return { fillColor: fill, fillOpacity: .82, color: on ? TB.css("--ink") : "#ffffff", weight: on ? 4 : 1.2 };
}

let legend;
function drawLegend() {
  if (legend) legend.remove();
  legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "legend"), m = METRICS[metric];
    if (m.cat) div.innerHTML = `<b>${m.label}</b><br>` + Object.entries(m.cat).map(([k, c]) => `<i style="background:${c}"></i>${k}`).join("<br>");
    else {
      const vs = S.districts.map((x) => x[metric]).filter((x) => x != null), lo = Math.min(...vs), hi = Math.max(...vs);
      div.innerHTML = `<b>${m.label}</b><br>` + RAMP.map((c, i) => `<i style="background:${c}"></i>${(lo + (hi - lo) * i / RAMP.length).toFixed(0)}+`).join("<br>");
    }
    return div;
  };
  legend.addTo(map);
}

function select(code, fly = true) {
  selected = code; document.getElementById("dsel").value = code;
  panel(byCode(code)); layer.setStyle(style);
  if (fly) layer.eachLayer((l) => { if (l.feature.properties.code === code) map.flyToBounds(l.getBounds(), { padding: [60, 60], duration: .8 }); });
}

// No third-party tile service (no API keys): districts are drawn directly on a plain background.
function tiles(m) {
  m.attributionControl.setPrefix(false);
  m.attributionControl.addAttribution("Borders: geoBoundaries · Clinics: © OpenStreetMap contributors · Population: WorldPop");
  return { remove() {} };
}

function initMap() {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: true, zoomSnap: 0.25, minZoom: 7, maxZoom: 13 });
  let t = tiles(map);
  window.addEventListener("themechange", () => { t.remove(); t = tiles(map); });
  layer = L.geoJSON(GEO, {
    style,
    onEachFeature: (f, l) => {
      const d = byCode(f.properties.code);
      l.bindTooltip(() => `<b>${d.district}</b><br>${METRICS[metric].label}: ${METRICS[metric].cat ? (d[metric] || "No data") : TB.fmt(d[metric], 1, METRICS[metric].unit)}`, { sticky: true });
      l.on({ click: () => select(d.code), mouseover: (e) => e.target.setStyle({ fillOpacity: .95 }), mouseout: () => layer.setStyle(style) });
    },
  }).addTo(map);
  map.fitBounds(layer.getBounds(), { padding: [10, 10] });
  const seg = document.getElementById("metric");
  seg.innerHTML = Object.entries(METRICS).map(([k, m]) => `<button data-k="${k}" class="${k === metric ? "on" : ""}">${m.label} <span class="badge ${m.badge[0]}">${m.badge[1]}</span></button>`).join("");
  seg.onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    metric = b.dataset.k; seg.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    layer.setStyle(style); drawLegend(); document.getElementById("mnote").textContent = METRICS[metric].note;
  };
  document.getElementById("mnote").textContent = METRICS[metric].note;
  drawLegend();
  const sel = document.getElementById("dsel");
  sel.innerHTML = [...S.districts].sort((a, b) => a.district.localeCompare(b.district)).map((d) => `<option value="${d.code}">${d.district}</option>`).join("");
  sel.onchange = () => select(sel.value);
  const strongest = [...S.districts].sort((a, b) => (b.desert_points || 0) - (a.desert_points || 0))[0];
  select(strongest.code, false);
}

/* ---------------- planner ---------------- */
let pmap, mode = "auto", target = "expected_tb", custom = new Set(), pLayer, facLayer;
const COVER = () => S.cover_km;
const coverOf = (ids) => {
  const fac = ids.map((id) => S.facilities.find((f) => f[0] === id)).filter(Boolean);
  let exp = 0, pop = 0;
  const covered = new Array(GRID.cells.length).fill(false);
  GRID.cells.forEach((c, i) => { if (fac.some((f) => TB.hav(c[0], c[1], f[4], f[5]) <= COVER())) { covered[i] = true; exp += c[3]; pop += c[2]; } });
  return { exp, pop, covered, fac };
};
const TOTAL_EXP = () => GRID.cells.reduce((a, c) => a + c[3], 0);

function marginal(ids) {
  const out = []; let prev = { exp: 0 };
  ids.forEach((_, i) => { const cur = coverOf(ids.slice(0, i + 1)); out.push(cur.exp - prev.exp); prev = cur; });
  return out;
}

function renderPlan() {
  const n = +document.getElementById("n").value;
  document.getElementById("nval").textContent = n;
  const ids = mode === "auto"
    ? S.siting.filter((r) => r.version === target && r.n_units <= n).sort((a, b) => a.n_units - b.n_units).map((r) => r.osm_id)
    : [...custom];
  const c = coverOf(ids), tot = TOTAL_EXP();
  if (mode === "auto") {  // show the analysis' exact 1 km results for recommended plans
    const r = S.siting.find((x) => x.version === target && x.n_units === n);
    if (r) { c.exp = r.covered_expected_cases; c.pop = r.covered_pop; }
  }
  const pct = tot ? c.exp / tot * 100 : 0;
  TB.count(document.getElementById("p-exp"), c.exp, 0, 600);
  document.getElementById("p-pop").textContent = Math.round(c.pop).toLocaleString();
  document.getElementById("p-pct").textContent = `${pct.toFixed(1)}% of Johor's expected TB · ${ids.length} unit${ids.length === 1 ? "" : "s"}`;
  document.getElementById("p-bar").style.width = `${pct}%`;
  const k = Math.max(1, Math.min(5, ids.length));
  const rec = S.siting.filter((r) => r.version === "expected_tb" && r.n_units <= k).map((r) => r.osm_id);
  const best = rec.length ? coverOf(rec).exp : null;  // same 5 km grid as the user's plan
  document.getElementById("p-cmp").innerHTML = ids.length && best !== null
    ? `Recommended plan with ${k} unit${k > 1 ? "s" : ""}: <b>${Math.round(best).toLocaleString()}</b> expected TB. ` +
      (mode === "custom" ? (c.exp >= best - 0.5 ? "Your plan matches or beats it." : `Your plan reaches <b>${Math.round(best - c.exp).toLocaleString()}</b> fewer.`) : "")
    : (mode === "custom" ? "Pick sites from the list or the map." : "");

  if (pLayer) pLayer.remove();
  pLayer = L.layerGroup().addTo(pmap);
  GRID.cells.forEach((cell, i) => {
    if (!c.covered[i]) return;
    const h = GRID.deg / 2;
    L.rectangle([[cell[0] - h, cell[1] - h], [cell[0] + h, cell[1] + h]], { interactive: false, stroke: false, fillColor: "#2f7a5f", fillOpacity: Math.min(.55, .08 + cell[3] / 12) }).addTo(pLayer);
  });
  const adds = marginal(ids);
  c.fac.forEach((f, i) => {
    L.circle([f[4], f[5]], { interactive: false, radius: COVER() * 1000, color: "#c97f10", weight: 1.5, fillOpacity: 0, dashArray: "6 6" }).addTo(pLayer);
    L.marker([f[4], f[5]], { icon: L.divIcon({ className: "", html: `<div style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#1c4a3a,#2f7a5f);color:#fff;display:grid;place-items:center;font-weight:800;box-shadow:0 4px 12px rgba(28,74,58,.45);border:2px solid #fff">${i + 1}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] }) })
      .bindTooltip(`<b>${f[1]}</b><br>${f[2]} · adds ${Math.round(adds[i])} expected TB`).addTo(pLayer);
  });
  document.getElementById("ptable").innerHTML = c.fac.map((f, i) => {
    const d = f[3] ? byCode(f[3]) : null;
    return `<tr><td>${i + 1}</td><td>${f[1]}</td><td>${f[2]}</td><td>${d ? d.district : "–"}</td><td>${Math.round(adds[i]).toLocaleString()}</td></tr>`;
  }).join("") || `<tr><td colspan="5" style="color:var(--muted)">No sites selected.</td></tr>`;
  facLayer.eachLayer((m) => { m.setStyle({ fillColor: custom.has(m.options.fid) ? "#1c4a3a" : "#a8a290" }); m.setRadius(custom.has(m.options.fid) ? 7 : 4); });
  renderChips();
}

function renderList() {
  const q = document.getElementById("q").value.toLowerCase();
  const items = S.facilities.filter((f) => !q || f[1].toLowerCase().includes(q) || (f[3] && byCode(f[3]).district.toLowerCase().includes(q))).slice(0, 80);
  document.getElementById("flist").innerHTML = items.map((f) =>
    `<label><input type="checkbox" data-id="${f[0]}" ${custom.has(f[0]) ? "checked" : ""}> <span>${f[1]} <span style="color:var(--muted)">· ${f[2]}${f[3] ? " · " + byCode(f[3]).district : ""}</span></span></label>`).join("");
}
function renderChips() {
  document.getElementById("chips").innerHTML = [...custom].map((id) => `<span class="chip" data-id="${id}">${S.facilities.find((f) => f[0] === id)[1]} ×</span>`).join("");
}
function toggle(id) { custom.has(id) ? custom.delete(id) : custom.add(id); renderList(); renderPlan(); }

function initPlanner() {
  pmap = L.map("pmap", { scrollWheelZoom: true, zoomSnap: 0.25, minZoom: 7, maxZoom: 13 });
  let t = tiles(pmap);
  window.addEventListener("themechange", () => { t.remove(); t = tiles(pmap); });
  const outline = L.geoJSON(GEO, { interactive: false, style: () => ({ color: TB.css("--line-strong"), weight: 1.2, fillColor: TB.css("--surface"), fillOpacity: 1 }) }).addTo(pmap);
  pmap.fitBounds(outline.getBounds());
  pmap.createPane("fac"); pmap.getPane("fac").style.zIndex = 450;  // clinic dots above coverage shading
  facLayer = L.layerGroup(S.facilities.map((f) => L.circleMarker([f[4], f[5]], { pane: "fac", fid: f[0], radius: 4, weight: 1, color: "#fff", fillColor: "#a8a290", fillOpacity: .95 })
    .bindTooltip(`${f[1]} · ${f[2]}`).on("click", () => { if (mode !== "custom") setMode("custom"); toggle(f[0]); }))).addTo(pmap);
  document.getElementById("n").oninput = renderPlan;
  const seg = (a, b, fn) => { document.getElementById(a).onclick = () => fn(a); document.getElementById(b).onclick = () => fn(b); };
  seg("s-tb", "s-pop", (id) => { target = id === "s-tb" ? "expected_tb" : "population_only";
    document.getElementById("s-tb").classList.toggle("on", id === "s-tb"); document.getElementById("s-pop").classList.toggle("on", id === "s-pop"); renderPlan(); });
  seg("m-auto", "m-custom", (id) => setMode(id === "m-auto" ? "auto" : "custom"));
  document.getElementById("q").oninput = renderList;
  document.getElementById("flist").onchange = (e) => toggle(e.target.dataset.id);
  document.getElementById("chips").onclick = (e) => { const c = e.target.closest(".chip"); if (c) toggle(c.dataset.id); };
  renderList(); renderPlan();
}
function setMode(m) {
  mode = m;
  document.getElementById("m-auto").classList.toggle("on", m === "auto");
  document.getElementById("m-custom").classList.toggle("on", m === "custom");
  document.getElementById("auto-ui").classList.toggle("hidden", m !== "auto");
  document.getElementById("custom-ui").classList.toggle("hidden", m !== "custom");
  if (m === "custom" && !custom.size) S.siting.filter((r) => r.version === "expected_tb" && r.n_units <= 2).forEach((r) => custom.add(r.osm_id));
  renderList(); renderPlan();
}

function view(v) {
  document.getElementById("v-map").classList.toggle("hidden", v !== "map");
  document.getElementById("v-plan").classList.toggle("hidden", v !== "plan");
  document.getElementById("t-map").classList.toggle("on", v === "map");
  document.getElementById("t-plan").classList.toggle("on", v === "plan");
  if (v === "plan" && !pmap) initPlanner();
  setTimeout(() => (v === "plan" ? pmap : map).invalidateSize(), 50);
  history.replaceState(null, "", v === "plan" ? "#planner" : "#map");
}

TB.load().then(({ site, geo, grid }) => {
  S = site; GEO = geo; GRID = grid;
  initMap();
  document.getElementById("t-map").onclick = () => view("map");
  document.getElementById("t-plan").onclick = () => view("plan");
  if (location.hash === "#planner") view("plan");
}).catch((e) => { document.getElementById("map").innerHTML = `<p style="padding:20px">Could not load data (${e.message}).</p>`; });
