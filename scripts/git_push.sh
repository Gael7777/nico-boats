#!/usr/bin/env bash
# Push the current branch to Gael7777/nico-boats with GITHUB_NICO_BOATS_TOKEN.
# The token is only put in the push URL for this one command: it is never
# saved in .git/config, never echoed, and redacted from git's output.
# Usage: scripts/git_push.sh            (pushes HEAD to main, rebasing on origin/main first)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPO="github.com/Gael7777/nico-boats.git"
if [[ -z "${GITHUB_NICO_BOATS_TOKEN:-}" ]]; then
  echo "GITHUB_NICO_BOATS_TOKEN is not set." >&2
  exit 2
fi
redact() { sed -e "s#${GITHUB_NICO_BOATS_TOKEN}#***#g" -e 's#x-access-token:[^@]*@#x-access-token:***@#g'; }
# Keep the saved remote clean (no credentials in .git/config)
git remote set-url origin "https://${REPO}"
# The repo is public: fetching needs no token. Rebase local commits on top of any remote ones.
git fetch -q origin main
if ! git merge-base --is-ancestor origin/main HEAD; then
  git rebase -q --autostash origin/main || { git rebase --abort || true; echo "Rebase on origin/main failed; resolve by hand." >&2; exit 1; }
fi
set +e
GIT_TERMINAL_PROMPT=0 git -c credential.helper= push "https://x-access-token:${GITHUB_NICO_BOATS_TOKEN}@${REPO}" HEAD:main 2>&1 | redact
rc=${PIPESTATUS[0]}
set -e
if [[ "$rc" -ne 0 ]]; then
  echo "git push failed (exit $rc)." >&2
  exit "$rc"
fi
git fetch -q origin main   # update origin/main tracking ref
echo "Pushed $(git rev-parse --short HEAD) to main."
