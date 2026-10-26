# Location bridge

`LocationService` uses `CLLocationManager`, automotive activity, and starts/stops updates only with `ACTIVE_NAVIGATION`. It normalizes to `{lat, lon, accuracy, speed, heading, timestamp, source:"ios_core_location"}`. `NativeLocationBridge` forwards this value to a generic Navigation Core sink; the core has no `CLLocation` dependency. The iOS path does not use `navigator.geolocation`.

Background location entitlement and real heading/accuracy/battery behavior require a physical iPhone validation.
