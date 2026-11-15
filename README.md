# Nico Boats

Pipeline that emails a daily HTML digest of cheap boat listings near Geneva.

The box that builds the digest **cannot** reach outbound SMTP. GitHub Actions runners can, so the digest is committed here and a workflow sends it through Infomaniak. A public site can later be published from this repository with GitHub Pages (built separately; no placeholder site is required in the repo).

## How a morning run works

1. The routine writes an HTML digest locally.
2. [`publish_and_send.sh`](publish_and_send.sh) commits it as `digest/latest.html` and an archive copy `digest/YYYY-MM-DD.html`, pushes to `main`, then dispatches the workflow.
3. [`.github/workflows/send-digest.yml`](.github/workflows/send-digest.yml) checks out the repo and runs [`scripts/send_email.py`](scripts/send_email.py) over SMTP STARTTLS.

There is **no cron** in the workflow. Nothing is sent unless something (the routine, or a manual dispatch) triggers it.

## Recipients and secrets

Because this repository may be public, recipient addresses are **not** stored in files.

| Item | Value |
| --- | --- |
| Recipients | repo Actions secret **`MAIL_RECIPIENTS`** (comma-separated) |
| From / SMTP user | `info@gmc-works.com` |
| Host | `mail.infomaniak.com:587` (STARTTLS, EHLO `gmc-works.com`) |
| Password | repo Actions secret **`SMTP_PASSWORD`** (do not put it in a file) |

Optionally override recipients for a single run with the `recipients` workflow input. Leave that input empty to use the secret.

## Dispatch the workflow

From the Actions tab: **Send digest** → **Run workflow**. Set `subject`, optionally `recipients` and `body_path` (defaults to `digest/latest.html`).

From this machine, once `GITHUB_NICO_BOATS_TOKEN` is in the environment:

```bash
./publish_and_send.sh --html /path/to/digest.html --subject "Nico Boats – 15 Nov 2026"
```

Preview without pushing or sending:

```bash
./publish_and_send.sh --dry-run --html /path/to/digest.html --subject "Nico Boats – 15 Nov 2026"
```

The token needs **Contents**, **Actions**, and **Workflows** read/write on this repository. Never commit it, and never print it.

Manual dispatch only (after the HTML is already on `main`):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $GITHUB_NICO_BOATS_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Gael7777/nico-boats/actions/workflows/send-digest.yml/dispatches \
  -d '{"ref":"main","inputs":{"subject":"Nico Boats – 15 Nov 2026"}}'
```

A `204` response means GitHub accepted the dispatch. The run then appears under [Actions](https://github.com/Gael7777/nico-boats/actions).

## Layout

```
.github/workflows/send-digest.yml   # workflow_dispatch only
scripts/send_email.py               # stdlib smtplib + multipart HTML/text
digest/latest.html                  # current body
digest/YYYY-MM-DD.html              # dated archive copies
publish_and_send.sh                 # commit + dispatch helper
```
