# High-speed camera diagnostic

## Root cause

The 90 km/h failure was a smoke-capture race: the earlier focused script took its screenshot immediately after `receivePosition`, while MapLibre had not necessarily completed the independent camera animation/render cycle. It was not a map-matching, marker-render, look-ahead, or viewport failure.

The corrected smoke waits for `cameraDuration + 250 ms` before measuring/capturing. No application camera, marker, matching, radar, or source code was changed. Camera durations remain 300 / 200 / 120 / 75 ms.

| speed | visible | x / y px | safe zone | look-ahead | duration | zoom | bearing | pitch | reason |
|---:|---|---:|---|---:|---:|---:|---:|---:|---|
| 60 km/h | yes | 195 / 518 | yes | 66.7 m | 200 ms | 16.5 | 90° | 42° | settled |
| 80 km/h | yes | 195 / 512 | yes | 88.9 m | 120 ms | 15.9 | 90° | 42° | settled |
| 90 km/h | yes | 195 / 516 | yes | 100 m | 120 ms | 15.9 | 90° | 42° | settled |
| 100 km/h | yes | 195 / 520 | yes | 111.1 m | 120 ms | 15.9 | 90° | 42° | settled |

Viewport was 390×844; safe zone is x 78–312 and y 380–717. The full raw/matched/display/camera state and render timing are in `high-speed-diagnostic.json` and `PLAYWRIGHT_RESULTS.json`. Marker render lag was 5–14 ms; settled camera lag was 124–228 ms.
