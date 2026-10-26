# Sideloadly iOS Pipeline V1

## Final state: SIDELOADLY_PIPELINE_READY_NOT_EXECUTED

1. Device arm64 build configured: yes.
2. macOS CI configured: yes.
3. CI executed: no (`CI_NOT_EXECUTED`).
4. `RELAS.app`: not generated yet.
5. Binary arm64: not verified yet.
6. `RELAS-unsigned.ipa`: not generated.
7. IPA preflight: not run; placeholder records why.
8. Incompatible free capabilities: push, associated domains, app groups/iCloud and CarPlay are not enabled; Sign in with Apple needs configuration.
9. Bundle rewrite: safe by design; no business logic depends on bundle ID.
10. Core Location: contract and usage declarations remain present.
11. Beta backend: environment-configured; credentials are external.
12. Telemetry: local queue contract remains; backend ingestion external.
13. Download after CI: `RELAS-sideload-build-<build_number>`.
14. Drag into Sideloadly: `RELAS-unsigned.ipa`.
15. iPhone: trust USB, sideload with your own free Apple ID, then approve developer/Developer Mode prompts if asked.
16. Final state: `SIDELOADLY_PIPELINE_READY_NOT_EXECUTED`.
