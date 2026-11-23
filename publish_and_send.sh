#!/usr/bin/env bash
# Commit the digest + data + site data, push main, and dispatch the Send digest workflow.
# Usage:
#   ./publish_and_send.sh [--html PATH] [--subject "..."] [--recipients "a,b"] [--date YYYY-MM-DD] [--no-send] [--dry-run]
# Defaults: --html report/digest/latest.html, --subject "Nico Boats – <date en français>" (report/frdate.py).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

html_path="report/digest/latest.html"
subject=""
recipients=""
digest_date=""
dry_run=0
no_send=0

usage() {
  cat <<'USAGE'
Usage: ./publish_and_send.sh [options]

  --html PATH          Local HTML file to publish as the digest body
                       (default: report/digest/latest.html)
  --subject TEXT       Email subject (default: "Nico Boats – 24 novembre 2026",
                       French date of --date). English month/day names in a
                       given subject are translated to French.
  --recipients LIST    Optional comma-separated override; omit to use the
                       MAIL_RECIPIENTS repository secret
  --date YYYY-MM-DD    Digest date (default: today in Europe/Zurich)
  --no-send            Commit and push (data, site, digest) but do NOT dispatch the email
  --dry-run            Print the plan; do not commit, push, or dispatch
  -h, --help           Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --html) html_path="${2:-}"; shift 2 ;;
    --subject) subject="${2:-}"; shift 2 ;;
    --recipients) recipients="${2:-}"; shift 2 ;;
    --date) digest_date="${2:-}"; shift 2 ;;
    --no-send) no_send=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -f "$html_path" ]]; then
  echo "HTML file not found: $html_path" >&2
  exit 2
fi

if [[ -z "$digest_date" ]]; then
  digest_date="$(TZ=Europe/Zurich date +%F)"
fi
if [[ ! "$digest_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "Invalid --date (expected YYYY-MM-DD): $digest_date" >&2
  exit 2
fi
if [[ -z "$subject" ]]; then
  subject="$(python3 report/frdate.py subject "$digest_date")"
else
  subject="$(python3 report/frdate.py fix "$subject")"
fi

archive_path="digest/${digest_date}.html"
abs_html="$(cd "$(dirname "$html_path")" && pwd)/$(basename "$html_path")"

echo "Would publish:"
echo "  source:     $abs_html"
echo "  latest:     $ROOT/digest/latest.html"
echo "  archive:    $ROOT/$archive_path"
echo "  also:       data/ site/data/ config/ report/digest/ (if changed)"
echo "  subject:    $subject"
if [[ "$no_send" -eq 1 ]]; then
  echo "  send:       NO (--no-send)"
elif [[ -n "$recipients" ]]; then
  echo "  recipients: $recipients"
else
  echo "  recipients: (MAIL_RECIPIENTS secret)"
fi
echo "  branch:     main"

if [[ "$dry_run" -eq 1 ]]; then
  echo "Dry run: no commit, no push, no dispatch."
  exit 0
fi

if [[ -z "${GITHUB_NICO_BOATS_TOKEN:-}" ]]; then
  echo "GITHUB_NICO_BOATS_TOKEN is not set." >&2
  exit 2
fi

mkdir -p digest
cp "$abs_html" digest/latest.html
cp "$abs_html" "$archive_path"

if [[ ! -d .git ]]; then
  echo "Not a git repository: $ROOT" >&2
  exit 2
fi

git add digest/latest.html "$archive_path"
for p in data site/data config report/digest; do
  if [[ -e "$p" ]]; then git add -A -- "$p"; fi
done
if git diff --cached --quiet; then
  echo "Nothing new to commit."
else
  git commit -q -m "Digest, data and site ${digest_date}"
  echo "Committed $(git rev-parse --short HEAD)."
fi
# Push whatever is ahead of origin (also earlier commits that failed to push)
git fetch -q origin main
if [[ -n "$(git rev-list origin/main..HEAD)" ]]; then
  "$ROOT/scripts/git_push.sh"
else
  echo "main already up to date on GitHub."
fi

if [[ "$no_send" -eq 1 ]]; then
  echo "--no-send: email workflow NOT dispatched."
  exit 0
fi

payload="$(python3 - "$subject" "$recipients" <<'PY'
import json, sys
subject = sys.argv[1]
recipients = sys.argv[2] if len(sys.argv) > 2 else ""
inputs = {"subject": subject}
if recipients:
    inputs["recipients"] = recipients
print(json.dumps({"ref": "main", "inputs": inputs}))
PY
)"

tmp_hdr="$(mktemp)"
tmp_body="$(mktemp)"
set +e
status="$(curl -sS -o "$tmp_body" -D "$tmp_hdr" -w "%{http_code}" -X POST \
  -H "Authorization: Bearer ${GITHUB_NICO_BOATS_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/Gael7777/nico-boats/actions/workflows/send-digest.yml/dispatches" \
  -d "$payload")"
curl_rc=$?
set -e
# Print only the HTTP status line, never request headers (they contain the token)
if [[ -f "$tmp_hdr" ]]; then
  head -n 1 "$tmp_hdr"
fi
rm -f "$tmp_hdr"
if [[ "$curl_rc" -ne 0 ]]; then
  rm -f "$tmp_body"
  echo "curl failed while dispatching the workflow." >&2
  exit 1
fi
if [[ "$status" != "204" ]]; then
  echo "Dispatch failed (HTTP $status):" >&2
  cat "$tmp_body" >&2
  rm -f "$tmp_body"
  exit 1
fi
rm -f "$tmp_body"
echo "Dispatched Send digest on main (HTTP 204)."
echo "Runs: https://github.com/Gael7777/nico-boats/actions"
