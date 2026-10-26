# iOS native map migration

V1 keeps the current renderer behind a future `MapRendererProtocol`. MapLibre Native can be evaluated later for native render performance; icon assets and route/radar data contracts are reusable, while map gesture/UI layout and render lifecycle need deliberate redesign. Migration cost is intentionally deferred; no map was moved natively here.
