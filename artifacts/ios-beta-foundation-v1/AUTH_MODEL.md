# Auth model

The app blocks the map while unauthenticated. Access tokens and generated install IDs use Keychain, never UserDefaults. Internal telemetry identity is `user_id`, `session_id`, `device_install_id`, `app_session_id`, `trip_id`; email is never an event key.

`CONFIG_REQUIRED`: the existing backend only authenticates administrators. A user auth issuer/validator and Sign in with Apple Apple Developer configuration are external prerequisites; no credentials were fabricated.
