#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
arch="$(uname -m)"
case "$arch" in
  arm64) label="AppleSilicon" ;;
  x86_64) label="Intel" ;;
  *) echo "Unsupported macOS architecture: $arch" >&2; exit 2 ;;
esac
app="$root/dist/VideoInbox.app"
suffix=""
if [[ "${VIDEO_INBOX_UNSIGNED_TEST:-0}" == "1" ]]; then suffix="-unsigned-test"; fi
output="$root/dist/installers/VideoInbox-macOS-$label$suffix.dmg"
stage="$root/build/dmg-stage"
test -d "$app"
rm -rf "$stage"
mkdir -p "$stage" "$(dirname "$output")"
cp -R "$app" "$stage/Video Inbox.app"
ln -s /Applications "$stage/Applications"
rm -f "$output"
hdiutil create -volname "Video Inbox" -srcfolder "$stage" -ov -format UDZO "$output"
echo "$output"
