# Navigation Core Hardening V1 report

1. Street + number search: corrected with structured parsing alias, explicit ranking and address states.
2. Rui Barbosa 198: PASS in deterministic search test.
3. Rui Barbosa 521: PASS.
4. Rui Barbosa 818: PASS.
5. Nonexistent number retains the exact street: PASS (`APPROXIMATE_NUMBER`).
6. Duplicate protection: retained and semantic address state added; PASS in provider fixture behavior.
7. Drive Simulator: PASS.
8. Scenarios: normal, urban, highway, gps-noise, gps-delay, gps-loss, off-route, parallel-road, wrong-direction, stop-and-go, high-speed.
9. Marker lag: simulator p50/p95 below 0.001 ms; this is code-path timing, not GPU rendering.
10. Camera lag: 300 ms at 20 km/h, 200 ms at urban speed, 120 ms at 100 km/h, 75 ms >100 km/h.
11. End-to-end: 200.009 ms p50 urban; 120.009 ms p50 highway; GPS-delay 1100.009 ms p50.
12. Marker smoothing is separate from camera: PASS.
13. Camera duration adaptive: PASS.
14. Map matching regression: none in 69 final Node tests.
15. Radar P0: preserved; navigation intelligence tests passed.
16. Wrong-direction suppression: preserved; navigation tests passed.
17. GPS-loss recovery: preserved; location and simulator tests passed.
18. Remaining limitations: browser smoke blocked by missing Playwright; no physical-device latency claim.
19. Ready for a controlled new physical test: YES, conditional on completing the documented browser/device smoke first.

No push or deployment was performed.
