# Playwright visual validation

## Final state: VISUALLY_READY_FOR_CONTROLLED_PHYSICAL_TEST

1. Playwright was installed locally with `npm install --no-save --package-lock=false playwright`; Chromium was installed and executed.
2. Street/number search: PASS in browser responses. All four Rui Barbosa queries returned HTTP 200, Rua Rui Barbosa / Praia Grande first, no duplicates, and `APPROXIMATE_NUMBER` for unavailable numbers. The provider did not expose exact 198/521/818 house points, so those are correctly approximate rather than fabricated exact addresses.
3. Marker fluency: PASS after the capture waits for camera settle; 60/80/90/100 km/h are visible and inside the safe zone.
4. Camera independence: PASS. `displayLocation` and `cameraTarget` remain separate; no application behavior was changed.
5. Perceptible delay at 30/60/90/100: PASS in the settled smoke. No camera duration was changed.
6. GPS delay 900 ms: SAFE in deterministic simulator profile (it is represented as delay, not hidden by prediction); not a physical-device visual claim.
7. Wrong-direction: PASS in `road-navigation-smoke.js`.
8. Parallel-road: PASS in navigation intelligence/location final tests; the simulator scenario executed deterministically. No extra physical-road claim.
9. Radar P0: PASS in navigation intelligence smoke and browser road-navigation smoke.
10. Route progress: PASS in road-navigation smoke.
11. ROAD_MODE: PASS in navigation-intelligence smoke.
12. Mobile: PASS at 375x812, 390x844 and 430x932 (no horizontal overflow); screenshots saved.
13. Page/console errors: none in focused smoke; existing browser smokes passed.
14. HTTP errors: none in focused smoke.
15. `VISUALLY_READY_FOR_CONTROLLED_PHYSICAL_TEST`: YES.

Initial runner failure was an obsolete test-only service-worker cache assertion (`relas-v232-road-test` while the app serves `relas-v233-road-test`). It was corrected in the smoke expectation only, then the final browser run passed: road browser, road navigation, location browser, map UI v3 and navigation intelligence.

The later high-speed diagnostic established that the observation was a screenshot timing race, not a marker/camera defect. Final screenshots are `visual/60kmh-final.png`, `80kmh-final.png`, `90kmh-final.png`, and `100kmh-final.png`; machine results are in `PLAYWRIGHT_RESULTS.json`. No deployment or push was performed.
