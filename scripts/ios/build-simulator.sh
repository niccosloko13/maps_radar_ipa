#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; ios="$root/apps/ios"; out="$root/artifacts/free-ios-build-v1/ci"
mkdir -p "$out" "$ios/build"
cd "$ios"
xcodebuild -project RelasBeta.xcodeproj -scheme RelasBeta -configuration Debug -sdk iphonesimulator -derivedDataPath build CURRENT_PROJECT_VERSION="${BUILD_NUMBER:-1}" build | tee "$out/simulator-build.log"
xcodebuild -project RelasBeta.xcodeproj -scheme RelasBeta -configuration Debug -sdk iphonesimulator -derivedDataPath build CURRENT_PROJECT_VERSION="${BUILD_NUMBER:-1}" test | tee "$out/simulator-test.log"
