#!/usr/bin/env bash
# Push current branch to GitHub using HTTPS and a personal access token.
# Required env:
#   GIT_USER          GitHub username (used in URL and optional commit identity)
#   GIT_PAT           Personal access token (fine-grained or classic)
#   GIT_REPO_FULLNAME Repository as owner/repo (e.g. myuser/DomainRAG)
# Optional:
#   GIT_EMAIL         Commit author email (defaults to GIT_USER@users.noreply.github.com)
set -euo pipefail

: "${GIT_USER:?Set GIT_USER (GitHub username)}"
: "${GIT_PAT:?Set GIT_PAT (personal access token)}"
: "${GIT_REPO_FULLNAME:?Set GIT_REPO_FULLNAME (e.g. owner/DomainRAG)}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

git config user.name "$GIT_USER"
git config user.email "${GIT_EMAIL:-$GIT_USER@users.noreply.github.com}"

URL="https://${GIT_USER}:${GIT_PAT}@github.com/${GIT_REPO_FULLNAME}.git"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$URL"
else
  git remote add origin "$URL"
fi

BRANCH="$(git branch --show-current)"
git push -u origin "$BRANCH"
