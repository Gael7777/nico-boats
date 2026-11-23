# Research: sites that republish Tutti.ch / Anibis.ch ads

**Question:** Is there a site that re-uses or republishes Tutti or Anibis classifieds (especially boats), that we can fetch from the box without bypassing Cloudflare?

**Short answer:** Yes. **ScanMarket.ch** currently republishes a large, fresh Tutti + Anibis inventory and is scriptable from the box via a JSON API. **Fundorama.ch** also republishes both sources and is scriptable, but its whole index has been frozen since 17 November 2026, 11:46 Europe/Paris. There is no official public SMG read API. Tutti and Anibis themselves still return HTTP 403 `cf-mitigated: challenge` from the box (including `robots.txt`).

**Update 23 Nov 2026, 12:40 Europe/Paris:** Gael approved ScanMarket with one polite read per day. It is now the automatic fallback in `report/collect.py` when the direct tutti / anibis scrape is blocked (see `report/README.md`, « Lessons (2026-11-23, ScanMarket) »). First live pass: 544 ads (330 Tutti, 214 Anibis), 140 boats kept after the accessory and price rules. ScanMarket turned out to be a partial mirror (157 of our 272 active Tutti/Anibis boats were absent), so absence only removes ads that an earlier ScanMarket pass had seen.

**Original recommendation:** Do not wire anything into the daily routine yet. ScanMarket is the only live republisher that clearly works today; treat it as an unofficial third-party scrape (its `robots.txt` disallows `/api/`). Ask Gael before using it in production. Keep official Tutti/Anibis email alerts as the first-party fallback. Watch Fundorama — if their crawler comes back, its category HTML pages are a cleaner fit.

Date accessed: Monday 23 November 2026, around 10:25–10:33 Europe/Paris. All live checks were done with `curl` from the box. No captcha was bypassed. The pipeline was not changed; a standalone parser lives in `report/sources_candidates/scanmarket.py` and is not imported by `build.py` / `collect.py`.

## 1. ScanMarket.ch — best live candidate

- **URL:** https://scanmarket.ch/ (how it works: https://scanmarket.ch/how-it-works)
- **What it is:** Independent Swiss meta-search. It says it aggregates Tutti, Anibis, Ricardo, Shpock and eBay, deduplicates, normalises prices to CHF, and always links back to the original ad. It is not an SMG product.
- **Coverage (live, 23 Nov 2026 ~10:30 Europe/Paris):**
  - `/api/stats`: 879,464 listings in total, of which **509,547 Tutti** and **255,380 Anibis**, plus 107,523 Ricardo; **4,498 new in the last hour**.
  - Boats category, Tutti+Anibis only: **`total` 548–552** (`category=boats&sources=tutti,anibis`). Split: **329 Tutti**, **219 Anibis**. This is “Boote & Zubehör” style (boats, engines, trailers, accessories), not hulls only.
- **Freshness:** Live. Ads posted this morning are already in the index, for example:
  - Anibis `1073971067` “Pontonboot/Katamaran”, Grand-Lancy, posted `2026-11-23T08:42:26` (no timezone on the field; either 08:42 or 09:42 Europe/Paris).
  - Tutti `81086805` NELO Surfski, Biberist, posted `2026-11-23T06:41:35`.
  - Tutti `80508987` “Fischerboot (Howa Fario)”, Uzwil, posted `2026-11-22T12:34:40`, scraped `2026-11-23T09:29:36`.
  - Across a union of 255 Tutti/Anibis boat ads pulled from several queries: 44 posted since 17 Nov, 14 since 21 Nov, 8 since 22 Nov, 3 since 23 Nov; 146/255 had `scraped_at` dated today. Many `scraped_at` values were 10:29–10:30 Europe/Paris this morning.
- **Does it really contain Tutti/Anibis ads?** Yes. Each item has `source` (`tutti` / `anibis`), `source_listing_id` (the original ID), and `listing_url` back to the official ad, e.g. `https://www.anibis.ch/de/vi/1074137008` (Guy Marine 560, Yvonand, CHF 4,800 — same ID Fundorama also has from an earlier crawl) and `https://www.tutti.ch/de/vi/.../80508987`. Thumbnails come from `c.tutti.ch` / `c.anibis.ch`. Descriptions look complete, not truncated.
- **Scriptability from the box:** Yes, no captcha.
  - `GET https://scanmarket.ch/api/search?q=&category=boats&sources=tutti,anibis&page=1&page_size=50` → HTTP 200, JSON.
  - Pagination: `page`, `page_size` (max useful value seen: 50; `limit` is ignored). About 12 pages for the full boats set.
  - Useful fields: `source`, `source_listing_id`, `listing_url`, `title`, `description`, `price_chf`, `city`, `canton`, `postal_code`, `posted_at`, `scraped_at`, `first_scraped_at`, `image_url`, `category`, `condition`.
  - HTML listing pages (`/l/tutti/{id}`) are a JavaScript shell (~4.7 KB) and are not usable without the API.
  - `/api/health` returned `{"status":"ok", ... "scraper_api":"configured"}`.
- **Caveats (why this should not be silently wired in):**
  1. `robots.txt` **Disallow: /api/** (also `/auth/`, `/admin`). Category HTML is allowed but empty without JS.
  2. Undocumented API; no public OpenAPI. Parameters and availability can change. `sort=` / `/api/newest` did not reliably return newest-posted-first, so a daily job must paginate the whole boats category (or several keywords).
  3. It is itself a scraper of Tutti/Anibis (they mention a scraper API and credits). Anibis terms prohibit automated collection. Using ScanMarket avoids hitting Cloudflare, but it is not an official SMG feed.
  4. Query `boot` also matches shoes (“Boots”). Always pass `category=boats` and `sources=tutti,anibis`.
  5. They say they “trigger a live search if needed” (`scraping: true` appeared on one query). Do not hammer the API.

## 2. Fundorama.ch — honest republisher, currently stale

- **URL:** https://fundorama.ch/ — sources page: https://fundorama.ch/quellen — boats: https://fundorama.ch/kategorie/boote
- **What it is:** A Swiss meta-search that explicitly says it does not host the ads. It reads public overview pages only, shows title, price, place, category, timestamp and thumbnail, and sends the buyer to the original site. Operators can opt out by writing to hallo@fundorama.ch.
- **Coverage (23 Nov 2026):** Their sources page reported **142,211 Tutti** and **82,946 Anibis** ads in the index, plus 304 boot24 and 60,472 petitesannonces. Boats category: **705 ads = 304 boot24 + 285 Tutti + 116 Anibis**. Detail pages use slugs like `/inserat/anibis-1074137008` and `/inserat/tutti-83022824`, and link to `https://www.anibis.ch/de/vi/{id}` / `https://www.tutti.ch/de/vi/{id}`.
- **Freshness:** **Stale since Tuesday 17 November 2026, 11:46 Europe/Paris.** Public `GET https://fundorama.ch/api/health` (HTTP 200) returned:

```json
{
  "status": "veraltet",
  "newest": "2026-11-17T10:46:31+00:00",
  "crawler": {
    "letzter_lauf": "2026-11-17T10:46:31+00:00",
    "egress": "handy",
    "hinweis": "Der Crawler holt gerade nichts Neues (Handy offline oder ohne Exit-Freigabe). Die Suche zeigt den Stand von 2026-11-17T10:46:31+00:00."
  }
}
```

  They crawl via a phone uplink that has been offline or without exit permission since that moment (~5 days 22 hours at the time of the check; `egress_geprueft` was 23 Nov 2026, 10:25 Europe/Paris). Category pages all say “0 from the last 24 hours” and “last seen 6 days ago”. `/suche?tage=1` returned 0 hits. Ads posted after the freeze (Howa Fario 22 Nov, today’s Pontonboot, Mändli K520, etc.) **404 on Fundorama**. An older ID such as Tutti `80964700` is still there, but last checked 11 days ago, with a stale title/price compared with ScanMarket.
- **Scriptability:** Yes, no captcha, nginx, HTTP 200. `/kategorie/boote` is a real HTML page (~419 KB) and is **not** disallowed by robots (robots disallows `/api/`, `/suche?`, `/weiter/`, `/merkliste`, `/agenten`, `/vergleich`). Listing HTML includes a truncated description, price, postcode, town and the original URL. Search query URLs and the API are robots-disallowed. There is no useful public listings API (`/api/listings?q=boot` returned `[]`).
- **Use today:** Historical snapshot only. Worth checking `/api/health` occasionally; if `frisch` becomes true, Fundorama becomes the politer HTML source.

## 3. Official SMG API / partner feed — none found

- No public read API for Tutti or Anibis turned up (SMG company profiles also record “no API”).
- Freshpage and similar tools offer a **seller-side push** into Tutti/Anibis, not a public listing feed we can pull.
- AutoScout24 can cross-list cars onto Tutti/Anibis; that is outbound from AutoScout, not a Tutti dump.
- SMG announced on 20 October 2026 that Tutti and Anibis will gradually **mirror selected categories on each other**. That does not help while both sites are behind the same Cloudflare challenge.
- Unofficial PyPI clients (`tutti-sdk`, `anibis-sdk`) talk to the official GraphQL endpoints and would hit the same 403. Not recommended (ToS + captcha).

Tutti and Anibis `robots.txt` still return **HTTP 403, `cf-mitigated: challenge`** from the box as of 23 Nov 2026, 10:33 Europe/Paris.

## 4. Other candidates, ranked lower

| Candidate | Result |
| --- | --- |
| **Official Tutti / Anibis email alerts** | Not a republisher, but the clean first-party path. Gael has to create them (captcha + account). We can parse inbound mail into the digest. |
| **FlowMarket** (https://flow-market.org/) | Marketing pages mention Tutti/Anibis alerts. The site and `/api/search?q=…&country=CH` are scriptable (HTTP 200 JSON), but every CH search I ran returned only **Ricardo, eBay and Vinted** — zero Tutti/Anibis items. `marketplace=tutti` / `source=tutti` did not change that. Not usable for this gap today. `robots.txt` also disallows `/api/`. |
| **Findolino** (https://findolino.ch/) | HTTP 200, no captcha. The homepage claims Tutti/Anibis, but `/top/boote`, `/finde/motorboot` and `/suche/boot` linked to **trovas.ch, topinserate.ch, markt.ch, flohmarkt.ch, pinwand.ch** — not Tutti or Anibis. |
| **Trovas.ch** | HTTP 403 Cloudflare challenge from the box, same class of block as Tutti/Anibis. A 2024 Reddit comment claimed Trovas scraped Tutti/Anibis; 2026 articles treat it as its own marketplace. Fundorama lists Trovas among sources it will not crawl because of that challenge. Not verified, not fetchable. |
| **allekleinanzeigen.ch** | TLS error (`unexpected eof`) from the box. Looks dead. |
| **blitzfa.st Suchagent** | Paid watcher that scrapes Tutti/Anibis itself. Not a republisher we can fetch; would face the same captcha unless they use a paid residential scraper. |
| **Google / Bing cache or site search** | Not tested as a structured daily feed. Even `robots.txt` on Tutti/Anibis is challenged, so relying on a search-engine cache would be delayed, incomplete and brittle. No substitute for a listing API. |
| **Boat portals already in the pipeline** (Boat24 / bateau24.ch, lakeboat.ch, aquaboat.ch, petitesannonces.ch) | First-party sources, not Tutti/Anibis republishers. Petitesannonces still offers official RSS for non-commercial reuse. Leave as they are. |
| **Swissnaut** (swissyacht.vercel.app) | Demo/placeholder marketplace, not an aggregator. |
| **Joomil, markt.ch, quickad, usato, toutypasse** | Own inventories (Fundorama also indexes some). They do not republish Tutti/Anibis. |

## 5. Prototype

`report/sources_candidates/scanmarket.py` parses ScanMarket boat JSON (Tutti/Anibis only) into a simple record list. It is **not** imported by the routine. Default mode reads `scanmarket_fixture.json`. `--fetch` would call the live API and is off by default; the file comments the robots.txt restriction.

## Open questions

- Will ScanMarket grant a legitimate feed or tolerate a polite daily boats pull? Unknown; no usable terms page was returned (legal URLs are JS shells).
- Will Fundorama’s phone egress come back, and will their Tutti/Anibis crawl still work if it does?
- Are official Tutti/Anibis email alerts acceptable to Gael as the long-term first-party path?

## Recommendation

1. Tell Gael that a live republisher exists: ScanMarket has today’s Tutti/Anibis boat ads, with original IDs and links, and is fetchable from the box — but it is unofficial and its robots file disallows the API. Do not start daily pulls until he agrees.
2. Offer the official email-alert path again (he creates two saved searches; we read the mailbox).
3. Optionally ping Fundorama later; if `GET /api/health` shows `"frisch": true`, prefer their category HTML over ScanMarket’s API.
4. Do not bypass Cloudflare on Tutti, Anibis, Trovas or Ricardo.

## Sources consulted

Checked live from the box on 23 November 2026 (Europe/Paris), unless noted.

- https://fundorama.ch/quellen — 142,211 Tutti and 82,946 Anibis in index; method: overview pages only.
- https://fundorama.ch/kategorie/boote — 705 boats; 0 in last 24 hours; 285 Tutti / 116 Anibis / 304 boot24.
- https://fundorama.ch/api/health — `"status":"veraltet"`, last crawl 17 Nov 2026, 10:46 UTC (11:46 Europe/Paris), phone egress offline.
- https://fundorama.ch/inserat/anibis-1074137008 and `/inserat/tutti-83022824` — original URLs confirmed; fields thinner than first-party pages.
- https://fundorama.ch/inserat/tutti-80508987 and several post-17-Nov IDs — 404 (not in the frozen index).
- https://fundorama.ch/robots.txt, sitemap.xml — `/kategorie/*` allowed; `/api/` and `/suche?` disallowed.
- https://scanmarket.ch/api/stats, `/api/search`, `/api/health`, `/api/sitemap-listings.xml` — live Tutti/Anibis JSON; boats totals above.
- https://scanmarket.ch/how-it-works — “trigger a live search if needed”; “new listings appear within minutes”.
- https://scanmarket.ch/robots.txt — `Disallow: /api/`.
- https://scanmarket.ch/l/anibis/1074137008 — JS shell only.
- https://findolino.ch/, `/top/boote`, `/finde/motorboot`, `/suche/boot`.
- https://flow-market.org/de-CH/, `/de/suche/?q=boot`, `/api/search?q=boot&country=CH`.
- https://trovas.ch/ — 403 cf-mitigated: challenge.
- https://allekleinanzeigen.ch/ — TLS failure.
- https://www.tutti.ch/robots.txt, https://www.anibis.ch/robots.txt — 403 cf-mitigated: challenge.
- https://www.persoenlich.com/prcorporate-communication/tutti-und-anibis-rucken-enger-zusammen (20 Oct 2026) — SMG cross-listing announcement.
- https://www.freshpage.ch/funktionen/marktplaetze — seller-side Tutti/Anibis export, not a public feed.
- https://pypi.org/project/anibis-sdk/ — unofficial GraphQL client, same origin as the blocked sites.
- https://www.petitesannonces.ch/outils/rss/ — official RSS, already in the pipeline.
- Reddit r/askswitzerland “Aggregator of ricardo, TUTTI, anibis, etc” (2022, comment 2024) — allekleinanzeigen / Trovas mentions, treated as outdated and then verified live.

### Verification notes

- HTTP statuses, counts, timestamps and example IDs above were read from responses saved under `/tmp/agg-research/` during this session, not from memory.
- `posted_at` on ScanMarket has no timezone; freshness conclusions do not depend on the one-hour UTC vs Europe/Paris ambiguity.
- I did not log into any site, did not solve any captcha, and did not modify `collect.py` or send mail.
