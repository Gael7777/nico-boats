# -*- coding: utf-8 -*-
"""Nico Boats daily pipeline.
  python3 build.py                 # scrape + merge store + digest + site data + previews
  python3 build.py --no-collect    # reuse report/data/raw_today.json (no network scraping)
  python3 build.py --no-mark       # build digest without marking boats as sent
  python3 build.py --no-shots      # skip PNG previews
Daily digest (French, filtre global): only matching boats not yet sent (the 2026-11-15 baseline is excluded).
Marking: unless --no-mark, every boat written into today's digest gets sent_in_digest = today. Use --no-mark for
any build that will NOT be sent (rebuilds, tests), otherwise tomorrow's digest would skip those boats."""
import argparse, json, shutil, subprocess, sys
from datetime import date
from pathlib import Path
import store, digest, digest_fr, filtre

REPORT = Path(__file__).resolve().parent
PROJECT = REPORT.parent
SITE = PROJECT / "site"
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome"

def shot(html_path, png_path, width, height=16000):
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}",
                    "--virtual-time-budget=15000", f"--screenshot={png_path}", html_path.as_uri() if isinstance(html_path, Path) else html_path],
                   check=True, capture_output=True, timeout=180)
    try:   # trim the empty background below the content
        from PIL import Image, ImageChops
        im = Image.open(png_path).convert("RGB"); bg = Image.new("RGB", im.size, im.getpixel((2, im.height - 2)))
        bbox = ImageChops.difference(im, bg).getbbox()
        if bbox: im.crop((0, 0, im.width, min(im.height, bbox[3] + 24))).save(png_path, optimize=True)
    except Exception as ex:
        print("trim skipped:", ex, file=sys.stderr)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-collect", action="store_true")
    ap.add_argument("--no-mark", action="store_true")
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--no-enrich", action="store_true")
    ap.add_argument("--selection-initiale", action="store_true",
                    help="Write a one-time French digest of ALL current matches, ignoring sent marks (do not send).")
    ap.add_argument("--date", default=date.today().isoformat())
    a = ap.parse_args(); today = a.date
    raw_p = REPORT / "data" / "raw_today.json"
    if not a.no_collect:
        import collect
        rows, status = collect.main()
        raw_p.write_text(json.dumps({"date": today, "rows": rows, "status": status}, ensure_ascii=False, indent=1))
    raw = json.loads(raw_p.read_text()); rows, status = raw["rows"], raw["status"]
    import collect   # re-apply the current keyword rules so rule fixes take effect without re-scraping
    kept = []
    for r in rows:
        if r["source"] in ("tutti", "anibis"):
            c = collect.classify_text(r["title"], r.get("snippet") or "")
            if c is None: continue
            r["category"] = c
            r.pop("year", None)
            for k in ("brand", "model", "width_m", "engine_type", "engine_brand", "fuel", "hours", "sail_area_m2", "berths", "material", "trailer", "mooring_included", "condition"):
                r.pop(k, None)
            for k, v in collect.rich_fields(r["title"], r.get("snippet") or "").items(): r.setdefault(k, v)
            y = collect.year_from(r["title"] + " . " + (r.get("snippet") or ""))
            if y: r["year"] = y
        elif r["source"] == "bateau24":
            c = collect.b24_keep(r)
            if c is None: continue
            r["category"] = c
        elif r["source"] in ("lakeboat", "petitesannonces"):
            c = collect.classify_hint(r["title"], (r.get("snippet") or "") + " " + (r.get("type_label") or ""), r.get("rubric_hint"))
            if c is None: continue
            if r.get("rubric_hint") == "sail" and c in ("open", "motor", "other"): c = "sail"
            r["category"] = c
        if not r.get("town") and (r.get("region") or "").strip().lower() in ("suisse", "schweiz", "svizzera", "switzerland"):
            for k in ("lat", "lon", "distance_km", "distance_method", "geo_precision"): r[k] = None   # country centroid is meaningless
        if r.get("canton") == "FL" or r.get("canton") == "LI": continue   # Liechtenstein is outside Switzerland
        kept.append(r)
    rows = collect.merge_duplicates(kept, collect.known_ids())   # idempotent; re-applies duplicate rules on --no-collect
    for s_ in status.values():
        if "kept" in s_: s_["kept"] = None
    for src in ("tutti", "anibis", "bateau24", "lakeboat", "petitesannonces", "aquaboat"):
        if src in status: status[src]["kept"] = sum(1 for r in rows if r["source"] == src)
    st = store.load()
    changes, removed = store.merge(st, rows, status, today)
    active = [r for r in st["records"].values() if r["status"] == "active"]
    cfg = filtre.load_config()
    if not a.no_enrich:
        filtre.enrich_records(active, fetch_missing=True, limit_fetches=40, cfg=cfg)
    daily = filtre.daily_candidates(active, today, cfg)
    htm = digest_fr.render_filtre(daily, active, status, today, mode="daily")
    out = REPORT / "digest" / f"{today}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(htm)
    (REPORT / "digest" / "latest.html").write_text(htm)
    root_digest = PROJECT / "digest"
    root_digest.mkdir(exist_ok=True)
    (root_digest / f"{today}.html").write_text(htm)
    (root_digest / "latest.html").write_text(htm)
    sel_info = None
    if a.selection_initiale:
        sel = filtre.selection_candidates(active, cfg)
        sel_htm = digest_fr.render_filtre(sel, active, status, today, mode="selection")
        sel_path = REPORT / "digest" / f"selection-initiale-{today}.html"
        sel_path.write_text(sel_htm)
        sel_info = {"path": str(sel_path), "bytes": len(sel_htm.encode()), "counts": filtre.counts(sel)}
        if not a.no_shots:
            pv = REPORT / "preview"; pv.mkdir(exist_ok=True)
            shot(sel_path, pv / f"selection-initiale-{today}-desktop.png", 760)
            shot(sel_path, pv / f"selection-initiale-{today}-mobile.png", 390)
            sel_info["previews"] = [str(pv / f"selection-initiale-{today}-desktop.png"),
                                    str(pv / f"selection-initiale-{today}-mobile.png")]
    if not a.no_mark:
        for r, _ in daily:
            r["sent_in_digest"] = today
    store.save(st)
    # Site payload: all records, plus _filtre for the default view (master store stays clean)
    classified = filtre.classify_all(list(st["records"].values()), cfg)
    site_store = {k: v for k, v in st.items() if k != "records"}
    site_store["filtre_global"] = {"version": cfg.get("version"), "updated": cfg.get("updated"), "label": cfg.get("label")}
    site_store["records"] = {rid: filtre.attach(rec, classified[rid]) for rid, rec in st["records"].items()}
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    payload = json.dumps(site_store, ensure_ascii=False, indent=1)
    (SITE / "data" / "listings.json").write_text(payload)
    (SITE / "data" / "listings.js").write_text("window.__LISTINGS__ = " + payload + ";\n")
    shutil.copy(filtre.CONFIG_PATH, SITE / "data" / "filtre_global.json")
    for lock in list((SITE / "data").glob(".~lock*")) + list(store.STORE.parent.glob(".~lock*")):
        lock.unlink()
    if not a.no_shots:
        pv = REPORT / "preview"; pv.mkdir(exist_ok=True)
        shot(out, pv / f"{today}-desktop.png", 760)
        shot(out, pv / f"{today}-mobile.png", 390)
    print(json.dumps({"digest": str(out), "bytes": len(htm.encode()), "in_digest": len(daily),
                      "active": len(active), "price_changes": len(changes), "removed": len(removed),
                      "filtre": filtre.counts(daily), "selection_initiale": sel_info,
                      "status": {k: (v.get("ok"), v.get("error")) for k, v in status.items()}}, indent=1))

if __name__ == "__main__":
    main()
