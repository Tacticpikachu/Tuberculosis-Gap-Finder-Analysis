// Shared: nav, theme toggle, scroll reveal, count-up, data loader
const TB = {};
TB.nav = (active) => {
  const el = document.getElementById("nav");
  el.innerHTML = `<div class="wrap">
    <a class="logo" href="index.html"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="30" height="30" role="img" aria-label="TB Gap Finder">
  <rect width="64" height="64" rx="16" fill="#1c4a3a"/>
  <path d="M32 12v17" stroke="#f6f4ea" stroke-width="3.4" stroke-linecap="round"/>
  <path d="M32 26c-2 3-5 4-7 4" stroke="#f6f4ea" stroke-width="2.6" stroke-linecap="round" fill="none"/>
  <path d="M32 26c2 3 5 4 7 4" stroke="#f6f4ea" stroke-width="2.6" stroke-linecap="round" fill="none"/>
  <path d="M27.5 23.5c-3.2-3.6-8.6-4.6-11.3-.9-3.6 4.9-4.6 14.6-2.8 20.9 1.1 3.9 4.8 5.6 8.5 3.8 3.9-1.9 5.6-5.6 5.6-10.6z" fill="#f6f4ea"/>
  <path d="M36.5 23.5c3.2-3.6 8.6-4.6 11.3-.9 3.6 4.9 4.6 14.6 2.8 20.9-1.1 3.9-4.8 5.6-8.5 3.8-3.9-1.9-5.6-5.6-5.6-10.6z" fill="#f6f4ea" fill-opacity=".45"/>
  <circle cx="43.5" cy="38" r="5.6" fill="none" stroke="#c97f10" stroke-width="2"/>
  <circle cx="43.5" cy="38" r="2.4" fill="#c97f10"/>
</svg><span class="t">TB Gap Finder</span></a>
    <div class="links">
      <a href="index.html" class="${active === "home" ? "active" : ""}">Home</a>
      <a href="explore.html" class="${active === "explore" ? "active" : ""}">Explore</a>
      <a href="method.html" class="${active === "method" ? "active" : ""}">Method</a>
      <button class="theme" id="theme" title="Toggle theme" aria-label="Toggle theme"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></button>
      <a href="explore.html#planner" class="pill">Plan X-ray units</a>
    </div></div>`;
  try { const t = localStorage.getItem("tb-theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
  document.getElementById("theme").onclick = () => {
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const cur = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("tb-theme", next); } catch (e) {}
    window.dispatchEvent(new Event("themechange"));
  };
};
TB.reveal = () => {
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); e.target.dispatchEvent(new Event("revealed")); }
  }), { threshold: 0.15 });
  document.querySelectorAll(".reveal").forEach((n) => io.observe(n));
};
TB.count = (el, to, dec = 0, ms = 1400) => {
  const t0 = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - p, 3);
    el.textContent = (to * e).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec });
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
};
TB.load = async () => {
  const [site, geo, grid] = await Promise.all(["data/site.json", "data/districts.geojson", "data/grid.json"]
    .map((u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); })));
  return { site, geo, grid };
};
TB.fmt = (v, d = 1, unit = "") => (v === null || v === undefined || Number.isNaN(v)) ? "No data"
  : (typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d }) + unit : String(v));
TB.hav = (la1, lo1, la2, lo2) => {
  const r = Math.PI / 180, a = Math.sin((la2 - la1) * r / 2) ** 2 + Math.cos(la1 * r) * Math.cos(la2 * r) * Math.sin((lo2 - lo1) * r / 2) ** 2;
  return 2 * 6371.0088 * Math.asin(Math.sqrt(a));
};
TB.css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
