# -*- coding: utf-8 -*-
"""Nico Boats daily pipeline.
  python3 build.py                 # scrape + merge store + digest + site data + previews
  python3 build.py --no-collect    # reuse report/data/raw_today.json (no network scraping)
  python3 build.py --no-mark       # build digest without marking boats as sent
  python3 build.py --no-shots      # skip PNG previews
Digest contains only active boats whose sent_in_digest is N/A (or today, so same-day reruns are idempotent)."""
import argparse, json, shutil, subprocess, sys
from datetime import date
from pathlib import Path
import store, digest

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
    ap = argparse.ArgumentParser(); ap.add_argument("--no-collect", action="store_true"); ap.add_argument("--no-mark", action="store_true")
    ap.add_argument("--no-shots", action="store_true"); ap.add_argument("--date", default=date.today().isoformat())
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
        if not r.get("town") and (r.get("region") or "").strip().lower() in ("suisse", "schweiz", "svizzera", "switzerland"):
            for k in ("lat", "lon", "distance_km", "distance_method", "geo_precision"): r[k] = None   # country centroid is meaningless
        if r.get("canton") == "FL" or r.get("canton") == "LI": continue   # Liechtenstein is outside Switzerland
        kept.append(r)
    rows = kept
    for s_ in status.values():
        if "kept" in s_: s_["kept"] = None
    for src in ("tutti", "anibis", "bateau24"):
        if src in status: status[src]["kept"] = sum(1 for r in rows if r["source"] == src)
    st = store.load()
    changes, removed = store.merge(st, rows, status, today)
    active = [r for r in st["records"].values() if r["status"] == "active"]
    # First edition until a previous day's digest has been marked; same-day reruns stay idempotent.
    first_run = not any(r.get("sent_in_digest") not in (store.NA, today) for r in st["records"].values())
    todays = [r for r in active if r["sent_in_digest"] in (store.NA, today)]
    if first_run:
        todays = active
    chg = [st["records"][i] for i in changes if st["records"][i]["status"] == "active"]
    htm = digest.render(todays, active, status, today, chg, len(removed), first_run)
    out = REPORT / "digest" / f"{today}.html"; out.parent.mkdir(exist_ok=True); out.write_text(htm)
    (REPORT / "digest" / "latest.html").write_text(htm)
    root_digest = PROJECT / "digest"
    root_digest.mkdir(exist_ok=True)
    (root_digest / f"{today}.html").write_text(htm)
    (root_digest / "latest.html").write_text(htm)
    if not a.no_mark:
        for r in todays: r["sent_in_digest"] = today
    store.save(st)
    # site data (GitHub Pages serves site/; it fetches data/listings.json, listings.js is the file:// fallback)
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy(store.STORE, SITE / "data" / "listings.json")
    (SITE / "data" / "listings.js").write_text("window.__LISTINGS__ = " + store.STORE.read_text() + ";\n")
    for lock in (SITE / "data").glob(".~lock*"):
        lock.unlink()
    for lock in store.STORE.parent.glob(".~lock*"):
        lock.unlink()
    if not a.no_shots:
        pv = REPORT / "preview"; pv.mkdir(exist_ok=True)
        shot(out, pv / f"{today}-desktop.png", 760); shot(out, pv / f"{today}-mobile.png", 390)
    by_src, by_cat = {}, {}
    for r in todays:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1; by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print(json.dumps({"digest": str(out), "bytes": len(htm.encode()), "in_digest": len(todays), "active": len(active), "price_changes": len(changes),
                      "removed": len(removed), "by_source": by_src, "by_category": by_cat,
                      "status": {k: (v.get("ok"), v.get("error")) for k, v in status.items()}}, indent=1))

if __name__ == "__main__":
    main()
