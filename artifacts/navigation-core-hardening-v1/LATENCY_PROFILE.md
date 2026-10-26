# Latency profile

Measurements are deterministic simulator timings, not physical-device render claims. They record received, processing, match, marker target/render, camera command/settle and end-to-end virtual visual latency separately.

| scenario | speed | gps age p50 | processing p50 | marker p50 | camera p50 | end-to-end p50 |
|---|---:|---:|---:|---:|---:|---:|
| urban | 50 km/h | 0 ms | 0.009 ms | <0.001 ms | 200 ms | 200.009 ms |
| highway | 100 km/h | 0 ms | 0.009 ms | <0.001 ms | 120 ms | 120.009 ms |
| high-speed | 120 km/h | 0 ms | 0.014 ms | <0.001 ms | 75 ms | 75.015 ms |
| gps-delay | 50 km/h | 900 ms | 0.009 ms | <0.001 ms | 200 ms | 1100.009 ms |
| gps-loss recovery | 30 km/h | 0 ms | 0.009 ms | <0.001 ms | 200 ms | 200.009 ms |

p95 is retained in `drive-simulator-results.json`. The profile demonstrates that injected GPS delay dominates end-to-end delay; it is not attributed to smoothing.
