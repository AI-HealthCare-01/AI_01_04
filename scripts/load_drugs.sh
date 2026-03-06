#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/load_drugs.sh
#   bash scripts/load_drugs.sh /path/to/drugs.csv

CSV_PATH="${1:-scripts/init-db/02-seed-drugs.csv}"

UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" \
uv run python scripts/load_drugs_csv.py --csv "$CSV_PATH"
