#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; ios="$root/apps/ios"; out="$root/artifacts/sideloadly-ios-v1"; derived="$ios/build/ios-sideload"
mkdir -p "$out" "$derived"; cd "$ios"
xcodebuild -project RelasBeta.xcodeproj -scheme RelasBeta -configuration Debug -sdk iphoneos -derivedDataPath "$derived" CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO ONLY_ACTIVE_ARCH=NO ARCHS=arm64 CURRENT_PROJECT_VERSION="${BUILD_NUMBER:-1}" build | tee "$out/build.log"
app="$derived/Build/Products/Debug-iphoneos/RELAS.app"
test -f "$app/RELAS" || { echo 'RELAS.app executable missing' >&2; exit 1; }
lipo -info "$app/RELAS" | grep -q arm64 || { echo 'device arm64 missing' >&2; exit 1; }
plutil -extract CFBundleIdentifier raw "$app/Info.plist" >/dev/null
plutil -extract CFBundleExecutable raw "$app/Info.plist" | grep -qx RELAS
plutil -extract CFBundleVersion raw "$app/Info.plist" >/dev/null
plutil -extract CFBundleShortVersionString raw "$app/Info.plist" >/dev/null
plutil -extract MinimumOSVersion raw "$app/Info.plist" >/dev/null
printf '{"app_version":"0.1.0","build_number":"%s","git_commit":"%s","xcode_version":"%s","sdk":"iphoneos","architecture":"arm64","signing":"unsigned_for_sideloadly"}\n' "${BUILD_NUMBER:-1}" "$(git -C "$root" rev-parse HEAD)" "$(xcodebuild -version | tr '\n' ' ')" > "$out/build-info.json"
