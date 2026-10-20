"""Generate deterministic application icons without external artwork or brands."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'packaging' / 'generated'


def icon(size: int) -> Image.Image:
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = round(size * .08)
    radius = round(size * .20)
    draw.rounded_rectangle((margin, margin, size - margin, size - margin), radius=radius,
                           fill='#164a58')
    # Inbox tray, followed by a play triangle. Keep high contrast at tiny sizes.
    tray = (round(size * .21), round(size * .50), round(size * .79), round(size * .72))
    draw.rounded_rectangle(tray, radius=round(size * .05), fill='#dff2ef')
    draw.rectangle((round(size * .29), round(size * .43), round(size * .71), round(size * .57)), fill='#dff2ef')
    triangle = [(round(size * .46), round(size * .25)), (round(size * .46), round(size * .46)), (round(size * .64), round(size * .355))]
    draw.polygon(triangle, fill='#7bd4c8')
    return image


def write_windows_icon() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / 'videoinbox.ico'
    largest = icon(256)
    largest.save(target, format='ICO', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return target


def write_macos_icon() -> Path:
    iconset = OUTPUT / 'videoinbox.iconset'
    iconset.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        icon(size).save(iconset / f'icon_{size}x{size}.png')
        icon(size * 2).save(iconset / f'icon_{size}x{size}@2x.png')
    target = OUTPUT / 'videoinbox.icns'
    subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(target)], check=True)
    return target


def main() -> int:
    print(write_windows_icon())
    if sys.platform == 'darwin':
        print(write_macos_icon())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
