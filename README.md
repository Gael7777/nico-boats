# Nico Boats

Daily digest of used boats for sale across Switzerland (asking up to CHF 30'000, or free), aimed at a Léman mooring in Geneva.

The box that builds the digest **cannot** reach outbound SMTP. GitHub Actions runners can: the HTML is committed here and a workflow sends it through Infomaniak. The same data is published as a live table and map on GitHub Pages: **https://gael7777.github.io/nico-boats/**

## How a morning run works

1. `python3 report/build.py` scrapes the marketplaces, merges into the master store, writes today's HTML digest, refreshes the site data, and (optionally) takes PNG previews.
2. [`publish_and_send.sh`](publish_and_send.sh) copies the HTML to `digest/latest.html` and `digest/YYYY-MM-DD.html`, pushes to `main`, then dispatches the send workflow.
3. [`.github/workflows/send-digest.yml`](.github/workflows/send-digest.yml) checks out the repo and runs [`scripts/send_email.py`](scripts/send_email.py) over SMTP STARTTLS.

There is **no cron** in the send workflow. Nothing is emailed unless the routine (or a manual dispatch) triggers it. Pushing changes under `site/` or `data/` deploys the Pages site.

## Daily command sequence

From `/workspace/projects/nico-boats`, with `GITHUB_NICO_BOATS_TOKEN` in the environment:

```bash
# 1. Scrape, merge, write digest + site data + previews (~10 min the first time; later runs reuse cached ad pages)
python3 report/build.py

# Rebuild from the last scrape without hitting the network:
# python3 report/build.py --no-collect

# 2. Commit the digest, push, and dispatch the email (default recipients come from the MAIL_RECIPIENTS secret)
./publish_and_send.sh --html report/digest/latest.html --subject "Nico Boats – $(TZ=Europe/Zurich date +'%d %b %Y')"
```

Preview the publish step without pushing or sending:

```bash
./publish_and_send.sh --dry-run --html report/digest/latest.html --subject "Nico Boats – $(TZ=Europe/Zurich date +'%d %b %Y')"
```

Other useful flags: `--no-mark` (do not mark boats as sent), `--no-shots` (skip PNG previews).

### Dedup / sent tracking

The digest contains only **active** boats whose `sent_in_digest` is `N/A` (never mailed) or **today** (so a same-day rerun produces the same email). After the digest is written, each of those boats is marked `sent_in_digest = <date>` in `data/listings.json`. The first run is a baseline of every active listing. Later mornings only include boats that appeared since the last marked digest. Price changes on already-sent boats still show in a "Price changes" box.

## Recipients and SMTP

Because this repository is public, recipient addresses are **not** stored in files.

| Item | Value |
| --- | --- |
| Recipients | repo Actions secret **`MAIL_RECIPIENTS`** (comma-separated) |
| From / SMTP user | `info@gmc-works.com` |
| Host | `mail.infomaniak.com:587` (STARTTLS, EHLO `gmc-works.com`) |
| Password | repo Actions secret **`SMTP_PASSWORD`** |

Optionally override recipients for a single run with the `recipients` workflow input. Leave that input empty to use the secret. The token used by `publish_and_send.sh` (`GITHUB_NICO_BOATS_TOKEN`) needs **Contents**, **Actions**, and **Workflows** read/write; never commit it or print it.

Gmail clips HTML above about 102 KB. Large days therefore show a summary, the best eight matches per category, and a button to the live table; quiet days list every new boat. The file stays under ~95 KB.

## Master store and site

| Path | Role |
| --- | --- |
| `data/listings.json` | **Source of truth** — one record per boat |
| `data/listings.csv` | Flat export, rewritten every build |
| `site/` | Static GitHub Pages app (table, cards, map) |
| `site/data/listings.json` / `listings.js` | Copy of the master store (`listings.js` is the `file://` fallback) |
| `report/digest/latest.html` | Today's email body (also dated `YYYY-MM-DD.html`) |

The Pages workflow copies `data/listings.json` into `site/data/` on each deploy, then publishes `./site`. The app loads `data/listings.json` with a path that works under `/nico-boats/`.

Details of sources, classification, merge rules and the record schema are in [`report/README.md`](report/README.md).

## Layout

```
.github/workflows/send-digest.yml   # email, workflow_dispatch only
.github/workflows/pages.yml         # GitHub Pages from ./site
data/listings.json                  # master store
data/listings.csv
report/build.py                     # scrape → merge → digest → site data
report/digest/YYYY-MM-DD.html
site/                               # live table
publish_and_send.sh                 # commit digest + dispatch email
scripts/send_email.py
```
