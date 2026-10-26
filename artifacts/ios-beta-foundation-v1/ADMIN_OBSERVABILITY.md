# Admin observability

Planned authenticated `/api/admin/ios-beta` read model must provide Overview (active users/sessions/trips/crashes/GPS/radar rates), Users (internal ID only), Trips (GPS/map-match/reroute/radar/errors), Errors (code/build/device aggregation), and Releases (build comparison). Correlation is `user_id → session_id → trip_id → error_id`, with environment mandatory.

Not implemented against the current backend because beta-user authentication and telemetry persistence do not exist; adding a pseudo-admin endpoint would not satisfy the authenticated observability gate.
