# -*- coding: utf-8 -*-
"""French digest for the filtre global (daily + one-time selection)."""
from digest import (NAVY, TEAL, ORANGE, GREY, LGREY, GREEN, RED, INK, MUTED, PAPER,
                    SERIF, SANS, CAT_ICON, SITE_URL, e, chf, km, has, specs, where,
                    kpi, h2, box, cta)

CAT_LABEL_FR = {"sail": "Voiliers", "motor": "Bateaux à cabine", "open": "Bateaux ouverts et day-cruisers",
                "inflatable": "Pneumatiques et semi-rigides", "small": "Annexes, aviron et petits bateaux", "other": "Autres"}
SRC_LABEL_FR = {"tutti": "tutti.ch", "anibis": "anibis.ch", "bateau24": "boat24 (bateau24.ch)", "lakeboat": "lakeboat.ch",
                "petitesannonces": "petitesannonces.ch", "aquaboat": "aquaboat.ch", "ricardo": "ricardo.ch",
                "facebook_marketplace": "Facebook Marketplace", "swissboat.ch": "swissboat.ch"}
from frdate import fr_date_long

def date_fr(d):
    """'Lundi 23 novembre 2026', independent of the system locale."""
    return fr_date_long(d)

def badge_fr(text, bg, fg="#FFFFFF"):
    return (f'<span style="display:inline-block;background:{bg};color:{fg};font:700 10px/1 {SANS};'
            f'letter-spacing:.06em;text-transform:uppercase;padding:4px 6px;border-radius:3px;margin-right:4px;">{e(text)}</span>')

def also_fr(r):
    al = r.get("also_listed")
    if not isinstance(al, list) or not al:
        return ""
    return " · aussi sur " + ", ".join(f'<a href="{e(a["url"])}" style="color:{GREY};">{e(SRC_LABEL_FR.get(a["source"], a["source"]))}</a>' for a in al)

def card_fr(r, info=None, big=False):
    info = info or {}
    img = r.get("thumb_url") if has(r.get("thumb_url")) else None
    w = 120 if big else 84
    hgt = int(w * 0.75)
    pic = (f'<a href="{e(r["url"])}"><img src="{e(img)}" width="{w}" height="{hgt}" alt="" style="display:block;width:{w}px;height:{hgt}px;object-fit:cover;border-radius:5px;border:0;background:{LGREY};"></a>'
           if img else f'<div style="width:{w}px;height:{hgt}px;background:{LGREY};border-radius:5px;text-align:center;font:400 28px/{hgt}px {SANS};">{CAT_ICON.get(r["category"], "⚓")}</div>')
    price_col = GREEN if isinstance(r["price_chf"], (int, float)) and r["price_chf"] < 10000 else NAVY
    flags = ""
    if info.get("zone") == "zone1":
        flags += badge_fr("Zone 1" + (f" · {info['lake']}" if info.get("lake") else ""), TEAL) + " "
    elif info.get("zone") == "zone2":
        flags += badge_fr("Zone 2", NAVY) + " "
    if info.get("bucket") == "a_verifier":
        flags += badge_fr("À vérifier", ORANGE) + " "
    if info.get("opportunite"):
        flags += badge_fr("Très bonne opportunité", GREEN) + " "
    if r.get("trailer") == "yes":
        flags += badge_fr("Remorque", "#E8EEF5", NAVY) + " "
    sp = specs(r)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid {LGREY};"><tr>'
            f'<td width="{w + 12}" valign="top" style="padding:10px 12px 10px 0;">{pic}</td>'
            f'<td valign="top" style="padding:10px 0;"><a href="{e(r["url"])}" style="font:700 14px/1.3 {SANS};color:{NAVY};text-decoration:none;">{e(r["title"][:90])}</a>'
            f'<div style="font:400 12px/1.45 {SANS};color:{MUTED};margin-top:3px;">📍 {e(where(r))} · <b style="color:{INK};">{km(r)}</b> de Genève</div>'
            + (f'<div style="font:400 12px/1.45 {SANS};color:#33415C;margin-top:1px;">{e(sp)}</div>' if sp else "") +
            f'<div style="margin-top:5px;">{flags}<span style="font:400 11px/1 {SANS};color:{GREY};">{e(SRC_LABEL_FR.get(r["source"], r["source"]))}{also_fr(r)}</span></div></td>'
            f'<td width="96" valign="top" align="right" style="padding:10px 0 10px 8px;"><div style="font:900 15px/1.2 {SANS};color:{price_col};white-space:nowrap;">{chf(r["price_chf"])}</div>'
            f'<a href="{e(r["url"])}" style="display:inline-block;margin-top:8px;font:700 11px/1 {SANS};color:#FFFFFF;background:{NAVY};padding:6px 9px;border-radius:4px;text-decoration:none;">Voir l’annonce →</a></td></tr></table>')

def row_fr(r, info=None):
    info = info or {}
    cheap = isinstance(r["price_chf"], (int, float)) and r["price_chf"] < 10000
    sp = specs(r)
    flags = ""
    if info.get("opportunite"):
        flags += ' <span style="color:#2E9E5B;font-weight:700;">★ opportunité</span>'
    if info.get("bucket") == "a_verifier":
        flags += ' <span style="color:#F08A24;font-weight:700;">à vérifier</span>'
    return (f'<tr><td style="padding:5px 0;border-bottom:1px solid {LGREY};font:400 12.5px/1.35 {SANS};"><a href="{e(r["url"])}" style="color:{NAVY};font-weight:700;text-decoration:none;">{e(r["title"][:70])}</a>'
            f'<br><span style="color:{MUTED};font-size:11.5px;">{e(where(r))} · {km(r)}{" · " + e(sp) if sp else ""}{flags}</span></td>'
            f'<td align="right" valign="top" style="padding:5px 0 5px 8px;border-bottom:1px solid {LGREY};font:900 12.5px/1.35 {SANS};color:{GREEN if cheap else NAVY};white-space:nowrap;">{chf(r["price_chf"])}</td></tr>')

def render_filtre(pairs, all_active, status, today, mode="daily"):
    from datetime import date
    d = date.fromisoformat(today)
    n = len(pairs)
    z1 = sorted([(r, i) for r, i in pairs if i["bucket"] == "zone1"], key=lambda x: -x[1]["score"])
    z2 = sorted([(r, i) for r, i in pairs if i["bucket"] == "zone2"],
                key=lambda x: (not x[1].get("opportunite"), x[0]["price_chf"] if isinstance(x[0]["price_chf"], (int, float)) else 1e9))
    av = [(r, i) for r, i in pairs if i["bucket"] == "a_verifier"]
    av_z1 = [p for p in av if p[1].get("zone") == "zone1"]
    av_z2 = [p for p in av if p[1].get("zone") != "zone1"]
    opp_n = sum(1 for _, i in pairs if i.get("opportunite"))
    dfr = date_fr(d)

    if mode == "selection":
        kicker = "Sélection initiale"
        title = "Hors-bord pour une place au Léman"
        subtitle = (f"{dfr} · tous les bateaux actuellement en ligne qui correspondent au filtre global, "
                    "y compris ceux déjà envoyés dans la première édition")
        kpi_label = "Bateaux retenus"
    else:
        kicker = "Digest quotidien"
        title = "Nouveaux hors-bord depuis le dernier envoi"
        subtitle = (f"{dfr} · uniquement les bateaux pas encore envoyés, "
                    "filtrés pour une place d’amarrage au Léman")
        kpi_label = "Nouveaux bateaux"

    P = []
    P.append(
        f'<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="x-apple-disable-message-reformatting">'
        f'<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">'
        f'<title>Nico Boats · {dfr}</title>'
        f"<style>body{{margin:0;padding:0;background:#E9EDF2;}} a{{color:{NAVY};}} img{{border:0;}}"
        f"@media only screen and (max-width:620px){{ .wrap{{width:100%!important;}} .kpi{{display:inline-block!important;width:50%!important;box-sizing:border-box;padding:4px!important;}}"
        f".stack{{display:block!important;width:100%!important;box-sizing:border-box;}} .pad{{padding-left:14px!important;padding-right:14px!important;}} .hide-m{{display:none!important;}} }}</style></head>"
        f'<body style="margin:0;padding:0;background:#E9EDF2;">'
        f'<div style="display:none;max-height:0;overflow:hidden;">{n} bateaux hors-bord retenus · {len(z1)} en zone prioritaire · {opp_n} très bonnes opportunités</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#E9EDF2;"><tr><td align="center" style="padding:18px 8px;">'
        f'<table role="presentation" class="wrap" width="680" cellpadding="0" cellspacing="0" style="width:680px;max-width:680px;background:#FFFFFF;border-radius:10px;overflow:hidden;">'
    )
    P.append(
        f'<tr><td style="background:{NAVY};padding:26px 24px 22px 24px;" class="pad">'
        f'<div style="font:900 11px/1 {SANS};letter-spacing:.16em;color:{ORANGE};text-transform:uppercase;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{ORANGE};margin-right:6px;"></span>Nico Boats · {e(kicker)}</div>'
        f'<div style="font:400 32px/1.1 {SERIF};color:#FFFFFF;margin-top:10px;">{e(title)}</div>'
        f'<div style="font:400 14px/1.5 {SANS};color:#C8D3E0;margin-top:8px;">{subtitle}</div></td></tr>'
        f'<tr><td style="background:{TEAL};height:4px;font-size:0;line-height:0;">&nbsp;</td></tr>'
    )
    P.append(
        f'<tr><td style="padding:20px 20px 4px 20px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        + kpi(n, kpi_label, f"sur {len(all_active)} annonces actives", NAVY)
        + kpi(len(z1), "Zone 1", "Léman, Neuchâtel, Morat, Bienne", TEAL)
        + kpi(len(z2), "Zone 2", "reste de la Suisse", ORANGE)
        + kpi(len(av), "À vérifier", "un critère manque encore", "#7B5EA7")
        + "</tr></table></td></tr>"
    )
    P.append(cta("Ouvrir le tableau vivant et la carte →", "Toutes les annonces actives, avec filtres, carte et export CSV"))
    if n == 0:
        P.append(h2(
            "Aujourd’hui", "Aucun nouveau bateau depuis le dernier envoi",
            f'Rien de nouveau ne correspond au filtre global. Le <a href="{SITE_URL}" style="color:{NAVY};font-weight:700;">tableau vivant</a> liste toujours toutes les annonces actives, avec le filtre global activé par défaut.'
        ))
    else:
        lead = (
            "Hors-bord à coque rigide de 40 à 90 CV, largeur max. 2,30 m, longueur max. 7,00 m, prix max. CHF 15’000. "
            "Les pneumatiques, gonflables et semi-rigides (RIB) sont exclus. "
            "Zone 1 = lacs Léman, de Neuchâtel, de Morat et de Bienne. Zone 2 = le reste de la Suisse, "
            "avec les très bonnes opportunités mises en avant. "
            "Les bateaux dont la puissance, la largeur ou la longueur n’est pas indiquée ne sont pas écartés automatiquement : ils figurent sous « À vérifier »."
        )
        P.append(h2("Le filtre", "Comment lire cette sélection", lead))
        if z1:
            P.append(h2("Zone 1 — prioritaire", "Sur les lacs Léman, de Neuchâtel, de Morat et de Bienne",
                        f"{len(z1)} bateaux dont tous les critères connus sont dans les clous."))
            P.append('<tr><td style="padding:0 24px;" class="pad">' + "".join(card_fr(r, i, True) for r, i in z1) + "</td></tr>")
        if z2:
            opp_z2 = sum(1 for _, i in z2 if i.get("opportunite"))
            P.append(h2("Zone 2 — reste de la Suisse", "Plus loin, si ça vaut le déplacement",
                        f"{len(z2)} bateaux ailleurs en Suisse. {opp_z2} sont signalés comme très bonne opportunité (prix nettement sous des bateaux comparables, remorque, moteur récent…)."))
            P.append('<tr><td style="padding:0 24px;" class="pad">' + "".join(card_fr(r, i) for r, i in z2) + "</td></tr>")
        if av:
            P.append(h2("À vérifier", "Les autres critères correspondent, mais une donnée manque",
                        f"{len(av)} annonces (dont {len(av_z1)} en zone 1) où la puissance, la largeur, la longueur ou le type de moteur n’est pas indiqué. Elles ne sont pas écartées : à confirmer sur l’annonce."))
            P.append('<tr><td style="padding:0 24px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
                     + "".join(row_fr(r, i) for r, i in av_z1 + av_z2) + "</table></td></tr>")
        P.append(cta("Voir toute la sélection dans le tableau vivant →", "Toutes les annonces actives, avec filtres, carte et export CSV"))
    P.append('<tr><td style="padding:22px 24px 0 24px;" class="pad">' + box("⚓ Avant d’acheter pour une place au Léman, à Genève", [
        'Permis : en eaux suisses, un permis est exigé au-delà de 6 kW ou de 15 m² de voilure ; sur le Léman, la limite moteur est de 10 CV. Catégorie A = moteur (18 ans), D = voile (14 ans). '
        '<a href="https://www.bav.admin.ch/fr/navigation-de-plaisance">OFT</a> · <a href="https://www.ge.ch/obtenir-permis-conduire-bateaux">ge.ch</a>',
        'Immatriculation : un bateau amarré dans un port genevois doit être immatriculé à Genève (OCV, CHF 105). Un changement de canton ou de propriétaire implique un nouveau permis de navigation. '
        '<a href="https://www.ge.ch/immatriculer-bateau">ge.ch : immatriculer un bateau</a>',
        'Contrôle technique : obligatoire avant l’immatriculation pour les bateaux à moteur de plus de 9 ans dont le dernier contrôle date de plus de 4 ans (voile et aviron : plus de 7 ans). Demandez le permis et la date du dernier contrôle.',
        'Une assurance responsabilité civile est exigée pour s’immatriculer, sauf pour les barques à rames et les voiliers jusqu’à 15 m² de voilure.',
        'Pour un bateau loin du Léman, prévoyez le transport : remorque, largeur et poids pour votre rampe.'], ORANGE, "#FEF4E8") + "</td></tr>")
    src_lines = []
    for s, v in (status or {}).items():
        if s.startswith("_"):
            continue
        nm = SRC_LABEL_FR.get(s, s)
        cnt = sum(1 for r, _ in pairs if r["source"] == s or any(a.get("source") == s for a in (r.get("also_listed") if isinstance(r.get("also_listed"), list) else [])))
        src_lines.append(f"{nm} : {cnt} dans cette sélection" if v.get("ok") else f"{nm} : non inclus (captcha Cloudflare, le site refuse la collecte automatique depuis le 21 nov.)" if v.get("blocked") else f"{nm} : non inclus ({e(v.get('error') or 'échec')})")
    P.append(
        f'<tr><td style="padding:26px 24px 24px 24px;" class="pad"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #D5DCE4;"><tr><td style="padding-top:12px;font:400 11px/1.55 {SANS};color:{MUTED};">'
        f"<b style=\"color:{NAVY};\">Sources et méthode.</b> {' · '.join(src_lines)}. "
        "Filtre global (version enregistrée dans le dépôt) : hors-bord uniquement, 40 à 90 CV, largeur max. 2,30 m, longueur max. 7,00 m, prix max. CHF 15’000. "
        "Pas de voiliers, annexes, pédalos ni bateaux à rames. Pas de pneumatiques, gonflables ni semi-rigides (RIB) : ils sont repérés par la catégorie du site, le matériau (Hypalon, PVC), le titre, la description et les marques spécialisées (Zodiac, Bombard, Brig, Highfield, 3D Tender, Joker Boat…). "
        "Les valeurs manquantes (puissance, largeur, longueur) ne font pas écarter l’annonce : elle va dans « À vérifier », sauf si elle est clairement hors sujet. "
        f"La distance indiquée est la distance routière depuis le centre de Genève. Prix et caractéristiques sont ceux des vendeurs, relevés le {date_fr(d)[0].lower() + date_fr(d)[1:]}."
        "</td></tr></table></td></tr></table></td></tr></table></body></html>"
    )
    return "".join(P)
