"""Paths and per-user runtime state for source and packaged Video Inbox runs.

Application code and bundled assets are read-only once installed.  All mutable
state belongs in a platform-appropriate user directory instead.
"""
from __future__ import annotations

import json
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


def bootstrap_file() -> Path:
    """固定锚点：记录用户自选的缓存目录，必须与缓存目录本身无关。

    缓存被搬到别的盘以后，程序仍然靠这个位置找到「缓存现在在哪」，
    所以它永远留在系统用户配置目录，不随缓存迁移。
    """
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or (Path.home() / '.config'))
    return (base / APP_NAME / 'bootstrap.json').resolve()


def read_bootstrap() -> dict:
    try:
        value = json.loads(bootstrap_file().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def write_bootstrap(payload: dict) -> Path:
    path = bootstrap_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)
    return path


def default_data_dir() -> Path:
    """平台默认的数据目录，忽略用户设置与源码兼容目录。"""
    if sys.platform == 'darwin':
        return (Path.home() / 'Library' / 'Application Support' / APP_NAME).resolve()
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
        return (base / APP_NAME).resolve()
    return (Path(os.environ.get('XDG_DATA_HOME') or (Path.home() / '.local' / 'share')) / APP_NAME).resolve()


def user_data_dir() -> Path:
    """Return the persistent, writable data root without creating it."""
    override = os.environ.get('VIDEO_DATA_DIR', '').strip()
    if override:
        return Path(override).expanduser().resolve()
    configured = str(read_bootstrap().get('data_dir') or '').strip()
    if configured:
        candidate = Path(configured).expanduser()
        try:
            # 外接盘拔掉时不要卡在不存在的路径上，回退到默认目录。
            if candidate.is_dir():
                return candidate.resolve()
        except OSError:
            pass
    # Preserve a source-checkout user's existing history on first upgrade. A
    # packaged app never uses this compatibility path: its bundle is read-only
    # and new installs always use the platform directory below.
    legacy = resource_dir() / '.data'
    if not is_frozen() and (legacy / 'library.sqlite3').is_file():
        return legacy.resolve()
    return default_data_dir()


def data_dir_state() -> dict:
    """界面展示用：当前目录、来源、默认目录、锚点位置。"""
    override = os.environ.get('VIDEO_DATA_DIR', '').strip()
    configured = str(read_bootstrap().get('data_dir') or '').strip()
    current = user_data_dir()
    if override:
        origin = 'env'
    elif configured and current == Path(configured).expanduser().resolve():
        origin = 'setting'
    elif current == (resource_dir() / '.data').resolve():
        origin = 'legacy'
    else:
        origin = 'default'
    return {
        'data_dir': str(current),
        'default_dir': str(default_data_dir()),
        'origin': origin,
        # custom 只代表“用户在界面里选过”，源码目录的兼容缓存不算自定义。
        'custom': origin == 'setting',
        'configured': origin == 'setting',
        'env_override': origin == 'env',
        'settings_file': str(bootstrap_file()),
    }


def _copy_tree(source: Path, target: Path) -> int:
    """把缓存目录整份复制到新位置，跳过实例锁与临时文件。"""
    copied = 0
    for item in source.rglob('*'):
        if item.name in {'.instance.lock', '.setup.lock'}:
            continue
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if item.is_symlink() or not item.is_file():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        copied += item.stat().st_size
    return copied


def run_pending_migration() -> dict | None:
    """在服务启动早期执行挂起的目录迁移，此时没有任何任务在跑。

    迁移是「复制 → 校验 → 写配置」的顺序：任何一步失败都保留原目录，
    用户的数据不会因为换位置而丢失。源目录不会被删除，由用户自行决定。
    """
    settings = read_bootstrap()
    pending = settings.get('pending_migration')
    if not isinstance(pending, dict):
        return None
    source = Path(str(pending.get('from') or '')).expanduser()
    target = Path(str(pending.get('to') or '')).expanduser()
    report = {'from': str(source), 'to': str(target), 'ok': False}
    try:
        if not target.is_absolute() or not source.is_dir():
            raise ValueError('源目录不存在')
        target.mkdir(parents=True, exist_ok=True)
        report['bytes'] = _copy_tree(source, target)
        if (source / 'library.sqlite3').is_file() and not (target / 'library.sqlite3').is_file():
            raise OSError('数据库复制失败')
        if not (target / '.video-inbox-root').is_file():
            (target / '.video-inbox-root').write_text('video-inbox data root\n', encoding='utf-8')
        settings['data_dir'] = str(target.resolve())
        report['ok'] = True
    except (OSError, ValueError) as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        settings.pop('data_dir', None)
    settings.pop('pending_migration', None)
    settings['last_migration'] = report
    write_bootstrap(settings)
    return report


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
    run_pending_migration()
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
