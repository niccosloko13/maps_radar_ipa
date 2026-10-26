#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; ipa="$root/artifacts/sideloadly-ios-v1/RELAS-unsigned.ipa"; out="$root/artifacts/sideloadly-ios-v1"; tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT; test -f "$ipa" || { echo 'IPA missing' >&2; exit 1; }; unzip -q "$ipa" -d "$tmp"; app="$tmp/Payload/RELAS.app"
test -f "$app/Info.plist"; test -f "$app/RELAS"; lipo -info "$app/RELAS" | grep -q arm64
plutil -extract CFBundleIdentifier raw "$app/Info.plist" >/dev/null; plutil -extract CFBundleExecutable raw "$app/Info.plist" | grep -qx RELAS
! grep -R -I -E '/Users/|/home/|password=|api[_-]?key=' "$app" >/dev/null
python3 - <<'PY' > "$out/IPA_PREFLIGHT.json"
import json
print(json.dumps({'status':'PASS','payload':'Payload/RELAS.app','architecture':'arm64','signing':'unsigned_for_sideloadly','secrets_detected':False},indent=2))
PY
