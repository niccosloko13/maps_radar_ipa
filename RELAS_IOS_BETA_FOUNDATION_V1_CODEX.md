# RELAS — iOS BETA FOUNDATION V1
## APP NATIVO INSTRUMENTADO + CORE LOCATION + CONTA OBRIGATÓRIA + TELEMETRIA + FEATURE FLAGS

# MISSÃO

Criar a primeira fundação iOS do RELAS para teste real em iPhone, preservando o Navigation Core já validado e evitando uma reescrita prematura.

Esta missão NÃO é um redesign completo e NÃO é a migração total do mapa para nativo.

Objetivos:

1. criar app iOS beta instalável;
2. exigir conta autenticada no beta;
3. usar Core Location nativo para localização;
4. alimentar o Navigation Core existente com localização nativa;
5. registrar sessões, viagens, eventos, erros, performance e bugs;
6. permitir diagnóstico por usuário/sessão/versão/dispositivo no admin;
7. criar feature flags/remotely configurable behavior;
8. preservar radar P0, map matching, smoothing e regras atuais;
9. preparar migração gradual futura para mapa/renderização totalmente nativos.

---

# PRINCÍPIO DE ARQUITETURA

NÃO reescrever todo o RELAS agora.

Usar arquitetura de transição:

```text
iOS APP / SwiftUI
        |
        +-- Authentication
        +-- Core Location
        +-- Telemetry
        +-- Crash / Performance
        +-- Feature Flags
        +-- Native Bridge
                |
                v
        RELAS Navigation Core
                |
                v
        CURRENT MAP / UI
```

O objetivo do beta é obter:

- GPS nativo;
- comportamento real em dispositivo;
- telemetria confiável;
- bugs reproduzíveis;
- feedback de usuários;
- dados para decidir o que deve virar nativo depois.

---

# REGRAS

- Não fazer redesign global.
- Não mudar radar P0.
- Não enfraquecer wrong-direction suppression.
- Não enfraquecer parallel-road suppression.
- Não alterar Official Radar Finder.
- Não mexer em ARTESP/SIBH/PRF/ANTT.
- Não fazer deploy público.
- Não publicar na App Store nesta missão.
- Não quebrar PWA/web atual.
- Não colocar secrets no app.
- Não enviar chaves privadas no bundle iOS.
- Não registrar senha, token bruto ou conteúdo sensível.
- Não coletar localização em background fora de uma viagem ativa.
- Não coletar telemetria escondida.

---

# ANTI-LOOP

Para cada bloco:

```text
IMPLEMENTAR
→ testar bloco
→ no máximo 2 correções
→ se continuar falhando: BLOCKED + documentar
→ seguir
```

Não repetir build/test indefinidamente.

Full validation:
- uma vez no baseline;
- uma vez no final.

---

# 0. BASELINE

Registrar:

```text
branch
HEAD
git status
web/navigation core tests
current API base URL architecture
current auth state
current DB/backend architecture
```

Criar:

```text
artifacts/ios-beta-foundation-v1/BASELINE.md
```

---

# 1. DECISÃO TÉCNICA

Criar projeto iOS separado e organizado.

Sugestão:

```text
apps/ios/
```

Stack:

```text
Swift
SwiftUI
Core Location
URLSession
WebKit bridge only where required
```

Não adicionar SDK pesado sem necessidade.

Se o projeto atual já tiver uma escolha equivalente documentada, respeitar a arquitetura existente.

---

# 2. AUTH OBRIGATÓRIO NO BETA

## Objetivo

Nenhum beta tester entra no mapa sem sessão autenticada.

Fluxo:

```text
Launch
→ Auth Gate
→ Login/Create Account
→ Consent/Privacy
→ Home/Map
```

Suportar arquitetura para:

```text
email + password or magic link
Sign in with Apple
```

Implementar somente o que o backend atual suportar com segurança.

Se Sign in with Apple exigir configuração externa não disponível:
marcar `CONFIG_REQUIRED`, sem inventar credenciais.

---

# 2.1 IDENTIDADE INTERNA

Nunca usar email diretamente como chave de telemetry.

Criar:

```text
user_id
session_id
device_install_id
app_session_id
trip_id
```

`device_install_id` deve ser gerado pelo app e não ser advertising ID.

---

# 3. CONSENTIMENTO E PRIVACIDADE

Antes de iniciar telemetria de navegação:

mostrar claramente que o beta coleta dados técnicos para:

- corrigir bugs;
- medir GPS;
- medir performance;
- investigar falhas de rota;
- melhorar alertas;
- melhorar experiência de navegação.

Separar:

```text
ACCOUNT DATA
DIAGNOSTICS
USAGE EVENTS
LOCATION DURING ACTIVE NAVIGATION
```

Não registrar localização contínua quando não há viagem ativa, salvo requisito explícito e autorizado.

Permitir no futuro:

```text
Export my data
Delete my account/data
```

Documentar desde já os campos necessários.

---

# 4. CORE LOCATION NATIVO

## Objetivo

Substituir `navigator.geolocation` do app iOS por Core Location.

Criar:

```text
LocationService
```

Responsável por:

```text
authorization
location updates
accuracy
course
speed
timestamp
background navigation state
error handling
```

Configurar atividade para navegação automotiva quando aplicável.

Não ativar background location permanentemente.

Background só durante:

```text
ACTIVE_NAVIGATION
```

---

# 4.1 MODELO DE LOCATION

Normalizar Core Location para o formato esperado pelo Navigation Core:

```json
{
  "lat": 0,
  "lon": 0,
  "accuracy": 0,
  "speed": 0,
  "heading": 0,
  "timestamp": 0,
  "source": "ios_core_location"
}
```

Preservar:

```text
rawLocation
matchedLocation
displayLocation
cameraTarget
```

---

# 4.2 BRIDGE

Criar bridge explícito:

```text
NativeLocationBridge
```

Fluxo:

```text
Core Location
→ NativeLocationBridge
→ existing Location Engine
→ Map Matcher
→ Predictor
→ Display Location
```

O Navigation Core não deve depender de `CLLocation`.

O app iOS adapta `CLLocation` para o contrato comum.

---

# 5. TELEMETRIA

Criar TelemetryService central.

Nenhum componente envia eventos diretamente para backend.

Fluxo:

```text
App
→ TelemetryService
→ local queue
→ batch
→ backend
```

Suportar offline.

---

# 5.1 EVENT ENVELOPE

Todo evento:

```json
{
  "event_id": "...",
  "event_name": "...",
  "occurred_at": "...",
  "user_id": "...",
  "session_id": "...",
  "trip_id": "...",
  "app_version": "...",
  "build_number": "...",
  "platform": "ios",
  "os_version": "...",
  "device_model": "...",
  "properties": {}
}
```

---

# 5.2 EVENTOS ESSENCIAIS

## App

```text
app_open
app_background
app_foreground
app_crash_recovered
auth_login_success
auth_login_failure
```

## Search

```text
search_started
search_results_received
search_result_selected
search_no_result
search_address_exact
search_address_approximate
```

## Route

```text
route_requested
route_created
route_failed
navigation_started
navigation_finished
navigation_cancelled
reroute_started
reroute_completed
reroute_failed
```

## GPS

```text
gps_update_received
gps_accuracy_degraded
gps_delay_detected
gps_lost
gps_recovered
map_match_changed
map_match_low_confidence
```

## Camera / Marker

```text
marker_lag_threshold_exceeded
camera_lag_threshold_exceeded
marker_outside_safe_zone
camera_recentered
```

## Radar

```text
radar_candidate
radar_alert_eligible
radar_alert_presented
radar_alert_suppressed_wrong_direction
radar_alert_suppressed_parallel_road
radar_alert_late
radar_alert_missed
```

## UI / Errors

```text
screen_view
user_action
ui_error
api_error
navigation_error
unexpected_state
```

Não registrar cada toque indiscriminadamente.
Registrar ações relevantes para diagnóstico.

---

# 5.3 LOCATION TELEMETRY

Não enviar cada fix bruto para servidor indefinidamente.

Criar níveis:

```text
OFF
DIAGNOSTIC_SUMMARY
ACTIVE_TRIP_DEBUG
```

Default beta:

```text
DIAGNOSTIC_SUMMARY
```

Enviar métricas agregadas:

```text
gps accuracy p50/p95
gps age p50/p95
marker lag p50/p95
camera lag p50/p95
map-match confidence
GPS loss count
reroute count
radar alerts
missed/late alerts
```

`ACTIVE_TRIP_DEBUG` pode armazenar sequência detalhada somente quando:

- usuário consentiu;
- beta/debug mode está ativo;
- retention curta;
- necessário para diagnóstico.

---

# 6. TRIP SESSION

Criar conceito:

```text
TripSession
```

Campos:

```text
trip_id
user_id
started_at
ended_at
app_version
device_model
os_version
route_id
origin_resolution_quality
destination_resolution_quality
distance
duration
city_mode_seconds
road_mode_seconds
gps_loss_count
reroute_count
radar_candidate_count
radar_alert_count
late_alert_count
missed_alert_count
crash_count
```

---

# 7. ERROR MODEL

Criar IDs de erro rastreáveis.

Exemplo:

```text
REL-NAV-001
REL-GPS-002
REL-SEARCH-003
REL-RADAR-004
REL-API-005
```

Erro enviado:

```json
{
  "error_code": "REL-GPS-002",
  "message": "GPS update stale",
  "context": {},
  "trip_id": "...",
  "session_id": "..."
}
```

Stack trace somente quando seguro.

---

# 8. CRASH + PERFORMANCE

Usar primeiro recursos nativos disponíveis.

Integrar:

```text
MetricKit
OSLog / Logger
```

Criar camada:

```text
DiagnosticsService
```

Preparar adapter para ferramenta externa futura, sem acoplar domínio a um fornecedor.

Medir:

```text
launch time
hangs
crashes
memory pressure
navigation frame/render health
API latency
battery impact indicators
```

---

# 9. FEATURE FLAGS

Criar:

```text
FeatureFlagService
```

Flags mínimas:

```text
ios_native_location
precision_engine_v2
adaptive_camera
road_mode
radar_voice
route_progress
debug_trip_logging
new_map_icons
```

Requisitos:

- defaults locais seguros;
- remote override opcional;
- cache local;
- rollback rápido.

Se backend remote config não existir:
implementar interface + defaults locais e documentar backend futuro.

---

# 10. APP VERSION / BUILD TRACEABILITY

Toda sessão deve registrar:

```text
app_version
build_number
git_commit
environment
```

Ambientes:

```text
development
beta
production
```

Nunca misturar logs sem ambiente.

---

# 11. ADMIN — BETA OBSERVABILITY

Adicionar uma seção no admin existente:

```text
iOS Beta
```

Telas mínimas:

## Overview

```text
active beta users
sessions
trips
crashes
navigation failures
GPS degraded sessions
late radar alerts
missed radar alerts
```

## Users

Mostrar:

```text
internal user_id
account state
app version
last session
device model
OS version
number of trips
recent errors
```

Evitar expor email desnecessariamente.

## Trips

Mostrar:

```text
trip_id
user
version
duration
distance
GPS health
map match health
reroutes
radar stats
errors
```

## Errors

Agrupar:

```text
error_code
count
affected users
affected app versions
first seen
last seen
```

## Releases

Comparar:

```text
build X
build Y
```

por:

```text
crash rate
navigation errors
GPS lag
marker lag
camera lag
late/missed radar alerts
```

---

# 12. SECURITY

Obrigatório:

- TLS only;
- auth token in Keychain;
- no token in UserDefaults;
- no secrets in JS;
- no private backend credentials in iOS bundle;
- server validates user/session;
- telemetry endpoint authenticated;
- rate limiting;
- payload size limits;
- reject malformed telemetry;
- scrub secrets from logs.

---

# 13. DATA RETENTION

Definir no projeto, sem deixar infinito.

Sugestão para beta:

```text
raw debug trip data: short retention
aggregated diagnostics: longer retention
crash/error metadata: longer retention
```

Não hardcode política legal final sem revisão.

Documentar configuração.

---

# 14. MAPA E ÍCONES

NÃO fazer redesign nesta missão.

Mas preparar arquitetura para:

```text
MapRendererProtocol
```

Implementação V1 pode manter renderer atual.

Criar documento:

```text
IOS_NATIVE_MAP_MIGRATION.md
```

Analisar:

- renderer atual;
- MapLibre Native;
- current icon system;
- migration cost;
- what can be reused;
- what must be redesigned.

Não migrar ainda.

---

# 15. TESTES

## Unit

```text
auth state
location adapter
telemetry envelope
offline queue
trip session
feature flags
error model
```

## Integration

```text
Core Location mock
native bridge
navigation core
telemetry batching
auth + API
```

## Simulated Drive

Reutilizar fixtures do Drive Simulator.

Rodar:

```text
urban
highway
gps-delay
gps-loss
parallel-road
wrong-direction
```

---

# 16. iOS SIMULATOR VS REAL DEVICE

Documentar claramente:

```text
SIMULATOR_VALIDATED
REAL_DEVICE_REQUIRED
```

Core Location, background behavior, heading, battery and real GPS quality devem ser considerados `REAL_DEVICE_REQUIRED`.

---

# 17. GATES

## BUILD GATE

```text
iOS project builds
app launches
auth gate renders
```

## AUTH GATE

```text
unauthenticated cannot enter map
authenticated session persists securely
```

## LOCATION GATE

```text
native location reaches Navigation Core
web geolocation not used inside iOS beta path
```

## TELEMETRY GATE

```text
session/trip/errors reach backend
offline queue works
no secret leakage
```

## NAVIGATION GATE

```text
radar P0 preserved
wrong-direction preserved
parallel-road preserved
gps-loss recovery preserved
```

## OBSERVABILITY GATE

```text
admin can trace:
user → session → trip → error
```

---

# 18. ARTEFATOS

Criar:

```text
artifacts/ios-beta-foundation-v1/
  BASELINE.md
  ARCHITECTURE.md
  AUTH_MODEL.md
  LOCATION_BRIDGE.md
  TELEMETRY_SCHEMA.md
  TRIP_SESSION_MODEL.md
  ERROR_CATALOG.md
  FEATURE_FLAGS.md
  SECURITY_REVIEW.md
  PRIVACY_DATA_MAP.md
  ADMIN_OBSERVABILITY.md
  IOS_NATIVE_MAP_MIGRATION.md
  TEST_RESULTS.json
  REPORT.md
```

---

# 19. PRIVACY DATA MAP

`PRIVACY_DATA_MAP.md` deve listar para cada dado:

```text
data type
why collected
when collected
where stored
retention class
user-linked?
precise location?
third-party shared?
```

Obrigatório incluir:

```text
account identifier
precise location during active navigation
search queries
route/trip information
product interaction
crash data
performance data
device/app metadata
```

---

# 20. ESTADO FINAL

Somente:

```text
IOS_BETA_FOUNDATION_READY_FOR_DEVICE_TEST
```

ou:

```text
IOS_BETA_FOUNDATION_PARTIAL
```

ou:

```text
IOS_BETA_FOUNDATION_BLOCKED
```

---

# 21. REPORT FINAL

Responder:

1. app iOS foi criado?
2. build compila?
3. auth é obrigatório?
4. sessão persiste no Keychain?
5. Core Location está integrado?
6. localização nativa chega no Navigation Core?
7. navigator.geolocation foi evitado no caminho iOS?
8. telemetry funciona offline?
9. trips possuem trip_id?
10. user/session/trip/error são correlacionáveis?
11. radar P0 foi preservado?
12. wrong-direction passou?
13. parallel-road passou?
14. GPS-loss recovery passou?
15. feature flags existem?
16. admin consegue rastrear bugs por build/device/trip?
17. há secrets no bundle/log?
18. Privacy Data Map foi gerado?
19. o que ainda exige configuração externa?
20. o que exige iPhone físico?
21. estado final?

---

# 22. NÃO FAZER AINDA

Não:

- publicar App Store;
- criar assinatura;
- rewards;
- community;
- CarPlay;
- Android Auto;
- migrar mapa inteiro para native;
- trocar banco inteiro;
- refatorar Official Radar Finder;
- adicionar grandes features.

Primeiro obter um beta observável e testável.

---

# PRINCÍPIO FINAL

O beta deve permitir responder com evidência:

```text
qual usuário?
qual build?
qual dispositivo?
qual viagem?
qual estado de GPS?
qual atraso?
qual rota?
qual alerta?
qual erro?
quando aconteceu?
```

Sem isso, um bug relatado como “o carro ficou atrasado” continua sendo opinião.

Com isso, vira um incidente reproduzível.
