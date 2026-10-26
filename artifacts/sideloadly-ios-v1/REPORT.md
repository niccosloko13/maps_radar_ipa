# Sideloadly iOS Pipeline V1

## Final state: SIDELOADLY_IPA_READY

1. GitHub CLI authenticated: yes, account `niccosloko13` with `repo` and `workflow` scopes.
2. Branch used: `feat/navigation-v3-phase-b1`.
3. Correction commits needed in this completion cycle: 1 (`8452f06`, explicit `CFBundleExecutable` metadata). Earlier pipeline corrections on the branch fixed XcodeGen dependency syntax and script execute permissions.
4. XcodeGen: passed in macOS CI.
5. `iphoneos` unsigned build: passed with arm64.
6. `RELAS.app`: created at `Payload/RELAS.app` in the packaged IPA.
7. Binary: verified arm64 by CI preflight and downloaded-artifact inspection.
8. IPA: `RELAS-unsigned.ipa` created.
9. Preflight: passed; ZIP, Payload, app, Info.plist, executable, arm64, no local absolute paths, and no secrets verified.
10. Workflow: green, run `40415947995`.
11. Artifact: uploaded.
12. Exact artifact name: `RELAS-sideload-build-5`.
13. Exact IPA name: `RELAS-unsigned.ipa`.
14. Free-signing limitations: push, associated domains, app groups/iCloud, CarPlay, and Sign in with Apple are not enabled; Apple free signing itself is interactive and account/device limited.
15. Core Location: preserved (`LocationService.swift`, usage descriptions, and native bridge remain unchanged).
16. Telemetry: preserved (local telemetry service/queue unchanged; focused telemetry tests passed).
17. Navigation Core: preserved; focused 33-test regression set passed, including radar P0, opposite/parallel-road suppression, route progress, camera policy, and GPS-loss recovery.
18. Secrets exposed: no; CI preflight returned `secrets_detected: false` and no signing credentials were configured.
19. Windows next step: download artifact `RELAS-sideload-build-5`, extract/use `RELAS-unsigned.ipa`, connect the iPhone, and select that IPA in Sideloadly with the user's own Apple ID. Complete any iPhone trust/Developer Mode prompts.
20. Final state: `SIDELOADLY_IPA_READY`.
