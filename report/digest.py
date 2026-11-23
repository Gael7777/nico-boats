# -*- coding: utf-8 -*-
"""Email-safe HTML digest (table layout, inline CSS, no JS, no SVG since Gmail strips it,
no web fonts required). Visual language of /workspace/tools/pdf-report-kit (navy/teal/orange,
serif headings, KPI tiles with coloured top rule, takeaway boxes)."""
from frdate import fr_date_long, fr_date_short
import html, statistics
from datetime import date

NAVY, TEAL, ORANGE, GREY, LGREY, GREEN, RED, INK, MUTED, PAPER = "#0B1F3A", "#1A9E9A", "#F08A24", "#9AA5B1", "#E6EAEF", "#2E9E5B", "#D64545", "#1E2A3B", "#6B7A8F", "#F4F6F9"
SERIF = "Georgia,'Times New Roman',serif"   # DM Serif Display is not available in mail clients
SANS = "Helvetica,Arial,sans-serif"            # Lato fallback chain, shortened to keep the email small
CAT_ORDER = ["sail", "open", "motor", "inflatable", "small", "other"]
CAT_LABEL = {"sail": "Sailboats", "motor": "Motorboats (cabin)", "open": "Open boats & day-cruisers",
             "inflatable": "Inflatables & RIBs", "small": "Dinghies, rowing & small boats", "other": "Other"}
CAT_ICON = {"sail": "⛵", "motor": "🛥️", "open": "🚤", "inflatable": "🛟", "small": "🛶", "other": "⚓"}
CAT_COL = {"sail": TEAL, "motor": NAVY, "open": ORANGE, "inflatable": "#7B5EA7", "small": GREEN, "other": GREY}
PRICE_BANDS = [("Free – 2k", 0, 2000), ("2k – 5k", 2000, 5000), ("5k – 10k", 5000, 10000), ("10k – 20k", 10000, 20000), ("20k – 30k", 20000, 30001)]
DIST_BANDS = [("< 30 km", 0, 30), ("30 – 80 km", 30, 80), ("80 – 150 km", 80, 150), ("150 – 250 km", 150, 250), ("> 250 km", 250, 10000), ("unknown", None, None)]
SRC_LABEL = {"tutti": "tutti.ch", "anibis": "anibis.ch", "bateau24": "boat24 (bateau24.ch)"}
NA = "N/A"
SITE_URL = "https://gael7777.github.io/nico-boats/"   # GitHub Pages URL of ../site (change if deployed elsewhere)
PICKS_PER_CAT = 8        # large digests: top N per category (price + proximity to Geneva)
CARDS_PER_CAT = 4        # unused in large mode; kept for reference
COMPACT_PER_CAT = 10
BIG = 40                 # above this, list picks only (Gmail clips HTML above ~102 KB; stay under ~95 KB)
MAX_DIGEST_BYTES = 95_000
e = lambda s: html.escape(str(s), quote=True)

def chf(v):
    if v == 0: return "Free"
    return "CHF " + f"{int(v):,}".replace(",", "'")

def km(r):
    d = r.get("distance_km_from_geneva")
    return f"{int(d)} km" if isinstance(d, (int, float)) else "km n/a"

def has(v): return v not in (None, NA, "")

def specs(r):
    out = []
    if has(r.get("length_m")): out.append(f"{r['length_m']:g} m")
    if has(r.get("hp")): out.append(f"{r['hp']:g} CV")
    if has(r.get("year")): out.append(str(r["year"]))
    if has(r.get("engine_type")) and r["engine_type"] in ("outboard", "inboard", "electric"): out.append(r["engine_type"])
    if r.get("trailer") == "yes": out.append("trailer")
    if r.get("mooring_included") == "yes": out.append("mooring incl.")
    return " · ".join(out)

def where(r):
    t = r.get("town") if has(r.get("town")) else (r.get("region") if has(r.get("region")) else "")
    c = r.get("canton") if has(r.get("canton")) else ""
    return (f"{t} ({c})" if t and c else t or c or "location n/a")

def badge(text, bg, fg="#FFFFFF"):
    return f'<span style="display:inline-block;background:{bg};color:{fg};font:700 10px/1 {SANS};letter-spacing:.06em;text-transform:uppercase;padding:4px 6px;border-radius:3px;">{e(text)}</span>'

def kpi(v, label, sub, col):
    return (f'<td class="kpi" width="25%" valign="top" style="padding:0 4px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};border-top:4px solid {col};border-radius:6px;">'
            f'<tr><td style="padding:12px 12px 10px 12px;"><div style="font:900 24px/1.1 {SANS};color:{NAVY};">{v}</div>'
            f'<div style="font:700 10px/1.3 {SANS};color:#33415C;text-transform:uppercase;letter-spacing:.05em;margin-top:4px;">{label}</div>'
            f'<div style="font:400 11px/1.3 {SANS};color:{MUTED};margin-top:2px;">{sub}</div></td></tr></table></td>')

def h2(kicker, title, lead=None, anchor=None):
    a = f'<a name="{anchor}" id="{anchor}"></a>' if anchor else ""
    s = (f'<tr><td style="padding:28px 24px 6px 24px;">{a}<div style="font:900 11px/1 {SANS};letter-spacing:.14em;color:{ORANGE};text-transform:uppercase;">{e(kicker)}</div>'
         f'<div style="font:400 26px/1.15 {SERIF};color:{NAVY};margin-top:6px;">{e(title)}</div>')
    if lead: s += f'<div style="font:400 14px/1.5 {SANS};color:#33415C;border-left:4px solid {TEAL};padding-left:10px;margin-top:10px;">{lead}</div>'
    return s + "</td></tr>"

def bar_rows(items, maxv, col_fn):
    rows = []
    for label, v, col in items:
        w = max(2, int(100 * v / maxv)) if maxv else 2
        rows.append(f'<tr><td width="38%" style="font:400 12px/1.3 {SANS};color:{INK};padding:3px 8px 3px 0;white-space:nowrap;">{label}</td>'
                    f'<td style="padding:3px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                    f'<td width="{w}%" style="background:{col};height:14px;border-radius:2px;font-size:0;line-height:0;">&nbsp;</td>'
                    f'<td style="font:700 12px/1 {SANS};color:{NAVY};padding-left:6px;white-space:nowrap;">{v}</td></tr></table></td></tr>')
    return '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + "".join(rows) + "</table>"

def col_chart(items, height=90):
    """Vertical columns as table cells (renders in Gmail/Apple Mail; no SVG)."""
    maxv = max([v for _, v in items] + [1]); cells, labels = [], []
    for i, (label, v) in enumerate(items):
        hgt = max(3, int(height * v / maxv)); col = ORANGE if i < 3 else TEAL
        cells.append(f'<td align="center" valign="bottom" style="padding:0 6px;height:{height + 18}px;"><div style="font:700 12px/1 {SANS};color:{NAVY};padding-bottom:4px;">{v}</div>'
                     f'<div style="background:{col};height:{hgt}px;line-height:{hgt}px;font-size:0;border-radius:3px 3px 0 0;">&nbsp;</div></td>')
        labels.append(f'<td align="center" style="font:400 11px/1.2 {SANS};color:{MUTED};padding:5px 2px 0 2px;border-top:1px solid #C9D2DC;">{e(label)}</td>')
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{"".join(cells)}</tr><tr>{"".join(labels)}</tr></table>'

def card(r, big=False):
    img = r.get("thumb_url") if has(r.get("thumb_url")) else None
    w = 120 if big else 84; hgt = int(w * 0.75)
    pic = (f'<a href="{e(r["url"])}"><img src="{e(img)}" width="{w}" height="{hgt}" alt="" style="display:block;width:{w}px;height:{hgt}px;object-fit:cover;border-radius:5px;border:0;background:{LGREY};"></a>'
           if img else f'<div style="width:{w}px;height:{hgt}px;background:{LGREY};border-radius:5px;text-align:center;font:400 28px/{hgt}px {SANS};">{CAT_ICON.get(r["category"], "⚓")}</div>')
    price_col = GREEN if isinstance(r["price_chf"], (int, float)) and r["price_chf"] < 10000 else NAVY
    flags = ""
    if isinstance(r["price_chf"], (int, float)) and r["price_chf"] < 10000: flags += badge("< 10k", GREEN) + " "
    if isinstance(r.get("distance_km_from_geneva"), (int, float)) and r["distance_km_from_geneva"] <= 80: flags += badge("near GE", TEAL) + " "
    if r.get("licence_leman", "").startswith("no"): flags += badge("no licence", "#E8EEF5", NAVY) + " "
    sp = specs(r)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid {LGREY};"><tr>'
            f'<td width="{w + 12}" valign="top" style="padding:10px 12px 10px 0;">{pic}</td>'
            f'<td valign="top" style="padding:10px 0;"><a href="{e(r["url"])}" style="font:700 14px/1.3 {SANS};color:{NAVY};text-decoration:none;">{e(r["title"][:90])}</a>'
            f'<div style="font:400 12px/1.45 {SANS};color:{MUTED};margin-top:3px;">📍 {e(where(r))} · <b style="color:{INK};">{km(r)}</b> from Geneva</div>'
            + (f'<div style="font:400 12px/1.45 {SANS};color:#33415C;margin-top:1px;">{e(sp)}</div>' if sp else "") +
            f'<div style="margin-top:5px;">{flags}<span style="font:400 11px/1 {SANS};color:{GREY};">{e(SRC_LABEL.get(r["source"], r["source"]))}</span></div></td>'
            f'<td width="96" valign="top" align="right" style="padding:10px 0 10px 8px;"><div style="font:900 15px/1.2 {SANS};color:{price_col};white-space:nowrap;">{chf(r["price_chf"])}</div>'
            f'<a href="{e(r["url"])}" style="display:inline-block;margin-top:8px;font:700 11px/1 {SANS};color:#FFFFFF;background:{NAVY};padding:6px 9px;border-radius:4px;text-decoration:none;">View ad →</a></td></tr></table>')

def row(r):
    """compact one-line listing (keeps big digests small)."""
    cheap = isinstance(r["price_chf"], (int, float)) and r["price_chf"] < 10000
    sp = specs(r)
    return (f'<tr><td style="padding:5px 0;border-bottom:1px solid {LGREY};font:400 12.5px/1.35 {SANS};"><a href="{e(r["url"])}" style="color:{NAVY};font-weight:700;text-decoration:none;">{e(r["title"][:70])}</a>'
            f'<br><span style="color:{MUTED};font-size:11.5px;">{e(where(r))} · {km(r)}{" · " + e(sp) if sp else ""}</span></td>'
            f'<td align="right" valign="top" style="padding:5px 0 5px 8px;border-bottom:1px solid {LGREY};font:900 12.5px/1.35 {SANS};color:{GREEN if cheap else NAVY};white-space:nowrap;">{chf(r["price_chf"])}</td></tr>')

def box(title, items, col=NAVY, bg="#EEF2F7"):
    lis = "".join(f'<li style="margin:0 0 5px 0;">{i}</li>' for i in items)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{bg};border-left:5px solid {col};border-radius:6px;"><tr><td style="padding:12px 14px;">'
            f'<div style="font:900 13px/1.3 {SANS};color:{NAVY};margin-bottom:6px;">{title}</div><ul style="margin:0;padding-left:18px;font:400 12.5px/1.45 {SANS};color:{INK};">{lis}</ul></td></tr></table>')


def cta(label="Open the full live table &amp; map →", caption="Every active boat, with filters, a map and CSV export"):
    cap = (f'<div style="font:400 12px/1.45 {SANS};color:{MUTED};margin-top:8px;">{caption}</div>' if caption else "")
    return (f'<tr><td align="center" style="padding:18px 24px 6px 24px;" class="pad">'
            f'<a href="{SITE_URL}" style="display:inline-block;background:{ORANGE};color:#FFFFFF;font:900 15px/1.1 {SANS};'
            f'padding:14px 24px;border-radius:8px;text-decoration:none;letter-spacing:.02em;">{label}</a>'
            f'{cap}</td></tr>')

def dist_of(r):
    d = r.get("distance_km_from_geneva")
    return d if isinstance(d, (int, float)) else 400

def pick_score(r):
    """Lower is better for a Geneva mooring: cheap and close."""
    price = r["price_chf"] if isinstance(r["price_chf"], (int, float)) else 50_000
    return (price * (1 + min(dist_of(r), 800) / 60.0), price, dist_of(r))

def top_picks(rows, n=PICKS_PER_CAT):
    return sorted(rows, key=pick_score)[:n]

def render(rows, all_active, status, today, changes, removed_n, first_run):
    d = date.fromisoformat(today)
    n = len(rows); priced = [r for r in rows if isinstance(r["price_chf"], (int, float))]
    under10 = [r for r in priced if r["price_chf"] < 10000]
    dist = lambda r: r["distance_km_from_geneva"] if isinstance(r.get("distance_km_from_geneva"), (int, float)) else 9999
    near = [r for r in rows if dist(r) <= 80]
    med = int(statistics.median([r["price_chf"] for r in priced])) if priced else 0
    mooring_cats = ("sail", "open", "motor")
    cheapest = sorted([r for r in priced if r["category"] in mooring_cats], key=lambda r: (r["price_chf"], dist(r)))[:5]
    value = sorted([r for r in priced if r["category"] in mooring_cats and dist(r) <= 120 and r["price_chf"] >= 300],
                   key=lambda r: r["price_chf"] * (1 + dist(r) / 60))[:5]
    by_cat = {c: sorted([r for r in rows if r["category"] == c], key=lambda r: (r["price_chf"], dist(r))) for c in CAT_ORDER}
    P = []
    P.append(f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"><title>Nico Boats · {fr_date_short(d)}</title>
<style>body{{margin:0;padding:0;background:#E9EDF2;}} a{{color:{NAVY};}} img{{border:0;}}
@media only screen and (max-width:620px){{ .wrap{{width:100%!important;}} .kpi{{display:inline-block!important;width:50%!important;box-sizing:border-box;padding:4px!important;}}
.stack{{display:block!important;width:100%!important;box-sizing:border-box;}} .pad{{padding-left:14px!important;padding-right:14px!important;}} .hide-m{{display:none!important;}} }}</style></head>
<body style="margin:0;padding:0;background:#E9EDF2;">
<div style="display:none;max-height:0;overflow:hidden;">{n} boats under CHF 30'000 across Switzerland · {len(under10)} under 10k · {len(near)} within 80 km of Geneva</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#E9EDF2;"><tr><td align="center" style="padding:18px 8px;">
<table role="presentation" class="wrap" width="680" cellpadding="0" cellspacing="0" style="width:680px;max-width:680px;background:#FFFFFF;border-radius:10px;overflow:hidden;">''')
    # header
    P.append(f'''<tr><td style="background:{NAVY};padding:26px 24px 22px 24px;" class="pad">
<div style="font:900 11px/1 {SANS};letter-spacing:.16em;color:{ORANGE};text-transform:uppercase;"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{ORANGE};margin-right:6px;"></span>Nico Boats · Daily digest</div>
<div style="font:400 32px/1.1 {SERIF};color:#FFFFFF;margin-top:10px;">Affordable used boats across Switzerland</div>
<div style="font:400 14px/1.5 {SANS};color:#C8D3E0;margin-top:8px;">{fr_date_long(d)} · {"First edition: every boat currently listed" if first_run else "Only boats not sent in a previous digest"} · sorted for a Léman mooring in Geneva</div></td></tr>
<tr><td style="background:{TEAL};height:4px;font-size:0;line-height:0;">&nbsp;</td></tr>''')
    if n == 0:
        P.append(h2("Today", "No new boats since the last digest", "Nothing new matched the filters today. The web table still lists every active boat."))
    # KPIs
    P.append(f'<tr><td style="padding:20px 20px 4px 20px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
             + kpi(n, "New boats" if not first_run else "Boats listed", f"of {len(all_active)} active in the store", NAVY)
             + kpi(len(under10), "Under CHF 10k", "highlighted green below", GREEN)
             + kpi(len(near), "Within 80 km", "road distance from Geneva", TEAL)
             + kpi(chf(med) if priced else "n/a", "Median price", "all categories, cap 30k", ORANGE)
             + "</tr></table></td></tr>")
    P.append(cta())
    # price changes
    if changes:
        P.append(h2("Price changes", "Known boats with a new asking price"))
        lines = []
        for r in changes:
            old = r.get("previous_price_chf"); arrow = "▼" if isinstance(old, (int, float)) and r["price_chf"] < old else "▲"
            lines.append(f'<a href="{e(r["url"])}" style="color:{NAVY};font-weight:700;">{e(r["title"][:70])}</a>: {chf(old) if isinstance(old,(int,float)) else old} → <b>{chf(r["price_chf"])}</b> {arrow} · {km(r)}')
        P.append(f'<tr><td style="padding:0 24px;" class="pad">' + box("Price moves since the last run", lines, TEAL, "#EEF7F6") + "</td></tr>")
    if n:
        # summary charts
        cat_items = [(f'{CAT_ICON[c]} {CAT_LABEL[c]}', len(by_cat[c]), CAT_COL[c]) for c in CAT_ORDER if by_cat[c]]
        band_items = [(lbl, sum(1 for r in priced if lo <= r["price_chf"] < hi)) for lbl, lo, hi in PRICE_BANDS]
        P.append(h2("Summary", "What is on the market today"))
        P.append(f'<tr><td style="padding:6px 24px 0 24px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                 f'<td class="stack" width="50%" valign="top" style="padding-right:12px;"><div style="font:900 12px/1.3 {SANS};color:{NAVY};margin-bottom:8px;">Boats by category</div>{bar_rows(cat_items, max(v for _, v, _ in cat_items), None)}</td>'
                 f'<td class="stack" width="50%" valign="top" style="padding-left:12px;"><div style="font:900 12px/1.3 {SANS};color:{NAVY};margin-bottom:8px;">Price distribution (CHF)</div>{col_chart(band_items)}</td></tr></table>'
                 f'<div style="background:#EEF7F6;border-radius:6px;padding:8px 12px;font:400 12.5px/1.45 {SANS};color:#12403E;margin-top:14px;"><b style="color:{TEAL};">Takeaway</b> '
                 f'{sum(v for _, v in band_items[:3])} of {len(priced)} boats ask under CHF 10k; {len([r for r in under10 if r["category"] in mooring_cats])} of those are sail, open or cabin boats that suit a mooring.</div></td></tr>')
        large = n > BIG
        if not large:
            # small days: list every new boat
            if value:
                P.append(h2("Best value near Geneva", "Cheap and close: worth a visit first", "Sail, open and cabin boats within 120 km, ranked by price × (1 + km/60), so a boat 60 km away has to be half the price to tie with one next door.", "value"))
                P.append(f'<tr><td style="padding:0 24px;" class="pad">' + "".join(card(r, True) for r in value) + "</td></tr>")
            if cheapest:
                P.append(h2("Cheapest picks", "Lowest asking prices anywhere in Switzerland", None, "cheapest"))
                P.append(f'<tr><td style="padding:0 24px;" class="pad">' + "".join(card(r) for r in cheapest) + "</td></tr>")
        P.append(f'<tr><td style="padding:22px 24px 0 24px;" class="pad">' + box("⚓ Before you buy for a Léman mooring in Geneva", [
            'Boat licence: on Swiss waters a licence is needed above 6 kW engine power or 15 m² of sail; on Lake Geneva the motor limit is 10 CV. Category A = motor (18+), D = sail (14+). '
            '<a href="https://www.bav.admin.ch/fr/navigation-de-plaisance">OFT</a> · <a href="https://www.ge.ch/obtenir-permis-conduire-bateaux">ge.ch</a>',
            'Plates: a boat moored in a Geneva port must be registered in Geneva (OCV, CHF 105). Moving a boat from another canton or changing owner means a new navigation permit. '
            '<a href="https://www.ge.ch/immatriculer-bateau">ge.ch: immatriculer un bateau</a>',
            'Inspection: required before registration for motorboats over 9 years old last checked more than 4 years ago (sail and rowing boats: more than 7 years). Ask the seller for the permit and the last inspection date.',
            'Liability insurance is required to register, except rowing boats and sailboats up to 15 m² of sail.',
            'Boats far from the Léman need road transport: check for a trailer, and the beam and weight for your slip.'], ORANGE, "#FEF4E8") + "</td></tr>")
        if large:
            nav = " · ".join(f'<a href="#cat-{c}" style="color:{NAVY};">{CAT_LABEL[c]} ({len(by_cat[c])})</a>' for c in CAT_ORDER if by_cat[c])
            lead = (f"This edition has {n} new boats, so the email shows the {PICKS_PER_CAT} best matches in each category "
                    f"(ranked by asking price and road distance from Geneva; three as cards, the rest as a short list). "
                    f'<a href="{SITE_URL}" style="color:{NAVY};font-weight:700;">The live table</a> has every boat, with filters, a map and CSV export. Jump to: {nav}')
            P.append(h2("Top picks", "Best matches per category for a Geneva mooring", lead))
            FEATURED = 3  # full cards, then compact rows, so 8 picks stay under the Gmail size cap
            for c in CAT_ORDER:
                if not by_cat[c]:
                    continue
                picks = top_picks(by_cat[c], PICKS_PER_CAT)
                featured, compact = picks[:FEATURED], picks[FEATURED:]
                extra = "" if len(by_cat[c]) <= len(picks) else (
                    f'<div style="padding:10px 0 0;font:700 12px/1.3 {SANS};">'
                    f'<a href="{SITE_URL}#v=cats" style="color:{ORANGE};">+ {len(by_cat[c]) - len(picks)} more {CAT_LABEL[c].lower()} in the live table →</a></div>'
                )
                compact_html = ""
                if compact:
                    compact_html = (
                        f'<div style="font:700 11px/1 {SANS};color:{MUTED};text-transform:uppercase;letter-spacing:.06em;padding:12px 0 2px;">also in the top {len(picks)}</div>'
                        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
                        + "".join(row(r) for r in compact) + "</table>"
                    )
                P.append(f'<tr><td style="padding:18px 24px 0 24px;" class="pad"><a name="cat-{c}" id="cat-{c}"></a><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                         f'<td style="border-bottom:3px solid {CAT_COL[c]};padding-bottom:6px;font:400 20px/1.2 {SERIF};color:{NAVY};">{CAT_ICON[c]} {CAT_LABEL[c]}</td>'
                         f'<td align="right" style="border-bottom:3px solid {CAT_COL[c]};padding-bottom:6px;font:700 12px/1 {SANS};color:{MUTED};white-space:nowrap;">{len(by_cat[c])} boats · top {len(picks)} · from {chf(by_cat[c][0]["price_chf"])}</td></tr></table>'
                         + "".join(card(r) for r in featured) + compact_html + extra + "</td></tr>")
            P.append(cta("See all " + str(n) + " boats in the live table →"))
        else:
            nav = " · ".join(f'<a href="#cat-{c}" style="color:{NAVY};">{CAT_LABEL[c]} ({len(by_cat[c])})</a>' for c in CAT_ORDER if by_cat[c])
            P.append(h2("All boats", "Listings by category", f"Every new boat, sorted by price within each category. Jump to: {nav}"))
            for c in CAT_ORDER:
                if not by_cat[c]:
                    continue
                P.append(f'<tr><td style="padding:18px 24px 0 24px;" class="pad"><a name="cat-{c}" id="cat-{c}"></a><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                         f'<td style="border-bottom:3px solid {CAT_COL[c]};padding-bottom:6px;font:400 20px/1.2 {SERIF};color:{NAVY};">{CAT_ICON[c]} {CAT_LABEL[c]}</td>'
                         f'<td align="right" style="border-bottom:3px solid {CAT_COL[c]};padding-bottom:6px;font:700 12px/1 {SANS};color:{MUTED};white-space:nowrap;">{len(by_cat[c])} boats · from {chf(by_cat[c][0]["price_chf"])}</td></tr></table>'
                         + "".join(card(r) for r in by_cat[c]) + "</td></tr>")
            P.append(h2("Filter view", "By price band", "Compact index of the same boats; tap a name to open the ad.", "price-bands"))
            for lbl, lo, hi in PRICE_BANDS:
                rs = sorted([r for r in priced if lo <= r["price_chf"] < hi], key=dist)
                if not rs:
                    continue
                items = " · ".join(f'<a href="{e(r["url"])}" style="color:{NAVY};text-decoration:none;">{e(r["title"][:42])}</a> <span style="color:{MUTED};">{chf(r["price_chf"])}, {km(r)}</span>' for r in rs)
                P.append(f'<tr><td style="padding:8px 24px 0 24px;" class="pad"><div style="font:900 12px/1.3 {SANS};color:{ORANGE};text-transform:uppercase;letter-spacing:.06em;">{lbl} CHF · {len(rs)} boats (nearest first)</div>'
                         f'<div style="font:400 12px/1.6 {SANS};color:{INK};margin-top:3px;">{items}</div></td></tr>')
            P.append(h2("Filter view", "By distance from Geneva", "Road distance; counts per category, then the three cheapest boats in each band.", "distance-bands"))
            head = "".join(f'<th style="font:700 10px/1.2 {SANS};color:#FFFFFF;background:{NAVY};padding:6px 4px;text-transform:uppercase;">{CAT_ICON[c]}</th>' for c in CAT_ORDER)
            body = []
            for lbl, lo, hi in DIST_BANDS:
                inb = (lambda r: not isinstance(r.get("distance_km_from_geneva"), (int, float))) if lo is None else (lambda r, lo=lo, hi=hi: lo <= dist(r) < hi)
                rs = [r for r in rows if inb(r)]
                if not rs:
                    continue
                cells = "".join(f'<td align="center" style="font:400 12px/1 {SANS};padding:6px 2px;border-bottom:1px solid {LGREY};color:{INK if any(r["category"]==c for r in rs) else GREY};">{sum(1 for r in rs if r["category"]==c) or "·"}</td>' for c in CAT_ORDER)
                top = sorted([r for r in rs if isinstance(r["price_chf"], (int, float))], key=lambda r: r["price_chf"])[:3]
                tops = "<br>".join(f'<a href="{e(r["url"])}" style="color:{NAVY};text-decoration:none;">{e(r["title"][:34])}</a> <span style="color:{MUTED};">{chf(r["price_chf"])}</span>' for r in top)
                body.append(f'<tr><td style="font:700 12px/1.2 {SANS};color:{NAVY};padding:6px 4px;border-bottom:1px solid {LGREY};white-space:nowrap;">{lbl}<div style="font:400 11px/1.2 {SANS};color:{MUTED};">{len(rs)} boats</div></td>{cells}'
                            f'<td class="hide-m" style="font:400 11px/1.4 {SANS};padding:6px 4px;border-bottom:1px solid {LGREY};">{tops}</td></tr>')
            P.append(f'<tr><td style="padding:6px 24px 0 24px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
                     f'<tr><th align="left" style="font:700 10px/1.2 {SANS};color:#FFFFFF;background:{NAVY};padding:6px 4px;text-transform:uppercase;">Band</th>{head}<th class="hide-m" align="left" style="font:700 10px/1.2 {SANS};color:#FFFFFF;background:{NAVY};padding:6px 4px;text-transform:uppercase;">Cheapest three</th></tr>{"".join(body)}</table></td></tr>')
        # footer
    src_lines = []
    for s, v in status.items():
        nm = {"tutti": "tutti.ch", "anibis": "anibis.ch", "bateau24": "boat24 Swiss site (bateau24.ch)", "ricardo": "ricardo.ch", "facebook_marketplace": "Facebook Marketplace"}.get(s, s)
        cnt = sum(1 for r in rows if r["source"] == s)
        src_lines.append(f"{nm}: {cnt} in this digest" if v.get("ok") else f"{nm}: not included ({e(v.get('error') or 'failed')})")
    P.append(f'''<tr><td style="padding:26px 24px 24px 24px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #D5DCE4;"><tr><td style="padding-top:12px;font:400 11px/1.55 {SANS};color:{MUTED};">
<b style="color:{NAVY};">Sources & method.</b> {" · ".join(src_lines)}. Used boats asking up to CHF 30'000 (or free), located in Switzerland; accessories, engines, trailers, moorings, kayaks and SUPs are filtered out by keywords, so a few odd items can slip through. Categories come from the site's boat type (boat24) or from title keywords (tutti, anibis).
Distance = driving distance by road from Geneva centre (46.2044 N, 6.1432 E) via the public OSRM router on OpenStreetMap data, to the listing's coordinates (tutti, anibis) or to the town geocoded with Nominatim (boat24; lake centre when only the lake is given). If OSRM is unreachable: straight line × 1.25.
{removed_n} boats were marked removed since the last run. Licence hints use the stated engine power only; always check the ad. Prices and details are the sellers' own, copied {fr_date_short(d)}.
</td></tr></table></td></tr></table></td></tr></table></body></html>''')
    return "".join(P)
