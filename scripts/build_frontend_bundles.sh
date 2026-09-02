#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
frontend="$repo_root/custom_components/nikas_house/frontend"
dist="$frontend/dist"

mkdir -p "$dist"

build_panel() {
  dependency=$1
  entry=$2
  output=$3
  temporary="$output.tmp"
  cp "$dependency" "$temporary"
  sed '1{/^import /d;}' "$entry" >> "$temporary"
  mv "$temporary" "$output"
}

build_panel \
  "$frontend/nikas-house-hero.js" \
  "$frontend/nikas-house-overview.js" \
  "$dist/nikas-house-overview.js"

if grep -Eq '^[[:space:]]*import[[:space:]]' "$dist/nikas-house-overview.js"; then
  echo "runtime import remains in House bundle" >&2
  exit 1
fi
