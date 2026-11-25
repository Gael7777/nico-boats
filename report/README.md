# Nico Boats : digest quotidien et magasin

Les textes destinés à Gael (digest, site, ce chapitre sur le filtre) sont en **français**. Le détail technique ci-dessous reste utile pour relancer le pipeline.

## Filtre global (`../config/filtre_global.json`)

Fichier versionné (aujourd’hui version 2 : exclusion des pneumatiques et semi-rigides). `build.py` s’en sert pour le score / la classification, le digest, et les valeurs par défaut du site.

- **Type :** hors-bord à coque rigide seulement (bateaux ouverts ou à cabine). Pas de voiliers, annexes, pédalos, aviron.
- **Pneumatiques / semi-rigides (v2) :** exclus. `filtre.inflatable_reason()` regarde, dans l’ordre : catégorie `inflatable` du site ; mots-clés (`criteria.inflatables.keywords`) dans le titre ou le type du site, sauf « annexe / avec pneumatique / remorque pour… » ; matériau Hypalon / PVC (le « PVC/Hypalon » deviné dans le texte libre ne compte que si « hypalon » est écrit, sinon une « bâche PVC » ferait sauter un bateau rigide) ; marques 100 % pneumatiques (champ marque structuré de boat24 / lakeboat / aquaboat, ou marque écrite dans le titre ; jamais une marque devinée dans la description) ; marques mixtes seulement pour les gammes pneumatiques (`brands_mixed` : Ranieri Cayman, Capelli Tempest, Selva D…, Quicksilver Heavy-Duty…) ; enfin la description, si le mot décrit le bateau lui-même et qu’aucune coque polyester / alu / bois n’est mentionnée. La raison est visible dans `site/data/listings.json` → `_filtre.reasons`.
- **Puissance :** 40 à 90 CV. **Largeur max. 2,30 m. Longueur max. 7,00 m. Prix max. CHF 15’000.**
- **Zone 1 (prioritaire) :** sur ou près des lacs Léman, de Neuchâtel, de Morat et de Bienne (listes de communes et de codes postaux dans le JSON, plus distance à la rive ≤ 12 km si l’on a les coordonnées).
- **Zone 2 :** reste de la Suisse, dans une section à part, avec un badge « Très bonne opportunité » si le prix est clairement sous des bateaux comparables (longueur / puissance / année), s’il y a une remorque ou un moteur récent.
- **Valeurs manquantes :** une puissance, une largeur ou une longueur en N/A ne fait **pas** écarter le bateau en silence. Il va dans le seau **« À vérifier »** si le reste correspond, sauf s’il est clairement hors sujet ( « sans permis », à donner, moteur in-bord, etc.).
- **Déduplication :** les 912 bateaux de la première édition restent marqués `sent_in_digest = 2026-11-15`. Le digest quotidien suivant ne contient que les nouveaux bateaux encore en `N/A` qui passent le filtre. La sélection initiale (`digest/selection-initiale-YYYY-MM-DD.html`) liste *tous* les correspondants actuels, déjà envoyés ou non, et **n’est pas envoyée** automatiquement.

Pour régénérer sans recollecter :

```bash
python3 build.py --no-collect --selection-initiale
```


Daily scan of used boats for sale across Switzerland (asking up to CHF 30'000, or free), for a Léman mooring in Geneva.
This folder builds the HTML email and updates the master store; `../site/` is the static web table.

## Layout
```
nico-boats/
├── data/listings.json      MASTER STORE (source of truth), one record per boat
├── data/listings.csv       same, flat CSV export (rewritten every run)
├── report/
│   ├── build.py            pipeline entry point (scrape → merge → digest → site data → previews)
│   ├── collect.py          scrapers + classification + geocoding/road distance
│   ├── store.py            record schema, merge rules, CSV export
│   ├── digest.py           email-safe HTML renderer
│   ├── data/raw_today.json last scrape (raw rows + per-source status)
│   ├── digest/YYYY-MM-DD.html (+ latest.html)   the email body
│   ├── preview/YYYY-MM-DD-desktop.png / -mobile.png
│   └── cache/              detail-page HTML (7 days), geocodes, OSRM routes
└── site/                   static site for GitHub Pages (index.html, assets/, data/listings.json)
```

## Rerun
```bash
cd /workspace/projects/nico-boats/report
python3 build.py                 # full run: scrape, merge into the store, write today's digest, refresh site data, PNG previews
python3 build.py --no-collect    # rebuild from report/data/raw_today.json without scraping
python3 build.py --no-mark       # do not mark boats as sent (dry run of the digest)
python3 build.py --no-shots      # skip the headless-Chrome previews
```
Needs Python 3 with `requests` (and Pillow for preview trimming) and Google Chrome for previews. A full run takes about 10 minutes the first time
(detail pages are fetched politely, ~0.5 s apart); later runs reuse cached detail pages and only fetch new ads.

## Rules
* **Dedup / sent tracking**: the digest contains only active boats whose `sent_in_digest` is `N/A` (or today, so a same-day rerun gives the same email).
  After writing the digest each boat gets `sent_in_digest = <date>`. The first run sends everything as a baseline.
* **Merge, never overwrite**: new id → `first_seen`; known id → fields refreshed and `last_seen` updated, a value found before is never replaced by `N/A`;
  price change → appended to `price_history`, `previous_price_chf` + `price_changed_on` set, and listed in the digest's "Price changes" box;
  active boat not seen today **and its source worked today** → `status = removed`, `removed_on`.
* Missing values are always the string `"N/A"`.
* **Distance**: road distance from Geneva centre (46.2044, 6.1432) by the public OSRM router (OpenStreetMap). Origin point: the ad's own coordinates
  (tutti, anibis) or the town geocoded with Nominatim (boat24; lake centre if only the lake is given). Fallback when OSRM fails: straight line × 1.25.
* `licence_leman` is a hint from the stated engine power only (OFT: licence above 6 kW or 15 m² sail on Swiss waters; motor limit 10 CV on Lake Geneva).

## Sources (status 2026-11-23)
| Source | Method | Status |
|---|---|---|
| lakeboat.ch | Yoast sitemap `job_listing-sitemap.xml` (FR URLs `/bateau-occasion-suisse/…`), each detail page: JSON-LD `LocalBusiness` (name, description, address, lat/lng, photos) + MyListing `item-attr`/`item-property` pairs (type, marque, modèle, prix, lac). Schools, rentals and accessories have no "Bateau moteur"/"Voilier" block and are skipped | works; the sitemap also lists old ads (posted 2025), they stay until they disappear |
| petitesannonces.ch | rubric lists `/r/3503` (moteur), `/r/3504` (voiliers), `/r/3506` (pneumatiques), `/r/3502` (barques), `?p=N`; detail `/a/<id>` for text, postcode/town, date, photo. Foreign ads (France, Italie) skipped | works |
| aquaboat.ch | dealer at Le Bouveret; public `https://aquaboat.ch/boats.json` (the site's own catalogue feed, no login), only offers *occasion / déstockage / démonstration*; detail page for length/width/description | works (few boats under CHF 30k) |
| boot24.ch | same Boat24 database as bateau24.ch (German domain, same listing ids) | covered by the bateau24 scraper, not scraped twice |
| trovas.ch | keyword search aggregator; republishes petitesannonces ads, no plain pagination | not scraped (duplicates petitesannonces) |
| swissboat.ch | Anubis proof-of-work bot wall | not scraped |
| tutti.ch | direct: category "Bateaux & accessoires" search pages (`__NEXT_DATA__` JSON), ad pages for coordinates and full text. **Fallback: ScanMarket** (below) | direct scrape **blocked since 2026-11-21** (worked 15-20 Nov): every URL on the domain, even `robots.txt`, answers HTTP 403 `cf-mitigated: challenge` with an interactive Cloudflare Turnstile page. Same from headless/headful Chrome and from GitHub Actions runners. Not worked around (no captcha solving, no borrowed cookies). The collector still tries it first every morning (one request, stops at the first challenge) and falls back to ScanMarket |
| anibis.ch | same platform as tutti, same method and same fallback | direct scrape **blocked since 2026-11-21**, same Turnstile page |
| scanmarket.ch (tutti + anibis republisher) | `GET https://scanmarket.ch/api/search?q=&category=boats&sources=tutti,anibis&page=N&page_size=50`, whole boats category (~11 pages), 1.5 s between pages, UA `nico-boats-digest/1.0 (+repo; one read per day)`, backoff on 429/5xx, stops cleanly on failure. The pass is saved in `report/cache/scanmarket/<date>.json` and reused by any rerun that day (one read per day). Fields: title, full description, price, town, postcode, canton, photo, `posted_at`, `scraped_at`. No coordinates: the town is geocoded (Nominatim), or the exact coordinates already stored from the direct scrape are kept. Approved by Gael on 2026-11-23 although its `robots.txt` disallows `/api/` | works (2026-11-23: 550 reported, 544 unique = 330 tutti + 214 anibis, of which 140 boats kept) |
| boat24 Swiss site (bateau24.ch) | server-rendered list `bateauxdoccasion/?whr=CHF&prs_max=30000&page=<offset>`, ad pages for specs and town | works (boat24.com itself sits behind a Cloudflare challenge) |
| ricardo.ch | search page, category page, `/api/mfa/search`, mobile UA, headless Chrome | blocked (2026-11-15 retry): HTTP 403 "Ricardo Captcha" page, API answers 429 / Cloudflare error 1015, headless Chrome gets "Just a moment…". Not worked around (no captcha solving, no borrowed cookies) |
| Facebook Marketplace | n/a | needs a logged-in session, not scraped |

Accessories, engines, trailers, moorings, kayaks and SUPs are filtered by keyword rules in `collect.py` (`ACC_START`, `ACC_ANY`, `BOAT`). Fix a rule there and run
`python3 build.py --no-collect` to re-apply it.

## Cross-source duplicates
`collect.merge_duplicates()` merges the same boat seen on several sites (or reposted on one site, except boat24 dealers): same price, title tokens overlap ≥ 60 % (brand/model words, without "bateau", "moteur"…), and within 30 km when both have coordinates (otherwise ≥ 80 % title overlap). The kept row is the one **already in the store** (so `sent_in_digest` and price history follow it), otherwise by source priority boat24 > tutti > anibis > lakeboat > petitesannonces > aquaboat. The others become `also_listed: [{source, url}]` (shown as "aussi sur …" in the site and the digest) and fill the kept row's empty fields. Two rows that are both already in the store are only cross-linked, never merged, so no stored boat is suddenly marked removed.

## Lessons (2026-11-15)
* `build.py` marks the digest's boats as sent **when it builds**, not when the mail leaves. Always use `--no-mark` for rebuilds that will not be sent; on the baseline day (2026-11-15) a marked boat would even be treated as "baseline" and never be sent.
* `rich_fields()` must not call a boat electric because the text mentions an "électrique" pump or windlass; it now needs "moteur électrique", Torqeedo, ePropulsion, Minn Kota… and no thermal power ≥ 20 CV.
* For free-text sites, run `rich_fields()` before `extract_specs()` (`apply_text_fields`): "9 m x 3.18 m" otherwise yields a 3.18 m length.
* The store never replaces a known value by N/A, so a wrong value parsed once (e.g. an old "electric") sticks on existing records until a source gives a new non-N/A value.
* Inflatable detection: never trust a brand guessed from the description (an ad can mention "notre ancien Zodiac"), and treat "annexe pneumatique / avec pneumatique" as an extra, not as the boat.

## Lessons (2026-11-23)
* **Dates in French without locale.** `fr_FR` is not installed on the box, so `strftime("%B")` and `date +%B` give English. Use `report/frdate.py` (`fr_date`, `fr_date_long`, `subject`): hard-coded French month / day names, « 1er » for the first. `python3 report/frdate.py subject 2026-11-24` → `Nico Boats – 24 novembre 2026`. `publish_and_send.sh` builds this subject by default and translates any English month left in a `--subject`.
* **Push.** `publish_and_send.sh` now commits `digest/`, `data/`, `site/data/`, `config/` and `report/digest/`, then calls `scripts/git_push.sh`: fetch + rebase on `origin/main`, push with `GITHUB_NICO_BOATS_TOKEN` in the URL of that one command (never in `.git/config`, output redacted). `--no-send` pushes without dispatching the e-mail. A push touching `data/` or `site/` redeploys Pages.
* **Bot walls.** `collect.get()` raises `Blocked` on a Cloudflare challenge (`cf-mitigated: challenge` or captcha markers) instead of retrying, backs off exponentially on 429 / 5xx (honours `Retry-After`), and `main()` stores `blocked: true` so the digest says « captcha Cloudflare » rather than a raw error. Moving the scrape to GitHub Actions does not help: runner IPs get the same Turnstile (tested 2026-11-23).

## Lessons (2026-11-23, ScanMarket)
* **Records keep the original source.** ScanMarket rows become `tutti:<id>` / `anibis:<id>` (ScanMarket's `source_listing_id` is the tutti / anibis id), so they update the boats already in the store and `sent_in_digest` is kept: an already-sent boat is never sent again. `url` is `https://www.<site>.ch/fr/vi/<id>`. `via_scanmarket` (`true` / `false`) and `collecte` (« ScanMarket (republication de tutti.ch), lu par ScanMarket le … » or « direct (tutti.ch) ») say how each fiche was read.
* **ScanMarket is a partial mirror.** On 2026-11-23 it had 330 tutti ads in « boats » while tutti's own category reported 1’062 (accessories included), and 157 of our 272 active tutti/anibis boats were absent. Marking every absent ad as removed would have removed boats that are still online. Rule in `store.merge()`: for a source read through ScanMarket, an absent ad is marked `removed` only if it carries `via_scanmarket = true` (an earlier ScanMarket pass had it) **and** today's pass is complete (no error, `has_more` false, ≥ 97 % of `total`, and at least half as many ads as we hold for that source). An incomplete pass still adds / updates boats (`partial: true`) but never removes.
* **ScanMarket data can be old.** It re-reads an ad only now and then (`scraped_at` from 24 Oct to 23 Nov on 2026-11-23). A ScanMarket value older than our own `last_seen` does not change the stored price, and an ad we saw go (`removed_on`) is not brought back by a `scraped_at` older than that date (10 skipped on 2026-11-23).
* **German titles.** ScanMarket gives SMG's German version of each ad (« Motorboot Cobalt 233 » for « Bateau à moteur Cobalt 233 »). Known boats keep their French title and excerpt (the German text is appended for spec extraction). `classify_text()` gained German accessory rules (`ACC_DE`: Anhänger / Trailer / Slipwagen unless « inkl. / mit / + Trailer », Ersatz…, Sitz, Plane, Schraube, Pumpe, Bootslagerung, Miete, « für …boot », « Boots-/Schiffsmotor »…), and the spec parser reads « Länge 475, Breite 200 » (cm without unit), skips « Gewicht (ohne Motor) » as « sans moteur », and « Jahrgang irgendwann 1978 ».
* **Enrichment.** `filtre.enrich_records()` never fetches tutti / anibis pages for `via_scanmarket` records (Turnstile); it still uses cached pages from before 21 Nov.
* **Adding a source without re-scraping the others.** Reset `data/listings.json` from git if a test build already merged rows, patch `report/data/raw_today.json` with the new rows, then `python3 build.py --no-collect --no-mark --no-shots`, and restore the already-sent `digest/<today>.html` / `latest.html` from git (a rebuild rewrites them).

## Lessons (2026-11-25)

* **Pages deploy can upload an artifact and still fail to see it.** On 2026-11-25 both attempts of run 45556911169 (commit `5da51cc`) failed at "Deploy to GitHub Pages". `actions/upload-pages-artifact@v3` had just uploaded `github-pages` (776 858 bytes, artifact id 14996615049), but `actions/deploy-pages@v4` immediately listed 0 artifacts: "No artifacts named \"github-pages\" were found… Ensure artifacts are uploaded with actions/upload-artifact@v4 or later" and "Fetching artifact metadata failed. Is githubstatus.com reporting issues…". GitHub Status showed Actions and Pages operational (the only incident that morning was Copilot, resolved at 01:15 UTC, hours before the 05:55 UTC deploy). The `github-pages` environment already allowed `main`; the artifact was well under size limits; the site kept serving 2026-11-24. The job log also warned that Node.js 20 is deprecated and that `checkout@v4`, `configure-pages@v5`, `deploy-pages@v4` and `upload-artifact@v4` were being forced onto Node 24. Fix: bump to `actions/checkout@v5`, `configure-pages@v6`, `upload-pages-artifact@v5`, `deploy-pages@v5` (the official starter already uses deploy-pages v5), add `permissions.actions: read` so the deploy step can list the artifact, and set `concurrency.cancel-in-progress: false` so a production deploy is not cancelled mid-flight. After changing `.github/workflows/pages.yml`, a push (or `workflow_dispatch`) redeploys; do not rerun the old job, it still pins the old actions. Never dispatch `send-digest` just to refresh the site.
* **Confirm the live table, not only a green run.** After a successful deploy, `https://gael7777.github.io/nico-boats/data/listings.json` must have `"updated": "<today>"` (allow a few minutes for the CDN). A green workflow with yesterday's `updated` field means the previous site is still being served.

## Sending
This folder only produces HTML; the email itself is sent by `../publish_and_send.sh` and the GitHub Actions workflow in the repo. Recipient addresses
are NOT stored in this repo; keep them in the `MAIL_RECIPIENTS` secret.

Gmail clips HTML above about 102 KB, so the digest stays under ~95 KB. Days with many new boats (the first run listed every active boat) show a summary, the best 8 matches per category (price and road distance from Geneva), and a prominent button to the live table at https://gael7777.github.io/nico-boats/. Quiet days list every new boat.

## Record schema (data/listings.json → `records[<id>]`)
Top level: `{schema_version, updated, sources{<source>: {ok, error, raw, kept}}, records{<id>: record}}`. Every record has all keys below; unknown = `"N/A"`.

| field | meaning |
|---|---|
| id | `<source>:<listing id>` (e.g. `tutti:84171824` — also for ads read through ScanMarket, `bateau24:755798`, `lakeboat:<slug>`, `petitesannonces:8250977`, `aquaboat:<slug>`), stable across runs |
| source, source_listing_id, url | site key, the site's own id, **link to the advert** |
| title, category, category_label | ad title; `sail` / `open` / `motor` / `inflatable` / `small` / `other` |
| brand, model, year | maker, model, build year |
| price_chf, price_label | asking price (0 = free), price text as shown |
| length_m, width_m | length and beam in metres |
| engine_type, engine_brand, engine_model, hp, kw | outboard / inboard / electric / none; CV and kW (one derived from the other) |
| fuel, hours, sail_area_m2, berths, material | as stated |
| trailer, mooring_included | yes / no |
| condition, licence_leman | seller's condition; licence hint on the Léman (>10 CV or >15 m² sail) |
| town, canton, postcode, region, lat, lon, geo_precision | location; precision = listing coordinates / town / lake-region |
| distance_km_from_geneva, distance_method | road km from Geneva centre; `osrm` or `haversine x1.25` |
| seller_type | private / dealer (tutti/anibis: site's advertiser flag; boat24: dealer page link) |
| posted_date | date on the ad (tutti/anibis only) |
| photo_url, thumb_url | first photo (large / small) |
| description_excerpt | first 500 chars, e-mails and phone numbers hidden |
| first_seen, last_seen, status, removed_on | tracking (`active` / `removed`) |
| sent_in_digest | date of the digest that included the boat, or N/A |
| price_changed_on, previous_price_chf, price_history | price tracking (`[{date, price_chf}]`) |
| also_listed | same boat on other sites: `[{source, url}]`, or N/A |
| via_scanmarket, collecte | tutti / anibis only: `true` if read through scanmarket.ch, `false` if read directly; how and when the ad was read |

## Web table (../site)
Static, no build step: `index.html` + `assets/app.js` + `assets/style.css`, Leaflet and fonts from CDNs. It fetches `data/listings.json`
(copied there by `build.py`) and falls back to `data/listings.js` when opened from disk. Views: Table (sortable, column toggles, CSV export),
Cards, By category, Map; search, category chips, source/canton/status/new filters, dual sliders for price, distance, length, CV and year.
Deep links: `#v=table`, `#v=cards`, `#v=cats`, `#v=map`. Serve it with GitHub Pages from the `site/` folder. Set `SITE_URL` in `digest.py`
to the deployed address (default `https://gael7777.github.io/nico-boats/`).

## Public repo hygiene
No recipient addresses anywhere in these files. `.gitignore` keeps `report/cache/` (raw ad pages) and `report/data/raw_today.json` out of git.
