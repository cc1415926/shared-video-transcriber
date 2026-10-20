# Third-party notices for packaged Video Inbox

Video Inbox source code is MIT licensed. A packaged distribution also contains
third-party components under their own terms:

| Component | License / notice |
|---|---|
| Python | PSF License |
| FastAPI, Uvicorn, faster-whisper, CTranslate2, MCP SDK | MIT |
| Playwright | Apache-2.0 |
| PyAV, HTTPX, Pillow | BSD-style licenses |
| python-dotenv | BSD-3-Clause |
| OpenCC Python reimplementation | Apache-2.0 |
| PyInstaller | GPL-2.0-or-later with its bootloader special exception |
| yt-dlp Python package | Unlicense; review its bundled dependency notices before every release |

This test package does **not** bundle FFmpeg, Whisper models, or a Playwright
browser. If a later release bundles FFmpeg, its exact binary build and license
(LGPL or GPL) must be disclosed and distributed in compliance with that build's
terms. The current H.264 clip path requests `libx264`, so a GPL FFmpeg build
cannot be silently labelled as LGPL-only.

Platform websites, uploaded media, and AI services have their own terms. Users
must only process media they are authorized to access and use.
