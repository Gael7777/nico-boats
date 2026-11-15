/* Nico Boats live table: vanilla JS, no build step. Data: data/listings.json (fetch) or data/listings.js (file:// fallback). */
(function () {
  "use strict";
  const NA = "N/A";
  const CATS = { sail: ["Sailboats", "#1A9E9A", "⛵"], open: ["Open boats & day-cruisers", "#F08A24", "🚤"], motor: ["Motorboats (cabin)", "#0B1F3A", "🛥️"],
    inflatable: ["Inflatables & RIBs", "#7B5EA7", "🛟"], small: ["Dinghies, rowing & small", "#2E9E5B", "🛶"], other: ["Other", "#9AA5B1", "⚓"] };
  const SRC = { tutti: "tutti.ch", anibis: "anibis.ch", bateau24: "boat24" };
  const COLS = [
    ["thumb_url", "Photo", true], ["title", "Boat", true], ["category", "Category", true], ["price_chf", "Price CHF", true],
    ["distance_km_from_geneva", "km GE", true], ["town", "Town", true], ["canton", "Canton", true], ["length_m", "Length m", true],
    ["hp", "CV", true], ["year", "Year", true], ["brand", "Brand", false], ["model", "Model", false], ["width_m", "Beam m", false],
    ["engine_type", "Engine", true], ["engine_brand", "Engine brand", false], ["kw", "kW", false], ["fuel", "Fuel", false], ["hours", "Hours", false],
    ["sail_area_m2", "Sail m²", false], ["berths", "Berths", false], ["material", "Material", false], ["trailer", "Trailer", true],
    ["mooring_included", "Mooring", false], ["condition", "Condition", false], ["licence_leman", "Licence Léman", true], ["seller_type", "Seller", false],
    ["source", "Source", true], ["posted_date", "Posted", false], ["first_seen", "First seen", true], ["last_seen", "Last seen", false],
    ["status", "Status", false], ["url", "Ad", true]];
  const NUM = new Set(["price_chf", "distance_km_from_geneva", "length_m", "hp", "year", "width_m", "kw", "hours", "sail_area_m2", "berths"]);
  const $ = (s, el = document) => el.querySelector(s), $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const has = (v) => v !== null && v !== undefined && v !== "" && v !== NA;
  const chf = (v) => (v === 0 ? "Free" : has(v) ? "CHF " + Math.round(v).toLocaleString("de-CH").replace(/’/g, "'") : NA);
  let ALL = [], META = {}, view = "table", sort = { key: "price_chf", asc: true }, map = null, layer = null;
  const visible = JSON.parse(localStorage.getItem("nb-cols") || "null") || Object.fromEntries(COLS.map((c) => [c[0], c[2]]));
  const cats = new Set(Object.keys(CATS));
  const R = {};

  function siteDir() {
    let path = window.location.pathname;
    if (path.endsWith("/index.html")) path = path.slice(0, -10);
    else if (!path.endsWith("/")) path = path + "/";
    return path;
  }
  async function load() {
    const url = siteDir() + "data/listings.json";
    try { const r = await fetch(url, { cache: "no-cache" }); if (!r.ok) throw 0; return await r.json(); }
    catch (e) { if (window.__LISTINGS__) return window.__LISTINGS__; throw e; }
  }
  function today() { return META.updated || new Date().toISOString().slice(0, 10); }
  function daysSince(d) { return has(d) ? (Date.parse(today()) - Date.parse(d)) / 864e5 : 1e9; }

  function setupRange(id, key, step, fmt) {
    const vals = ALL.map((r) => r[key]).filter((v) => typeof v === "number");
    const el = $("#" + id), lo = $(".lo", el), hi = $(".hi", el);
    const mn = vals.length ? Math.floor(Math.min(...vals)) : 0, mx = vals.length ? Math.ceil(Math.max(...vals)) : 1;
    [lo, hi].forEach((i) => { i.min = mn; i.max = mx; i.step = step; });
    lo.value = mn; hi.value = mx;
    const upd = () => { if (+lo.value > +hi.value) [lo.value, hi.value] = [hi.value, lo.value]; $(".val", el).textContent = fmt(+lo.value) + " – " + fmt(+hi.value); render(); };
    lo.oninput = hi.oninput = upd; $(".val", el).textContent = fmt(mn) + " – " + fmt(mx);
    R[key] = { lo, hi, mn, mx, reset() { lo.value = mn; hi.value = mx; $(".val", el).textContent = fmt(mn) + " – " + fmt(mx); } };
  }

  function filtered() {
    const q = $("#q").value.trim().toLowerCase(), src = $("#f-source").value, can = $("#f-canton").value, st = $("#f-status").value, nw = $("#f-new").value;
    const keepNA = $("#t-na").checked, nolic = $("#t-nolic").checked, trailer = $("#t-trailer").checked;
    return ALL.filter((r) => {
      if (!cats.has(r.category)) return false;
      if (st !== "all" && r.status !== st) return false;
      if (src && r.source !== src) return false;
      if (can && r.canton !== can) return false;
      if (nw && daysSince(r.first_seen) >= +nw) return false;
      if (nolic && !String(r.licence_leman).startsWith("no")) return false;
      if (trailer && r.trailer !== "yes") return false;
      for (const k in R) {
        const v = r[k], g = R[k], lo = +g.lo.value, hi = +g.hi.value;
        const full = lo <= g.mn && hi >= g.mx;
        if (typeof v !== "number") { if (!full && !(keepNA && k !== "price_chf")) return false; continue; }
        if (v < lo || v > hi) return false;
      }
      if (q) { const hay = [r.title, r.brand, r.model, r.town, r.canton, r.region, r.description_excerpt, r.category_label].join(" ").toLowerCase(); if (!q.split(/\s+/).every((w) => hay.includes(w))) return false; }
      return true;
    }).sort((a, b) => {
      const x = a[sort.key], y = b[sort.key], xa = has(x), ya = has(y);
      if (!xa && !ya) return 0; if (!xa) return 1; if (!ya) return -1;
      const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
      return sort.asc ? c : -c;
    });
  }

  const tags = (r) => (daysSince(r.first_seen) < 1 && r.status === "active" ? '<span class="tag new">new</span> ' : "") + (r.status === "removed" ? '<span class="tag removed">removed</span> ' : "") +
    (typeof r.price_chf === "number" && r.price_chf < 10000 ? '<span class="tag cheap">&lt;10k</span> ' : "") + (typeof r.distance_km_from_geneva === "number" && r.distance_km_from_geneva <= 80 ? '<span class="tag near">near GE</span>' : "");
  const catHtml = (c) => `<span class="cat"><i style="background:${(CATS[c] || CATS.other)[1]}"></i>${esc((CATS[c] || CATS.other)[0])}</span>`;
  function cell(r, k) {
    const v = r[k];
    if (k === "thumb_url") return has(v) ? `<td><a href="${esc(r.url)}" target="_blank" rel="noopener"><img class="thumb" loading="lazy" src="${esc(v)}" alt=""></a></td>` : `<td class="na">${(CATS[r.category] || CATS.other)[2]}</td>`;
    if (k === "title") return `<td class="title"><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a><div>${tags(r)}</div></td>`;
    if (k === "category") return `<td>${catHtml(v)}</td>`;
    if (k === "price_chf") return `<td class="num"><span class="price ${typeof v === "number" && v < 10000 ? "cheap" : ""}">${chf(v)}</span>${has(r.previous_price_chf) ? `<div class="na">was ${chf(r.previous_price_chf)}</div>` : ""}</td>`;
    if (k === "url") return `<td><a class="btn small" href="${esc(v)}" target="_blank" rel="noopener">View ad →</a></td>`;
    if (k === "source") return `<td>${esc(SRC[v] || v)}</td>`;
    if (!has(v)) return `<td class="na ${NUM.has(k) ? "num" : ""}">N/A</td>`;
    return `<td class="${NUM.has(k) ? "num" : ""}">${esc(k === "distance_km_from_geneva" ? Math.round(v) : v)}</td>`;
  }
  function renderTable(rows) {
    const cols = COLS.filter((c) => visible[c[0]]);
    $("#tbl thead").innerHTML = "<tr>" + cols.map((c) => `<th data-k="${c[0]}" class="${sort.key === c[0] ? "sorted" + (sort.asc ? " asc" : "") : ""}">${c[1]}</th>`).join("") + "</tr>";
    $("#tbl tbody").innerHTML = rows.map((r) => "<tr>" + cols.map((c) => cell(r, c[0])).join("") + "</tr>").join("");
    $$("#tbl th").forEach((th) => th.onclick = () => { const k = th.dataset.k; sort = { key: k, asc: sort.key === k ? !sort.asc : true }; render(); });
  }
  function spec(r) { return [has(r.length_m) && r.length_m + " m", has(r.hp) && r.hp + " CV", has(r.year) && r.year, has(r.engine_type) && r.engine_type, r.trailer === "yes" && "trailer"].filter(Boolean).join(" · "); }
  function cardHtml(r) {
    const c = CATS[r.category] || CATS.other;
    return `<article class="card" style="border-top-color:${c[1]}"><a class="ph" href="${esc(r.url)}" target="_blank" rel="noopener" style="background-image:url('${has(r.thumb_url) ? esc(r.photo_url !== NA ? r.photo_url : r.thumb_url) : ""}')"><span class="tags">${tags(r)}</span></a>
      <div class="bd">${catHtml(r.category)}<h3><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a></h3>
      <div class="meta">📍 ${esc(has(r.town) ? r.town : has(r.region) ? r.region : "N/A")}${has(r.canton) ? " (" + esc(r.canton) + ")" : ""} · <b>${typeof r.distance_km_from_geneva === "number" ? Math.round(r.distance_km_from_geneva) + " km" : "km N/A"}</b> from Geneva</div>
      <div class="spec">${esc(spec(r))}</div>
      <div class="ft"><span class="price ${typeof r.price_chf === "number" && r.price_chf < 10000 ? "cheap" : ""}">${chf(r.price_chf)}</span><a class="btn small" href="${esc(r.url)}" target="_blank" rel="noopener">View ad →</a></div></div></article>`;
  }
  function renderCats(rows) {
    $("#v-cats").innerHTML = Object.keys(CATS).map((k) => {
      const rs = rows.filter((r) => r.category === k); if (!rs.length) return "";
      const pr = rs.map((r) => r.price_chf).filter((v) => typeof v === "number").sort((a, b) => a - b);
      const med = pr.length ? pr[Math.floor(pr.length / 2)] : null;
      return `<div class="catblock"><h2 style="border-color:${CATS[k][1]}">${CATS[k][2]} ${esc(CATS[k][0])}<small>${rs.length} boats · from ${chf(pr[0])} · median ${chf(med)}</small></h2><div class="grid">${rs.map(cardHtml).join("")}</div></div>`;
    }).join("") || "<p>No boats match.</p>";
  }
  function renderMap(rows) {
    if (!window.L) { $("#map").innerHTML = "<p style='padding:20px'>Map library could not load.</p>"; return; }
    if (!map) {
      map = L.map("map").setView([46.75, 8.1], 8);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
      L.circleMarker([46.2044, 6.1432], { radius: 9, color: "#fff", weight: 3, fillColor: "#D64545", fillOpacity: 1 }).addTo(map).bindTooltip("Geneva (your mooring)");
      layer = L.layerGroup().addTo(map);
    }
    layer.clearLayers();
    rows.filter((r) => typeof r.lat === "number").forEach((r) => {
      const c = (CATS[r.category] || CATS.other)[1];
      L.circleMarker([r.lat, r.lon], { radius: 7, color: "#fff", weight: 1.5, fillColor: c, fillOpacity: .9 }).addTo(layer)
        .bindPopup(`<div class="pop">${has(r.thumb_url) ? `<img src="${esc(r.thumb_url)}" alt="">` : ""}<b>${esc(r.title)}</b><br>${chf(r.price_chf)} · ${typeof r.distance_km_from_geneva === "number" ? Math.round(r.distance_km_from_geneva) + " km" : ""}<br>${esc(spec(r))}<br><a href="${esc(r.url)}" target="_blank" rel="noopener">View ad →</a></div>`);
    });
    setTimeout(() => map.invalidateSize(), 50);
  }
  function renderKpis() {
    const act = ALL.filter((r) => r.status === "active"), pr = act.map((r) => r.price_chf).filter((v) => typeof v === "number").sort((a, b) => a - b);
    const k = (v, l, s, c) => `<div class="kpi ${c}"><div class="v">${v}</div><div class="l">${l}</div><div class="s">${s}</div></div>`;
    $("#kpis").innerHTML = k(act.length, "Active boats", "under CHF 30'000 or free", "") + k(act.filter((r) => r.price_chf < 10000).length, "Under CHF 10k", "green price tag", "green") +
      k(act.filter((r) => r.distance_km_from_geneva <= 80).length, "Within 80 km", "road distance from Geneva", "teal") +
      k(pr.length ? chf(pr[Math.floor(pr.length / 2)]) : NA, "Median price", "all categories", "orange") + k(act.filter((r) => daysSince(r.first_seen) < 1).length, "New today", "first seen " + today(), "purple");
  }
  function render() {
    const rows = filtered();
    $("#count").textContent = rows.length + " of " + ALL.length + " boats";
    if (view === "table") renderTable(rows); else if (view === "cards") $("#grid").innerHTML = rows.map(cardHtml).join(""); else if (view === "cats") renderCats(rows); else renderMap(rows);
  }
  function csv() {
    const rows = filtered(), keys = Object.keys(ALL[0] || {}).filter((k) => k !== "price_history");
    const q = (v) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
    const blob = new Blob([keys.join(",") + "\n" + rows.map((r) => keys.map((k) => q(r[k])).join(",")).join("\n")], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "nico-boats-" + today() + ".csv"; a.click();
  }
  function init(data) {
    META = data; ALL = Object.values(data.records || {});
    $("#updated").textContent = "Updated " + (data.updated || "") + ".";
    const opts = (sel, vals, lab) => vals.forEach((v) => sel.insertAdjacentHTML("beforeend", `<option value="${esc(v)}">${esc(lab ? lab(v) : v)}</option>`));
    opts($("#f-source"), [...new Set(ALL.map((r) => r.source))].sort(), (v) => SRC[v] || v);
    opts($("#f-canton"), [...new Set(ALL.map((r) => r.canton).filter(has))].sort());
    $("#cats").innerHTML = Object.entries(CATS).map(([k, c]) => `<span class="chip on" data-c="${k}" style="background:${c[1]}">${c[2]} ${esc(c[0])}<span class="n">${ALL.filter((r) => r.category === k && r.status === "active").length}</span></span>`).join("");
    $$("#cats .chip").forEach((ch) => ch.onclick = () => { const k = ch.dataset.c; if (cats.has(k)) { cats.delete(k); ch.classList.remove("on"); ch.style.background = "#fff"; } else { cats.add(k); ch.classList.add("on"); ch.style.background = CATS[k][1]; } render(); });
    setupRange("r-price", "price_chf", 100, (v) => (v >= 1000 ? Math.round(v / 1000) + "k" : v));
    setupRange("r-dist", "distance_km_from_geneva", 5, (v) => v + " km");
    setupRange("r-len", "length_m", 0.1, (v) => v.toFixed(1));
    setupRange("r-hp", "hp", 1, (v) => v);
    setupRange("r-year", "year", 1, (v) => v);
    $("#cols").innerHTML = COLS.map((c) => `<label><input type="checkbox" data-k="${c[0]}" ${visible[c[0]] ? "checked" : ""}> ${c[1]}</label>`).join("");
    $$("#cols input").forEach((i) => i.onchange = () => { visible[i.dataset.k] = i.checked; localStorage.setItem("nb-cols", JSON.stringify(visible)); render(); });
    ["#q", "#f-source", "#f-canton", "#f-status", "#f-new", "#t-na", "#t-nolic", "#t-trailer"].forEach((s) => $(s).addEventListener("input", render));
    $("#reset").onclick = () => { $("#q").value = ""; ["#f-source", "#f-canton", "#f-new"].forEach((s) => $(s).value = ""); $("#f-status").value = "active"; Object.values(R).forEach((g) => g.reset());
      Object.keys(CATS).forEach((k) => cats.add(k)); $$("#cats .chip").forEach((ch) => { ch.classList.add("on"); ch.style.background = CATS[ch.dataset.c][1]; }); render(); };
    $$("#tabs > button").forEach((b) => b.onclick = () => { view = b.dataset.view; $$("#tabs > button").forEach((x) => x.classList.toggle("on", x === b));
      ["table", "cards", "cats", "map"].forEach((v) => $("#v-" + v).classList.toggle("hidden", v !== view)); history.replaceState(null, "", "#v=" + view); render(); });
    $("#csv").onclick = csv;
    const h = (location.hash.match(/v=(\w+)/) || [])[1]; if (["table", "cards", "cats", "map"].includes(h)) $(`#tabs > button[data-view="${h}"]`).click();
    const s = data.sources || {};
    $("#foot").innerHTML = "<b>Sources.</b> " + Object.entries(s).map(([k, v]) => `${esc(SRC[k] || k)}: ${v.ok ? "ok" : "not included (" + esc(v.error || "failed") + ")"}`).join(" · ") +
      ". Distance = road distance from Geneva centre via OSRM (OpenStreetMap), straight line × 1.25 as fallback. Missing values are shown as N/A. Prices and details are the sellers' own; always check the ad.";
    renderKpis(); render();
  }
  load().then(init).catch((e) => { document.querySelector("main").insertAdjacentHTML("afterbegin", "<p class='panel'>Could not load data/listings.json.</p>"); console.error(e); });
})();
