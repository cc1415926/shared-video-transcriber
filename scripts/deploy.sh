#!/usr/bin/env bash
set -euo pipefail

# Agent-friendly, repeatable source deployment for macOS.
# It never deletes .venv, .data, the platform data directory, or user media.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
export PYTHONUTF8=1
start=0
check_only=0
skip_browser=0
install_ffmpeg=0
for arg in "$@"; do
  case "$arg" in
    --start) start=1 ;;
    --check) check_only=1 ;;
    --skip-browser) skip_browser=1 ;;
    --install-ffmpeg) install_ffmpeg=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

find_python() {
  command -v python3 || command -v python || true
}
find_uv() {
  command -v uv || true
}
uv_bin="$(find_uv)"
if [[ -z "$uv_bin" ]]; then
  python_bin="$(find_python)"
  if [[ -z "$python_bin" ]]; then
    echo 'uv and Python were not found. Install Python 3.12 from python.org, then run this script again.' >&2
    exit 1
  fi
  echo 'Installing uv 0.12.8 into the current user Python location…'
  "$python_bin" -m pip install --user 'uv==0.12.8'
  export PATH="$($python_bin -m site --user-base)/bin:$PATH"
  uv_bin="$(find_uv)"
  if [[ -z "$uv_bin" ]]; then
    echo 'uv was installed but is not on PATH. Restart the terminal and run again.' >&2
    exit 1
  fi
fi
echo "uv: $($uv_bin --version)"
venv_python="$root/.venv/bin/python"

if [[ "$check_only" == 1 ]]; then
  [[ -x "$venv_python" ]] || { echo 'Project environment is not installed. Run scripts/deploy.sh first.' >&2; exit 1; }
  exec "$venv_python" diagnostics.py
fi
if [[ -e "$root/.venv" && ! -x "$venv_python" ]]; then
  echo 'Found an incomplete .venv. This script will not delete it: stop the app, rename .venv as a backup, then retry. Do not delete .data or user data.' >&2
  exit 1
fi
if [[ ! -x "$venv_python" ]]; then
  echo 'Creating the project Python 3.12 environment; uv reuses a local interpreter and cache when available…'
  "$uv_bin" venv --python 3.12 .venv
fi
echo 'Installing/repairing pinned dependencies from requirements.lock…'
"$uv_bin" pip install --python "$venv_python" -r requirements.lock
"$uv_bin" pip check --python "$venv_python"

browser="$("$venv_python" -c "from runtime_paths import browser_executable; print(browser_executable() or '')")"
cached_browser="$("$venv_python" -c "from runtime_paths import configure_runtime; configure_runtime(); from pathlib import Path; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print('yes' if Path(p.chromium.executable_path).is_file() else ''); p.stop()")"
if [[ "$skip_browser" != 1 && -z "$browser" && -z "$cached_browser" ]]; then
  echo 'No system Chrome/Edge or Playwright Chromium was found; installing Chromium only when needed…'
  "$venv_python" -c 'from runtime_paths import configure_runtime; configure_runtime()'
  "$venv_python" -m playwright install chromium
elif [[ -n "$browser" ]]; then
  echo "Reusing system browser: $browser"
elif [[ "$skip_browser" == 1 ]]; then
  echo 'Skipped browser install: local files, transcription and clips remain available.'
fi

ffmpeg="$("$venv_python" -c "from runtime_paths import executable; print(executable('ffmpeg') or '')")"
if [[ -z "$ffmpeg" ]]; then
  if [[ "$install_ffmpeg" == 1 ]]; then
    command -v brew >/dev/null 2>&1 || { echo 'Homebrew is required for --install-ffmpeg. Install FFmpeg manually from a trusted source, then retry.' >&2; exit 1; }
    brew install ffmpeg
  else
    echo 'WARNING: FFmpeg was not found. Full download merging, audio extraction and clip export require it.' >&2
    echo 'Retry with: bash scripts/deploy.sh --install-ffmpeg' >&2
  fi
else
  echo "Reusing FFmpeg: $ffmpeg"
fi

"$venv_python" diagnostics.py
if [[ "$start" == 1 ]]; then
  echo 'Starting the local service (127.0.0.1 only)…'
  exec "$venv_python" app.py
fi
echo 'Deployment complete. Start with: bash scripts/deploy.sh --start'
