# Free iOS Build Pipeline V1 report

## Final state: FREE_IOS_BUILD_BLOCKED

1. macOS CI compile: configured, not executed; external CI repository/account connection is absent.
2. Simulator build: configured, not run.
3. Device no-sign build: configured, not run.
4. Tests: iOS tests configured, not run; portable Navigation Core regression passed.
5. GitHub Actions: configured, manual trigger only.
6. Codemagic: configured, credentials-free.
7. Zero-cost option today: GitHub Actions for a public repository, or Codemagic individual free tier (verify current eligibility); for physical install, interactive Xcode + free Apple ID on a Mac.
8. Card: not required or configured by this pipeline; providers may vary.
9. Paid Apple Developer: not required for compilation/simulator; not acquired.
10. Personal Team automatic CI signing: no; interactive Xcode is required.
11. Installable IPA: no.
12. Blocker: no macOS CI run was authorized/connected, and no valid Apple device signing is available.
13. Artifacts: scripts, workflows, config and reports were generated; remote build products cannot exist before a CI run.
14. Zero-cost iPhone route: Path A in `INSTALL_ON_IPHONE.md`.
15. Final state: `FREE_IOS_BUILD_BLOCKED`.
