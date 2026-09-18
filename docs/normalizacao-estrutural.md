# Normalização estrutural de relatórios operacionais

Este documento registra a implementação e a validação iniciais. A evolução posterior da confiança por blocos, dos resíduos auditados e das fórmulas opcionais está documentada em [relatorios-repetitivos.md](relatorios-repetitivos.md), que substitui as regras iniciais de bloqueio absoluto descritas abaixo.

## Diagnóstico e arquitetura

A ingestão anterior assumia uma tabela por arquivo e lia apenas a primeira aba do Excel. A inspeção da V0.9 já detectava cabeçalhos, criava nomes neutros, resolvia duplicatas e removia somente eixos totalmente vazios. Foi reutilizada sem alterar suas regras. O ETL, semantic mapper, relacionamentos e módulos analíticos permanecem intactos.

O loader agora inspeciona as abas/regiões antes do ETL. `report_normalizer.py` retorna `aplicado`, uma lista de DataFrames em `blocos` e `metadados` auditáveis. Quando a estrutura é convencional, o caminho anterior permanece, incluindo inferência de tipos e leitura CSV. A falta de cabeçalho, isoladamente, não aciona limpeza agressiva.

`carregar_tabelas_arquivo()` expõe as regiões ao multi-loader. O pipeline escolhe o modo único ou multitabela pela quantidade de tabelas resultantes, permitindo um Excel com várias tabelas. Regiões incompatíveis não são concatenadas. O detector, merger e enricher existentes continuam responsáveis por relacionamentos; um Excel com tabelas independentes sem relação exige revisão.

## Heurísticas e segurança

- Células recebem assinaturas de vazio, texto, número, data ou marcador monetário. Datas ISO, datas brasileiras e datas nativas do Excel são reconhecidas sem adivinhar significado financeiro.
- A repetição de assinaturas e a similaridade com até 32 padrões frequentes ajudam a reconhecer registros, inclusive com pequenas lacunas. O score combina repetição, presença de números/datas, preenchimento e cabeçalho/contexto de bloco. Não é uma probabilidade estatística.
- Rótulos de total, subtotal, meta, média, saldo, resultado, percentual atingido e dias úteis são sinais de resumo. Comentários, separadores e períodos são tratados separadamente. Um rótulo de total junto com data é considerado ambíguo, evitando aceitá-lo como venda.
- Meses em português/inglês, anos e trimestres servem como contexto, independentemente da posição. `periodo_contexto` acompanha as linhas seguintes na auditoria. Uma data existente permanece intacta; contexto não preenche ou substitui células.
- Cabeçalhos repetidos reutilizam os rótulos. Mudanças de cabeçalho separam blocos. Cabeçalhos compostos usam apenas textos realmente presentes; mesclagem é expandida somente para compor rótulos, nunca para preencher transações. Cabeçalhos tardios são localizados pela varredura das linhas, além da amostra inicial da V0.9.
- Nomes ausentes continuam neutros (`coluna_1`, etc.). Nenhuma coluna é batizada como faturamento, lucro ou cliente por posição.
- Colunas 100% vazias são removidas pelo preparador existente; colunas esparsas com dados permanecem. Nomes duplicados e `Unnamed` seguem a V0.9.
- Linhas desconhecidas preservam valores e coordenadas. Uma região complexa com qualquer linha desconhecida bloqueia a análise completa: não se publica apenas a parte reconhecida como sucesso.

O score de linha combina até 45 pontos por repetição/similaridade, 25 por evidência numérica/data, 20 por ao menos dois campos de dados e 10 por contexto de tabela. O limiar principal é 80; há aceitação contextual para linhas com cabeçalho, números/datas e similaridade parcial. Mudanças incompatíveis de tipo voltam a ser desconhecidas. `confianca_estrutural` mede a proporção de registros reconhecidos entre registros candidatos e desconhecidos; não avalia a qualidade financeira do negócio.

## Moedas e fórmulas

O parser aceita formatos brasileiros/americanos inequívocos, sinal negativo e parênteses: `1.204,00`, `1,204.00`, `1204,00`, `1204.00`, `-R$ 35,35`, `(1.200,00)`. Suporta R$, US$, $, £, €, ¥ e ₹, sem converter taxas de câmbio. Um separador único seguido de três casas, como `1.204`, permanece ambíguo.

Uma coluna de marcadores só é retirada quando suas células preenchidas contêm exclusivamente símbolos e há uma associação numérica adjacente confiável. Havendo duas candidatas, um formato monetário explícito pode desambiguar; caso contrário, exige revisão. Mistura de moedas também exige revisão. Valores e marcadores originais ficam registrados. Textos como “FALTAM R$ 458,00” não são transformados em valores.

XLSX usa os resultados armazenados no arquivo para fórmulas; o DataAgent não executa Excel nem recalcula fórmulas. Fórmulas sem cache em registros exigem revisão. Fórmulas em totais permanecem na auditoria dos resumos. A leitura paralela das fórmulas e das mesclagens usa openpyxl já existente. XLS usa os valores fornecidos pelo leitor existente; não recupera texto de fórmulas legadas.

## Blocos e abas

Abas vazias são ignoradas com metadados. Abas de resumos permanecem na auditoria, sem virar métricas. Continuações só são concatenadas quando têm cabeçalhos reais idênticos e dtypes iguais; a origem de cada parte é preservada em `continuacoes`. Abas sem cabeçalho não são concatenadas automaticamente.

Regiões laterais com corredor vazio e cabeçalhos em linhas diferentes são separadas para inspeção, mas exigem revisão antes da análise. Uma coluna vazia, sozinha, não prova que existem duas tabelas. Regiões lado a lado com cabeçalhos perfeitamente alinhados não têm detecção automática garantida. Estruturas que mudam sem cabeçalho e não mantêm compatibilidade de tipos são bloqueadas.

## Auditoria, qualidade e API

`summary.dados.ingestao.normalizacao` inclui estrutura, confiança, linhas originais, registros, resumos, períodos, vazias, desconhecidas, percentuais reconhecidos/desconhecidos, linhas separadas, blocos e transformações. Também guarda classificação por linha, resumos com valores originais, coordenadas dos blocos, cabeçalhos e evidências Excel. No modo multitabela, essas informações ficam no diagnóstico de cada tabela/aba.

A V1.0 apresenta a normalização como informação de qualidade e transformação real. O score executivo e os cálculos analíticos não são alterados. A página Dados mostra apenas os campos recebidos, com a identidade visual existente e sem cálculos de negócio.

O POST existente retorna 200 com o contrato habitual quando há segurança para analisar. Caso contrário retorna 422 com `detail` textual e `diagnostico_estrutural`. O diagnóstico também é salvo em `reports/diagnostico_estrutural.json`, antes da limpeza temporária. A análise anterior e seu histórico não são substituídos por um resultado parcial. Não foram criados endpoints nem dependências.

## Exemplo

Entrada: cabeçalho `Pedido_ID | Data | Faturamento | Lucro`, separador `Janeiro`, registros `(1, 2025-01-01, 100, 40)` e `(2, 2025-01-02, 200, 50)`, seguido de `Total | vazio | 300 | 90`.

Saída: dois registros; um período e um total preservados fora dos dados. O pipeline retorna faturamento 300, não 600. O JSON completo da auditoria está em [normalizacao-estrutural-validacao.json](normalizacao-estrutural-validacao.json).

## Validação

- 53 novos testes Python: estruturas convencionais, CSV irregular, XLS/XLSX, ausência/cabeçalho parcial/tardio/composto, períodos, comentários, moedas, valores negativos, padrões repetidos, regiões distintas, abas, fórmulas, ambiguidades, serialização e POST.
- Regressão completa: 135 testes Python, 52 testes de interface e cinco fluxos reais de upload; TypeScript/build.
- Os 14 datasets de `data/samples` e `data/processed/vendas_tratadas.csv` mantiveram linhas, colunas, nomes e hash dos valores. Todas as seções analíticas e de qualidade do resumo multitabela ficaram equivalentes ao snapshot anterior, exceto metadados adicionais de ingestão.
- Benchmark sintético: 30.061 linhas, 30.000 registros, 30 separadores mensais e 30 subtotais; normalização em aproximadamente 1,29 segundo neste ambiente. Isso mede a normalização, não o pipeline completo.
- Excel complexo pelo React: POST 200, resumo atualizado sem reload e auditoria exibida na página Dados. Os testes existentes de CSV, múltiplos CSVs, erro e preservação do estado também passaram.
- `PLANILHA VITOR.xlsx`: revisão conservadora na aba VENDAS, com 3.286 registros candidatos, 36 resumos, 11 períodos e 52 desconhecidas. Nenhum resultado parcial publicado. O teste identificou e corrigiu a atribuição de fórmula textual em coluna numérica do pandas; foi incluída regressão específica.

## Limitações

As heurísticas não identificam universalmente qualquer relatório. Registros e resumos com formas indistinguíveis podem exigir intervenção humana. Identificação estrutural não garante que o semantic mapper consiga calcular KPIs em colunas neutras. Não há inferência de ano ausente, preenchimento de células mescladas de dados, conversão cambial, avaliação de fórmulas ou OCR. Auditoria detalhada aumenta o tamanho do JSON proporcionalmente ao número de linhas. Resultados em cache de fórmulas podem estar desatualizados no arquivo de origem; o DataAgent não verifica sua atualização.

Não houve alteração em analytics, ETL, semantic mapper ou regras de relacionamento. Alterações anteriores do worktree, incluindo V1.1 e o CSV processado, foram preservadas. Nenhum commit, push ou tag foi realizado.
