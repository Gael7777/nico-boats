# -*- coding: utf-8 -*-
"""Filtre global: classifies boats into zone 1 / zone 2 / à vérifier / excluded
and flags « très bonne opportunité ». Config: ../config/filtre_global.json."""
from __future__ import annotations

import json, math, re, sys
from pathlib import Path

REPORT = Path(__file__).resolve().parent
PROJECT = REPORT.parent
CONFIG_PATH = PROJECT / "config" / "filtre_global.json"
NA = "N/A"

def log(*a):
    print(*a, file=sys.stderr, flush=True)

def load_config(path=None):
    p = Path(path) if path else CONFIG_PATH
    return json.loads(p.read_text(encoding="utf-8"))

def num(v):
    if v in (None, NA, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def norm_text(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()

def haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))

def _town_key(s):
    t = norm_text(s)
    t = re.sub(r"\b(le|la|les|saint|ste|st)\b", lambda m: {"saint": "st", "ste": "st"}.get(m.group(0), m.group(0)), t)
    t = t.replace("saint ", "st ").replace("ste ", "st ")
    return t

def zone_for(record, cfg=None):
    """Return (zone_id, lake_name_or_None, method). zone_id is 'zone1' or 'zone2'."""
    cfg = cfg or load_config()
    zcfg = cfg["zones"]
    max_km = zcfg.get("max_km_to_shore", 12)
    lat, lon = num(record.get("lat")), num(record.get("lon"))
    town = _town_key(record.get("town") if record.get("town") not in (None, NA, "") else "")
    region = _town_key(record.get("region") if record.get("region") not in (None, NA, "") else "")
    pc = str(record.get("postcode") or "").strip()
    best = None
    for lake in zcfg["lakes"]:
        # coordinates → distance to shore
        if lat is not None and lon is not None:
            pts = lake.get("shore_points") or []
            if pts:
                d = min(haversine_km((lat, lon), (p[0], p[1])) for p in pts)
                if d <= max_km and (best is None or d < best[0]):
                    best = (d, lake["name"], "shore")
        # town / region name
        names = set(lake.get("towns") or [])
        def _hit(label):
            if not label:
                return False
            compact = label.replace(" ", "")
            for n in names:
                nc = n.replace(" ", "")
                if label == n or compact == nc:
                    return True
                if len(n) >= 4 and (label.startswith(n + " ") or n.startswith(label + " ")):
                    return True
            return False
        if _hit(town):
            return "zone1", lake["name"], "town"
        if _hit(region):
            return "zone1", lake["name"], "region"
        # postcode prefixes
        for pref in lake.get("postcode_prefixes") or []:
            if pc and pc.startswith(str(pref)):
                return "zone1", lake["name"], "postcode"
    if best:
        return "zone1", best[1], f"shore_{best[0]:.1f}km"
    return "zone2", None, "default"

def _haystack(record):
    return " ".join([
        str(record.get("title") or ""),
        str(record.get("description_excerpt") or ""),
        str(record.get("snippet") or ""),
        str(record.get("category_label") or ""),
        str(record.get("engine_type") or ""),
    ])

def clearly_excluded_type(record, cfg):
    cat = record.get("category")
    if cat in (cfg["criteria"].get("exclude_categories") or []):
        return True
    t = norm_text(_haystack(record))
    for kw in cfg["criteria"].get("exclude_keywords") or []:
        if norm_text(kw) and re.search(r"\b" + re.escape(norm_text(kw)) + r"\b", t):
            # don't exclude RIB/semi-rigide just because of a generic keyword
            if kw in ("dinghy", "annexe") and record.get("category") == "inflatable":
                continue
            return True
    return False

def infer_outboard(record):
    if record.get("engine_type") == "outboard":
        return True
    t = norm_text(_haystack(record) + " " + str(record.get("engine_brand") or "") + " " + str(record.get("engine_model") or ""))
    if re.search(r"(sans hors[- ]?bord|ohne aussenbord|ohne outboard|senza fuoribordo)", t):
        return False
    if re.search(r"(hors[- ]?bord|aussenbord|ausserbord|fuoribordo|outboard)", t):
        return True
    # typical portable outboard brands at 40–90 CV, unless an inboard/stern-drive is mentioned
    if re.search(r"(in[- ]?bord|inbord|z[- ]?drive|sterndrive|mercruiser|volvo penta|entrobordo)", t):
        return False
    if re.search(r"\b(yamaha|honda|suzuki|tohatsu|selva|parsun|mariner|evinrude|johnson|mercury)\b", t) and num(record.get("hp")) and 40 <= num(record.get("hp")) <= 90:
        return True
    return False

def clearly_out_of_scope(record, cfg):
    """Tiny dinghies, giveaways, 'sans permis', hulls sold without an engine, etc."""
    t = norm_text(_haystack(record))
    if re.search(r"(sans permis|ohne (boots)?schein|kein bootsfuhrerschein|sans brevet|a donner|zu verschenken|bootspartner|partenaire pour notre bateau)", t):
        return True
    if re.search(r"(sans hors[- ]?bord|ohne aussenbord|sans moteur compris|ohne motor$|scafe ohne motor)", t):
        return True
    length, hp, price = num(record.get("length_m")), num(record.get("hp")), num(record.get("price_chf"))
    if length is not None and length < 3.8 and not (hp is not None and 40 <= hp <= 90):
        return True
    if price is not None and price < 1500 and hp is None and (length is None or length < 4.2):
        return True
    if price == 0:
        return True
    return False

def _inf_cfg(cfg):
    return ((cfg or {}).get("criteria") or {}).get("inflatables") or {}

def inflatable_reason(record, cfg=None):
    """Why a record is a pneumatique / semi-rigide (RIB), or None. Careful with rigid boats sold *with* a dinghy."""
    cfg = cfg or load_config()
    ic = _inf_cfg(cfg)
    if record.get("category") == "inflatable":
        return "catégorie pneumatique / semi-rigide"
    title = norm_text(str(record.get("title") or ""))
    typ = norm_text(" ".join(str(record.get(k) or "") for k in ("type_label", "category_label") if record.get(k) not in (None, NA)))
    brand = norm_text(str(record.get("brand") or "")) if record.get("brand") not in (None, NA) else ""
    model = norm_text(str(record.get("model") or "")) if record.get("model") not in (None, NA) else ""
    mat = norm_text(str(record.get("material") or "")) if record.get("material") not in (None, NA) else ""
    desc = norm_text(" ".join(str(record.get(k) or "") for k in ("description_excerpt", "snippet") if record.get(k) not in (None, NA)))
    kws = [norm_text(k) for k in ic.get("keywords") or []]
    kw_re = r"\b(" + "|".join(re.escape(k) for k in sorted(kws, key=len, reverse=True)) + r")\b" if kws else None
    tender = r"(annexe|beiboot|dinghy|tender|pour (un |une )?(bateau )?pneumatique|remorque|anhanger|trailer pour|moteur pour|fur schlauchboot|plus (un |une )?(petit )?(bateau )?pneumatique|avec (un |une |son )?(petit )?(canot |bateau )?pneumatique|\+ ?(un )?(canot |bateau )?pneumatique)"
    # 1. title / site type
    if kw_re:
        m = re.search(kw_re, title)
        if m and not re.search(tender + r".{0,25}" + re.escape(m.group(1)), title):
            return f"titre : « {m.group(1)} »"
        m = re.search(kw_re, typ)
        if m:
            return f"type : « {m.group(1)} »"
    # 2. hull material
    rigid_mat = re.search(r"(polyester|fibre|gfk|grp|alu|bois|holz|acier|stahl|composite|hdpe|polyethylene)", mat)
    if mat == "pvc/hypalon" and "hypalon" not in desc + " " + title:
        mat = ""          # rich_fields guess from free text (e.g. "bâche PVC" on a rigid boat): not a hull material
    if mat and not rigid_mat:
        for mm in ic.get("materials") or []:
            if re.search(r"\b" + re.escape(norm_text(mm)) + r"\b", mat):
                return f"matériau : {record.get('material')}"
    # 3. brands that only build inflatables / RIBs
    structured = record.get("source") in ("bateau24", "lakeboat", "aquaboat")      # brand from a form field, not guessed from text
    for b in ic.get("brands_inflatable_only") or []:
        nb = norm_text(b)
        if brand and (structured or re.search(r"\b" + re.escape(nb) + r"\b", title)) and (brand == nb or brand.startswith(nb + " ") or brand.startswith(nb + "-")):
            return f"marque : {record.get('brand')}"
    for b in ic.get("brands_title_safe") or []:
        if re.search(r"\b" + norm_text(b) + r"\b", title):
            return f"marque (titre) : {b.split(chr(92))[0].strip()}"
    for b, models in (ic.get("brands_mixed") or {}).items():
        nb = norm_text(b)
        if (brand.startswith(nb) or re.search(r"\b" + re.escape(nb) + r"\b", title)) and re.search(models, title + " " + model):
            return f"gamme pneumatique : {b}"
    # 4. description: an inflatable keyword describing the boat itself (not a dinghy sold with it), and no rigid hull mentioned
    if kw_re and desc:
        hits = [m for m in re.finditer(kw_re, desc)
                if not re.search(tender + r".{0,30}$", desc[max(0, m.start() - 45):m.start() + len(m.group(1))])]
        strong = [m for m in hits if m.group(1) not in ("zodiac", "rib", "hypalon", "boudin", "boudins") or m.start() < 40]
        rigid_desc = re.search(r"(coque (en )?(polyester|alu|aluminium|bois|fibre)|polyesterrumpf|gfk[- ]rumpf|aluminiumrumpf|bateau (en )?(polyester|alu|aluminium)|coque rigide en (polyester|alu))", desc)
        if not rigid_desc and (strong or len(hits) >= 2):
            return f"description : « {(strong or hits)[0].group(1)} »"
    return None

def is_inflatable(record, cfg=None):
    cfg = cfg or load_config()
    if not ((cfg.get("criteria") or {}).get("exclude_inflatables")):
        return False
    return inflatable_reason(record, cfg) is not None

def classify(record, cfg=None, peers=None):
    """Return a dict: bucket, zone, lake, opportunite, reasons, score."""
    cfg = cfg or load_config()
    cr = cfg["criteria"]
    reasons = []
    cat = record.get("category")
    if cr.get("exclude_inflatables") and inflatable_reason(record, cfg):
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False,
                "reasons": ["pneumatique", inflatable_reason(record, cfg)], "score": 0, "config_version": cfg.get("version")}
    if clearly_excluded_type(record, cfg) or clearly_out_of_scope(record, cfg):
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["type"], "score": 0}

    if cat not in (cr.get("include_categories") or ["open", "motor", "inflatable"]):
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["category"], "score": 0}

    engine = record.get("engine_type")
    if engine in (None, "", NA) and re.search(r"\b(correct craft|mastercraft|malibu|moomba|centurion|tige|axis wake|supra (saltare|comp|launch|sa\b)|ski nautique|sport nautique)\b", norm_text(str(record.get("title") or ""))):
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["engine_type", "ski-boat in-bord"], "score": 0}
    is_out = engine == "outboard" or infer_outboard(record)
    if engine in ("inboard", "electric", "none") and not is_out:
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["engine_type"], "score": 0}

    hp, width, length, price = num(record.get("hp")), num(record.get("width_m")), num(record.get("length_m")), num(record.get("price_chf"))

    # clearly out of range on a known field → drop
    if hp is not None and not (cr["hp_min"] <= hp <= cr["hp_max"]):
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["hp_out_of_range"], "score": 0}
    if width is not None and width > cr["width_m_max"]:
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["width_out_of_range"], "score": 0}
    if length is not None and length > cr["length_m_max"]:
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["length_out_of_range"], "score": 0}
    if price is not None and price > cr["price_chf_max"]:
        return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["price_out_of_range"], "score": 0}

    unknown = []
    if not is_out and engine in (NA, None, "", "N/A"):
        unknown.append("engine_type")
    if hp is None:
        unknown.append("hp")
    if width is None:
        unknown.append("width_m")
    if length is None:
        unknown.append("length_m")
    if price is None:
        unknown.append("price_chf")

    zone, lake, zmethod = zone_for(record, cfg)
    opportunite = is_opportunite(record, peers, cfg) if not unknown else False

    if unknown:
        # Keep unknowns only when the rest of the profile still looks like a 40–90 CV hors-bord
        plausible = (
            (hp is not None and cr["hp_min"] <= hp <= cr["hp_max"])
            or (is_out and (length is None or length >= 3.8) and (price is None or price >= 2000))
            or (length is not None and length >= 4.2 and (price is None or price >= 3000) and engine not in ("inboard", "electric", "none"))
        )
        if not plausible:
            return {"bucket": "excluded", "zone": None, "lake": None, "opportunite": False, "reasons": ["implausible_unknown"], "score": 0}
        bucket = "a_verifier"
        reasons = unknown
        score = 20 + (40 if zone == "zone1" else 0)
    else:
        bucket = zone  # zone1 or zone2
        reasons = [zmethod]
        score = (100 if zone == "zone1" else 50) + (30 if opportunite else 0)
        if record.get("trailer") == "yes":
            score += 8
    return {
        "bucket": bucket,
        "zone": zone,
        "lake": lake,
        "opportunite": bool(opportunite),
        "reasons": reasons,
        "score": score,
        "config_version": cfg.get("version"),
    }

def is_opportunite(record, peers, cfg):
    ocfg = (cfg or {}).get("opportunite") or {}
    price = num(record.get("price_chf"))
    if price is None:
        return False
    length, hp, year = num(record.get("length_m")), num(record.get("hp")), num(record.get("year"))
    trailer = record.get("trailer") == "yes"
    text = norm_text(_haystack(record))
    recent_engine = bool(re.search(r"(moteur (neuf|revise|revisee|recent|nouveau)|motor (neu|revidiert|uberholt)|peu d.?heures|wenig stunden|few hours)", text))
    recent_year = year is not None and year >= ocfg.get("recent_year_from", 2008)

    peer_prices = []
    if peers:
        dl = ocfg.get("peer_length_m", 1.2)
        dh = ocfg.get("peer_hp", 20)
        for p in peers:
            if p.get("id") == record.get("id"):
                continue
            if p.get("category") != record.get("category"):
                continue
            pp = num(p.get("price_chf"))
            if pp is None:
                continue
            pl, ph = num(p.get("length_m")), num(p.get("hp"))
            if length is not None and pl is not None and abs(pl - length) > dl:
                continue
            if hp is not None and ph is not None and abs(ph - hp) > dh:
                continue
            if (length is None or pl is None) and (hp is None or ph is None):
                continue
            peer_prices.append(pp)
    median = None
    if len(peer_prices) >= ocfg.get("min_peers", 3):
        s = sorted(peer_prices)
        median = s[len(s) // 2]

    if median:
        if price <= median * ocfg.get("price_vs_median", 0.8):
            return True
        if trailer and price <= median * ocfg.get("price_vs_median_with_trailer", 0.9):
            return True
        if (recent_year or recent_engine) and price <= median * 0.85:
            return True
    # without enough peers: still flag a clear "worth the trip" combo far from the lakes
    if trailer and (recent_year or recent_engine) and price <= 10000 and hp and 40 <= hp <= 90:
        return True
    return False

def classify_all(records, cfg=None):
    cfg = cfg or load_config()
    recs = list(records)
    out = {}
    for r in recs:
        out[r["id"]] = classify(r, cfg, peers=recs)
    return out

def daily_candidates(records, today, cfg=None):
    """Matching boats not yet sent, for the daily digest.
    Marks from the unfiltered baseline date are treated as already sent even on that same day."""
    cfg = cfg or load_config()
    baseline = str((cfg.get("dedup") or {}).get("baseline_sent_on") or "")
    classified = classify_all(records, cfg)
    kept = []
    for r in records:
        info = classified[r["id"]]
        if info["bucket"] == "excluded":
            continue
        sent = r.get("sent_in_digest")
        if sent in (NA, None, ""):
            kept.append((r, info))
            continue
        if sent == today and sent != baseline:
            kept.append((r, info))
    return kept

def selection_candidates(records, cfg=None):
    """All current matches, ignoring sent_in_digest (one-time sélection initiale)."""
    cfg = cfg or load_config()
    classified = classify_all(records, cfg)
    return [(r, classified[r["id"]]) for r in records if classified[r["id"]]["bucket"] != "excluded"]

def counts(pairs):
    c = {"zone1": 0, "zone2": 0, "a_verifier": 0, "opportunite": 0, "total": len(pairs)}
    for r, info in pairs:
        if info["bucket"] == "a_verifier":
            c["a_verifier"] += 1
        elif info["zone"] == "zone1":
            c["zone1"] += 1
        else:
            c["zone2"] += 1
        if info.get("opportunite"):
            c["opportunite"] += 1
    return c

# --------------------------------------------------------------------------- enrich
def enrich_from_cache(record, fetch_if_missing=False, sleep=0.4):
    """Re-parse the cached detail page (and optionally fetch it) to fill hp/width/length/engine."""
    import collect
    key = record.get("id") or ""
    cache_f = collect.HTML_CACHE / (re.sub(r"[^\w.-]", "_", key) + ".html")
    html = None
    if cache_f.exists():
        html = cache_f.read_text(errors="replace")
    elif fetch_if_missing and record.get("url"):
        try:
            html = collect.get_cached(record["url"], key, sleep=sleep)
        except Exception as ex:
            log("enrich fetch fail", key, ex)
            return {}
    if not html:
        return {}
    found = {}
    src = record.get("source")
    try:
        if src in ("tutti", "anibis"):
            d = collect.next_data(html)
            if d:
                body = ""
                for q in d["props"]["pageProps"]["dehydratedState"]["queries"]:
                    if q["queryKey"][0] == "GetListingDetails":
                        L = q["state"]["data"]["listing"]
                        body = L["localization"].get("body") or ""
                        break
                text = (record.get("title") or "") + " . " + body
                for k, v in collect.extract_specs(text).items():
                    found[k] = v
                for k, v in collect.rich_fields(record.get("title") or "", body).items():
                    found.setdefault(k, v)
        elif src == "bateau24":
            import html as H
            kv = {}
            for k, v in re.findall(r'list__key">([^<]*)</span><span class="list__value">(.*?)</span>', html, re.S):
                k = H.unescape(k).strip()
                v = re.sub(r"\s+", " ", H.unescape(re.sub("<[^>]+>", " ", v))).strip()
                if k not in kv or len(v) > len(kv[k]):
                    kv[k] = v
            g = kv.get
            if g("Longueur x Largeur"):
                mm = re.findall(r"([\d.]+) m", g("Longueur x Largeur"))
                if len(mm) >= 1:
                    found["length_m"] = float(mm[0])
                if len(mm) >= 2:
                    found["width_m"] = float(mm[1])
            if g("Propulsion"):
                pz = collect.norm(g("Propulsion"))
                found["engine_type"] = "outboard" if "hors" in pz else "electric" if "electr" in pz else "inboard"
            pw = g("Puissance du moteur")
            if pw:
                mh = re.search(r"([\d.]+)\s*cv", pw, re.I)
                mk = re.search(r"([\d.]+)\s*kW", pw, re.I)
                if mh:
                    found["hp"] = float(mh.group(1))
                if mk:
                    found["kw"] = float(mk.group(1))
            if g("Moteur"):
                found["engine_model"] = g("Moteur")
            dsc = re.search(r'id="description-content">(.*?)</div>', html, re.S)
            body = ""
            if dsc:
                body = re.sub(r"\s+", " ", H.unescape(re.sub("<[^>]+>", " ", dsc.group(1).replace("<br>", " ")))).strip()
            for k, v in collect.extract_specs((record.get("title") or "") + " . " + body).items():
                found.setdefault(k, v)
            for k, v in collect.rich_fields(record.get("title") or "", body).items():
                found.setdefault(k, v)
    except Exception as ex:
        log("enrich parse fail", key, ex)
        return {}
    # keep only useful filled fields
    useful = {}
    for k in ("hp", "kw", "width_m", "length_m", "engine_type", "engine_brand", "engine_model", "trailer", "year"):
        if k in found and found[k] not in (None, "", NA):
            useful[k] = found[k]
    return useful

def needs_enrich(record, cfg=None):
    cfg = cfg or load_config()
    if clearly_excluded_type(record, cfg) or is_inflatable(record, cfg):
        return False
    if record.get("category") not in (cfg["criteria"].get("include_categories") or []):
        return False
    price = num(record.get("price_chf"))
    if price is not None and price > cfg["criteria"]["price_chf_max"]:
        return False
    engine = record.get("engine_type")
    if engine in ("inboard", "electric", "none") and not infer_outboard(record):
        return False
    hp, width, length = num(record.get("hp")), num(record.get("width_m")), num(record.get("length_m"))
    if hp is not None and not (cfg["criteria"]["hp_min"] <= hp <= cfg["criteria"]["hp_max"]):
        return False
    if width is not None and width > cfg["criteria"]["width_m_max"]:
        return False
    if length is not None and length > cfg["criteria"]["length_m_max"]:
        return False
    return (hp is None or width is None or length is None or engine in (NA, None, "", "N/A"))

def enrich_records(records, fetch_missing=True, limit_fetches=40, cfg=None):
    """Fill missing hp/width/length/engine from cached (or, if few, fetched) detail pages.
    Mutates records in place. Returns the count of records updated."""
    cfg = cfg or load_config()
    updated = 0
    fetches = 0
    for r in records:
        if not needs_enrich(r, cfg):
            continue
        import collect
        key = r.get("id") or ""
        cache_f = collect.HTML_CACHE / (re.sub(r"[^\w.-]", "_", key) + ".html")
        do_fetch = fetch_missing and (not cache_f.exists()) and fetches < limit_fetches
        if do_fetch:
            fetches += 1
        found = enrich_from_cache(r, fetch_if_missing=do_fetch)
        if not found:
            continue
        changed = False
        for k, v in found.items():
            cur = r.get(k)
            if cur in (None, "", NA) and v not in (None, "", NA):
                r[k] = v
                changed = True
        # derive kw/hp if one appeared
        if num(r.get("hp")) is None and num(r.get("kw")) is not None:
            r["hp"] = round(num(r["kw"]) / 0.7355, 1)
            changed = True
        if num(r.get("kw")) is None and num(r.get("hp")) is not None:
            r["kw"] = round(num(r["hp"]) * 0.7355, 1)
        if changed:
            updated += 1
    log(f"enrich: updated {updated} records, fetches {fetches}")
    return updated

def attach(record, info):
    """Shallow copy with _filtre for the site payload (master store stays clean)."""
    o = dict(record)
    o["_filtre"] = {
        "version": info.get("config_version"),
        "bucket": info["bucket"],
        "zone": info.get("zone"),
        "lake": info.get("lake"),
        "opportunite": bool(info.get("opportunite")),
        "reasons": info.get("reasons") or [],
        "score": info.get("score") or 0,
    }
    return o
