# Known limitations

- `RELAS-unsigned.ipa` is deliberately unsigned. Sideloadly must apply the user's own Apple ID signing on Windows; GitHub Actions contains no Apple ID, certificate, provisioning profile, or secret.
- Free Apple ID signing remains interactive and is limited by Apple account/device policy (including certificate/app limits and periodic re-signing). Installation on a particular iPhone is therefore still a physical-device step.
- Push notifications, associated domains, app groups/iCloud, CarPlay, and Sign in with Apple are not enabled. Background active-navigation location is not enabled; foreground Core Location remains declared and implemented.
- The artifact is a functional build/preflight result, not App Store/TestFlight distribution and not proof of device behavior.
- The iOS XCTest target is available but was not run in the unsigned device packaging job; its separate GitHub Actions workflow is not registered for dispatch at this repository state (CLI returned 404). The focused portable tests recorded in `BUILD_REPORT.md` passed 33/33.
- The Node.js 20 deprecation notice from third-party GitHub Actions is informational; the final workflow completed successfully.
