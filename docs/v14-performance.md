# V1.4 — Baseline de performance (Etapa 1)

Somente diagnóstico. Nenhum cálculo, contrato, frontend ou código de produção foi alterado.
Branch: `feature/v1.4-performance`; base: `bebfa23` (`v1.3.0`).

## Método

Windows 11, Python 3.13.3, pandas 3.0.5. Usamos o DataFrame normalizado
persistido de `2017 a 2020.xlsx` e o mapping homologado (confirmação:
`coluna_4 = valor_com_desconto`). O intermediário final anterior não estava
disponível; uma preparação isolada de 68,149 s refez ETL/analytics uma única vez,
sem reler Excel. Esse tempo não entra nas medições do merge.

Dataset analítico: 11.795 linhas × 12 colunas. Valores ocupam aproximadamente
3,84 MB segundo `memory_usage(deep=True)`, que não inclui os attrs.
A representação JSON dos attrs ocupa 2,60 MB; isso não é uma medição de heap.

Três POSTs reais via FastAPI TestClient, em série, cada um partindo de uma cópia
idêntica da análise pendente. Não medimos rede externa/browser.
Cronômetros temporários com `perf_counter` envolvem as funções e delegam ao
código original. Tempos inclusivos incluem chamadas filhas; tempos exclusivos
descontam as filhas e estão separados no JSON. Não somar ambos.

A primeira medição usa um processo recém-iniciado, com imports carregados.
As seguintes usam o mesmo processo, mas relêem o intermediário original.
Não esvaziamos cache do sistema operacional: não é um benchmark de disco frio.

## Fluxo auditado

`POST /api/analysis/{id}/entities` → `AnalysisRunner.decide_entity`:

1. `get_entities`, `obter_resumo`, `obter_analise`, validação da decisão.
2. `pd.read_pickle`, `registrar_decisao`.
3. `continuar_analytics`: deepcopy do contexto, `aplicar_aliases` numa cópia,
   `mapear_colunas`, `analisar_anomalias_temporais` e preparação do frame temporal.
4. `calcular_kpis`, `analisar_meses`, `analisar_clientes`,
   `analisar_desempenho`, `analisar_crescimento`, `analisar_dimensoes`,
   `analisar_produtos`, `analisar_oportunidades`, `gerar_insights`.
5. `gerar_resumo_executivo`/insight engine, `gerar_qualidade_dados`,
   `salvar_resumo_executivo`, `salvar_analise`.
6. Conferência dos KPIs/série, JSON dumps/loads, `persistir_resumo`,
   atualização atômica de latest e serialização HTTP.

Ingestão, ETL, detector e métricas derivadas **não** executam novamente no POST.
Os três primeiros foram protegidos por verificações que falhariam se chamados;
métricas derivadas tiveram zero chamadas.

## Medições

| Execução | POST (s) | Continuação informada pela API (s) |
|---|---:|---:|
| 1 | 20,746 | 19,837 |
| 2 | 18,815 | 18,135 |
| 3 | 17,368 | 16,675 |
| Média | 18,976 | 18,216 |

Mínimo 17,368 s; máximo 20,746 s. A terceira execução foi 16,3% mais rápida
que a primeira. Há aquecimento/variação, mas três amostras não isolam sua causa.
CPU média do processo: 18,260 s, aproximadamente 96,2% do tempo decorrido.
Nenhum cache foi criado.

Tempos inclusivos médios dos módulos, percentuais sobre o POST de 18,976 s:

| Módulo | Segundos | % |
|---|---:|---:|
| Customers | 5,218 | 27,50 |
| Qualidade temporal/anomalias | 2,825 | 14,89 |
| Temporal mensal | 2,342 | 12,34 |
| Business/KPIs | 2,107 | 11,10 |
| Mapeamento inicial | 0,993 | 5,23 |
| Dimensions | 0,990 | 5,22 |
| Performance/losses | 0,953 | 5,02 |
| Products | 0,945 | 4,98 |
| Growth | 0,933 | 4,92 |
| Aliases | 0,218 | 1,15 |
| Registro da decisão | 0,205 | 1,08 |
| Gravação do resumo executivo | 0,204 | 1,07 |
| Leitura do snapshot (duas vezes) | 0,111 | 0,59 |
| Persistência de history | 0,057 | 0,30 |
| Atualização de latest | 0,049 | 0,26 |
| Render JSON HTTP | 0,024 | 0,13 |
| Leitura do intermediário | 0,022 | 0,12 |
| Preparação da revisão | 0,005 | 0,03 |
| Insights | 0,00423 | 0,022 |
| Executive summary | 0,00261 | 0,014 |
| Relatório analítico | 0,00157 | 0,008 |
| Insight engine (dentro do resumo) | 0,00035 | 0,002 |
| Relatório de qualidade | 0,00006 | <0,001 |
| Opportunities | 0,00001 | <0,001 |
| Derived metrics | 0 | 0 |

A continuação completa mede 18,214 s (95,98% do POST), incluindo os módulos
acima, cópias, preparação temporal, logs e relatórios. Não somar essa linha aos
módulos. O tempo próprio restante da continuação foi 0,476 s em média.

## Por que demora

Uma quarta execução, apenas para detalhar a causa, levou 17,329 s:

- `pandas.core.generic.deepcopy`: **219 chamadas, 15,942 s (92,0% do POST)**.
  O pandas copia os attrs ao finalizar diversas seleções, cópias e resultados
  intermediários. Os metadados de auditoria estrutural acompanham essas operações.
- Sete mapeamentos adicionais dentro dos módulos: **6,272 s inclusivos**,
  dos quais apenas 0,269 s foram tempo próprio; a maior parte também está nas
  cópias de attrs. Há oito mapeamentos contando o inicial.
- Customers custa 4,788 s nessa execução, mas somente 0,110 s de tempo próprio
  fora das chamadas de mapeamento e deepcopy medidas.
- Products, growth e performance retornam ausência de conceitos necessários
  neste dataset, mas antes disso percorrem o mapper.

Portanto o gargalo predominante é **CPU copiando metadados**, não o detector,
a aritmética dos KPIs ou o disco. Esses números aninhados não devem ser somados.

Controle adicional sem cronômetros: POST 18,230 s, analytics 17,506 s.
O resumo completo coincidiu com o instrumentado, removendo somente o timestamp
da confirmação. Isso valida equivalência funcional, não uma estimativa exata
do overhead dos cronômetros em um sistema sujeito a variação.

## Repetições e I/O

- `customers._agregar_metrica` repete dropna/groupby/sort por métrica:
  três métricas disponíveis neste arquivo.
- Temporal agrupa uma vez para valores e outra para contagem mensal.
- Em datasets com faturamento/lucro, growth e performance fazem agrupamentos
  mensais próprios. Products e dimensions também podem repetir agrupamentos
  por produto; os módulos não compartilham resultados.
- Cópias explícitas: contexto, aliases, frame temporal filtrado, dropna/copy
  em temporal; seleções/cópias em growth e performance quando aplicáveis.
- `dimensions.analisar_dimensao` tem apply por linha do resumo;
  products usa iterrows no resumo de produtos; entity_helpers percorre grupos
  por ID. Não foram identificados como gargalos neste dataset sem esses conceitos.
  A qualidade temporal percorre anos, não cada transação.
- Insights/opportunities recebem dicionários. O resumo organiza resultados,
  calcula status e seleciona conclusões; não volta aos DataFrames.
  O insight engine repete deduplicação em listas pequenas, com custo desprezível.

JSON dump/dumps/loads somaram **0,419 s (2,21%)**; `dump` inclui escrita
bufferizada, portanto não é CPU pura. São duas gravações de relatórios,
round-trip JSON na API, leitura repetida de snapshot, serializações do histórico,
latest e resposta. Parte das 231 chamadas dumps gera IDs de candidatos,
não relatórios completos.

History + latest: **0,106 s inclusivos**, dos quais 0,046 s fora dos
cronômetros JSON. Esse restante inclui disco e organização de metadados,
não apenas I/O puro. Render HTTP está incluído nas medições JSON aninhadas.

## Dependências após decisão

Com semântica, valores, datas e linhas preservados:

| Merge | Recalcular | Não depende da alteração |
|---|---|---|
| Cliente | customers; oportunidades/insights de carteira; listas/status/resumo derivados; snapshot e decisão | KPIs globais, temporal/anomalias/growth, performance por lucro, products, dimensions |
| Produto | products e dimensão produto; oportunidades/insights e resumo derivados | customers, KPIs globais, temporal/growth/performance, demais dimensões |
| Categoria/loja/colaborador | a dimensão correspondente; oportunidades/insights e resumo derivados | customers/products no código atual, KPIs globais e temporal |

`CONFIG_DIMENSOES` não inclui cliente; campos como cidade/gênero do cliente
são colunas independentes que um alias de nome não modifica.
Não há módulo separado de pagamentos nessa continuação nem agrupamento por
forma de pagamento em CONFIG_DIMENSOES.
Qualidade financeira usa o DataFrame original; a revisão apenas atualiza
os contadores de entidades. Não propomos deixar metadados/resumos desatualizados.

Essas independências foram auditadas no código atual; antes de reutilizar
resultados, a Etapa 2 deve manter testes de contratos, mapping, IDs e auditoria.
Nenhuma execução seletiva foi implementada.

## Baseline menor e regressão

Amostra estruturada de 200 linhas × 12 colunas, lida do CSV sem modificá-lo.
Pipeline normal incluindo ETL, derivadas, detector e analytics:
0,184 / 0,165 / 0,156 s; média **0,169 s**.
O POST complexo é cerca de 112,5 vezes maior, mas os escopos/tamanhos e a
presença de metadados são diferentes: não atribuir toda a diferença às linhas.

O caso real preservou: 3.325 → 3.324 clientes; líder
R$ 632.033,34 → R$ 650.591,83; participação 7,47% → 7,69%;
Top 5 22,28% → 22,50%; Valor Total R$ 8.460.291,78;
11.695 pedidos; score 33; mesma série temporal.
O resumo completo foi igual entre repetições (exceto horário da decisão).
Hashes dos arquivos de origem, CSV e intermediários foram preservados.

## Propostas para a Etapa 2 — não implementadas

| Proposta | Risco | Impacto provável |
|---|---|---|
| Evitar transportar/copiar auditoria extensa em cada operação analítica, preservando-a no contexto e mantendo os attrs semânticos necessários | Médio | Alto |
| Reutilizar o mapping já calculado dentro da mesma continuação | Médio | Alto no baseline atual; menor depois de resolver attrs |
| Após merge, recalcular somente módulos dependentes e reconstruir o resumo | Médio | Alto |
| Reutilizar agrupamentos compatíveis por cliente/mês | Médio | Médio; medir novamente após attrs |
| Evitar escrita de relatórios temporários que o POST apaga; reduzir round-trips JSON | Baixo a médio | Baixo |

Prioridade: provar uma redução segura das cópias de auditoria com testes de
mapping, fórmulas, qualidade e preservação; medir novamente; então avaliar
reuso do mapping e execução seletiva. Não apagar attrs indiscriminadamente.
Threads, processos, cache distribuído e nova arquitetura não se justificam
por estas medições.

Detalhes por execução, tempos exclusivos e ambiente:
`reports/validacao_v14_performance_baseline.json`.
A instrumentação temporária foi removida; não há helper permanente.

## Etapa 2 — otimização dos metadados

A única otimização foi separar a auditoria da propagação automática de attrs
na cópia analítica. Nenhum cálculo mudou.

### Metadados e solução

Inspector, normalizer e loader escrevem `ingestao`; o mapping assistido grava
decisões e mapeamentos automáticos/confirmados. Antes da continuação, mapping
consulta evidências estruturais. Dentro dos analytics, business consulta
ingestão para comprovar fórmulas, bases semânticas e linhas de origem.

No intermediário real, os attrs serializados em JSON UTF-8 ocupavam
2.593.250 bytes: ingestão 2.591.348; mapping do usuário 1.572;
mapeamentos confirmados 34; automáticos 190 (mais a estrutura JSON).
A auditoria inclui 12.681 classificações de linhas, evidências Excel,
blocos, resumos e cabeçalhos tardios. Sem transportar ingestão, os attrs
ocupam 1.888 bytes. Esses tamanhos medem JSON, não memória heap.

`continuar_analytics` mantém a cópia feita por `aplicar_aliases`, extrai
apenas o dict `ingestao` dessa cópia e o passa a `calcular_kpis`.
Todos os demais attrs permanecem. Original e contexto conservam a auditoria
completa para relatórios e persistência. Fórmulas recebem o mesmo dict;
chamadas antigas de `calcular_kpis(df)` continuam lendo attrs.
Não há novo contexto, cache ou dependência.

### Benchmark pós-attrs e final

Mesmo intermediário de 2017 a 2020.xlsx: 11.795 linhas, 12 colunas,
mapping homologado, merge MINERAÇÃO CAIEIRAS + MINERAÇAO CAIEIRAS.
Cada execução parte de uma cópia isolada do mesmo estado pendente.
O POST não repete Excel, ETL ou detector.

| Medição | POST (s) | Analytics (s) |
|---|---:|---:|
| Baseline Etapa 1, média | 18,976004 | 18,216 |
| Controle anterior nesta etapa | 18,137590 | 17,429 |
| Pós-attrs 1 | 1,334546 | 0,681 |
| Pós-attrs 2 | 1,443984 | 0,695 |
| Pós-attrs 3 | 1,548631 | 0,794 |
| Pós-attrs, média | 1,442387 | 0,723333 |

POST mínimo 1,334546 s; máximo 1,548631 s.
Redução frente ao baseline: **17,533617 s / 92,40%**.
As três execuções usam relógio do POST e tempo analítico já existente,
sem profiling pesado. Não mostram vantagem warm relevante.

Execução detalhada separada: POST 1,477835 s, analytics 0,703 s.
As mesmas 219 cópias de metadados passaram de 15,9424 s para 0,427369 s;
os sete mappings adicionais de 6,2722 s para 0,101568 s inclusivos.
O mapper não mudou. Esses tempos inclusivos não devem ser somados.

### Correção e caminho conservador

Não foi necessário recálculo seletivo: benchmark final é o pós-attrs.
Todos os módulos continuam executando para qualquer entidade, sem reutilizar
resultados potencialmente incompatíveis. A continuação completa é o caminho
conservador, inclusive sem ingestão. Tipos inesperados de ingestão não são
removidos. Snapshots antigos continuam abrindo; ausência de intermediário
para decidir mantém o erro existente, sem fabricar dados ou reprocessar
automaticamente arquivos históricos.

O resumo completo de cada execução foi igual ao controle e à referência
da Etapa 1, excluindo apenas o horário da decisão. Isso inclui auditoria,
mapping e qualidade. Clientes 3.325 → 3.324; líder R$ 632.033,34 →
R$ 650.591,83; participação 7,47% → 7,69%; Top 5 22,28% → 22,50%.
Valor Total R$ 8.460.291,78, pedidos 11.695, score 33 e série temporal iguais.
Hashes de originais, pickle persistido, CSV preexistente e baseline preservados.

### Testes e limites

Python compile passou; 213 testes src e 30 API passaram (243 distintos).
Quatro testes novos cobrem ingestão externa/legada, fórmulas, mappings,
auditoria, preservação do original e continuação sem metadados.
Testes existentes cobrem merge, keep_separate, persistência, históricos
antigos, comparação, mapping assistido e preservação dos totais.
Frontend e contratos públicos não mudaram.

Cópias iniciais do DataFrame/contexto, serialização e persistência continuam
existindo. Não foram otimizadas. Medições representam este dataset e ambiente
(Python 3.13.3, pandas 3.0.5, Windows 11), sem garantir latência para qualquer
arquivo. Não há instrumentação permanente.

Resultados: `reports/validacao_v14_performance_optimized.json`.
O baseline da Etapa 1 permanece intacto.

## Validação final da release

Homologação concluída em 27/09/2026, reaproveitando o fluxo complexo medido
em 25/09. Microsoft Edge 153.0.4234.48, via Playwright, com FastAPI e Vite
reais e persistência isolada. Nenhum benchmark pesado foi repetido na retomada.

- Excel real `2017 a 2020.xlsx`: 11.795 linhas, 12 colunas; upload HTTP 200,
  `mapping_required`; confirmação `coluna_4 → valor_com_desconto` pelo navegador.
- Merge confirmado: HTTP 200 em 1,433 s; resultado disponível em 1,441 s;
  analytics 0,622 s. Um POST, nenhum GET redundante de latest.
  Baseline 18,976 s; média otimizada 1,442 s; redução de 92,40%.
- Clientes 3.325 → 3.324; MINERAÇÃO CAIEIRAS R$ 632.033,34 → R$ 650.591,83;
  participação 7,47% → 7,69%; Top 5 22,28% → 22,50%.
  Valor Total R$ 8.460.291,78, pedidos 11.695, score 33 e série temporal iguais.
- MARIA LUIZ BORGES / MARIA LUIZA BORGES mantidas separadas. Repetir ambas
  as decisões não duplicou decisões nem alterou novamente os resultados.
- Navegação concluída em Visão geral, Desempenho, Produtos, Clientes,
  Oportunidades, Dados e Histórico; sem exceção React, erro inesperado,
  loading infinito ou corrupção textual visível. Empty states respeitados.
- Histórico: abertura da análise nova e de duas antigas, uma sem
  `entity_resolution`, sem migração. Decisões e resultados persistidos após
  refresh e reinício do backend. Duas comparações antiga/nova retornaram 200,
  exibindo somente métricas comuns e reabilitando o botão.
- Dados/entidades e Histórico/comparação verificados em 1440, 390 e 320 px,
  sem overflow horizontal; capturas inspecionadas visualmente.
- Excel inválido: 422 controlado, mensagem compreensível, botão liberado e
  remoção disponível. Logo depois, `release-convencional.csv` retornou success,
  exibiu Faturamento R$ 400,00, sem mapping e sem candidatos de entidades.
- Multi-arquivo homologado: recorte de 40 vendas de `Historico_Vendas.csv`
  com `Clientes.csv` e `Produtos.csv`; três arquivos, HTTP 200, 39 clientes,
  39 produtos e navegação funcional. As amostras originais não foram editadas.
- Ingestão, mapping, transformações, qualidade e evidências preservados no
  snapshot. O DataFrame arquivado mantém os 3.325 clientes originais.
  Hashes do Excel, CSV protegido, amostras e dois baselines permaneceram iguais.

Suítes permanentes executadas novamente: Python compile, 213 testes src,
30 API, TypeScript, Vite build e 89 Playwright (82 principais + 7 uploads).
Total: **332 testes permanentes aprovados**. Scripts temporários de navegador
não entram nessa contagem.

Não houve correção de produção nesta etapa. O timeout de “Análise A” era
do seletor temporário: o label também contém o período dos dados. O script
passou a localizar o combobox pelo prefixo do nome. A varredura temporária
também passou a procurar NaN como palavra inteira, evitando “predominante”.

Limites: cobertura visual no Edge/Windows, sem garantir todos os navegadores;
tempos dependem da máquina/dataset; leitura inicial do Excel é separada do
merge. Nenhum recálculo seletivo ou nova otimização foi introduzido.
Relatório consolidado: `reports/validacao_v14_final.json`.
Temporários desta homologação foram removidos; evidências anteriores preservadas.
