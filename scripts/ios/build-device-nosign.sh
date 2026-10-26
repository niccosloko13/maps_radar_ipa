#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; ios="$root/apps/ios"; out="$root/artifacts/free-ios-build-v1/ci"
mkdir -p "$out"; cd "$ios"
xcodebuild -project RelasBeta.xcodeproj -scheme RelasBeta -configuration Debug -sdk iphoneos -derivedDataPath build CODE_SIGNING_ALLOWED=NO CURRENT_PROJECT_VERSION="${BUILD_NUMBER:-1}" build | tee "$out/device-nosign-build.log"
