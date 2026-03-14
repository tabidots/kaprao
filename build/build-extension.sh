#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "▶ Building content script..."

handlebars "$ROOT_DIR/extension/content/popup.handlebars" -f "$ROOT_DIR/extension/content/popup.precompiled.js"
handlebars "$ROOT_DIR/extension/content/entryBlock.handlebars" -f "$ROOT_DIR/extension/content/entryBlock.precompiled.js"
handlebars "$ROOT_DIR/extension/content/shortcutHint.handlebars" -f "$ROOT_DIR/extension/content/shortcutHint.precompiled.js"

npx esbuild \
  "$ROOT_DIR/extension/content/content.js" \
  --bundle \
  --format=iife \
  --target=chrome114 \
  --outfile="$ROOT_DIR/extension/content/bundle.js"

echo "✔ Extension JS built"