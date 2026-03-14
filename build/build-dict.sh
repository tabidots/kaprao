#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

DICT_DIR="$ROOT_DIR/dict"
DATA_DIR="$ROOT_DIR/data"
EXT_DATA_DIR="$ROOT_DIR/extension/data"

DB="$DICT_DIR/kaprao.db"
OUT_JSON="$DATA_DIR/thai_en.json"

mkdir -p "$DATA_DIR"
mkdir -p "$EXT_DATA_DIR"

echo "▶ Exporting JSON..."
python3 "$DICT_DIR/scripts/export_json.py" "$DB" "$OUT_JSON"

echo "▶ Compressing JSON..."
gzip -f -k "$OUT_JSON"

echo "▶ Copying data into extension..."
cp "$DATA_DIR/thai_en.json" "$EXT_DATA_DIR/"
cp "$DATA_DIR/thai_en.json.gz" "$EXT_DATA_DIR/"

echo "✔ Dictionary build complete:"
ls -lh "$EXT_DATA_DIR"