#!/usr/bin/env python3
"""Standalone ScanMarket parser for Tutti.ch / Anibis.ch boat ads.

Research prototype, kept for offline tests. Since 2026-11-23 the production
reader is collect.fetch_scanmarket() / collect_smg_via_scanmarket() (Gael
approved one read per day); this file is not imported by the pipeline.

ScanMarket (https://scanmarket.ch/) republishes Tutti and Anibis listings and
exposes them as JSON from the box, without a Cloudflare challenge. It is an
independent third-party scraper, not an SMG feed.

robots.txt on scanmarket.ch disallows /api/. Default mode therefore reads the
offline fixture captured during research. Pass --fetch only if you have
explicitly decided to hit the live API.

Usage:
    python3 report/sources_candidates/scanmarket.py
    python3 report/sources_candidates/scanmarket.py --fixture PATH
    python3 report/sources_candidates/scanmarket.py --fetch   # live API, see robots.txt
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
DEFAULT_FIXTURE = HERE / "scanmarket_fixture.json"

API_SEARCH = "https://scanmarket.ch/api/search"
USER_AGENT = "nico-boats-research/0.1 (prototype; not wired into the daily digest)"
PAGE_SIZE = 50
# boats = Tutti/Anibis "Boote & Zubehör". "boat" (singular) is Ricardo's category.
CATEGORY = "boats"
SOURCES = "tutti,anibis"


def parse_listing(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Map one ScanMarket API item to a flat record. Skip non-Tutti/Anibis."""
    source = (raw.get("source") or "").strip().lower()
    if source not in {"tutti", "anibis"}:
        return None
    listing_id = str(raw.get("source_listing_id") or "").strip()
    if not listing_id:
        return None
    url = raw.get("listing_url") or (
        f"https://www.{source}.ch/de/vi/{listing_id}"
    )
    return {
        "source": source,
        "source_id": listing_id,
        "url": url,
        "title": raw.get("title") or "N/A",
        "description": raw.get("description") or "N/A",
        "price_chf": raw.get("price_chf") if raw.get("price_chf") is not None else "N/A",
        "city": raw.get("city") or "N/A",
        "canton": raw.get("canton") or "N/A",
        "postcode": raw.get("postal_code") or "N/A",
        "category": raw.get("category") or "N/A",
        "posted_at": raw.get("posted_at") or "N/A",
        "scraped_at": raw.get("scraped_at") or "N/A",
        "first_scraped_at": raw.get("first_scraped_at") or "N/A",
        "photo_url": raw.get("image_url") or "N/A",
        "condition": raw.get("condition") or "N/A",
    }


def parse_response(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    else:
        items = payload.get("listings") or payload.get("items") or []
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in items:
        rec = parse_listing(raw)
        if not rec:
            continue
        key = (rec["source"], rec["source_id"])
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def load_fixture(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    listings = data.get("listings", data)
    return parse_response({"listings": listings})


def _http_get_json(url: str, timeout: int = 25) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def fetch_boats(max_pages: int = 12) -> list[dict[str, Any]]:
    """Paginate the boats category for Tutti + Anibis. Honours page_size=50.

    This hits a robots.txt-disallowed path. Call only with --fetch.
    """
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    total = None
    for page in range(1, max_pages + 1):
        query = {
            "q": "",
            "category": CATEGORY,
            "sources": SOURCES,
            "page": str(page),
            "page_size": str(PAGE_SIZE),
        }
        url = API_SEARCH + "?" + urllib.parse.urlencode(query)
        payload = _http_get_json(url)
        total = payload.get("total", total)
        batch = parse_response(payload)
        new = 0
        for rec in batch:
            key = (rec["source"], rec["source_id"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(rec)
            new += 1
        if not payload.get("has_more") or new == 0:
            break
    if total is not None:
        print(f"# ScanMarket declared total={total}, parsed unique={len(merged)}", file=sys.stderr)
    return merged


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="Offline JSON fixture")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Call the live ScanMarket API (robots.txt disallows /api/). Off by default.",
    )
    parser.add_argument("--json", action="store_true", help="Print records as JSON instead of a table")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.fetch:
        records = fetch_boats()
    else:
        if not args.fixture.exists():
            print(f"Fixture not found: {args.fixture}", file=sys.stderr)
            return 2
        records = load_fixture(args.fixture)

    if args.json:
        json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"{len(records)} Tutti/Anibis boat records")
    for rec in records:
        price = rec["price_chf"]
        price_s = "N/A" if price == "N/A" else f"CHF {price}"
        title = rec["title"].replace("\n", " ")[:60]
        print(
            f"{rec['source']:7s} {rec['source_id']:12s} {price_s:>14s}  "
            f"{rec['city']}  posted={rec['posted_at']}  {title}"
        )
        print(f"         {rec['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
