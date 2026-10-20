#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
args=()
start=1
for arg in "$@"; do
    case "$arg" in
        --check) args+=(--check); start=0 ;;
        --install-only) start=0 ;;
        --skip-browser) args+=(--skip-browser) ;;
        *) args+=("$arg") ;;
    esac
done
if [[ "$start" == 1 ]]; then args+=(--start); fi
exec bash scripts/deploy.sh "${args[@]}"
