# CI build report

Prepared workflow: `.github/workflows/ios-build.yml`; Codemagic fallback: `codemagic.yaml`. Both generate `RelasBeta.xcodeproj` from `apps/ios/project.yml`, record OS/Xcode/Swift/commit/build number, build and test iphonesimulator, compile iphoneos with signing disabled, and upload logs/build products.

Execution status: `NOT_RUN_EXTERNAL_CI_NOT_CONNECTED`. This Windows host has no `xcodebuild` or `swift`; no GitHub push, repository connection, Codemagic account or remote run was authorized. Thus no simulator `.app`, xcarchive, IPA, or macOS build log exists yet.
