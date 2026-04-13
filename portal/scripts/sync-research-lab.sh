#!/usr/bin/env bash
set -euo pipefail
SRC="$(git rev-parse --show-toplevel)/docs/models"
DST="$(git rev-parse --show-toplevel)/portal/public/research-lab"
mkdir -p "$DST"
cp "$SRC"/*.html "$DST"/ 2>/dev/null || true
cp "$SRC"/*.png  "$DST"/ 2>/dev/null || true
cp "$SRC"/*.csv  "$DST"/ 2>/dev/null || true
echo "Synced research-lab assets: $(ls -1 "$DST" | wc -l) files"
