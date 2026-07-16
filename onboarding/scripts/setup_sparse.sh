#!/usr/bin/env bash
#
# setup_sparse.sh — clone Content Writer and materialise ONLY the shared engine
# plus your own tenant folder (git sparse-checkout, cone mode).
#
# Usage (from an empty working directory):
#     bash setup_sparse.sh <tenant-id>
#     # example:  bash setup_sparse.sh es-es-ressources
#
# Result on disk: the engine (_shared, cli, scripts, ...) + tenants/<tenant-id>/.
# The other markets stay on GitHub and are NOT written to your computer.
#
# This script is standalone (pure git + bash): it runs BEFORE Python/pip are set up.
# After it finishes, follow onboarding/01-setup-machine.md to create the venv.

set -euo pipefail

REPO_URL="https://github.com/Sam-SEO-maker/content-writer.git"
REPO_DIR="content-writer"

TENANT_ID="${1:-}"
if [[ -z "$TENANT_ID" ]]; then
  echo "Usage: bash setup_sparse.sh <tenant-id>"
  echo "Find your tenant id after cloning with: python3 content_writer.py tenant list"
  exit 1
fi

# 1. Clone without checking out any file yet, and without downloading blobs eagerly.
if [[ -d "$REPO_DIR/.git" ]]; then
  echo "==> $REPO_DIR already cloned, reusing it."
else
  echo "==> Cloning $REPO_URL (metadata only)..."
  git clone --filter=blob:none --no-checkout "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"

# 2. Turn on sparse-checkout in cone mode (works by directory).
echo "==> Enabling sparse-checkout (cone mode)..."
git sparse-checkout init --cone

# 3. Materialise the shared engine + your tenant.
#    The engine directory list is the single source of truth in onboarding/.
#    (We read it from the git index because nothing is on disk yet.)
# Skip comment lines (#...) and blank lines; keep only the directory paths.
ENGINE_PATHS="$(git show HEAD:onboarding/engine-sparse-paths.txt | grep -vE '^\s*(#|$)' | tr '\n' ' ')"
echo "==> Materialising engine + tenants/$TENANT_ID ..."
# shellcheck disable=SC2086
git sparse-checkout set $ENGINE_PATHS "tenants/$TENANT_ID"

# 4. Check out the files.
git checkout main

# 5. Sanity check: root files (cone mode always includes the repo root) + your tenant.
echo ""
echo "==> Done. Your working tree now contains:"
ls -d _shared cli scripts content_writer.py "tenants/$TENANT_ID" 2>/dev/null || true
if [[ ! -d "tenants/$TENANT_ID" ]]; then
  echo ""
  echo "NOTE: tenants/$TENANT_ID does not exist in the catalog yet."
  echo "      Run 'python3 content_writer.py tenant init $TENANT_ID' after setting up Python"
  echo "      (see onboarding/02-onboard-my-tenant.md) to scaffold it."
fi
echo ""
echo "Next: open onboarding/01-setup-machine.md to create the Python environment."
