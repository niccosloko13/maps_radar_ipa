# RELAS — FREE iOS BUILD PIPELINE V1
## WINDOWS + CODEX + GITHUB + MACOS CI + ZERO-COST FIRST

# OBJETIVO

Preparar o RELAS iOS para ser desenvolvido no Windows com Codex e compilado em macOS CI, com prioridade absoluta para custo zero.

A missão deve:

1. preparar o projeto iOS para CI;
2. preparar repositório para GitHub;
3. configurar pipeline macOS;
4. gerar build iOS sem depender de Mac local;
5. tentar gerar artefato instalável quando tecnicamente possível;
6. detectar claramente quando assinatura Apple impedir instalação;
7. NÃO exigir plano Apple Developer pago;
8. NÃO exigir serviço pago;
9. NÃO inventar certificados/provisioning profiles;
10. NÃO publicar na App Store.

---

# PRINCÍPIO

O objetivo é:

```text
Windows + Codex
      ↓
GitHub
      ↓
macOS CI
      ↓
Xcode build/archive
      ↓
.app / archive / ipa se possível
```

Se assinatura gratuita Apple não puder ser automatizada em CI:

```text
BUILD_OK
SIGNING_BLOCKED_PERSONAL_TEAM
```

Não mascarar esse bloqueio.

---

# REGRAS

- custo esperado: R$ 0;
- não contratar Apple Developer Program;
- não contratar Mac cloud pago;
- não adicionar cartão;
- não publicar App Store;
- não fazer TestFlight;
- não fazer deploy de produção;
- não expor Apple ID/senha;
- não guardar senha em GitHub;
- não guardar token/certificado no repositório;
- não inventar provisioning profile;
- não modificar Navigation Core sem necessidade.

---

# 0. BASELINE

Registrar:

```text
OS local
branch
HEAD
git status
estrutura atual apps/ios
Xcode project/workspace existente?
bundle identifier
targets
schemes
build configurations
```

Criar:

```text
artifacts/free-ios-build-v1/BASELINE.md
```

---

# 1. PROJETO iOS CI-READY

Garantir que:

```text
apps/ios/
```

possa ser compilado de forma não interativa.

Verificar:

- project/workspace;
- target;
- scheme compartilhado;
- Info.plist;
- entitlements;
- bundle identifier;
- deployment target;
- version;
- build number.

Criar scheme compartilhado para CI se necessário.

Não alterar arquitetura do app sem necessidade.

---

# 2. BUILD SEM ASSINATURA

Primeiro provar que o código compila.

Executar em macOS CI equivalente a:

```bash
xcodebuild \
  -project <project>.xcodeproj \
  -scheme <scheme> \
  -configuration Debug \
  -sdk iphonesimulator \
  build
```

E também validar device compilation sem assinatura quando possível:

```bash
CODE_SIGNING_ALLOWED=NO
```

Objetivo:

```text
COMPILE_OK
```

antes de discutir assinatura.

---

# 3. GITHUB

Preparar:

```text
.github/workflows/
```

Criar workflow:

```text
ios-build.yml
```

Requisitos:

- runner macOS;
- checkout;
- detectar Xcode;
- instalar dependências somente se necessárias;
- build Simulator;
- build device sem signing quando permitido;
- testes;
- upload de artifacts.

Não fazer push automaticamente.

---

# 4. ARTIFACTS DE CI

Publicar como artifacts do job:

```text
build logs
test results
.app simulator build
xcarchive se gerável
```

Se `.ipa` não puder ser exportado por assinatura:

não falhar toda a pipeline.

Marcar:

```text
IPA_NOT_AVAILABLE_SIGNING_REQUIRED
```

---

# 5. ZERO-COST CI PROVIDERS

Preparar documentação para pelo menos:

```text
GitHub Actions macOS
Codemagic
```

Mas não assumir que plano gratuito estará disponível.

Criar matriz:

```text
provider
free tier available?
macOS runner?
minutes/limits
credit card required?
supports signing?
recommended?
```

Esta tabela deve ser atualizada com documentação vigente no momento da execução.

Se não houver tier gratuito utilizável:

marcar:

```text
NO_FREE_MACOS_CI_AVAILABLE
```

Não recomendar pagar automaticamente.

---

# 6. CODEMAGIC CONFIG

Criar, se fizer sentido:

```text
codemagic.yaml
```

Workflow:

```text
relas-ios-free-build
```

Etapas:

- select Xcode;
- resolve packages;
- build Simulator;
- run tests;
- build device without signing when possible;
- export logs/artifacts.

Não incluir credentials.

---

# 7. GITHUB ACTIONS CONFIG

Criar:

```text
.github/workflows/ios-build.yml
```

Trigger manual:

```text
workflow_dispatch
```

Opcionalmente push apenas em branch específica de iOS.

Evitar gastar minutos desnecessariamente.

Adicionar concurrency:

```text
cancel-in-progress: true
```

Adicionar cache somente se seguro e útil.

---

# 8. APPLE SIGNING — DETECÇÃO HONESTA

Criar documento:

```text
APPLE_FREE_SIGNING.md
```

Explicar separadamente:

## A. Compilar

Pode ocorrer sem certificado de distribuição.

## B. Rodar no Simulator

Não exige assinatura de device.

## C. Instalar em iPhone físico

Exige assinatura/provisioning aceito pelo aparelho.

## D. Personal Team / Apple ID gratuita

Se depender de Xcode interativo ou provisioning não automatizável em CI:

marcar:

```text
PERSONAL_TEAM_REQUIRES_XCODE_INTERACTION
```

Não pedir senha Apple em script.

Não tentar burlar mecanismos de assinatura.

---

# 9. IPA

Criar scripts:

```text
scripts/ios/build-simulator.sh
scripts/ios/build-device-nosign.sh
scripts/ios/archive.sh
scripts/ios/export-ipa.sh
```

`export-ipa.sh` deve:

1. detectar se existe signing válido;
2. se sim, tentar export;
3. se não, sair claramente:

```text
SIGNING_REQUIRED
```

Não produzir falso `.ipa` "instalável".

---

# 10. EXPORT OPTIONS

Criar templates separados, sem credenciais:

```text
config/ios/ExportOptions.example.plist
```

Não preencher:

```text
teamID
certificate
profile UUID
```

sem configuração real.

---

# 11. BUILD NUMBERS

CI deve gerar build number consistente.

Exemplo:

```text
Git commit count
ou
GitHub run number
```

Registrar:

```text
app_version
build_number
git_commit
```

no app.

---

# 12. LOGS

Cada build deve produzir:

```text
environment
Xcode version
Swift version
scheme
configuration
commit
build number
test result
signing status
artifact paths
```

Criar:

```text
artifacts/free-ios-build-v1/CI_BUILD_REPORT.md
```

---

# 13. TESTES

Executar apenas:

```text
iOS unit tests
native bridge tests
telemetry tests
location adapter tests
build smoke
```

Não reexecutar toda a suíte web repetidamente.

---

# 14. ANTI-LOOP

Máximo:

```text
1 tentativa inicial
2 correções por workflow
1 rodada final
```

Se continuar falhando:

```text
BLOCKED
```

e documentar.

---

# 15. NÃO FAZER

Não:

- comprar Apple Developer;
- pagar Codemagic;
- pagar MacStadium;
- adicionar cartão;
- criar conta paga;
- publicar App Store;
- publicar TestFlight;
- usar certificados encontrados na internet;
- usar certificados roubados/enterprise de terceiros;
- contornar assinatura Apple;
- compartilhar Apple ID/senha;
- armazenar 2FA codes.

---

# 16. RESULTADOS POSSÍVEIS

Estado final deve ser um destes:

```text
FREE_IOS_BUILD_READY
```

Build macOS funciona e artifacts são produzidos gratuitamente.

```text
FREE_IOS_BUILD_READY_SIGNING_BLOCKED
```

Compilação funciona gratuitamente, mas instalação em iPhone físico depende de assinatura/provisioning não automatizável no ambiente gratuito.

```text
FREE_IOS_BUILD_BLOCKED
```

Não há runner macOS gratuito/utilizável ou outro bloqueio técnico externo.

---

# 17. ARTEFATOS

Criar:

```text
artifacts/free-ios-build-v1/
  BASELINE.md
  FREE_CI_OPTIONS.md
  APPLE_FREE_SIGNING.md
  CI_BUILD_REPORT.md
  INSTALL_ON_IPHONE.md
  KNOWN_LIMITATIONS.md
  REPORT.md
```

Código/config:

```text
.github/workflows/ios-build.yml
codemagic.yaml
scripts/ios/build-simulator.sh
scripts/ios/build-device-nosign.sh
scripts/ios/archive.sh
scripts/ios/export-ipa.sh
config/ios/ExportOptions.example.plist
```

---

# 18. INSTALL_ON_IPHONE.md

Criar instruções separadas para:

```text
PATH A — Xcode + Apple ID gratuita
PATH B — CI build + signing disponível
PATH C — build compilado, assinatura ainda bloqueada
```

Nunca afirmar que `.ipa` sem assinatura pode ser instalado.

---

# 19. REPORT FINAL

Responder:

1. projeto iOS compila em macOS CI?
2. Simulator build passou?
3. device build sem signing passou?
4. tests passaram?
5. GitHub Actions está configurado?
6. Codemagic está configurado?
7. qual opção pode ser usada sem pagar hoje?
8. precisa cartão?
9. precisa Apple Developer pago?
10. assinatura Personal Team pode ser feita automaticamente neste fluxo?
11. `.ipa` instalável foi gerado?
12. se não, exatamente o que bloqueou?
13. artifacts foram gerados?
14. qual caminho o usuário deve seguir para instalar no próprio iPhone sem pagar?
15. estado final?

---

# PRINCÍPIO FINAL

Não transformar:

```text
"quero testar de graça"
```

em:

```text
"assine Apple Developer"
```

Primeiro provar o máximo possível com:

```text
Codex
+ GitHub
+ macOS CI gratuito
+ Apple ID gratuita
```

E mostrar com precisão qual etapa, se houver, continua dependendo de Xcode/provisioning Apple.
