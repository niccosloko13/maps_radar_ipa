# RELAS Navigation V4 — Referências GitHub e decisões técnicas (28/10/2026)

## Repositórios consultados

| Fonte | Repositório | Padrão útil | Decisão RELAS |
|---|---|---|---|
| Valhalla | https://github.com/valhalla/valhalla | Route guidance, directed edges, map matching, maneuver metadata | Avaliar contratos já expostos pelo backend; não substituir o roteador nesta sprint |
| GraphHopper | https://github.com/graphhopper/graphhopper | Snap-to-road, turn restrictions, path details, GNSS trace matching | Referência para map matching em vias paralelas e sentido correto, com teste de regressão |
| MapLibre GL JS | https://github.com/maplibre/maplibre-gl-js | Style specification, symbol placement, road layers, route rendering | **Reutilizar motor existente**; criar estilo controlado e hierarquia por zoom/contexto |
| Organic Maps | https://github.com/organicmaps/organicmaps | Navegação turn-by-turn, comportamento mobile, rotas alternativas | Referência UX e testes de chegada, sem copiar interface/ativos |
| GraphHopper map matching | https://github.com/graphhopper/graphhopper/tree/master/map-matching | HMM / Viterbi, conectividade de vias | Estudo futuro: o matcher atual conhece sobretudo a geometria da rota, não a malha completa |

Licenças: validar individualmente antes de incorporar código/ativos; **referência arquitetural não é autorização para copiar símbolos, estilos ou código**.

## Fatos conferidos no próprio RELAS

- `app/app.js`: MapLibre com estilo remoto OpenFreeMap Liberty; ponto escolhido usa coordenadas para construir rota.
- `app/navigation/road-runtime.js`: segue progresso projetado e aplica câmera adaptativa; chegada ainda depende de validação externa do geocoder e de waypoint de acesso.
- `app/icons/`: família SVG de radar, semáforo, SAU, PRF etc.; não há hierarquia visual suficiente ao dirigir.
- `scripts/drive-simulator/simulator.cjs`: **LIMITAÇÃO IMPORTANTE**: fixture `rui-barbosa.json` é linha sintética com apenas 2 pontos; replay interpola 40 posições; `routeCompleted:true` é constante, não uma medição de chegada; contadores de alertas também são placeholders. Não chamar isto de teste completo da navegação nem de “trajeto real”. Testes do core passam, mas não provam navegação do app visual ou chegada a um imóvel.
- `tests/navigation-arrival.test.js`: cobre o novo núcleo de confirmação conservadora; ainda falta verificação do contrato real de precisão do geocoder.

## Prioridades práticas

### P0 — Endereço e chegada
1. Identificar na API de geocoding a fonte real do número, posição de imóvel/entrada e nível de precisão.
2. Criar destination contract incluindo geocode quality, routeable waypoint, ponto solicitado, lado da via quando disponível, diferença em metros e evidência; jamais inferir `exact` de rua apenas.
3. A chegada exata só deve ser anunciada quando houver dados e posição consistente com acesso real. Sem isso: “Você está próximo do destino aproximado”.
4. Testar com endereços reais verificados, ambas as direções, acesso separado e GPS ruidoso; comparar chegada com posição de entrada informada.

### P1 — Map-first, radar-first
1. Aumentar legibilidade de manobra, número da rodovia, pista/sentido, distância, ETA e marcador.
2. Priorizar câmera/radar elegível na rota e sentido; sem colocar ícones genéricos à frente de P0.
3. Reduzir poluição do mapa via filtros por zoom, contexto e colisão. Para símbolos críticos, planejar `icon-allow-overlap` com parcimônia.
4. Estilo vetorial próprio sobre MapLibre, sem clonar aparência/ícones do Waze. Conferir licencia de tiles e fontes.

### P2 — Simulação de verdade
1. Carregar rotas reais arquivadas com distância cumulativa; amostrar por tempo/velocidade em vez de índice de vértice.
2. Injetar fixes no mesmo pipeline e avançar o runtime/UI via Playwright.
3. Medir estado de chegada, falso positivo de radar, regressão wrong-direction, camera/marker p50/p95 e resultado de teste browser.
4. Exigir relatórios **measured vs simulated vs placeholder**; remover contadores fictícios para status de aprovação.

## Gates antes do preview público
- Node syntax + unit tests executados (não apenas escritos).
- Playwright screenshots 390x844, 430x932 e desktop em parada, cidade, rodovia, radar e chegada.
- Nenhuma falsa confirmação de imóvel sem dado exato.
- Radar P0 e filtros por sentido preservados.
- Preview em branch, não deploy sobre produção.

## Fontes primárias
- https://github.com/valhalla/valhalla
- https://github.com/graphhopper/graphhopper
- https://github.com/graphhopper/graphhopper/tree/master/map-matching
- https://github.com/maplibre/maplibre-gl-js
- https://github.com/organicmaps/organicmaps
