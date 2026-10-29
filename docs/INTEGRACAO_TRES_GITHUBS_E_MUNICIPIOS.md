# RELAS — integração dos três GitHubs e radares municipais

Status: implementação de coletores **apenas para staging**, sem alteração do Neon. Data: 2026-10-28.

## Executar coleta segura
```bash
python tools/stage_external_sources.py --output artifacts/staging/external-sp.json
# opcional: uma única página (até 100 pontos) da API pública para verificar contrato
python tools/stage_external_sources.py --bunda-sample --output artifacts/staging/external-sp.json
# sem rede, para validar arquivos fornecidos:
python tools/stage_external_sources.py --offline --pardal-file dados/sp-radares.csv --freeflow-file dados/porticos.csv --output artifacts/staging/external-sp.json
```
Nunca faça upload de dados sem validação e licença apropriada. O script não abre o Neon nem substitui a tabela de radares.

| Projeto | O que aproveitamos agora | Restrições |
|---|---|---|
| [Murkiriel/pardal](https://github.com/Murkiriel/pardal) | CSV `estados/SP/radares.csv`: posição, tipo, limite e heading quando presentes; tudo candidato | ODbL; `active=1` não comprova operação oficial atual |
| [Challado/Bunda-de-Urso](https://github.com/Challado/Bunda-de-Urso) | Endpoint API `/api/v1/radares/busca` amostrado com `--bunda-sample`, não incorporação direta | Inspecionar resposta, fonte, licenças e autorização de redistribuição |
| [Sem-Parar/SEM-PARAR-FREE-FLOW](https://github.com/Sem-Parar/SEM-PARAR-FREE-FLOW) | CSV `dados/porticos-free-flow.csv`, filtrado para SP | CC BY 4.0 com atribuição; quilômetros não são coordenadas e não geram pin automático |

## Três municípios: validação de radares
1. **São Bernardo do Campo**: https://saobernardo.sp.gov.br/radares — documentos oficiais 2026 para fixos, semafóricos, lombadas eletrônicas, detectores de altura e faixas de ônibus. Extrair endereços, sentidos e velocidade, registrar URL do documento e data de referência.
2. **Santo André**: https://portais.santoandre.sp.gov.br/observatoriomob/fiscalizacao-eletronica-de-transito-radares/ — usar inventário SIGA / fiscalização eletrônica, observando data de publicação.
3. **São Paulo**: CET-SP fiscalização eletrônica e GeoSampa WFS para semáforos. Semáforo geolocalizado não fornece sua cor ao vivo.

A classificação por município do CSV Pardal exige geocodificação por fronteiras oficiais IBGE; caixas geográficas do protótipo indicam **candidatos** e sobrepõem municípios. Não se pode concluir que um radar pertence ao município só pela caixa.

## Próximo estágio antes da integração no mapa
- Executar inventário read-only `tools/radar_quality_report.py` contra a configuração autorizada.
- Normalizar nomes/identificadores oficiais, separar os tipos e verificar coordenadas, pista, sentido, velocidades, status e datas.
- Criar diff com registros atuais, documentar duplicações e divergências; nunca substituir fonte oficial por GitHub.
- Rever licenças dos dados derivados, registrar atribuição. Backup, revisão humana, testes e rollback antes de qualquer merge em produção.
- Não exibir radares móveis sem observação recente e corroboração: ponto cadastral é diferente de fiscalização temporária ativa.

**Esta tarefa não significa que as bases já estejam alimentando o mapa em tempo real.** É uma camada de aquisição auditável preparada para validação e evolução.
