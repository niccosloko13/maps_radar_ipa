# Build report

Final CI run: [40415947995](https://github.com/niccosloko13/maps_radar_ipa/actions/runs/40415947995), completed successfully on 2026-10-26 from commit `8452f0635e1222e59f88a926e97377bf3489219b`.

The macOS runner installed XcodeGen, generated `RelasBeta.xcodeproj`, and built `RELAS.app` for `iphoneos` with `ARCHS=arm64`, `CODE_SIGNING_ALLOWED=NO`, and `CODE_SIGNING_REQUIRED=NO`. It then packaged `Payload/RELAS.app` into `RELAS-unsigned.ipa`, ran the IPA preflight, and uploaded artifact `RELAS-sideload-build-5`.

The downloaded artifact was independently inspected: the IPA opens as a ZIP; it contains `Payload/RELAS.app/Info.plist` and `Payload/RELAS.app/RELAS`; `CFBundleExecutable` is `RELAS`; the executable is a device Mach-O arm64 binary; no additional application frameworks are required; and the preflight reports no absolute local paths or secrets.

Focused portable regression tests passed locally: 33/33 Navigation Core, radar priority/suppression, route/camera, GPS-loss recovery, simulator, location-state, and telemetry tests. The iOS XCTest target remains available in `apps/ios/RelasBetaTests`; it is not part of the unsigned device packaging job and requires a macOS simulator runner to execute.
