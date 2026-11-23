# -*- coding: utf-8 -*-
"""Nico Boats collector: pulls real used-boat listings from Swiss marketplaces.

Sources that work from the box (2026-11-15): tutti.ch, anibis.ch (Next.js __NEXT_DATA__ JSON; since 2026-11-21 both
answer the box with an interactive Cloudflare Turnstile page, see report/README.md, so they are reported as blocked),
bateau24.ch = boat24.com Swiss site (server-rendered HTML; boot24.ch is the same site in German),
lakeboat.ch (sitemap + MyListing detail pages), petitesannonces.ch (rubric lists), aquaboat.ch (dealer, public boats.json). Blocked: ricardo.ch (Cloudflare captcha /
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

class Blocked(RuntimeError):
    """The site answered with a bot wall (Cloudflare Turnstile / captcha). Retrying does not help."""

def challenge_kind(r):
    """Return a short description if the response is a bot-protection page, else None."""
    head = r.text[:4000]
    if r.headers.get("cf-mitigated") == "challenge":
        return "Cloudflare challenge (cf-mitigated: challenge, page « Vous y êtes presque » / Turnstile « Vérifiez que vous êtes humain »)"
    if r.status_code in (403, 503) and re.search(r"Just a moment|Un instant|Security check|CAPTCHA|cf_chl_opt", head):
        return "page captcha / contrôle de sécurité"
    return None

def get(url, tries=3, sleep=0.8):
    """Polite GET: pause after each request, exponential backoff on 429/5xx/network errors
    (honours Retry-After), and no retries at all on a bot wall."""
    last = None
    for i in range(tries):
        try:
            r = S.get(url, timeout=30)
            time.sleep(sleep)
            if r.status_code == 200: return r.text
            kind = challenge_kind(r)
            if kind:
                raise Blocked(f"HTTP {r.status_code} {kind} on {url}")
            log("HTTP", r.status_code, url); last = r.status_code
            if r.status_code in (404, 410): break
            ra = r.headers.get("Retry-After")
            if ra and ra.isdigit():
                time.sleep(min(int(ra), 120)); continue
        except Blocked:
            raise
        except Exception as e:
            log("ERR", e, url); last = str(e)
        time.sleep(3 * 2 ** i)
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
ACC_ANY = r"(\brc\b|radiocommande|telecommande|ferngesteuert|(voiles?|mat|bome|spi|spinnaker|taud|bache) (de|pour|du) (bateau|voilier)|ber de stockage|bateau lit|lit bateau|lit enfant|lit pour enfant|\bcable\b|kabel|autos? ?- ?motos?|7j7|24h24|rachat|debarras|achete (tous|bateaux)|kaufe (boote|alle)|moteurs? de bateau|pieces de bateau|utilisation partagee|(taud|couverture|protection|vis|passerelle|coussin|sieges?|roues?|haut-parleurs?|instruments?|chariot|berceau|support|halle|table|radio|lautsprecher|traineau) (de|a|pour) (bateau|barca)|\bpour (bateau|bateaux|voilier|zodiac|pneumatique)|\bfur (boot|boote|segelboot|schlauchboot)|\bper (barca|barche|gommone)|\bfor (boat|boats)|maquette|modellbau|modellboot|model boat|bateau modele|rc boot|rc boat|ferngesteuert|teleguide|jouet|spielzeug|lego|playmobil|bootsplatz|liegeplatz|place d.amarrage|place de port|kayak|kajak|kanu|kanadier|canoe|\bsup\b|stand ?up paddle|paddleboard|luftmatratze|gonflable pour enfant|badeboot|schwimmring|pedalo de piscine|permis (de )?bateau|bateau[- ]ecole|cours de (navigation|permis|voile)|hivernage|gardiennage|chantier naval|part de bateau|bootsanteil|^(cherche|recherche|suche|achete|kaufe)\b|\ba louer\b|louer (un |le )?bateau|zu vermieten|\bvermiete|partager (un |le |mon )?bateau|partage de frais|co-?navigation)"

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
    elif re.search(r"(moteur (a propulsion )?electrique|propulsion electrique|bateau electrique|elektromotor|elektro-?aussenborder|elektroboot|elektroantrieb|electric (motor|outboard|boat)|motore elettrico|torqeedo|epropulsion|minn ?kota|aquamot)", t) \
            and not re.search(r"\b([2-9]\d|[1-9]\d\d)\s*(cv|ch|ps|hp)\b", t): o["engine_type"] = "electric"
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

# ---------------------------------------------------------------- generic helpers for the smaller sites
CANTON_NAMES = {"geneve": "GE", "vaud": "VD", "valais": "VS", "fribourg": "FR", "neuchatel": "NE", "jura": "JU", "berne": "BE", "bern": "BE",
                "zurich": "ZH", "lucerne": "LU", "luzern": "LU", "tessin": "TI", "ticino": "TI", "argovie": "AG", "aargau": "AG",
                "saint-gall": "SG", "st. gallen": "SG", "thurgovie": "TG", "thurgau": "TG", "schwyz": "SZ", "zoug": "ZG", "zug": "ZG",
                "soleure": "SO", "solothurn": "SO", "grisons": "GR", "graubunden": "GR", "uri": "UR", "obwald": "OW", "nidwald": "NW",
                "glaris": "GL", "glarus": "GL", "schaffhouse": "SH", "schaffhausen": "SH", "bale": "BS", "basel": "BS", "appenzell": "AR"}
CH_CANTONS = set("AG AI AR BE BL BS FR GE GL GR JU LU NE NW OW SG SH SO SZ TG TI UR VD VS ZG ZH".split())

def html_text(fragment):
    t = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", fragment or "", flags=re.I)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t\xa0]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()

def classify_hint(title, body, hint=None):
    """classify_text, plus a fallback for sites whose rubric already says 'motor boat' (titles like 'Rodman Ventura 790')."""
    c = classify_text(title, body)
    if c is not None or not hint: return c
    t = norm(title)
    if re.search(ACC_ANY, t) or re.search(ACC_START, t): return None
    if hint == "sail": return "sail"
    if hint == "inflatable": return "inflatable"
    txt = t + " " + norm(body)
    if re.search(r"(cabine|kajut|kabinen|cabin|cruiser|hardtop|flybridge|timonier|couchette|wc\b|toilette)", txt): return "motor"
    return "open"

def apply_text_fields(r):
    """rich_fields first: its 'L x W m' pattern is more reliable than extract_specs' first 'N.NN m' (which can be the beam)."""
    txt = r["title"] + " . " + (r.get("snippet") or "")
    for k, v in rich_fields(r["title"], r.get("snippet") or "").items(): r.setdefault(k, v)
    for k, v in extract_specs(txt).items(): r.setdefault(k, v)

# ---------------------------------------------------------------- petitesannonces.ch (Suisse romande classifieds)
PA_BASE = "https://www.petitesannonces.ch"
PA_RUBRICS = {"3503": "open", "3504": "sail", "3506": "inflatable", "3502": "small"}   # bateaux à moteur, voiliers, canots pneumatiques, barques
PA_ROW = re.compile(r'<div class="ele[^"]*">.*?<a href="/a/(\d+)"[^>]*>([^<]+)</a></div><div class="el[ap] elsp[^"]*">([^<]*)</div><div class="ela elsl[^"]*">([^<]*)</div><div class="ela elss[^"]*">([^<]*)</div>', re.S)

def collect_petitesannonces(max_pages=30):
    items, seen = [], set()
    for tid, hint in PA_RUBRICS.items():
        for p in range(1, max_pages + 1):
            h = get(f"{PA_BASE}/r/{tid}" + (f"?p={p}" if p > 1 else ""), sleep=0.6)
            rows = PA_ROW.findall(h); new = 0
            for lid, title, price, loc, day in rows:
                if lid in seen: continue
                seen.add(lid); new += 1
                items.append({"lid": lid, "title": H.unescape(title).strip(), "price_label": H.unescape(price).strip(),
                              "loc": H.unescape(loc).replace("\xa0", " ").strip(), "hint": hint, "tid": tid})
            log(f"petitesannonces {tid} page {p}: +{new}")
            if new == 0 or f"?p={p + 1}" not in h: break
    STATUS["petitesannonces"] = {"ok": True, "raw": len(items)}
    res = []
    for it in items:
        town, _, cc = it["loc"].rpartition(",")
        cc = cc.strip()
        if cc not in CH_CANTONS: continue                     # France, Italie, ...
        price = parse_price(it["price_label"]) if it["price_label"] not in ("-", "") else None
        if price is None or price > PRICE_CAP or 0 < price < 150: continue
        cat = classify_hint(it["title"], "", it["hint"])
        if cat is None: continue
        res.append({"id": f"petitesannonces:{it['lid']}", "source": "petitesannonces", "title": it["title"], "category": cat,
                    "price_chf": price, "price_label": it["price_label"] + " CHF", "url": f"{PA_BASE}/a/{it['lid']}",
                    "town": town.strip(), "canton": cc, "postcode": None, "lat": None, "lon": None, "snippet": "",
                    "rubric_hint": it["hint"], "posted": None})
    for r in res:
        try:
            h = get_cached(r["url"], r["id"], sleep=0.5)
            d = re.search(r'<div class="cdk bls">(.*?)</div>', h, re.S)
            if d: r["snippet"] = html_text(d.group(1))[:1500]
            m = re.search(r'Ville:</td><td><a [^>]*>(\d{4})\s+([^<&]+?)(?:&nbsp;|\s)*\((\w\w)\)', h)
            if m: r["postcode"], r["town"], r["canton"] = m.group(1), H.unescape(m.group(2)).strip(), m.group(3)
            m = re.search(r'Publication:</td><td>(\d\d)\.(\d\d)\.(\d{4})', h)
            if m: r["posted"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            m = re.search(r'id="img"[^>]*src="(/i/m/[^"]+)"', h)
            if m:
                r["photo"] = PA_BASE + m.group(1).replace("/i/m/", "/i/l/"); r["thumb"] = PA_BASE + m.group(1)
            r["seller_type"] = "dealer" if re.search(r"(professionnel|chantier naval|garage|marine sa|nautique sa|sàrl|sarl\b|gmbh)", norm(r["snippet"])) else "private"
        except Exception as e:
            log("petitesannonces detail fail", r["url"], e)
        c2 = classify_hint(r["title"], r["snippet"], r["rubric_hint"])
        if c2: r["category"] = c2
        apply_text_fields(r)
    res = [r for r in res if classify_hint(r["title"], r["snippet"], r["rubric_hint"]) is not None]
    STATUS["petitesannonces"]["kept_before_geo"] = len(res)
    return res

# ---------------------------------------------------------------- lakeboat.ch (MyListing WordPress, Swiss lakes)
LAKE_SITEMAP = "https://lakeboat.ch/job_listing-sitemap.xml"

def collect_lakeboat():
    sm = get(LAKE_SITEMAP)
    urls = [u for u in re.findall(r"<loc>([^<]+)</loc>", sm) if "/bateau-occasion-suisse/" in u]
    STATUS["lakeboat"] = {"ok": True, "raw": len(urls)}
    res = []
    for u in urls:
        slug = u.rstrip("/").rsplit("/", 1)[-1]
        rid = f"lakeboat:{slug}"
        try:
            h = get_cached(u, rid, sleep=0.5)
        except Exception as e:
            log("lakeboat detail fail", u, e); continue
        ld = None
        for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S):
            try:
                j = json.loads(m.group(1))
            except Exception:
                continue
            if isinstance(j, dict) and j.get("@type") == "LocalBusiness": ld = j
        heads = [H.unescape(x).strip() for x in re.findall(r'<div class="title-style-1">\s*<i[^>]*></i>\s*<h5>([^<]+)</h5>', h)]
        kv = {}
        for k, v in re.findall(r'<div class="item-attr">([^<]+)</div>\s*<div class="item-property">(.*?)</div>', h, re.S):
            kv[H.unescape(k).strip()] = html_text(v)
        kind = "sail" if "Voilier" in heads else "open" if "Bateau moteur" in heads else None
        if kind is None: continue                                   # schools, rentals, accessories, shipyards
        title = H.unescape((ld or {}).get("name") or "").strip() or slug.replace("-", " ").title()
        desc = re.search(r'<span class="wp-editor-content">(.*?)</span>', h, re.S)
        body = html_text(desc.group(1)) if desc else html_text((ld or {}).get("description") or "")
        price_label = kv.get("Prix de vente") or kv.get("Prix") or ""
        price = parse_price(price_label.replace("CHF.", "").replace("CHF", ""))
        if price is None or price > PRICE_CAP or 0 < price < 150: continue
        typ = " ".join(v for k, v in kv.items() if k.lower().startswith("type"))
        cat = classify_hint(title, body + " " + typ, kind)
        if cat is None: continue
        if kind == "sail" and cat in ("open", "motor", "other"): cat = "sail"
        r = {"id": rid, "source": "lakeboat", "title": title, "category": cat, "price_chf": price, "price_label": price_label,
             "url": u, "snippet": (typ + ". " if typ else "") + body[:1500], "type_label": typ, "rubric_hint": kind,
             "lat": None, "lon": None, "postcode": None, "town": None, "canton": None, "posted": None}
        a = (ld or {}).get("address") or {}
        try:
            if a.get("lat") and a.get("lng"): r["lat"], r["lon"] = float(a["lat"]), float(a["lng"])
        except ValueError:
            pass
        if a.get("address"):
            parts = [p.strip() for p in a["address"].split(",") if p.strip()]
            r["region"] = a["address"]
            street = r"(\d|^(chemin|ch\.|route|rte|rue|quai|place|avenue|av\.|jetee|impasse|allee|sentier|promenade|strasse|weg|gasse|platz)\b)"
            while len(parts) > 1 and re.search(street, norm(parts[0])) and not re.match(r"^\d{4}\s+\D", parts[0]):
                parts = parts[1:]
            pc = re.match(r"^(\d{4})\s*(.*)$", parts[0])
            if pc: r["postcode"], r["town"] = pc.group(1), (pc.group(2) or None)
            elif not re.search(street, norm(parts[0])) and not norm(parts[0]).startswith("canton"): r["town"] = parts[0]
            for p in parts[1:]:
                cn = norm(p).replace("canton de ", "").replace("canton du ", "").replace("canton d'", "").strip()
                if cn in CANTON_NAMES: r["canton"] = CANTON_NAMES[cn]
            if "suisse" not in norm(a["address"]) and "schweiz" not in norm(a["address"]) and r["lat"] is None:
                r["region"] = a["address"]
        if kv.get("Lac"): r["lake"] = kv["Lac"]
        if not r["town"] and kv.get("Lac"): r["region"] = kv["Lac"]
        if kv.get("Marque"): r["brand"] = kv["Marque"]
        if kv.get("Modèle"): r["model"] = kv["Modèle"]
        for k, v in kv.items():
            nk = norm(k)
            if nk.startswith("annee") and re.search(r"\b(19|20)\d\d\b", v): r["year"] = int(re.search(r"\b((?:19|20)\d\d)\b", v).group(1))
            elif nk.startswith("longueur"):
                m = re.search(r"(\d+(?:[.,]\d+)?)", v)
                if m:
                    L = float(m.group(1).replace(",", ".")); r["length_m"] = L / 100 if L > 30 else L
            elif nk.startswith("largeur"):
                m = re.search(r"(\d+(?:[.,]\d+)?)", v)
                if m:
                    W = float(m.group(1).replace(",", ".")); r["width_m"] = W / 100 if W > 10 else W
            elif nk.startswith("puissance") or nk == "cv" or nk.startswith("moteur"):
                m = re.search(r"(\d+(?:[.,]\d+)?)\s*(cv|ch|ps|hp)?", norm(v))
                if m and nk.startswith("puissance"): r["engine"] = f"{float(m.group(1).replace(',', '.')):g} CV"
                if nk.startswith("moteur"): r["engine_model"] = v
            elif nk.startswith("propulsion") or nk.startswith("type de moteur"):
                z = norm(v); r["engine_type"] = "outboard" if "hors" in z else "inboard" if ("in" in z and "bord" in z) else r.get("engine_type")
        m = re.search(r"longueur\D{0,12}(\d{3})\b.{0,30}?largeur\D{0,12}(\d{3})\b", norm(body))   # 'Longueur 645, largeur 250' (cm)
        if m:
            r.setdefault("length_m", int(m.group(1)) / 100); r.setdefault("width_m", int(m.group(2)) / 100)
        ph = (ld or {}).get("image") or []
        if ph: r["photo"] = r["thumb"] = ph[0]
        if (ld or {}).get("datePublished"): r["posted"] = ld["datePublished"][:10]
        dp = re.search(r'"datePublished":"([0-9-]{10})', h)
        if dp: r["posted"] = dp.group(1)
        r["seller_type"] = "dealer" if re.search(r"(chantier naval|marine s\.?a|nautic|sarl|sàrl|gmbh|\bag\b|professionnel|garage)", norm(title + " " + body[:400])) else "private"
        apply_text_fields(r)
        if r.get("engine_type") is None: r.pop("engine_type", None)
        res.append(r)
    STATUS["lakeboat"]["kept_before_geo"] = len(res)
    return res

# ---------------------------------------------------------------- aquaboat.ch (dealer, Le Bouveret / Port-Valais VS)
AQUA_JSON = "https://aquaboat.ch/boats.json"
AQUA_OFFER = {"offeroption1": "promotion", "offeroption2": "occasion", "offeroption3": "destockage", "offeroption4": "demonstration"}
AQUA_TYPE = {"typeoption1": "motor", "typeoption2": "open", "typeoption3": "open", "typeoption4": "open", "typeoption7": "other"}

def collect_aquaboat():
    r0 = S.get(AQUA_JSON, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest", "X-Language": "fr"}, timeout=30)
    r0.raise_for_status()
    data = r0.json()["data"]
    STATUS["aquaboat"] = {"ok": True, "raw": len(data)}
    res = []
    for x in data:
        c = x.get("content") or {}
        offer = AQUA_OFFER.get(c.get("offer") or "")
        if offer not in ("occasion", "destockage", "demonstration"): continue      # new boats from the catalogue are not second-hand ads
        price = parse_price(c.get("price") or "")
        if price is None or price > PRICE_CAP or price < 150: continue
        slug = x["url"].rstrip("/").rsplit("/", 1)[-1]
        r = {"id": f"aquaboat:{slug}", "source": "aquaboat", "title": (c.get("title") or "") if norm(c.get("title") or "").startswith(norm(c.get("brand") or "-")) else f"{c.get('brand') or ''} {c.get('title') or ''}".strip(),
             "category": AQUA_TYPE.get(c.get("type"), "open"), "price_chf": price, "price_label": f"CHF {price:,}".replace(",", "'") + ".-",
             "url": x["url"], "brand": c.get("brand"), "model": c.get("title"),
             "engine_type": "outboard" if c.get("engine") == "engineoption2" else "inboard",
             "thumb": c.get("image"), "town": "Le Bouveret", "postcode": "1897", "canton": "VS", "seller_type": "dealer",
             "lat": 46.3806, "lon": 6.8623, "condition": offer, "snippet": "", "posted": None}
        try:
            h = get_cached(x["url"], r["id"], sleep=0.5)
            main = re.search(r'<main.*?</main>', h, re.S); main = main.group(0) if main else h
            p = re.search(r'<p class="mrgt0">(.*?)</p>', main, re.S)
            if p: r["snippet"] = html_text(p.group(1))[:1500]
            items = [html_text(li) for li in re.findall(r"<li>(.*?)</li>", (re.search(r'<ul class="list-stacked[^"]*">(.*?)</ul>', main, re.S) or [None, ""])[1], re.S)]
            for it in items:
                m = re.match(r"([\d.]+)\s*Longueur", it); m2 = re.match(r"([\d.]+)\s*Largeur", it)
                if m: r["length_m"] = float(m.group(1))
                if m2: r["width_m"] = float(m2.group(1))
            if len(items) > 2: r["type_label"] = items[2]
            img = re.search(r'<img [^>]*src="(https://aquaboat\.ch/media/pages/boats/[^"]+)"', main)
            if img: r["photo"] = img.group(1)
        except Exception as e:
            log("aquaboat detail fail", x["url"], e)
        c2 = classify_hint(r["title"], r["snippet"] + " " + (r.get("type_label") or ""), r["category"])
        if c2 and c2 != "other": r["category"] = c2
        apply_text_fields(r)
        res.append(r)
    STATUS["aquaboat"]["kept_before_geo"] = len(res)
    return res

# ---------------------------------------------------------------- cross-source duplicates
SOURCE_PRIORITY = ["bateau24", "tutti", "anibis", "lakeboat", "petitesannonces", "aquaboat"]
STOP = set("bateau bateaux boat boot a de du la le les avec mit und et en au aux pour fur vends vendre verkaufe zu verkaufen moteur motor motorboot bateau-moteur occasion cv ps hp ch chf the of sur from sport sports peche plaisance".split())

def title_tokens(t):
    return {w for w in re.findall(r"[a-z0-9]+", norm(t)) if len(w) >= 2 and w not in STOP}

def _hp(r):
    if r.get("hp") is not None: return float(r["hp"])
    m = re.match(r"([\d.]+)\s*(CV|PS|HP|kW)", r.get("engine") or "")
    if not m: return None
    return float(m.group(1)) / 0.7355 if m.group(2) == "kW" else float(m.group(1))

def same_boat(a, b):
    pa, pb = a.get("price_chf"), b.get("price_chf")
    if not pa or not pb: return False
    ta, tb = title_tokens(a["title"]), title_tokens(b["title"])
    if pa != pb:
        # same ad text at a different price on another site (seller updated one site only): same place, and either the
        # same title or the same stated power, and prices within 40 %
        if abs(pa - pb) > 0.4 * max(pa, pb) or a.get("lat") is None or b.get("lat") is None: return False
        if haversine((a["lat"], a["lon"]), (b["lat"], b["lon"])) > 2: return False
        if a["source"] == b["source"] and "private" not in (a.get("seller_type"), b.get("seller_type")):
            return False                      # one dealer, several similar units (e.g. two "X3 - STOCK")
        ha, hb = _hp(a), _hp(b)
        same_title = len(ta) >= 2 and ta == tb and abs(pa - pb) <= 0.15 * max(pa, pb)
        same_hp = (ha is not None and hb is not None and abs(ha - hb) <= 1.5 and ha >= 20
                   and (ta & tb or not ta or not tb))          # dealers at one marina: different models, same power
        return same_title or same_hp
    near = False
    if a.get("lat") is not None and b.get("lat") is not None:
        near = haversine((a["lat"], a["lon"]), (b["lat"], b["lon"])) <= 3
    elif a.get("town") and b.get("town"):
        near = norm(a["town"]) == norm(b["town"])
    if near and ta & tb:                      # short titles ("Ancien bateau") but same price, same place, a shared word
        return True
    if min(len(ta), len(tb)) < 2: return False
    sim = len(ta & tb) / min(len(ta), len(tb))
    if sim < 0.6: return False
    if a.get("lat") is not None and b.get("lat") is not None:
        return haversine((a["lat"], a["lon"]), (b["lat"], b["lon"])) <= 30
    return sim >= 0.8

def merge_duplicates(rows, known_ids=()):
    """Same boat on several sites -> one row; the others become also_listed links. A row whose id is already in the
    store stays primary (so sent marks and history follow it). Two rows that are both already in the store are only cross-linked."""
    known = set(known_ids)
    pri = {s: i for i, s in enumerate(SOURCE_PRIORITY)}
    order = sorted(rows, key=lambda r: (r["id"] not in known, pri.get(r["source"], 99)))
    kept = []
    for r in order:
        hit = None
        for k in kept:
            if k["source"] != r["source"] or k["source"] != "bateau24":
                if same_boat(k, r): hit = k; break
        if hit is None:
            kept.append(r); continue
        link = {"source": r["source"], "url": r["url"], "id": r["id"]}
        def add(row, lk):
            al = row.setdefault("also_listed", [])
            if lk["id"] != row["id"] and all(x["id"] != lk["id"] for x in al): al.append(lk)
        if r["id"] in known and hit["id"] in known:            # both already stored: keep both, cross-link
            add(hit, link); add(r, {"source": hit["source"], "url": hit["url"], "id": hit["id"]})
            kept.append(r); continue
        add(hit, link)
        for lk in r.get("also_listed") or []: add(hit, lk)
        for k2, v in r.items():                                  # fill gaps from the duplicate
            if k2 not in ("id", "source", "url", "also_listed") and hit.get(k2) in (None, "", []) and v not in (None, "", []):
                hit[k2] = v
        STATUS.setdefault("_duplicates", {"merged": 0})["merged"] += 1
    return kept

def known_ids():
    try:
        return set(json.loads((ROOT.parent / "data" / "listings.json").read_text())["records"].keys())
    except Exception:
        return set()

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
    for name, fn in [("tutti", lambda: collect_smg("tutti")), ("anibis", lambda: collect_smg("anibis")), ("bateau24", collect_b24),
                     ("lakeboat", collect_lakeboat), ("petitesannonces", collect_petitesannonces), ("aquaboat", collect_aquaboat)]:
        try:
            all_rows += fn()
        except Blocked as e:
            STATUS[name] = {"ok": False, "blocked": True, "error": str(e)[:300]}; log("SOURCE BLOCKED", name, e)
        except Exception as e:
            STATUS[name] = {"ok": False, "error": str(e)[:200]}; log("SOURCE FAILED", name, e)
    # Ricardo: try once; record status honestly (Cloudflare captcha from the box; no captcha solving, no borrowed cookies)
    try:
        r = S.get("https://www.ricardo.ch/fr/s/bateau", timeout=30)
        blocked = r.status_code != 200 or "Captcha" in r.text[:3000] or "Just a moment" in r.text[:3000]
        STATUS["ricardo"] = {"ok": False, "kept": 0, "probe_http": r.status_code,
                             "error": f"HTTP {r.status_code}, page captcha / contrôle Cloudflare" if blocked else
                                      "page joignable ce jour (HTTP 200), mais Ricardo est d’habitude derrière un captcha ; pas encore de lecteur"}
    except Exception as e:
        STATUS["ricardo"] = {"ok": False, "error": str(e)[:200], "kept": 0}
    STATUS["facebook_marketplace"] = {"ok": False, "error": "nécessite une session Facebook connectée ; non collecté", "kept": 0}
    STATUS["swissboat.ch"] = {"ok": False, "error": "mur anti-robot (Anubis) ; non collecté", "kept": 0}
    # geo
    rows = []
    for r in all_rows:
        add_geo(r)
        if r.get("foreign") or r.get("lat") is None and r["source"] in ("bateau24", "lakeboat"): continue
        rows.append(r)
    # exact repost on the same platform (tutti <-> anibis share one backend): title + price + town
    out, keys = [], {}
    for r in rows:
        k = (norm(r["title"])[:40], r["price_chf"], norm(r.get("town") or ""))
        if k in keys and keys[k]["source"] in ("tutti", "anibis") and r["source"] in ("tutti", "anibis"):
            keys[k].setdefault("also_listed", []).append({"source": r["source"], "url": r["url"], "id": r["id"]}); continue
        keys.setdefault(k, r); out.append(r)
    return merge_duplicates(out, known_ids()), STATUS

if __name__ == "__main__":
    rows, st = main()
    out = ROOT / "data" / "raw_today.json"
    out.write_text(json.dumps({"rows": rows, "status": st}, ensure_ascii=False, indent=1))
    log("rows", len(rows), json.dumps(st))
