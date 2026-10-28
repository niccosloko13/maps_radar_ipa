# RELAS Motion — design reference approved by project owner (2026-10-28)

## Visual target

The approved reference is the image generated in the conversation showing a premium RELAS navigation UI presentation board. **The image is a visual reference, not existing executable screens or proof of available real-time data.** It should be attached to the development task from the conversation; do not assume it is stored in the Git repository.

### Screen families shown and approved
1. **City driving (light)**: full map, purple route, blue vehicle chevron low in viewport, dark large maneuver banner, route road shield, discreet individual traffic signals, speed, ETA and remaining distance.
2. **Highway driving (dark)**: high-contrast roads, guidance to highway exit, limit shield only when verified, road incidents, tuned zoom/camera and compact travel stats.
3. **Close radar warning**: prominent red panel, radar type, distance and verified speed limit. Real alert eligibility, map matching and direction safeguards remain authoritative.
4. **Zoom 5 / 10 / 14 / 17**: progressive detail. Statewide major routes → city major roads → local streets and traffic signals → detailed map geometry. Never fabricate property numbers or traffic signals.
5. **Day/night** styles with consistent semantic colors.
6. **Route planning** with origin/destination, alternative routes **only if router provides them**, and trustworthy travel estimates.
7. **Driver information**: speed, known limit, next relevant radar, remaining time/distance, ETA.
8. **Own custom pictogram family** for fixed radar, signal camera, mobile radar, electronic speed bump, police enforcement, traffic lights, construction, incident, hazard, weather, tolls and road restrictions.
9. **Driver camera modes**: 2D default, 3D road view, extended look-ahead. On-web 3D means map perspective; not literal 3D buildings guaranteed.

## Tokens
- Route purple: #6B57DB.
- Vehicle cyan-blue: differentiate from active purple route, bright white outline.
- HUD ink: #182C3B, off-white card surfaces.
- Positive: #168A79; attention: #F3A43C; urgent: #D94A42.
- Park: #DCEBDC; water: #B8DFEB; secondary streets: #FFFDFA; highways: warm #EDCBAA.
- Night variants must pass contrast checks.

## Implementation order
**P0** Render proper route lines and traffic/radar source priority and preserve official-source semantics.
**P1** Individual SVGs with 24, 32, 40 px tests (no emoji) and icon collision rules.
**P2** Progressive map zoom style, city/road mode, primary/secondary road labels.
**P3** Three navigation screen states, accessible touch targets and voice controls.
**P4** Route planning / info panel polish and optional camera modes.
**P5** Playwright desktop/mobile screenshots and GPS replay tests, preview deploy on branch.

## Non-negotiable guardrails
- Don't copy Waze source assets or trademarks.
- The design mockup includes sample labels/limits/ETA; never present illustrative numbers as live measurements.
- Traffic conditions and alternate routes require actual providers; don't fake live data.
- No uncontrolled icon flood: zoom/context rules and route-eligibility.
- Preserve radar P0, direction matching, parallel-road suppression, GPS loss recovery and security boundaries.
- Do not call approved for driving until route, exact address, and real vehicle tests are complete.

## Acceptance
- Compare screenshots on 390×844, 430×932, desktop, driving and idle.
- Validate zooms 5/10/14/17, city/highway, dark/day, imminent radar and degraded GPS.
- Run automated tests and keep a distinction between pass, not run and blocked.
- Publish a preview URL separately, verify HTTP and screenshot before reporting deployed.
