"""Paths and per-user runtime state for source and packaged Video Inbox runs.

Application code and bundled assets are read-only once installed.  All mutable
state belongs in a platform-appropriate user directory instead.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_NAME = 'VideoInbox'


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def resource_dir() -> Path:
    """Return the immutable source/bundle directory containing app assets."""
    if is_frozen():
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent)).resolve()
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Return the persistent, writable data root without creating it."""
    override = os.environ.get('VIDEO_DATA_DIR', '').strip()
    if override:
        return Path(override).expanduser().resolve()
    # Preserve a source-checkout user's existing history on first upgrade. A
    # packaged app never uses this compatibility path: its bundle is read-only
    # and new installs always use the platform directory below.
    legacy = resource_dir() / '.data'
    if not is_frozen() and (legacy / 'library.sqlite3').is_file():
        return legacy.resolve()
    if sys.platform == 'darwin':
        return (Path.home() / 'Library' / 'Application Support' / APP_NAME).resolve()
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
        return (base / APP_NAME).resolve()
    return (Path(os.environ.get('XDG_DATA_HOME') or (Path.home() / '.local' / 'share')) / APP_NAME).resolve()


def runtime_dirs() -> dict[str, Path]:
    root = user_data_dir()
    return {
        'root': root,
        'logs': root / 'logs',
        'models': root / 'models',
        'playwright': root / 'playwright',
        'config': root / 'config',
    }


def configure_runtime() -> dict[str, Path]:
    """Configure cache locations without writing to disk during module import."""
    paths = runtime_dirs()
    # Respect explicit advanced overrides, but never put mutable caches in the app bundle.
    os.environ.setdefault('HF_HOME', str(paths['models'] / 'huggingface'))
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(paths['playwright'] / 'browsers'))
    return paths


def prepare_runtime() -> dict[str, Path]:
    """Create writable roots after the user has explicitly launched the app."""
    paths = configure_runtime()
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def bundled_executable(name: str) -> Path | None:
    """Locate an optional platform-specific tool shipped by a future installer."""
    executable = name + ('.exe' if os.name == 'nt' else '')
    candidate = resource_dir() / 'bin' / executable
    return candidate if candidate.is_file() else None


def executable(name: str) -> str | None:
    bundled = bundled_executable(name)
    return str(bundled) if bundled else shutil.which(name)


def browser_executable() -> str | None:
    """Return an explicitly configured or normally installed Chromium browser."""
    configured = os.environ.get('VIDEO_PLAYWRIGHT_CHROMIUM', '').strip()
    if configured and Path(configured).is_file():
        return configured
    candidates: list[Path] = []
    if os.name == 'nt':
        for base in filter(None, [os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'), os.environ.get('LOCALAPPDATA')]):
            candidates.extend([
                Path(base) / 'Google/Chrome/Application/chrome.exe',
                Path(base) / 'Microsoft/Edge/Application/msedge.exe',
            ])
    elif sys.platform == 'darwin':
        candidates.extend([
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'),
            Path('/Applications/Chromium.app/Contents/MacOS/Chromium'),
        ])
    return next((str(path) for path in candidates if path.is_file()), None)
