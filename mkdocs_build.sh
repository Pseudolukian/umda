#!/usr/bin/env bash
# ──────────────────────────────────────────────────
# mkdocs_build.sh — UMDA → MkDocs full pipeline
# ──────────────────────────────────────────────────
# Paths from umda.yml. Finds umda.yml automatically.
# Usage: sh mkdocs_build.sh | . mkdocs_build.sh | ./mkdocs_build.sh

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
    # Fallback: search sibling directories of script
    for dir in "$_SD"/../*/; do
        [ -f "${dir}umda.yml" ] && echo "$(cd "$dir" && pwd)/umda.yml" && return
    done
    echo ""
}

_CONF="$(_find_umda)"
if [ -z "$_CONF" ]; then echo "ERROR: umda.yml not found. Set UMDA_YML or run from doc source dir."; return 1 2>/dev/null; exit 1; fi
_C="python3 $_SD/umda_conf.py $_CONF"

DOC_INPUT=$($_C config.doc_input)
DOC_OUTPUT=$($_C adapers.mkdocs.doc_output)
SITE_DIR=$($_C adapers.mkdocs.site_dir)
MKDOCS_PATH=$($_C adapers.mkdocs.mkdocs_path)
CONFIG_NAME=$($_C adapers.mkdocs.config.output_config_name)

echo "═══════════════════════════════════════"
echo "  MkDocs Build Pipeline"
echo "═══════════════════════════════════════"
echo "  umda.yml:   $_CONF"
echo "  doc_output: $DOC_OUTPUT"
echo "  site_dir:   $SITE_DIR"

echo ""
echo "▶ Clean: $DOC_OUTPUT, $SITE_DIR"
rm -rf "${DOC_OUTPUT:?}"/* 2>/dev/null
rm -rf "${SITE_DIR:?}"/* 2>/dev/null

echo ""
echo "▶ Step 1: UMDA mkdocs adapter"
cd "$DOC_INPUT"
python3 "$_SD/main.py" mkdocs build || { echo "ERROR: UMDA failed"; cd "$_OD"; return 1 2>/dev/null; exit 1; }

echo ""
echo "▶ Step 2: MkDocs build"
cd "$MKDOCS_PATH"
uv run mkdocs build -f "$CONFIG_NAME.yml" --site-dir "$SITE_DIR" --clean || { echo "ERROR: MkDocs failed"; cd "$_OD"; return 1 2>/dev/null; exit 1; }

echo ""
echo "✔ Done → $SITE_DIR"
cd "$_OD"
