Validação de textos da V1.2 - 18/09/2026

A alteração desta tarefa afeta apenas literais e apresentação textual. Nenhuma regra financeira, temporal, de clientes, ingestão, mapping ou comparação foi modificada.

Diagnóstico real

- Foram examinados os 70 JSONs de data/analysis_history, o GET /api/analysis/history e o DOM em http://localhost:5173/history, sem interceptar a API.
- N&atilde;o dispon&iacute;vel não estava armazenado nesses JSONs. Nas entradas do Excel 2017 a 2020.xlsx com status ausente, status e status_negocio são null no índice e na resposta HTTP.
- Exemplo verificado: analysis_20260918_153821511932_cb0904aab1514945a680def8c9729d7b. Qualidade armazenada/API: critica. Período: 2017-01 a 2020-12.
- History.tsx fornece o fallback textual. A correção anterior desse fallback para Não disponível já estava presente no estado recebido. O helper de compatibilidade no service também já existia.
- Nesta execução, a entidade literal reportada não foi reproduzida no navegador com o código atual. Não foi comprovado que cache ou bundle antigo explicavam a sessão de homologação anterior.
- Foi reproduzido Hist?rico na sidebar. Também foram localizados literais defeituosos nas mensagens de erro da API, conexão do service, conversão do ETL e mensagem de datas inválidas. Esses defeitos já existiam nos arquivos-fonte antes da serialização.
- Snapshots antigos contêm per?odo. Eles e o período antigo 1017-02 a 2048-04 foram preservados.

Solução

- Correção dos literais identificados, gravados em UTF-8. Aproximadamente 40 linhas de texto ajustadas, sem mudanças de cálculo.
- Reutilizado normalizeHistoricalText em frontend/src/services/dataAgentService.ts: função de 3 linhas, tabela de entidades conhecidas e aplicação apenas aos campos textuais de histórico, aproximadamente 30 linhas existentes no total. Acrescentado um comentário explicando o legado.
- Uma passagem, apenas na leitura do service. Não há decodificação no backend ou no componente. Entidades duplamente escapadas não são decodificadas repetidamente; per?odo permanece inalterado.
- History.tsx apresenta os labels Crítica, Atenção e Saudável para os respectivos códigos, mantendo valores/arquivos originais.
- Nenhuma dependência adicionada; nenhum uso de dangerouslySetInnerHTML.
- Persistência existente mantida: encoding="utf-8" e ensure_ascii=False.

Provas

- JSON real e resposta HTTP: status null; quality.classificacao_qualidade = critica. A API preserva os códigos de dados.
- DOM e captura real: Status: Não disponível · Qualidade: Crítica.
- Captura: validacao-encoding-historico.png.
- Verificação visual em desktop e mobile; varredura do DOM em Visão geral, Desempenho, Produtos, Clientes, Oportunidades, Dados, Histórico, comparação e mapping pendente real. Nenhuma palavra corrompida nos textos atuais examinados.
- Uma análise nova foi executada pela API em pasta temporária. Arquivo de entrada com Análise, Período, Métricas, Qualidade, Histórico, Comparação, Crítica, Atenção, Evolução, Participação, Concentração e Não disponível: Unicode preservado no índice, registro e HTTP. Insight O período persistido corretamente no detalhe.
- Snapshot legado sintético com entidades: leitura preserva bytes, service apresenta Unicode no DOM. Markup <script> permanece texto, sem execução.
- SHA-256 dos 70 arquivos históricos reais permaneceu idêntico.

Arquivos de aplicação ajustados nesta tarefa

- api/analysis.py e api/app.py: somente mensagens/docstring.
- src/etl/cleaner.py: somente mensagens do log de transformação.
- src/analytics/temporal.py: somente uma mensagem de erro.
- frontend/src/services/dataAgentService.ts: duas mensagens de conexão e comentário do helper existente.
- frontend/src/components/layout/Sidebar.tsx: label Histórico.
- frontend/src/components/charts/PerformanceChart.tsx: texto Não disponível.
- frontend/src/components/common/SemanticMappingPanel.tsx: separador textual da origem da sugestão.
- frontend/src/pages/History.tsx: labels de apresentação.

Testes

- Novo: api/test_text_encoding.py, 3 testes (análise nova e persistência, legado imutável, erros Unicode).
- Ampliado: frontend/tests/history-page.spec.ts, 9 casos adicionais (entidades, Unicode, nome normal, texto perdido, dupla codificação e XSS).
- Ampliado: frontend/tests/api-integration.spec.ts, teste sem mocks de JSON real -> HTTP -> DOM.
- Python compile: passou.
- src: 187 aprovados.
- api: 20 aprovados.
- TypeScript e Vite build: passaram.
- Playwright principal: 72 aprovados.
- Playwright uploads reais, incluindo Excel, CSV e multi-file: 5 aprovados em servidores isolados.
- Total: 284 testes aprovados. Sem regressão observada.
- Configurações temporárias de teste removidas. Servidores preexistentes do usuário preservados.
- git diff --check: passou; apenas avisos de conversão LF/CRLF do Git.
- Worktree permanece com alterações anteriores de V1.2 e as correções descritas. Nenhum commit, push, tag ou troca de branch.

Limite deliberado: textos antigos com caractere perdido não são reconstruídos automaticamente. O helper trata entidades conhecidas, não tenta adivinhar mojibake ou dados originais.
