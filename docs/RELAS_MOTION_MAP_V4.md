# RELAS Motion — map & driving interface V4

## Implemented on the V4 branch
- Road paint classes: motorway/trunk, primary/secondary, local roads. Light palette uses warm hierarchy; dark palette uses controlled cool contrast.
- Water and vegetation receive distinct subdued hues.
- Active route has a consistent purple across base path and progress gradient.
- Mobile maneuver card scales text and prevents long instructions from overflowing.
- Alert intensity uses a visual hierarchy, with overspeed highlighted.
- During driving, generic markers are reduced and radar markers receive stronger emphasis while route-relevance and direction checks remain intact.

## Important caveats
- The base map comes from the external OpenFreeMap Liberty style; individual layer ids and source ids can change. The styling loop catches unsupported paint properties. A live-browser visual review is essential before shipping.
- Cartography color does **not** imply live traffic speed. Do not use green/red traffic coloring without validated traffic data.
- A traffic light shown on a map is not necessarily navigation-eligible; alert layers still apply road direction and route filters.
- The arrival tracker remains conservative and cannot establish a building entrance from an imprecise geocoder result.

## Acceptance review
1. Capture screenshots at 390 × 844, 430 × 932 and 1440 × 900.
2. Repeat for city and motorway route, road mode, radar imminent, dark theme and route-end state.
3. Check visible route at 15 / 17 / 19 zoom, road-name readability and pictogram collision.
4. Verify location arrow and active route are not hidden by the panels.
5. Test touch controls and screen reader labels at phone scale.
6. Execute Node navigation tests and browser smoke tests and document actual pass/fail.
7. Test in a controlled physical trip with another trusted navigation app; do not call this release approved for driving before that gate.

## Pending
- New radar and semaphore icon system with semantic sizing.
- Route shape styling with class-aware casing.
- Lane guidance and road shields when the routing provider actually supplies trusted road metadata.
- Multi-geometry recorded GPS replay and false-alert telemetry.
- Verified preview deploy + visual diff.
