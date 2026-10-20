"""Create a platform-native PyInstaller onedir bundle for Video Inbox."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build' / 'pyinstaller'
DIST = ROOT / 'dist'


def platform_name() -> str:
    if os.name == 'nt':
        return 'windows-x64'
    if sys.platform == 'darwin':
        machine = platform.machine().lower()
        if machine in {'arm64', 'aarch64'}:
            return 'macos-arm64'
        if machine in {'x86_64', 'amd64'}:
            return 'macos-x64'
    raise RuntimeError(f'unsupported release build host: {sys.platform} {platform.machine()}')


def build() -> Path:
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'generate_icons.py')], check=True)
    icon = ROOT / 'packaging' / 'generated' / ('videoinbox.ico' if os.name == 'nt' else 'videoinbox.icns')
    separator = ';' if os.name == 'nt' else ':'
    command = [
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', 'VideoInbox', '--icon', str(icon), '--workpath', str(BUILD), '--distpath', str(DIST),
        '--add-data', f'{ROOT / "static"}{separator}static',
        '--add-data', f'{ROOT / "LICENSE"}{separator}.',
        '--add-data', f'{ROOT / "THIRD_PARTY_NOTICES.md"}{separator}.',
        '--collect-all', 'faster_whisper', '--collect-all', 'ctranslate2', '--collect-all', 'av',
        '--collect-all', 'playwright', '--collect-submodules', 'mcp.server', '--collect-all', 'yt_dlp',
        '--hidden-import', 'opencc', '--hidden-import', 'app', '--hidden-import', 'server', '--hidden-import', 'webapp',
    ]
    for package in ('fastapi', 'uvicorn', 'faster-whisper', 'ctranslate2', 'av', 'playwright', 'yt-dlp', 'mcp', 'pillow', 'python-dotenv', 'httpx'):
        command += ['--copy-metadata', package]
    command.append(str(ROOT / 'launcher.py'))
    subprocess.run(command, cwd=ROOT, check=True)
    bundle = DIST / ('VideoInbox.app' if sys.platform == 'darwin' else 'VideoInbox')
    if not bundle.exists():
        raise RuntimeError(f'PyInstaller did not produce expected bundle: {bundle}')
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--print-platform', action='store_true')
    options = parser.parse_args(argv)
    if options.print_platform:
        print(platform_name())
        return 0
    print(build())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
