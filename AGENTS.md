# Video Inbox: Agent deployment contract

This repository is a local-first FastAPI application. Preserve its existing video collection, SQLite history, transcript, clip export and MCP behavior; do not replace it with Electron, Docker, cloud hosting, an installer, or a second service.

## One-command deployment

Run from the repository root after cloning. The scripts create or repair only the project `.venv`; they preserve `.data`, platform user data, media, `.env`, and cached models.

```powershell
# Windows PowerShell
.\scripts\deploy.ps1 -Start
```

```bash
# macOS
bash scripts/deploy.sh --start
```

The app prints a local URL, normally `http://127.0.0.1:7860`. Do not expose it on a LAN or public network.

## Required agent behavior

- Read this file and `README.md` before changing code.
- Use `requirements.lock` with `uv`; do not run unpinned global `pip install` for app dependencies.
- Reuse an existing compatible browser and FFmpeg. Do not download Chromium unless no compatible system browser or Playwright cache exists.
- Whisper models download only after a user selects a recognition profile. Do not pre-download models.
- Never disable TLS verification, install certificates, change system proxy settings, or ask for/copy `.env` credentials.
- Do not delete `.venv`, `.data`, the platform data directory, user videos, or model cache to “fix” an error. Report the error and use the scripts' recovery guidance.

## Checks and MCP

```powershell
.\scripts\deploy.ps1 -CheckOnly
```

```bash
bash scripts/deploy.sh --check
```

MCP uses the existing `server.py`; do not create a duplicate server. Configure the agent with the project virtual-environment Python and absolute `server.py` path, then start the web service before calling shared task tools.
