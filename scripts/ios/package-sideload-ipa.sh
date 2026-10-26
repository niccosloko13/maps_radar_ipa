#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; ios="$root/apps/ios"; out="$root/artifacts/sideloadly-ios-v1"; app="$ios/build/ios-sideload/Build/Products/Debug-iphoneos/RELAS.app"; stage="$ios/build/sideload-package"
test -d "$app" || { echo 'RELAS.app not built; run build-sideload-device.sh first' >&2; exit 1; }
rm -rf "$stage"; mkdir -p "$stage/Payload"; cp -R "$app" "$stage/Payload/RELAS.app"
(cd "$stage" && /usr/bin/zip -qry "$out/RELAS-unsigned.ipa" Payload)
unzip -Z1 "$out/RELAS-unsigned.ipa" | grep -qx 'Payload/RELAS.app/Info.plist'
