# Known limitations

- `CI_NOT_EXECUTED`: no connected GitHub repository/run was authorized.
- Windows has no Xcode/Swift, so arm64 `.app`, IPA and preflight were not produced locally.
- Sideloadly/Apple ID signing is user-interactive and untested here.
- Free signing compatibility ultimately depends on the Apple account/device and enabled capabilities.
- Backend beta auth/telemetry configuration remains external from the iOS foundation mission.
