# RELAS — radar/traffic-signal source assessment, 2026-10-28

This is a source assessment and integration gate, **not** evidence that these sources have been ingested. No live signal phase (red/amber/green) feed is verified.

| Provider | URL | Coverage | What can be used | Caveat | Next action |
|---|---|---|---|---|---|
| CET SP official | https://www.cetsp.com.br/consultas/fiscalizacao-eletronica-do-transito.aspx | São Paulo municipality | Activated/deactivated enforcement location reference | Inspect machine-readable access and terms; status may change | Compare official records using identifiers, position, road and effective status |
| GeoSampa WFS official | https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs | São Paulo municipality | Geocoded signalized intersections | Static infrastructure, NOT live signal color; exact feature type and CRS need validation | Fetch capabilities, inspect schema, import only via staging |
| Pardal | https://github.com/Murkiriel/pardal | Brazil; state files | Radar and speed-limit candidate comparison | ODbL derivative database obligations, not official, can be stale | Perform license review and use read-only diff of SP files |
| Bunda de Urso | https://github.com/Challado/Bunda-de-Urso | Brazil | Public API and point/source/history metadata | Code is source-available, NOT free to reuse; published data under CC BY 4.0 with attribution and upstream constraints | Query public endpoints carefully, compare results, avoid copying code |
| OSM/Overpass | https://wiki.openstreetmap.org/wiki/Overpass_API | Variable coverage | Supplemental traffic_signals, speed_camera and speed limits | Community mapping, API usage limits, ODbL attribution | Bounded queries only, record OSM ids + timestamp |
| SPTrans Olho Vivo | https://www.sptrans.com.br/desenvolvedores | São Paulo | Real-time bus position, some road flow information | NOT real-time traffic-light phases and not a speed camera registry | Separate future traffic module |

## RELAS implementation requirements
1. Query existing inventory read-only first: radars, map_points, road_objects, source_syncs, municipality_sources and radar_validations.
2. Generate per-source completeness/age and municipality gap reports. Distinguish last ingest, last official verification and physical operational status.
3. Stage external candidates in a **separate dataset**, preserve original ID, timestamp, license, source link, road name and direction. Do not write directly to production inventory.
4. Canonical matching: exact source IDs before geography; for geographic matches require kind + close coordinates + road class/road name + compatible heading and speed. Crossings, parallel streets and opposite carriageways may be near each other.
5. Never overwrite an official record from community/GitHub data. Conflicts require review; retain source/history and tombstones.
6. Publish only through existing Admin approval flow; backup, validation and rollback are mandatory.
7. Never label traffic lights as live phase without a verified active sensor/API. Feature location is infrastructure, not status.
8. Attribution and license review before consuming data in the deployed public app; do not silently copy MapaRadar downloads as its terms restrict redistribution.

## Acceptance metrics
- Source and last successful sync, number of verified official IDs, lat/lon validity, percentage with speed/direction, documented inactive status, unmatched candidates and duplicate suspects.
- Recorded test cases on dual carriageways and adjacent street segments.
- Statewide data may be partial; never claim 'complete SP' based on a single feed.
- No new source is marked production-ready without logged test results and a known usage license.
