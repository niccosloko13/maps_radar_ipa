#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; ios="$root/apps/ios"; out="$root/artifacts/free-ios-build-v1/ci"
mkdir -p "$out"
if ! security find-identity -v -p codesigning 2>/dev/null | grep -Eq '[1-9][0-9]* valid identities'; then echo SIGNING_REQUIRED | tee "$out/ipa-status.txt"; exit 0; fi
if [ ! -d "$ios/build/RelasBeta.xcarchive" ]; then echo SIGNING_REQUIRED | tee "$out/ipa-status.txt"; exit 0; fi
xcodebuild -exportArchive -archivePath "$ios/build/RelasBeta.xcarchive" -exportPath "$ios/build/export" -exportOptionsPlist "$root/config/ios/ExportOptions.example.plist" | tee "$out/export-ipa.log"
