# RELAS — SIDELOADLY iOS PIPELINE V1
## WINDOWS + GITHUB ACTIONS macOS + UNSIGNED DEVICE BUILD + IPA + SIDELOADLY

# OBJETIVO

Criar um fluxo de custo zero para:

```text
Codex / Windows
→ GitHub
→ GitHub Actions macOS
→ build iOS arm64
→ gerar IPA não assinado / preparado para sideload
→ baixar no Windows
→ Sideloadly
→ Apple ID gratuita
→ iPhone
```

A missão NÃO deve exigir Apple Developer Program pago.

---

# PRINCÍPIO

A compilação e a assinatura serão separadas.

## Etapa A — CI

GitHub Actions/macOS:

```text
compila o app para iPhone
gera RELAS-unsigned.ipa
publica artifact
```

## Etapa B — Windows

Sideloadly:

```text
abre RELAS-unsigned.ipa
assina com Apple ID gratuita
instala no iPhone
```

Não tentar fazer Personal Team no CI.

---

# REGRAS

- custo alvo: R$ 0;
- não contratar Apple Developer;
- não usar certificado enterprise de terceiros;
- não armazenar Apple ID;
- não armazenar senha;
- não armazenar códigos 2FA;
- não incluir provisioning profile falso;
- não publicar App Store;
- não usar TestFlight;
- não quebrar web/PWA;
- não fazer push automaticamente;
- não fazer deploy público.

---

# 0. CHECKPOINT

Antes de alterar:

```text
git branch
git rev-parse HEAD
git status --short
```

Criar:

```text
artifacts/sideloadly-ios-v1/BASELINE.md
```

Registrar:

```text
apps/ios path
project/workspace
scheme
target
bundle identifier
deployment target
Xcode requirements
current build scripts
```

---

# 1. VALIDAR O PROJETO iOS

Garantir que exista um target real de device:

```text
iphoneos
arm64
```

Não confundir com:

```text
iphonesimulator
```

O IPA final precisa conter binário para device físico.

---

# 2. BUILD DEVICE SEM CODE SIGNING

Criar script:

```text
scripts/ios/build-sideload-device.sh
```

Usar `xcodebuild` com:

```text
-sdk iphoneos
-configuration Debug ou Beta
CODE_SIGNING_ALLOWED=NO
CODE_SIGNING_REQUIRED=NO
```

Usar DerivedData isolado:

```text
build/ios-sideload/
```

Resultado esperado:

```text
RELAS.app
```

Validar:

```text
RELAS.app/RELAS
```

e confirmar arquitetura:

```text
arm64
```

Falhar se o binário for apenas Simulator.

---

# 3. SANITY CHECK DO .APP

Antes de empacotar:

validar:

```text
Info.plist existe
CFBundleIdentifier existe
CFBundleExecutable existe
CFBundleVersion existe
CFBundleShortVersionString existe
MinimumOSVersion coerente
```

Verificar frameworks embarcados.

Não permitir dependência quebrada.

Se houver Swift frameworks:
garantir embedding correto.

---

# 4. ENTITLEMENTS

Como o Sideloadly fará a assinatura final:

não presumir que todos os entitlements do build original serão permitidos por Apple ID gratuita.

Criar relatório:

```text
SIDELOAD_ENTITLEMENTS.md
```

Classificar:

```text
REQUIRED
OPTIONAL
NOT_COMPATIBLE_WITH_FREE_SIDELOAD
UNKNOWN
```

Avaliar especialmente:

```text
location
background modes
push notifications
associated domains
keychain groups
app groups
iCloud
Sign in with Apple
CarPlay
```

Não remover requisito essencial silenciosamente.

Se uma capability impedir o sideload gratuito:

marcar claramente.

---

# 5. CRIAR IPA PARA SIDELOADLY

Criar:

```text
scripts/ios/package-sideload-ipa.sh
```

Estrutura obrigatória:

```text
Payload/
  RELAS.app/
```

Depois:

```bash
zip -r RELAS-unsigned.ipa Payload
```

Não apenas renomear `.app` ou outro ZIP.

Validar o conteúdo depois de gerar.

---

# 6. PREFLIGHT

Criar script:

```text
scripts/ios/validate-sideload-ipa.sh
```

Checar:

```text
IPA abre como ZIP
Payload/ existe
.app existe
Info.plist existe
executável existe
executável é arm64/device
frameworks existem
sem caminhos absolutos locais
sem secrets
```

Gerar:

```text
artifacts/sideloadly-ios-v1/IPA_PREFLIGHT.json
```

---

# 7. GITHUB ACTIONS

Criar/atualizar:

```text
.github/workflows/ios-sideload-build.yml
```

Runner:

```text
macos-latest
```

Trigger:

```text
workflow_dispatch
```

Não disparar automaticamente em toda alteração.

---

# 7.1 JOB

Etapas:

```text
checkout
detect Xcode
show Xcode version
resolve packages
build iphoneos arm64 no-sign
run iOS unit tests when possible
package RELAS-unsigned.ipa
validate IPA
upload artifact
```

Artifact:

```text
RELAS-sideload-build-<build_number>
```

Conteúdo:

```text
RELAS-unsigned.ipa
build-info.json
IPA_PREFLIGHT.json
build.log
```

---

# 7.2 CONCURRENCY

Adicionar:

```yaml
concurrency:
  group: relas-ios-sideload
  cancel-in-progress: true
```

Evitar desperdício de runner.

---

# 8. BUILD INFO

Gerar:

```text
build-info.json
```

Com:

```json
{
  "app_version": "",
  "build_number": "",
  "git_commit": "",
  "xcode_version": "",
  "sdk": "iphoneos",
  "architecture": "arm64",
  "signing": "unsigned_for_sideloadly"
}
```

---

# 9. BUNDLE IDENTIFIER

Usar bundle identifier próprio do RELAS.

Não reutilizar bundle ID de app da App Store.

Documentar:

```text
original_bundle_id
expected_sideload_bundle_id
```

Se Sideloadly alterar o bundle ID durante a assinatura:
o app precisa continuar funcional.

Não depender do bundle ID para lógica de negócio.

---

# 10. BACKEND / AUTH

O sideload não pode quebrar:

```text
API
login
telemetry
Core Location bridge
```

Não hardcode localhost.

Configurar endpoint beta por environment.

Exemplo:

```text
RELAS_API_ENV=beta
```

Nunca colocar backend secret no app.

---

# 11. CORE LOCATION

Garantir que a versão sideload continue contendo:

```text
NSLocationWhenInUseUsageDescription
```

e demais permissões realmente necessárias.

Background location somente se já aprovado na arquitetura beta.

Não pedir permissões extras só para facilitar teste.

---

# 12. SIDELOADLY WINDOWS GUIDE

Criar:

```text
artifacts/sideloadly-ios-v1/SIDELOADLY_WINDOWS_GUIDE.md
```

Instruções:

## No Windows

1. baixar Sideloadly do site oficial;
2. instalar componentes Apple exigidos pela ferramenta;
3. conectar iPhone via USB;
4. tocar `Confiar` no iPhone;
5. abrir Sideloadly;
6. arrastar:

```text
RELAS-unsigned.ipa
```

7. informar Apple ID gratuita no próprio Sideloadly;
8. iniciar sideload;
9. concluir trust/developer mode no iPhone se solicitado.

Não pedir Apple ID dentro do RELAS/Codex/GitHub.

---

# 13. PRIMEIRO TESTE NO IPHONE

Criar checklist:

```text
app abre
login abre
Core Location permission
posição aparece
heading funciona
speed funciona
marker move
camera acompanha
search funciona
route funciona
CITY_MODE
ROAD_MODE
radar P0
wrong-direction
parallel-road
gps loss/recovery
telemetry
```

---

# 14. DEVICE DIAGNOSTIC

Criar tela DEV:

```text
Settings → Diagnostics
```

Mostrar:

```text
app version
build number
device model
iOS version
location authorization
accuracy
raw speed
heading
gps age
marker lag
camera lag
trip id
session id
API health
telemetry queue
```

Sem secrets.

---

# 15. BETA BUG REPORT

Adicionar ação DEV:

```text
Reportar problema
```

Gerar pacote diagnóstico leve:

```text
timestamp
build
session_id
trip_id
GPS summary
navigation state
last error codes
```

Não exportar tokens/senha.

---

# 16. VALIDAÇÃO DE SIDELOAD COMPATIBILITY

Antes de declarar sucesso:

confirmar:

```text
device arm64 build
IPA structure valid
bundle metadata valid
no signing embedded requirement that blocks repacking
no missing dynamic framework
no forbidden absolute path
```

O CI não precisa assinar.

---

# 17. TESTES

Executar no CI:

```text
portable Navigation Core tests
iOS unit tests
bridge tests
telemetry tests
location adapter tests
IPA preflight
```

Não rodar browser Playwright nessa missão.

---

# 18. ANTI-LOOP

Máximo:

```text
1 primeira execução
2 correções técnicas
1 execução final
```

Se o GitHub CI não estiver autorizado/conectado:

não ficar tentando infinitamente.

Marcar:

```text
CI_NOT_EXECUTED
```

mas finalizar configuração.

---

# 19. ESTADOS FINAIS

Somente:

```text
SIDELOADLY_IPA_READY
```

Significa:

```text
CI executado
device build passou
IPA criado
preflight passou
artifact pronto para baixar
```

ou:

```text
SIDELOADLY_PIPELINE_READY_NOT_EXECUTED
```

Significa:

```text
configuração completa
CI ainda não executado
```

ou:

```text
SIDELOADLY_BLOCKED
```

Com motivo exato.

---

# 20. ARTEFATOS

Criar:

```text
artifacts/sideloadly-ios-v1/
  BASELINE.md
  BUILD_REPORT.md
  SIDELOAD_ENTITLEMENTS.md
  IPA_PREFLIGHT.json
  SIDELOADLY_WINDOWS_GUIDE.md
  IPHONE_FIRST_TEST.md
  KNOWN_LIMITATIONS.md
  REPORT.md
```

Código:

```text
scripts/ios/build-sideload-device.sh
scripts/ios/package-sideload-ipa.sh
scripts/ios/validate-sideload-ipa.sh
.github/workflows/ios-sideload-build.yml
```

---

# 21. REPORT FINAL

Responder:

1. device arm64 build está configurado?
2. CI macOS está configurado?
3. CI foi realmente executado?
4. RELAS.app foi gerado?
5. binário é arm64?
6. RELAS-unsigned.ipa foi gerado?
7. IPA passou no preflight?
8. existem capabilities incompatíveis com Apple ID gratuita?
9. bundle ID pode ser reescrito sem quebrar o app?
10. Core Location permanece funcional?
11. backend beta permanece funcional?
12. telemetry permanece funcional?
13. qual artifact devo baixar no GitHub?
14. qual arquivo devo arrastar no Sideloadly?
15. o que faço no iPhone depois?
16. estado final?

---

# PRINCÍPIO FINAL

O GitHub/macOS deve apenas:

```text
COMPILAR
+ EMPACOTAR
```

O Windows/Sideloadly deve:

```text
ASSINAR
+ INSTALAR
```

Não misturar as duas responsabilidades.

Não pagar Apple Developer enquanto o objetivo for somente testar o RELAS no próprio iPhone.
