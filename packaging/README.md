# Packaging inputs

`scripts/build_package.py` builds the platform-native PyInstaller `onedir` bundle.
It must run on its target OS and CPU architecture. The app remains local-only and
does not bundle user data, models, Playwright browsers or FFmpeg by default.

Windows: the full installer also bundles the pinned `wx_channel` v5.7.13
release. Run `scripts/prepare_wx_channel_bundle.ps1` with the official ZIP,
then run `powershell -ExecutionPolicy Bypass -File scripts/build_windows_installer.ps1`.
The preparation step validates the fixed SHA-256 and adds the MIT license before
Inno Setup creates the installer and its SHA256 companion file. The collector
is installed into the current user's `%LOCALAPPDATA%\\VideoInbox\\wx-channel`
folder; user downloads and login state are never build inputs.

macOS: build the `.app`, then run `scripts/create_dmg.sh`. An unsigned DMG is a
test build only. Code signing and notarization happen only when release secrets
are configured in CI.
