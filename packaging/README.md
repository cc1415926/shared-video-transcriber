# Packaging inputs

`scripts/build_package.py` builds the platform-native PyInstaller `onedir` bundle.
It must run on its target OS and CPU architecture. The app remains local-only and
does not bundle user data, models, Playwright browsers or FFmpeg by default.

Windows: run `powershell -ExecutionPolicy Bypass -File scripts/build_windows_installer.ps1`.
It builds the bundle if needed, checks for Inno Setup, creates the installer and
writes a SHA256 companion file. Missing Inno Setup is a clear build prerequisite,
not a reason to publish a ZIP under the installer name.

macOS: build the `.app`, then run `scripts/create_dmg.sh`. An unsigned DMG is a
test build only. Code signing and notarization happen only when release secrets
are configured in CI.
