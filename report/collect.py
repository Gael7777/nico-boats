# -*- coding: utf-8 -*-
"""Nico Boats collector: pulls real used-boat listings from Swiss marketplaces.

Sources that work from the box (2026-11-15): tutti.ch, anibis.ch (Next.js __NEXT_DATA__ JSON),
bateau24.ch = boat24.com Swiss site (server-rendered HTML). Blocked: ricardo.ch (Cloudflare captcha /
error 1015), boat24.com international domain (Cloudflare challenge; bateau24.ch works).
Every listing keeps its own URL. Nothing is invented: missing fields stay None.
"""
import base64, codecs, html as H, json, math, re, sys, time, unicodedata
from pathlib import Path
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
GEO_UA = "nico-boats-digest/1.0 (+https://github.com/Gael7777/nico-boats)"
ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
GENEVA = (46.2044, 6.1432)          # Geneva centre (Molard)
PRICE_CAP = 30000                   # CHF, sane cap for "inexpensive"
S = requests.Session(); S.headers.update({"User-Agent": UA, "Accept-Language": "fr-CH,fr;q=0.9,de;q=0.8"})
STATUS = {}

def log(*a): print(*a, file=sys.stderr, flush=True)

def get(url, tries=3, sleep=0.8):
    for i in range(tries):
        try:
            r = S.get(url, timeout=30)
            time.sleep(sleep)
            if r.status_code == 200: return r.text
            log("HTTP", r.status_code, url); last = r.status_code
        except Exception as e:
            log("ERR", e, url); last = str(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed {url}: {last}")

HTML_CACHE = CACHE / "html"; HTML_CACHE.mkdir(exist_ok=True)
def get_cached(url, key, max_age_days=7, sleep=0.5):
    f = HTML_CACHE / (re.sub(r"[^\w.-]", "_", key) + ".html")
    if f.exists() and time.time() - f.stat().st_mtime < max_age_days * 86400:
        return f.read_text()
    h = get(url, sleep=sleep); f.write_text(h); return h

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s)

# ---------------------------------------------------------------- classification
BOAT = r"(\bboat\b|bateau|bateaux|boot\b|boote\b|boots\b|barca|barche|barque|voilier|voiliers|segelboot|segelyacht|segeljacht|segler|motorboot|motorbot|sportboot|fischerboot|kajutboot|kabinenboot|schlauchboot|pneumatique|semi-rigide|semi rigide|gommone|festrumpf|canot|deriveur|jolle|optimist\b|laser\b|yacht|jacht|daysailer|day cruiser|catamaran|katamaran|ruderboot|pedalo|tretboot|weidling|zodiac|\brib\b|bowrider|sloop|motoscafo|cabin cruiser|lacustre|cruiser|vaurien|ponton|annexe|beiboot|dinghy|tender|jet ?ski|jetski|scooter des mers|wassertöff|surprise\b|corsaire\b|toucan\b|h-boot|yngling|grinde|first \d|kielboot|quillard|kahn\b|pinasse|launch)"
BRANDS = r"\b(beneteau|jeanneau|bayliner|quicksilver|sea ?ray|mandli|boesch|dehler|dufour|bavaria|hanse|archambault|marine s\.?r\.?o|zar\b|williams|bombard|takacat|honwave|terhi|linder|buster|mercury inflatable|ranieri|cranchi|chaparral|four winns|glastron|campion|wellcraft|draco|fletcher|maxum|larson|regal|rio\b|sessa|saver|marinello|pioner|uttern|crescent|ryds|whaler|achilles|3d tender|lomac|joker|zodiac|avon\b|plastimo|parker|elan\b|etap|gib.?sea|kelt|neptun|catalina|hunter|varianta|sunbeam|hallberg|albin|nauticat|wirz|portofino|riva|lurssen|staempfli|stampfli)"
ACC_START = r"^(grand[- ]?voile|chandelles?|location\b|balcon|chandeliers?|spi\b|ber\b|rc\b|place\b|places\b|emplacement|\W*nouveau(te)? (en magasin|dans la boutique)|\W*produit neuf|nouveau berceau|taud|traineau|unite de commande|pioneer|poulie|couverture|pieces?\b|vis\b|halle|table\b|instruments?|coussin|\d+ palettes|palettes?|berceau|collecteur|chariot|opel|deux sieges|sieges?|tres rare moteur|\d+ moteurs|de la collection|haut-parleurs?|aquain|gm mercruiser|mercruiser|passerelle|roues?|marine - |moteur|motor\b|motoren|outboard|hors[- ]?bord|aussenborder|aussenbordmotor|fuoribordo|remorque|anhanger|anhaenger|trailer|bootsanhanger|bootstrailer|gilet|gilets|rettungsweste|schwimmweste|ancre|anker|ancora|bache|persenning|plane|helice|propeller|elica|voile\b|voiles\b|segel\b|grossegel|spinnaker|genois|fock|mat\b|mast\b|bome|baum|pare[- ]?battage|fender|taquet|echolot|sondeur|fishfinder|batterie|pompe|pumpe|chaine|chaines|corde|seil|leine|winch|winsch|kit\b|housse|support|halterung|place d.amarrage|bootsplatz|liegeplatz|bojenplatz|anlegeplatz|wakeboard|ski nautique|wasserski|gps|sup\b|stand ?up|kayak|kajak|canoe|canoë|kanu|kanadier|paddle|paddel|pagaie|rame|rames|ruder\b|riemen|hublot|cockpit|siege|sitz|lampe|feu|navigationslicht|cable|kabel|tank|reservoir|bidon|klampe|bimini|sprayhood|capote|cover|eau douce|toilette|wc|chauffage|heizung|radio|vhf|compas|kompass|autopilot|pilote|telecommande|steuer|volant|lenkrad|hydrofoil|foil|bouee|boje|tube|ringo|schleppring|planche|surf|kite|antenne|pare|scie|outil|livre|buch|modell|model|maquette|lego|playmobil|poster|tableau|bild|figur|jouet|spielzeug|uhr|montre|t-shirt|pull|veste|jacke|bottes|stiefel|chaussures|schuhe)"
ACC_ANY = r"(\brc\b|radiocommande|telecommande|ferngesteuert|(voiles?|mat|bome|spi|spinnaker|taud|bache) (de|pour|du) (bateau|voilier)|ber de stockage|bateau lit|lit bateau|lit enfant|lit pour enfant|\bcable\b|kabel|autos? ?- ?motos?|7j7|24h24|rachat|debarras|achete (tous|bateaux)|kaufe (boote|alle)|moteurs? de bateau|pieces de bateau|utilisation partagee|(taud|couverture|protection|vis|passerelle|coussin|sieges?|roues?|haut-parleurs?|instruments?|chariot|berceau|support|halle|table|radio|lautsprecher|traineau) (de|a|pour) (bateau|barca)|\bpour (bateau|bateaux|voilier|zodiac|pneumatique)|\bfur (boot|boote|segelboot|schlauchboot)|\bper (barca|barche|gommone)|\bfor (boat|boats)|maquette|modellbau|modellboot|model boat|bateau modele|rc boot|rc boat|ferngesteuert|teleguide|jouet|spielzeug|lego|playmobil|bootsplatz|liegeplatz|place d.amarrage|place de port|kayak|kajak|kanu|kanadier|canoe|\bsup\b|stand ?up paddle|paddleboard|luftmatratze|gonflable pour enfant|badeboot|schwimmring|pedalo de piscine)"

def classify_text(title, body):
    t, b = norm(title), norm(body)
    if re.search(ACC_ANY, t): return None
    boatish = re.search(BOAT, t) or re.search(BRANDS, t)
    if not boatish: return None
    if re.search(ACC_START, t) and not re.match(r"^(motorboot|motorbot|motoscafo|moteur.*bateau complet)", t): return None
    txt = t + " " + b
    if re.search(r"(pneumatique|schlauchboot|gommone|semi[- ]rigide|festrumpf|\brib\b|zodiac|hypalon|inflatable|aufblasbar|gonflable|takacat|bombard|honwave|achilles|3d tender|lomac|joker boat|grand\b.*\bg\d)", t): return "inflatable"
    if re.search(r"(jet ?ski|jetski|scooter des mers|seadoo|sea-doo|wassertöff|waverunner)", t): return "other"
    if re.search(r"(deriveur|jolle|optimist|laser\b|vaurien|420\b|470\b|finn\b|ruderboot|barque|aviron|weidling|annexe|beiboot|dinghy|tender|pedalo|tretboot|kahn\b|canot|rudern|row)", t): return "small"
    if re.search(r"(voilier|\ba voile|segel|\bvela\b|sail|daysailer|quillard|kielboot|surprise\b|corsaire|toucan|h-boot|yngling|grinde|lacustre|first \d|catamaran|katamaran|sloop|dehler|dufour|bavaria|hanse|archambault|elan\b|etap|kelt|neptun|catalina|hunter|varianta|sunbeam|hallberg|albin|wirz|5\.5|dragon|drachen|star boot|j/\d|j\d\d)", t): return "sail"
    if re.search(r"(cabine|kajut|kabinen|cabin|cruiser|hardtop|flybridge|timonier|wheelhouse|steuerhaus|couchette|kojen|wc\b|toilette)", txt) and not re.search(r"(bowrider|open\b)", t): return "motor"
    if re.search(r"(bowrider|open\b|console|fischerboot|bateau de peche|peche|fisch|angel|sportboot|bateau de sport|ski|wake|ponton|pontoon|day ?boat|runabout|motoscafo|mandli|marine s\.?r\.?o|motorboot|bateau a moteur|motorbot|aluboot|alu\b|lomac|quicksilver|bayliner|sea ?ray|four winns|glastron|chaparral|draco|fletcher|maxum|larson|regal|campion|wellcraft|rio\b|sessa|saver|marinello|uttern|crescent|ryds|silver\b|whaler|terhi|linder|buster|pioner|riva|boesch|portofino|cranchi|selva|chris craft|draco|windy|campion)", txt): return "open"
    if re.search(r"(\d+\s*(cv|ch|ps|hp)\b|\bkw\b|moteur|motor|outboard|aussenborder)", txt): return "open"
    if re.search(r"(voil|segel|sail|mat\b|mast\b|gennaker|spi\b)", txt): return "sail"
    return "other"

B24_TYPES = {
    "sail": ["yacht a voile", "daysailer", "quillard", "deriveur habitable", "catamaran a voile", "trimaran", "voilier classique", "goelette", "ketch", "yawl", "sloop", "cotre", "motorsailer", "voilier"],
    "small": ["deriveur", "bateau annexe", "bateau a rames", "pedalo", "optimist", "laser"],
    "inflatable": ["bateau pneumatique", "pneumatique pliable", "semi-rigide", "semi rigide"],
    "motor": ["bateau a cabine", "hardtop", "flybridge", "bateau timonier", "careneadeplacement", "carene a deplacement", "bateau a moteur classique", "bateau offshore", "peniche", "maison flottante", "catamaran a moteur", "trawler", "yacht a moteur", "bateau de travail", "navire"],
    "open": ["bowrider", "bateau de sport", "bateau a console", "deck boat", "ski nautique", "wakeboard", "bateau de peche", "ponton", "sloep", "day cruiser", "walkaround", "bateau electrique", "bateau a moteur"],
    "other": ["scooter de mer"],
}
B24_EXCLUDE = ["hors-bord", "moteur in-bord", "remorque", "accessoire", "place", "canoe", "kayak", "stand up"]

B24_BOAT_PATHS = {"voiliers": "sail", "bateauxamoteur": "open", "bateauxpneumatiques": "inflatable", "petitsbateaux": "small"}
def b24_keep(r):
    """Second-stage filter for boat24 rows (needs URL + detail specs): boats only, used/demo only, no tiny prices.
    Returns the category or None."""
    m = re.search(r"/chfr/([a-z]+)/", r["url"]); sect = m.group(1) if m else ""
    if sect not in B24_BOAT_PATHS: return None
    offer = norm((r.get("specs_raw") or {}).get("Type d'offre", ""))
    if offer.startswith("bateau neuf") or "location" in offer or "charter" in offer: return None
    if 0 < r["price_chf"] < 150: return None
    t = norm(r.get("type_label", "")); first = t.split(",")[0].strip()
    if re.search(r"(canoe|kayak|stand up|sup\b)", first): return None
    cat = classify_b24(r.get("type_label", "")) or B24_BOAT_PATHS[sect]
    if cat == "other":
        if re.search(r"(deck-boat|runabout|cockpit central|walkaround)", first): cat = "open"
        elif re.search(r"(timonerie|cabine)", first): cat = "motor"
        elif re.search(r"catamaran", first): cat = "sail" if sect == "voiliers" else "motor"
        elif re.search(r"scooter", first): cat = "other"
        else: cat = B24_BOAT_PATHS[sect]
    if sect == "voiliers" and cat in ("open", "motor"): cat = "sail"
    if sect == "bateauxpneumatiques": cat = "inflatable"
    return cat

def classify_b24(types):
    t = norm(types)
    first = t.split(",")[0].strip()
    if any(x in first for x in B24_EXCLUDE): return None
    for cat, keys in B24_TYPES.items():
        if any(k == first or k in first for k in keys): return cat
    for cat, keys in B24_TYPES.items():
        if any(k in t for k in keys): return cat
    return "other"

def year_from(text):
    """Build year: a year in the title part (before ' . '), or in the body only next to a year keyword."""
    import datetime
    cur = datetime.date.today().year
    t = norm(text).replace(",", ".")
    title, _, body = t.partition(" . ")
    m = re.search(r"\b(19[4-9]\d|20[0-2]\d)\b", title)
    if not m:
        m = re.search(r"(?:annee|construction|construit|construite|baujahr|jahrgang|jg\.?|built|anno|immatricul\w*|mise en (?:circulation|service)|de|von|du|year)\s*:?\s*(?:en\s*)?(19[4-9]\d|20[0-2]\d)\b", body)
    if m and int(m.group(1)) <= cur: return int(m.group(1))
    return None

def extract_specs(text):
    t = norm(text).replace(",", ".")
    out = {}
    y = year_from(text)
    if y: out["year"] = y
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*(cv|ch|ps|hp)\b", t)
    if m and 1 <= float(m.group(1)) <= 1200: out["engine"] = f"{float(m.group(1)):g} {m.group(2).upper().replace('CH','CV')}"
    else:
        m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*kw\b", t)
        if m and 0.2 <= float(m.group(1)) <= 900: out["engine"] = f"{float(m.group(1)):g} kW"
    m = re.search(r"(?:longueur|lange|laenge|length|lunghezza|loa)\D{0,12}(\d{1,2}(?:\.\d{1,2})?)\s*m\b", t) or \
        re.search(r"\b(\d{1,2}\.\d{1,2})\s*m\b", t) or re.search(r"\b(\d{1,2}(?:\.\d{1,2})?)\s*(?:m|meter|metres|metre|mètres)\s*(?:x|lang|long)", t)
    if m and 1.8 <= float(m.group(1)) <= 16: out["length_m"] = float(m.group(1))
    return out

ENGINE_BRANDS = ["volvo penta", "mercruiser", "mercury", "yamaha", "honda", "suzuki", "tohatsu", "evinrude", "johnson", "mariner", "torqeedo", "selva", "yanmar", "nanni", "vetus", "nissan", "parsun", "minn kota", "epropulsion", "bukh", "bmw", "pleasurecraft", "indmar", "ilmor", "craftsman"]
BRAND_CANON = {"mandli": "Mändli", "sea ray": "Sea Ray", "searay": "Sea Ray", "marine s.r.o": "Marine s.r.o.", "marine sro": "Marine s.r.o.", "four winns": "Four Winns", "boston whaler": "Boston Whaler", "whaler": "Boston Whaler", "gib sea": "Gib'Sea", "gibsea": "Gib'Sea", "3d tender": "3D Tender", "hallberg": "Hallberg-Rassy"}

def rich_fields(title, text):
    """Optimistic extraction from free text (FR/DE/IT/EN). Only what is literally written."""
    t = norm(title + " . " + text).replace(",", ".")
    o = {}
    m = re.search(BRANDS, norm(title)) or re.search(BRANDS, t)
    if m:
        b = m.group(1).strip(); o["brand"] = BRAND_CANON.get(b, b.title())
        mm = re.search(re.escape(b) + r"\s+([a-z0-9][\w.\-/]*(?:\s+[0-9][\w.\-]*)?)", norm(title))
        if mm and not re.match(r"^(avec|mit|with|en|in|et|und|a|de|du|pour|fur|sans|ohne)$", mm.group(1)): o["model"] = mm.group(1).upper() if len(mm.group(1)) <= 4 else mm.group(1).title()
    m = re.search(r"\b(\d{1,2}(?:\.\d{1,2})?)\s*(?:m)?\s*x\s*(\d(?:\.\d{1,2})?)\s*m\b", t)
    if m and 1.8 <= float(m.group(1)) <= 16 and 0.8 <= float(m.group(2)) <= 6: o["length_m"] = float(m.group(1)); o["width_m"] = float(m.group(2))
    m = re.search(r"(?:largeur|breite|width|larghezza)\D{0,10}(\d(?:\.\d{1,2})?)\s*m\b", t)
    if m and "width_m" not in o and 0.8 <= float(m.group(1)) <= 6: o["width_m"] = float(m.group(1))
    if re.search(r"(hors[- ]?bord|aussenbord|ausserbord|fuoribordo|outboard)", t): o["engine_type"] = "outboard"
    elif re.search(r"(in[- ]?bord|inbord|z[- ]?drive|z-antrieb|sterndrive|d-drive|saildrive|entrobordo)", t): o["engine_type"] = "inboard"
    elif re.search(r"(electrique|elektro|electric|torqeedo|epropulsion|minn kota)", t): o["engine_type"] = "electric"
    elif re.search(r"(sans moteur|ohne motor|senza motore)", t): o["engine_type"] = "none"
    for eb in ENGINE_BRANDS:
        if re.search(r"\b" + eb + r"\b", t): o["engine_brand"] = eb.title(); break
    if re.search(r"\b(diesel|gasoil)\b", t): o["fuel"] = "diesel"
    elif re.search(r"\b(essence|benzin|benzina|petrol|gasoline|sans plomb|bleifrei)\b", t): o["fuel"] = "petrol"
    elif o.get("engine_type") == "electric": o["fuel"] = "electric"
    m = re.search(r"(\d{1,5})\s*(?:h\b|heures|std\b|stunden|betriebsstunden|ore\b|hours)", t)
    if m and 0 < int(m.group(1)) < 20000 and not re.search(r"\d{1,5}\s*h\s*(?:00|30)", m.group(0)): o["hours"] = int(m.group(1))
    m = re.search(r"(\d{1,3}(?:\.\d)?)\s*(?:m2|m²|qm)\b", t)
    if m and 2 <= float(m.group(1)) <= 200: o["sail_area_m2"] = float(m.group(1))
    m = re.search(r"(\d{1,2})\s*(?:couchettes|kojen|schlafplatze|schlafplaetze|posti letto|berths|places? de couchage)", t)
    if m: o["berths"] = int(m.group(1))
    for k, v in [(r"(polyester|gfk|fibre de verre|fiberglass|vetroresina|grp)", "polyester/GRP"), (r"\b(bois|holz|legno|wood|acajou|mahagoni)\b", "wood"),
                 (r"\b(alu|aluminium|aluminum)\b", "aluminium"), (r"\b(acier|stahl|steel)\b", "steel"), (r"(hypalon|pvc)", "PVC/Hypalon")]:
        if re.search(k, t): o["material"] = v; break
    if re.search(r"(sans remorque|ohne anhanger|ohne trailer|senza carrello)", t): o["trailer"] = "no"
    elif re.search(r"(remorque|anhanger|anhaenger|trailer|carrello)", t): o["trailer"] = "yes"
    if re.search(r"(sans place|ohne (liege|boots)?platz|ohne liegeplatz|place non comprise|sans amarrage|senza posto)", t): o["mooring_included"] = "no"
    elif re.search(r"(avec (sa |la )?place|place d.amarrage (incluse|comprise|disponible|possible)|inkl\.? (liege|boots|bojen)?platz|mit (liege|boots|bojen)platz|liegeplatz (inklusive|vorhanden|kann ubernommen)|posto barca incluso|reprise de la place)", t): o["mooring_included"] = "yes"
    for k, v in [(r"(a renover|a restaurer|bastler|restaurationsobjekt|to restore|da restaurare|pour bricoleur|defekt|epave)", "to restore"),
                 (r"(tres bon etat|sehr guter zustand|sehr gut erhalten|ottimo stato|excellent etat|top zustand|wie neu|comme neuf|etat neuf)", "very good"),
                 (r"(bon etat|guter zustand|gut erhalten|buono stato|good condition)", "good"), (r"(etat moyen|gebrauchsspuren|usure)", "fair")]:
        if re.search(k, t): o["condition"] = v; break
    return o

def parse_price(s):
    if s is None: return None
    n = norm(s)
    if any(w in n for w in ["gratuit", "gratis", "kostenlos", "free", "a donner", "zu verschenken"]): return 0
    d = re.sub(r"[^\d]", "", n.split(".-")[0].split(".–")[0])
    return int(d) if d else None

# ---------------------------------------------------------------- SMG (tutti / anibis)
SMG = {
    "tutti": "https://www.tutti.ch/fr/q/bateaux-accessoires/Ak8ClYm9hdHOUwMDAwA?sorting=newest&page={p}",
    "anibis": "https://www.anibis.ch/fr/q/bateaux-accessoires/Ak8ClYm9hdHOUwMDAwA?sorting=newest&page={p}",
}
def next_data(h):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    return json.loads(m.group(1)) if m else None

def collect_smg(src, max_pages=60):
    out, seen = [], set(); total = None
    for p in range(1, max_pages + 1):
        d = next_data(get(SMG[src].format(p=p)))
        q = [q for q in d["props"]["pageProps"]["dehydratedState"]["queries"] if q["queryKey"][0].startswith("SearchListings")][0]
        L = q["state"]["data"]["listings"]; total = L["totalCount"]
        new = 0
        for e in L["edges"]:
            n = e["node"]; lid = n["listingID"]
            if lid in seen: continue
            seen.add(lid); new += 1
            out.append(n)
        log(f"{src} page {p}: +{new} (total {total})")
        if new == 0 or len(seen) >= total: break
    STATUS[src] = {"ok": True, "raw": len(out), "total_reported": total}
    res = []
    for n in out:
        title = n["localization"]["title"].strip(); body = n["localization"].get("body") or ""
        price = parse_price(n.get("formattedPrice"))
        cat = classify_text(title, body)
        if cat is None or price is None: continue
        if price > PRICE_CAP: continue
        if 0 < price < 150: continue           # below this it's an accessory, not a boat
        pc = n.get("postcodeInformation") or {}
        res.append({
            "id": f"{src}:{n['listingID']}", "source": src, "title": title, "category": cat, "price_chf": price,
            "price_label": n.get("formattedPrice"), "postcode": pc.get("postcode"), "town": pc.get("locationName"),
            "canton": (pc.get("canton") or {}).get("shortName"),
            "url": f"https://www.{src}.ch/fr/vi/{n['listingID']}", "thumb": ((n.get("thumbnail") or {}).get("normalRendition") or {}).get("src"),
            "posted": (n.get("timestamp") or "")[:10], "snippet": body[:400], "lat": None, "lon": None,
        })
    # detail pages: full description + exact coordinates
    for r in res:
        try:
            d = next_data(get_cached(r["url"], r["id"]))
            for q in d["props"]["pageProps"]["dehydratedState"]["queries"]:
                if q["queryKey"][0] == "GetListingDetails":
                    L = q["state"]["data"]["listing"]
                    r["snippet"] = (L["localization"].get("body") or r["snippet"])[:1500]
                    c = L.get("coordinates") or {}
                    r["lat"], r["lon"] = c.get("latitude"), c.get("longitude")
                    si = L.get("sellerInfo") or {}
                    r["seller_type"] = "dealer" if si.get("subscriptionInfo") or si.get("logoURL") else "private"
                    imgs = L.get("images") or []
                    if imgs: r["photo"] = imgs[0]["rendition"]["src"]
                    if not r["thumb"] and imgs: r["thumb"] = imgs[0]["rendition"]["src"]
                if q["queryKey"][0] == "Placements":
                    kv = (q["state"]["data"] or {}).get("custom_targeting", {}).get("tutti_kvadvertiser")
                    if kv and kv[0]: r["seller_type"] = "dealer" if kv[0] != "private" else "private"
        except Exception as e:
            log("detail fail", r["url"], e)
        cat2 = classify_text(r["title"], r["snippet"])
        if cat2: r["category"] = cat2
        r.update({k: v for k, v in extract_specs(r["title"] + " . " + r["snippet"]).items()})
        for k, v in rich_fields(r["title"], r["snippet"]).items(): r.setdefault(k, v)
    STATUS[src]["kept"] = len(res)
    return res

# ---------------------------------------------------------------- bateau24.ch (boat24 Swiss site)
B24_LIST = "https://www.bateau24.ch/chfr/bateauxdoccasion/?whr=CHF&prs_max={cap}&page={off}"
FOREIGN = ["allemagne", "italie", "france", "autriche", "croatie", "pays-bas", "espagne", "slovenie", "grece", "turquie", "pologne", "belgique", "danemark", "suede", "norvege", "portugal", "hongrie", "republique tcheque", "royaume-uni", "monaco", "malte", "montenegro", "finlande", "lac de garde", "mer", "adriatique", "mediterranee"]

def collect_b24(max_pages=120):
    items, seen = [], set()
    for i in range(max_pages):
        h = get(B24_LIST.format(cap=PRICE_CAP, off=i * 20))
        blocks = h.split('<div class="blurb__main">')[1:]
        new = 0
        for blk in blocks:
            t = re.search(r'class="blurb__title"><a href="([^"]+)"[^>]*>([^<]+)', blk)
            if not t: continue
            url = t.group(1); lid = re.search(r"/detail/(\d+)/", url).group(1)
            if lid in seen: continue
            seen.add(lid); new += 1
            g = lambda pat: (re.search(pat, blk, re.S).group(1).strip() if re.search(pat, blk, re.S) else None)
            facts = dict((k, v) for v, k in re.findall(r'blurb__value">([^<]*)</span><span class="blurb__key">([^<]*)', blk))
            pr = g(r'blurb__price[^>]*>(.*?)</p>'); pr = re.sub("<[^>]+>", "", pr or "").strip()
            items.append({"lid": lid, "url": url, "title": H.unescape(t.group(2)), "types": H.unescape(g(r'blurb__title-header">([^<]*)') or ""),
                          "subtitle": H.unescape(g(r'blurb__subtitle">([^<]*)') or ""), "loc": H.unescape(g(r'blurb__location">([^<]*)') or ""),
                          "price_label": pr, "facts": {H.unescape(k): H.unescape(v) for k, v in facts.items()}})
        # thumbnails are in the block before blurb__main; map by listing id
        for m in re.finditer(r'thumbs/(?:large|small)/(\d+)-(\d+)\.jpg', h):
            for it in items:
                if it["lid"] == m.group(1) and "thumb" not in it:
                    it["thumb"] = f"https://static.b24.co/thumbs/xlarge/{m.group(1)}-{m.group(2)}.jpg"
        log(f"bateau24 page {i+1}: +{new}")
        if new == 0 or len(blocks) < 20: break
    STATUS["bateau24"] = {"ok": True, "raw": len(items)}
    res = []
    for it in items:
        cat = classify_b24(it["types"])
        price = parse_price(it["price_label"]) if "CHF" in it["price_label"] else None
        if cat is None or price is None or price > PRICE_CAP: continue
        if any(f in norm(it["loc"]) for f in FOREIGN): continue
        f = it["facts"]; r = {"id": f"bateau24:{it['lid']}", "source": "bateau24", "title": it["title"], "category": cat,
             "price_chf": price, "price_label": it["price_label"], "url": it["url"], "thumb": it.get("thumb"),
             "type_label": it["types"], "region": it["loc"], "snippet": it["subtitle"], "lat": None, "lon": None,
             "postcode": None, "town": None, "canton": None, "posted": None}
        dim = f.get("Dimensions")
        if dim and re.match(r"[\d.]+ x", dim): r["length_m"] = float(dim.split(" x ")[0])
        if f.get("Puissance du moteur"): r["engine"] = f["Puissance du moteur"].replace(".0 ", " ").replace("cv", "CV")
        if f.get("Année de fabrication", "").isdigit(): r["year"] = int(f["Année de fabrication"])
        res.append(r)
    # detail pages: structured key/value spec list, location, description, seller
    for r in res:
        try:
            h = get_cached(r["url"], r["id"], sleep=0.4)
            kv = {}
            for k, v in re.findall(r'list__key">([^<]*)</span><span class="list__value">(.*?)</span>', h, re.S):
                k = H.unescape(k).strip(); v = re.sub(r"\s+", " ", H.unescape(re.sub("<[^>]+>", " ", v))).strip()
                if k not in kv or len(v) > len(kv[k]): kv[k] = v
            r["specs_raw"] = kv
            loc = re.search(r'<div id="location">.*?<p class="text">(.*?)</p>', h, re.S)
            if loc:
                parts = [p.strip() for p in H.unescape(re.sub("<[^>]+>", "", loc.group(1))).split("»") if p.strip()]
                if parts: r["region"] = parts[0]
                if len(parts) > 1: r["town"] = parts[-1]
            dsc = re.search(r'id="description-content">(.*?)</div>', h, re.S)
            if dsc: r["snippet"] = re.sub(r"\s+", " ", H.unescape(re.sub("<[^>]+>", " ", dsc.group(1).replace("<br>", " ")))).strip()[:1500]
            r["seller_type"] = "dealer" if re.search(r'href="https://www\.bateau24\.ch/chfr/professionnels/\d+/', h) else "private"
            ph = re.search(r'https://static\.b24\.co/fotos/(?:big|large|medium)/[^"\s,]+\.jpg', h)
            if ph: r["photo"] = ph.group(0)
            g = kv.get
            if g("Longueur x Largeur"):
                mm = re.findall(r"([\d.]+) m", g("Longueur x Largeur"))
                if len(mm) >= 1: r["length_m"] = float(mm[0])
                if len(mm) >= 2: r["width_m"] = float(mm[1])
            if g("Fabricant"): r["brand"] = g("Fabricant")
            if g("Modèle"): r["model"] = g("Modèle")
            if g("Année de fabrication", "")[:4].isdigit(): r["year"] = int(g("Année de fabrication")[:4])
            if g("État"): r["condition"] = g("État")
            if g("Matériau"): r["material"] = g("Matériau")
            if g("Carburant"): r["fuel"] = re.sub(r"^[\d\s]*l\s+", "", g("Carburant"))
            if g("Heures Moteur"): r["hours"] = int(re.sub(r"\D", "", g("Heures Moteur")) or 0) or None
            if g("Nombre de couchettes"): r["berths"] = int(re.sub(r"\D", "", g("Nombre de couchettes")) or 0) or None
            if g("Surface de voilure") or g("Surface vélique"): r["sail_area_raw"] = g("Surface de voilure") or g("Surface vélique")
            if g("Propulsion"):
                pz = norm(g("Propulsion")); r["engine_type"] = "outboard" if "hors" in pz else "electric" if "electr" in pz else "inboard"
            if g("Moteur"):
                r["engine_model"] = g("Moteur")
                for eb in ENGINE_BRANDS:
                    if eb in norm(g("Moteur")): r["engine_brand"] = eb.title(); break
            pw = g("Puissance du moteur")
            if pw:
                mh = re.search(r"([\d.]+)\s*cv", pw); mk = re.search(r"([\d.]+)\s*kW", pw)
                if mh: r["hp"] = float(mh.group(1))
                if mk: r["kw"] = float(mk.group(1))
        except Exception as e:
            log("b24 detail fail", r["url"], e)
        for k, v in extract_specs(r["title"] + " . " + (r.get("snippet") or "")).items():
            r.setdefault(k, v)
        for k, v in rich_fields(r["title"], r.get("snippet") or "").items():
            r.setdefault(k, v)
    res = [r for r in res if b24_keep(r)]
    for r in res: r["category"] = b24_keep(r)
    STATUS["bateau24"]["kept_before_geo"] = len(res)
    return res

# ---------------------------------------------------------------- geo
def _load(p):
    return json.loads(p.read_text()) if p.exists() else {}
GEO = CACHE / "geocode.json"; ROUTE = CACHE / "routes.json"

def geocode(q, countries="ch"):
    c = _load(GEO); key = f"{countries}|{q}"
    if key in c: return c[key]
    time.sleep(1.1)
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "json", "limit": 1, "countrycodes": countries, "addressdetails": 1},
                         headers={"User-Agent": GEO_UA}, timeout=30).json()
        val = None
        if r:
            a = r[0].get("address", {})
            val = {"lat": float(r[0]["lat"]), "lon": float(r[0]["lon"]), "cc": a.get("country_code"),
                   "canton": a.get("ISO3166-2-lvl4", "").replace("CH-", "") or None, "name": r[0].get("display_name", "")[:120]}
    except Exception as e:
        log("geocode err", q, e); return None
    c[key] = val; GEO.write_text(json.dumps(c, ensure_ascii=False, indent=0)); return val

def haversine(a, b):
    R = 6371.0; la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def road_km(lat, lon):
    c = _load(ROUTE); key = f"{lat:.3f},{lon:.3f}"
    if key in c: return c[key]["km"], c[key]["method"]
    km, method = None, None
    try:
        r = requests.get(f"https://router.project-osrm.org/route/v1/driving/{GENEVA[1]},{GENEVA[0]};{lon},{lat}?overview=false", headers={"User-Agent": GEO_UA}, timeout=20).json()
        if r.get("code") == "Ok": km, method = round(r["routes"][0]["distance"] / 1000), "osrm"
        time.sleep(0.3)
    except Exception as e:
        log("osrm err", e)
    if km is None: km, method = round(haversine(GENEVA, (lat, lon)) * 1.25), "haversine x1.25"
    c[key] = {"km": km, "method": method}; ROUTE.write_text(json.dumps(c, indent=0)); return km, method

CANTON_FROM_POSTCODE = None
def add_geo(r):
    if r.get("lat") is None:
        g = None
        if r.get("town"):
            q = f"{(r.get('postcode') or '')} {r['town']}".strip()
            g = geocode(q, "ch,de,fr,it,at,li")
            if not g or g.get("cc") != "ch":          # prefer a Swiss match (e.g. Brissago TI vs Brissago IT)
                g2 = geocode(q, "ch")
                if g2: g = g2
        if (not g) and r.get("region"): g = geocode(r["region"], "ch")
        if not g: return r
        if g.get("cc") and g["cc"] != "ch": r["foreign"] = g["cc"]; return r
        r["lat"], r["lon"] = g["lat"], g["lon"]
        if not r.get("canton"): r["canton"] = g.get("canton")
        r["geo_precision"] = "town" if r.get("town") else "lake/region"
    else:
        r["geo_precision"] = "listing coordinates"
    if not r.get("canton") and r.get("lat"):
        pass
    r["distance_km"], r["distance_method"] = road_km(r["lat"], r["lon"])
    return r

def main():
    all_rows = []
    for name, fn in [("tutti", lambda: collect_smg("tutti")), ("anibis", lambda: collect_smg("anibis")), ("bateau24", collect_b24)]:
        try:
            all_rows += fn()
        except Exception as e:
            STATUS[name] = {"ok": False, "error": str(e)[:200]}; log("SOURCE FAILED", name, e)
    for name, why in [("ricardo", None), ("boat24.com", None)]:
        pass
    # Ricardo: try once; record status honestly
    try:
        r = S.get("https://www.ricardo.ch/fr/s/bateau", timeout=30)
        blocked = r.status_code != 200 or "Captcha" in r.text[:3000] or "Just a moment" in r.text[:3000]
        STATUS["ricardo"] = {"ok": not blocked, "error": f"HTTP {r.status_code}, captcha/Cloudflare challenge page" if blocked else None, "kept": 0}
    except Exception as e:
        STATUS["ricardo"] = {"ok": False, "error": str(e)[:200], "kept": 0}
    STATUS["facebook_marketplace"] = {"ok": False, "error": "requires a logged-in Facebook session; not scraped", "kept": 0}
    # geo + dedupe (same title+price+town across sites)
    rows, keys = [], set()
    for r in all_rows:
        add_geo(r)
        if r.get("foreign") or r.get("lat") is None and r["source"] == "bateau24": continue
        k = (norm(r["title"])[:40], r["price_chf"], norm(r.get("town") or ""))
        if k in keys: continue
        keys.add(k); rows.append(r)
    return rows, STATUS

if __name__ == "__main__":
    rows, st = main()
    out = ROOT / "data" / "raw_today.json"
    out.write_text(json.dumps({"rows": rows, "status": st}, ensure_ascii=False, indent=1))
    log("rows", len(rows), json.dumps(st))
