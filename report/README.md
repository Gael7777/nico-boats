# Nico Boats: daily digest + master store

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

## Sources (status 2026-11-15)
| Source | Method | Status |
|---|---|---|
| tutti.ch | category "Bateaux & accessoires" search pages (`__NEXT_DATA__` JSON), ad pages for coordinates and full text | works |
| anibis.ch | same platform as tutti, same method | works |
| boat24 Swiss site (bateau24.ch) | server-rendered list `bateauxdoccasion/?whr=CHF&prs_max=30000&page=<offset>`, ad pages for specs and town | works (boat24.com itself sits behind a Cloudflare challenge) |
| ricardo.ch | search page | blocked: captcha page / Cloudflare error 1015 from the box |
| Facebook Marketplace | n/a | needs a logged-in session, not scraped |

Accessories, engines, trailers, moorings, kayaks and SUPs are filtered by keyword rules in `collect.py` (`ACC_START`, `ACC_ANY`, `BOAT`). Fix a rule there and run
`python3 build.py --no-collect` to re-apply it.

## Sending
This folder only produces HTML; the email itself is sent by `../publish_and_send.sh` and the GitHub Actions workflow in the repo. Recipient addresses
are NOT stored in this repo; keep them in the `MAIL_RECIPIENTS` secret.

Gmail clips HTML above about 102 KB, so the digest stays under ~95 KB. Days with many new boats (the first run listed every active boat) show a summary, the best 8 matches per category (price and road distance from Geneva), and a prominent button to the live table at https://gael7777.github.io/nico-boats/. Quiet days list every new boat.

## Record schema (data/listings.json → `records[<id>]`)
Top level: `{schema_version, updated, sources{<source>: {ok, error, raw, kept}}, records{<id>: record}}`. Every record has all keys below; unknown = `"N/A"`.

| field | meaning |
|---|---|
| id | `<source>:<listing id>` (e.g. `tutti:84171824`, `bateau24:755798`), stable across runs |
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

## Web table (../site)
Static, no build step: `index.html` + `assets/app.js` + `assets/style.css`, Leaflet and fonts from CDNs. It fetches `data/listings.json`
(copied there by `build.py`) and falls back to `data/listings.js` when opened from disk. Views: Table (sortable, column toggles, CSV export),
Cards, By category, Map; search, category chips, source/canton/status/new filters, dual sliders for price, distance, length, CV and year.
Deep links: `#v=table`, `#v=cards`, `#v=cats`, `#v=map`. Serve it with GitHub Pages from the `site/` folder. Set `SITE_URL` in `digest.py`
to the deployed address (default `https://gael7777.github.io/nico-boats/`).

## Public repo hygiene
No recipient addresses anywhere in these files. `.gitignore` keeps `report/cache/` (raw ad pages) and `report/data/raw_today.json` out of git.
