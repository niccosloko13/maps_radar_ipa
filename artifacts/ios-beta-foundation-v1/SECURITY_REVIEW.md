# Security review

No endpoint secret, private credential, token or Apple configuration was added. Keychain stores the token/install ID; UserDefaults is not used for secrets. Production requires TLS-only API, server token/session validation, telemetry auth/rate/payload enforcement and log scrubber. No location collection outside an active trip.
