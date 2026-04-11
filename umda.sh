#!/usr/bin/env bash
# ============================================================
# UMDA CLI — global wrapper script
# ============================================================
#
# INSTALLATION:
#   1. Copy this file to /usr/local/bin/umda:
#        sudo cp umda.sh /usr/local/bin/umda
#        sudo chmod +x /usr/local/bin/umda
#
#   2. (Optional) Add alias to ~/.bashrc as a fallback:
#        echo 'alias umda="/usr/local/bin/umda"' >> ~/.bashrc
#        source ~/.bashrc
#
#   3. Adjust UMDA_DIR / UMDA_PROJECT_DIR below if paths differ.
#
# USAGE:
#   umda mkdocs build        # works from ANY directory
#
# ============================================================
set -euo pipefail

UMDA_DIR="/root/stormbpmn_project/umda"
VENV_DIR="${UMDA_DIR}/.mkdocs"

# Default project directory containing umda.yml.
# If the caller's CWD (or its parents) don't contain umda.yml,
# we auto-cd here so the build always finds it.
UMDA_PROJECT_DIR="/root/stormbpmn_project/stormbpmn_new_doc"

# Activate venv if it exists
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
fi

# --- Resolve working directory ---
# Walk up from CWD looking for umda.yml; if not found, fall back
# to UMDA_PROJECT_DIR.
find_umda_yml() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        [ -f "${dir}/umda.yml" ] && return 0
        dir="$(dirname "$dir")"
    done
    return 1
}

if ! find_umda_yml "$(pwd)"; then
    cd "${UMDA_PROJECT_DIR}"
fi

# --- Directories to chown after build (served by Caddy as user 'caddy') ---
CHOWN_DIRS=(
    "/var/www/html/media"
    "/var/www/html/stormbpm"
)
CHOWN_USER="caddy:caddy"

python3 "${UMDA_DIR}/main.py" "$@"
rc=$?

# Fix ownership so Caddy can serve the files
for dir in "${CHOWN_DIRS[@]}"; do
    [ -d "$dir" ] && chown -R "${CHOWN_USER}" "$dir" 2>/dev/null
done

exit $rc
