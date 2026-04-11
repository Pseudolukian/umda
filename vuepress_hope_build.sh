#!/usr/bin/env bash
# ──────────────────────────────────────────────────
# vuepress_hope_build.sh — UMDA → VuePress full pipeline
# ──────────────────────────────────────────────────
# Paths from umda.yml. Finds umda.yml automatically.
# Usage: sh vuepress_hope_build.sh | . vuepress_hope_build.sh | ./vuepress_hope_build.sh

if [ -n "${BASH_SOURCE+x}" ]; then
    _SD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    _SD="$(cd "$(dirname "$0")" && pwd)"
fi
_OD="$(pwd)"

# Find umda.yml: $UMDA_YML → cwd upward → sibling dirs of script
_find_umda() {
    [ -n "$UMDA_YML" ] && [ -f "$UMDA_YML" ] && echo "$UMDA_YML" && return
    local d="$(pwd)"
    while [ "$d" != "/" ]; do
        [ -f "$d/umda.yml" ] && echo "$d/umda.yml" && return
        d="$(dirname "$d")"
    done
    for dir in "$_SD"/../*/; do
        [ -f "${dir}umda.yml" ] && echo "$(cd "$dir" && pwd)/umda.yml" && return
    done
    echo ""
}

_CONF="$(_find_umda)"
if [ -z "$_CONF" ]; then echo "ERROR: umda.yml not found. Set UMDA_YML or run from doc source dir."; return 1 2>/dev/null; exit 1; fi
_C="python3 $_SD/umda_conf.py $_CONF"

DOC_INPUT=$($_C config.doc_input)
DOC_OUTPUT=$($_C adapers.vuepress_hope.doc_output)
SITE_DIR=$($_C adapers.vuepress_hope.site_dir)
VP_PATH=$($_C adapers.vuepress_hope.vuepress_path)
VP_PROJECT="$(dirname "$(dirname "$VP_PATH")")"

echo "═══════════════════════════════════════"
echo "  VuePress Hope Build Pipeline"
echo "═══════════════════════════════════════"
echo "  umda.yml:   $_CONF"
echo "  doc_output: $DOC_OUTPUT"
echo "  site_dir:   $SITE_DIR"

echo ""
echo "▶ Clean: $DOC_OUTPUT, $SITE_DIR, cache"
rm -rf "${DOC_OUTPUT:?}"/* 2>/dev/null
rm -rf "${SITE_DIR:?}"/* 2>/dev/null
rm -rf "$VP_PATH/.temp" "$VP_PATH/.cache" 2>/dev/null

echo ""
echo "▶ Step 1: UMDA vuepress_hope adapter"
cd "$DOC_INPUT"
python3 "$_SD/main.py" vuepress_hope build || { echo "ERROR: UMDA failed"; cd "$_OD"; return 1 2>/dev/null; exit 1; }

echo ""
echo "▶ Step 2: VuePress build"
cd "$VP_PROJECT"
npx vuepress-vite build src --dest "$SITE_DIR" || { echo "ERROR: VuePress failed"; cd "$_OD"; return 1 2>/dev/null; exit 1; }

echo ""
echo "✔ Done → $SITE_DIR"
cd "$_OD"
