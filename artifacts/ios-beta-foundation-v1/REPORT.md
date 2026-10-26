# iOS Beta Foundation V1 report

## Final state: IOS_BETA_FOUNDATION_PARTIAL

1. iOS app: source foundation created under `apps/ios/RelasBeta`.
2. Build: not compiled — Xcode/Swift unavailable on Windows (`REAL_DEVICE_REQUIRED`).
3. Auth required: yes; map is behind auth gate.
4. Session Keychain: yes, implementation uses Security generic-password storage.
5. Core Location: integrated in `LocationService`.
6. Native location reaches Navigation Core: bridge contract implemented.
7. `navigator.geolocation`: absent from iOS path.
8. Offline telemetry: queue/batch contract implemented.
9. `trip_id`: model implemented.
10. User/session/trip/error: schema correlates them.
11. Radar P0: preserved; baseline navigation tests pass.
12. Wrong-direction: preserved; tests pass.
13. Parallel-road: preserved; tests pass.
14. GPS-loss recovery: preserved; tests pass.
15. Feature flags: local safe defaults implemented.
16. Admin traceability: designed but blocked pending authenticated user telemetry backend.
17. Secrets: none placed in bundle/log source.
18. Privacy Data Map: generated.
19. External configuration: Xcode target/signing, TLS beta API, user-auth issuer/validator, telemetry ingestion/config backend, Sign in with Apple setup.
20. Physical iPhone: Core Location permissions/background behavior, heading, battery, MetricKit, actual WebKit bridge and build/install.
21. Final state: `IOS_BETA_FOUNDATION_PARTIAL`.

No push, deployment, App Store publication, map migration, source-system change, or radar/navigation-rule change was performed.
