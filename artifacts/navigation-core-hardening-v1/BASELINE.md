# Baseline

- Branch: `feat/navigation-v3-phase-b1`
- HEAD: `5f5bfa82ef823207f02ab23376934d467cf62b2e`
- Initial dirty file: `test_navigation_intelligence.py` (preserved).
- Relevant navigation/location baseline: 19 Node tests passed.
- Search baseline: existing navigation backend tests were later run as the scoped search suite.
- Current camera duration before this mission: fixed 450 ms (`cameraPolicy`).
- Marker before this mission: source updated directly from the matched position; no separate display state.
- Geocoder: Photon (structured then free text); ViaCEP for submitted CEP.
- Browser smoke: not run: Playwright is not installed. See `VISUAL_VALIDATION.md`.
