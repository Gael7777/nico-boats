# -*- coding: utf-8 -*-
"""Run the tutti.ch / anibis.ch collector on a GitHub Actions runner.

Since ~21 Nov 2026 both sites answer the box's network with an interactive Cloudflare
Turnstile page (HTTP 403, cf-mitigated: challenge). The same public pages load normally
from other networks, so the scrape (same polite code as report/collect.py) runs here and
the box downloads the result as an artifact. No cookies, no login, no captcha solving.
Output: smg_rows.json = {"rows": [...], "status": {...}}"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "report"))
import collect

rows = []
for src in ("tutti", "anibis"):
    try:
        rows += collect.collect_smg(src)
    except Exception as e:
        collect.STATUS[src] = {"ok": False, "error": str(e)[:200]}
        collect.log("SOURCE FAILED", src, e)
Path("smg_rows.json").write_text(json.dumps({"rows": rows, "status": {k: collect.STATUS.get(k) for k in ("tutti", "anibis")}},
                                            ensure_ascii=False))
print(json.dumps({k: collect.STATUS.get(k) for k in ("tutti", "anibis")}))
