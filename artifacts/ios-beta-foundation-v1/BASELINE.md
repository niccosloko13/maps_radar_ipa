# Baseline

Branch `feat/navigation-v3-phase-b1`; HEAD `5f5bfa82ef823207f02ab23376934d467cf62b2e`. Existing worktree changes were preserved. Navigation/location baseline: 35 Node tests passed. Current web API is same-origin PWA served by `server.py`; admin has separate admin cookie auth only. The backend has no safe beta-user auth, telemetry ingestion, or remote-config service. SQLite/local default and optional Neon/Postgres runtime exist; no schema was changed.

Host capability: Windows, no `swift` or `xcodebuild`; iOS build/device gates are `REAL_DEVICE_REQUIRED`.
