# Build report

Workflow `.github/workflows/ios-sideload-build.yml` is manual-only, uses `macos-latest`, generates the Xcode project, builds `iphoneos arm64` with `CODE_SIGNING_ALLOWED=NO` and `CODE_SIGNING_REQUIRED=NO`, packages a real `Payload/RELAS.app` ZIP as `RELAS-unsigned.ipa`, validates it, and uploads `RELAS-sideload-build-<build_number>`.

Status: `CI_NOT_EXECUTED`. Therefore `RELAS.app`, arm64 verification, `RELAS-unsigned.ipa`, and successful preflight remain unproven and no false artifact was produced.
