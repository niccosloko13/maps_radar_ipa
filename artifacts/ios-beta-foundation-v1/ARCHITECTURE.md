# Architecture

`apps/ios/RelasBeta` is a SwiftUI foundation: auth gate → consent → host view; Core Location → `NativeLocationBridge` → existing Navigation Core contract; all diagnostics → `TelemetryService` local queue → authenticated backend batch. No native renderer/map migration is included. `rawLocation`, `matchedLocation`, `displayLocation`, and `cameraTarget` remain Navigation Core concepts.

An Xcode project and beta API configuration must be created on macOS because this Windows workspace has no Xcode. No API URL or secret is bundled.
