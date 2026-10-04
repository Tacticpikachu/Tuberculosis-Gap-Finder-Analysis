// Shared: nav, theme toggle, scroll reveal, count-up, data loader
const TB = {};
TB.nav = (active) => {
  const el = document.getElementById("nav");
  el.innerHTML = `<div class="wrap">
    <a class="logo" href="index.html"><span class="dot">TB</span><span class="t">TB Gap Finder</span></a>
    <div class="links">
      <a href="index.html" class="${active === "home" ? "active" : ""}">Home</a>
      <a href="explore.html" class="${active === "explore" ? "active" : ""}">Explore</a>
      <a href="method.html" class="${active === "method" ? "active" : ""}">Method</a>
      <button class="theme" id="theme" title="Toggle theme" aria-label="Toggle theme">◐</button>
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
