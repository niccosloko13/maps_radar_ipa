# Drive Simulator V1

PASS. `scripts/drive-simulator/simulator.cjs` replays deterministic fixes through `LocationEngine`, with a cached local Rua Rui Barbosa 198 → 521 geometry fixture. Supported replay rates are 1x, 5x, 10x and 20x.

Executed: normal, urban, highway, gps-noise, gps-delay, gps-loss, off-route, parallel-road, wrong-direction, stop-and-go, high-speed. GPS-loss produced 5 loss ticks and 1 recovery. Off-route produced one simulated reroute. The fixture has no radar, SAU or toll inventory, so alert counters are zero rather than claims of field coverage.

Machine-readable details: `drive-simulator-results.json`. Test: `node --test tests/drive-simulator.test.cjs` — passed.
