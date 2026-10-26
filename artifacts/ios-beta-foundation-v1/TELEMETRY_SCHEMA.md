# Telemetry schema

Central `TelemetryService` owns a retained offline queue and batches authenticated events. Envelope: event_id, event_name, occurred_at, user_id, session_id, trip_id, app_version, build_number, platform, OS, device, properties. Default level is `DIAGNOSTIC_SUMMARY`; raw active-trip debug requires consent plus explicit debug mode and short retention.

Event families implemented in contract: app/auth, search, route/trip, GPS, marker/camera, radar eligibility/suppression, UI/API/navigation errors. Backend ingestion, size limits, rate limits and scrubber are `CONFIG_REQUIRED`.
