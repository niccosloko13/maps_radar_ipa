# Privacy data map

| data | purpose / when | storage / retention | linked / precise / third party |
|---|---|---|---|
| account identifier | authenticated beta access | backend, account policy | yes / no / no |
| precise location | only active navigation diagnostics | short debug retention when consented | yes / yes / no |
| search query | diagnose address quality | aggregated diagnostic retention | pseudonymous / no / no |
| route/trip | navigation health | trip retention | pseudonymous / route-derived / no |
| interaction | relevant diagnostic actions only | aggregate | pseudonymous / no / no |
| crash/performance | reliability | longer metadata retention | pseudonymous / no / no |
| device/app metadata | build/device correlation | longer metadata retention | pseudonymous / no / no |

Future API supports export/delete by internal account identity; no legal retention period is hardcoded.
