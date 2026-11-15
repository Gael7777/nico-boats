# -*- coding: utf-8 -*-
"""Master store: /workspace/projects/nico-boats/data/listings.json (+ listings.csv).
One record per boat, stable id "<source>:<listing id>". Missing values are the string "N/A".
Merging rules: new id -> first_seen=today; known id -> fields refreshed, last_seen=today, price change
appended to price_history; active id not seen today (and its source succeeded today) -> status=removed."""
import csv, json, re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
STORE = PROJECT / "data" / "listings.json"
CSV = PROJECT / "data" / "listings.csv"
NA = "N/A"
CAT_LABEL = {"sail": "Sailboats", "motor": "Motorboats (cabin)", "open": "Open boats & day-cruisers",
             "inflatable": "Inflatables & RIBs", "small": "Dinghies, rowing & small boats", "other": "Other"}
FIELDS = ["id", "source", "source_listing_id", "url", "title", "category", "category_label", "brand", "model", "year",
          "price_chf", "price_label", "length_m", "width_m", "engine_type", "engine_brand", "engine_model", "hp", "kw",
          "fuel", "hours", "sail_area_m2", "berths", "material", "trailer", "mooring_included", "condition",
          "licence_leman", "town", "canton", "postcode", "region", "lat", "lon", "geo_precision",
          "distance_km_from_geneva", "distance_method", "seller_type", "posted_date", "photo_url", "thumb_url",
          "description_excerpt", "first_seen", "last_seen", "status", "removed_on", "sent_in_digest",
          "price_changed_on", "previous_price_chf", "price_history", "also_listed"]

def _num(v):
    try:
        return float(v)
    except Exception:
        return None

def normalise(r):
    """raw collector row -> store record (all FIELDS, N/A for missing)."""
    o = {k: NA for k in FIELDS}
    o.update({"id": r["id"], "source": r["source"], "source_listing_id": r["id"].split(":", 1)[1], "url": r["url"],
              "title": r["title"], "category": r["category"], "category_label": CAT_LABEL.get(r["category"], r["category"]),
              "price_chf": r.get("price_chf"), "price_label": r.get("price_label")})
    for k in ["brand", "model", "year", "length_m", "width_m", "engine_type", "engine_brand", "engine_model", "fuel", "hours",
              "sail_area_m2", "berths", "material", "trailer", "mooring_included", "condition", "town", "canton", "postcode",
              "region", "lat", "lon", "geo_precision", "distance_method", "seller_type"]:
        if r.get(k) not in (None, "", []): o[k] = r[k]
    if r.get("distance_km") is not None: o["distance_km_from_geneva"] = r["distance_km"]
    o["posted_date"] = r.get("posted") or NA
    o["photo_url"] = r.get("photo") or r.get("thumb") or NA
    o["thumb_url"] = r.get("thumb") or r.get("photo") or NA
    desc = re.sub(r"\s+", " ", r.get("snippet") or "").strip()
    desc = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email hidden]", desc)                      # public repo: no contact details
    desc = re.sub(r"(\+41|0041|\b0)[\s./-]?\d{2}[\s./-]?\d{3}[\s./-]?\d{2}[\s./-]?\d{2}\b", "[phone hidden]", desc)
    desc = re.sub(r"(?<!\d)(?:\+|00)\d{2}[\s./-]?\d[\d\s./-]{7,14}\d(?!\d)", "[phone hidden]", desc)   # international numbers
    o["description_excerpt"] = desc[:500] or NA
    hp, kw = _num(r.get("hp")), _num(r.get("kw"))
    eng = r.get("engine") or ""
    if hp is None and kw is None and eng:
        m = re.match(r"([\d.]+)\s*(CV|PS|HP|kW)", eng)
        if m:
            if m.group(2) == "kW": kw = float(m.group(1))
            else: hp = float(m.group(1))
    if hp is None and kw is not None: hp = round(kw / 0.7355, 1)
    if kw is None and hp is not None: kw = round(hp * 0.7355, 1)
    if hp is not None: o["hp"], o["kw"] = hp, kw
    if r.get("sail_area_raw") and o["sail_area_m2"] == NA:
        m = re.search(r"([\d.]+)", r["sail_area_raw"])
        if m: o["sail_area_m2"] = float(m.group(1))
    # indicative licence need on the Swiss Leman (OFT: motor > 10 CV on Lake Geneva; sail > 15 m2)
    lic = NA
    if hp is not None: lic = "yes (>10 CV)" if hp > 10 else "no (≤10 CV)"
    if _num(o["sail_area_m2"]) and _num(o["sail_area_m2"]) > 15: lic = "yes (sail >15 m²)"
    o["licence_leman"] = lic
    if r.get("also_listed"): o["also_listed"] = [{"source": a["source"], "url": a["url"]} for a in r["also_listed"]]
    for k in FIELDS:
        if o[k] is None or o[k] == "" or o[k] == []: o[k] = NA
    return o

def load():
    if STORE.exists():
        st = json.loads(STORE.read_text())
        for rec in st["records"].values():
            for k in FIELDS: rec.setdefault(k, NA)
        return st
    return {"schema_version": 1, "updated": None, "sources": {}, "records": {}}

def merge(store, rows, status, today):
    recs = store["records"]; seen = set(); changes = []
    for r in rows:
        n = normalise(r); seen.add(n["id"])
        old = recs.get(n["id"])
        if old is None:
            n.update({"first_seen": today, "last_seen": today, "status": "active", "removed_on": NA, "sent_in_digest": NA,
                      "price_changed_on": NA, "previous_price_chf": NA, "price_history": [{"date": today, "price_chf": n["price_chf"]}]})
            recs[n["id"]] = n
        else:
            keep = {k: old.get(k, NA) for k in ["first_seen", "sent_in_digest", "price_history", "price_changed_on", "previous_price_chf"]}
            if old.get("price_chf") != n["price_chf"]:
                keep["price_history"] = (old.get("price_history") or []) + [{"date": today, "price_chf": n["price_chf"]}]
                keep["previous_price_chf"], keep["price_changed_on"] = old.get("price_chf"), today
                changes.append(n["id"])
            # never lose a value we had before because today's parse missed it
            for k in FIELDS:
                if n.get(k) == NA and old.get(k, NA) != NA and k not in ("removed_on",): n[k] = old[k]
            n.update(keep); n.update({"last_seen": today, "status": "active", "removed_on": NA})
            recs[n["id"]] = n
    ok_sources = {s for s, v in status.items() if v.get("ok")}
    removed = []
    for k, v in recs.items():
        if k not in seen and v["status"] == "active" and v["source"] in ok_sources:
            v["status"], v["removed_on"] = "removed", today; removed.append(k)
    store["updated"] = today; store["sources"] = status
    return changes, removed

def save(store):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(store, ensure_ascii=False, indent=1))
    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in sorted(store["records"].values(), key=lambda x: (x["category"], x["price_chf"] if isinstance(x["price_chf"], (int, float)) else 1e9)):
            row = dict(r)
            row["also_listed"] = " ".join(a["url"] for a in r.get("also_listed") or [] if isinstance(a, dict)) or NA
            row["price_history"] = "; ".join(f"{p['date']}={p['price_chf']}" for p in r.get("price_history") or []) or NA
            w.writerow(row)
