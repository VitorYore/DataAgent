# DataAgent V1.5 — Inteligência Analítica e Recomendações

## Etapa 1: auditoria e proposta

Auditoria inicial do working tree em 27/09/2026, branch
`feature/v1.5-analytical-intelligence`. As seções 1–11 registram o estado
encontrado naquela data e o plano original. As seções 12–17 documentam a
implementação concluída e a homologação final; prevalecem para o estado atual.
A auditoria inicial não alterou produção. A V1.5 permanece sem LLM ou serviços externos.

Objetivo: transformar resultados existentes em achados com evidência,
impacto, confiança e recomendação de investigação. Correlação e diferença
aritmética não demonstram causa, intenção, insatisfação ou oportunidade futura.

## 1. Arquitetura e fluxo encontrados

`main.py:continuar_analytics` aplica aliases confirmados em cópia analítica,
separa `ingestao` dos attrs, mapeia colunas e cria a máscara temporal. Executa:

1. `business.calcular_kpis(df_analise, ingestao=...)`;
2. `temporal.analisar_meses(df_temporal)`;
3. `customers.analisar_clientes(df_analise)`;
4. `performance.analisar_desempenho(df_analise, dados_temporais=df_temporal)`;
5. `growth.analisar_crescimento(df_temporal)`;
6. `dimensions.analisar_dimensoes` e `products.analisar_produtos`;
7. `opportunities.analisar_oportunidades`, usando resultados anteriores;
8. `insights.gerar_insights`, também usando resultados anteriores;
9. `executive_summary.gerar_resumo_executivo`, incluindo `organizar_listas`;
10. adiciona suficiência, qualidade, mapping, analysis_id e entity_resolution;
11. salva resumo executivo e relatório analítico. A API persiste o snapshot.

As métricas derivadas são preparadas antes da continuação; não são recriadas
no POST de entidades. `insights` e `opportunities` não repetem groupbys.
O resumo não é somente apresentação: calcula evolução da série principal,
status/score do negócio, consolida rankings e seleciona conclusões.
`data_quality` audita novamente a coerência financeira ao montar `dados`.

Referências complementares auditadas: `derived_metrics.py`,
`temporal_quality.py`, `entity_helpers.py`, `comparison.py`,
`reports/data_quality.py`, `analysis_report.py`, `json_report.py`,
`history/history_index.py`, `api/app.py`, `api/analysis.py`, os tipos e
consumidores das páginas Overview, Performance, Customers, Products,
Opportunities e History. A persistência usa JSON completo por analysis_id e
índice leve; comparação tem fluxo próprio, fora de `organizar_listas`.

## 2. Inventário de capacidades atuais

I = insight; O = oportunidade. A existência de um consumidor não comprova
que o pipeline atual produza seu campo de entrada.

| Módulo / análise | Entrada e dependências | Cálculo / regra e saída | Evidência disponível | I / O e frontend |
|---|---|---|---|---|
| Business: totais | Conceitos numéricos mapeados | Soma por conceito; não converte Valor Total em Faturamento | KPIs e coluna semântica; faltam coberturas uniformes por KPI | KPIs em Overview/Performance; não há achado dedicado para cada total |
| Pedidos / ticket | Pedido ou venda_id; faturamento para ticket | IDs válidos únicos; faturamento/pedidos | Quantidade de registros separada de pedidos | Cards; nenhuma inferência de pedido a partir de linha |
| Margens | Lucro + faturamento; ou margem bruta % e base comprovada | Lucro/faturamento ×100; percentual bruto ponderado por base única/evidência de fórmula | Método e, internamente, linhas-base quando fórmula permite | KPI; não existe regra atual geral de margem problemática |
| Derivadas | Quantidade, preço/custo unitários, faturamento/custo | Cria métricas ausentes: quantidade×preço, quantidade×custo unitário, faturamento−custo, margem | Logs com coluna, fórmula, origem derivada | Alimentam KPIs; não substituem coluna original existente |
| Temporal: série principal | Data filtrada + primeira métrica disponível: faturamento, valor_total, valor_com_desconto, margem_bruta, lucro, custo | Soma mensal, máximo/mínimo, variação entre meses calendários consecutivos; mês com <5 registros é suspeito | Série, conceito, extremos, períodos suspeitos | I de extremos e variação; gráfico/cards temporais |
| Growth | Data + faturamento obrigatório; lucro opcional | Primeiro/último, variações entre observações, sequências de pelo menos duas quedas; tendência >5%/<−5%, restante estável | Percentuais, sequências, motivo/absoluto para faturamento | I/O de queda e sequência; campos temporais do resumo |
| Performance | Lucro; data opcional | Conta linhas lucro<0, soma prejuízo; lucro mensal/extremos/meses negativos | Contagem, soma negativa e série | I/O resultado negativo; Performance. Não equivale a Margem Bruta |
| Clientes: rankings | Cliente_ID prioritário; senão nome/alias confirmado + métrica | Soma e Top 10 de faturamento, valor_total, valor_com_desconto, margem_bruta e lucro | Identidade, labels, conceito, valor, líderes | Cards e rankings Customers; I global de líder apenas faturamento |
| Clientes: participação/concentração | Métrica principal faturamento → valor_total → valor_com_desconto | Top1/total e Top5/total; total inclui valores sem cliente | Percentuais e metadata da métrica; quantidade de clientes | I textual da carteira + I global; O informativa quando Top5<20% |
| Clientes negativos | Lucro ou margem_bruta | Agrega por cliente, filtra agregado<0; lucro prevalece no destaque se ambos existem | Contagem e listas internas; resumo conserva contagem/conceito, não todas as listas | Insights textuais e cards Customers; zero calculado é válido |
| Produtos | Produto_ID prioritário, senão nome; quantidade/faturamento/lucro | Top5 por métrica, produtos com lucro agregado negativo | IDs, somas e rankings; resumo combina rankings em até 10 itens | Products e I de volume/faturamento; sem série por produto |
| Produto candidato a investigação | Produto + faturamento + lucro | Lucro agregado acima da média entre produtos e faturamento abaixo da média; até 5 | Valores por candidato; médias usadas não são devolvidas | I/O produto_crescimento; não prova crescimento futuro ou demanda |
| Dimensões | Produto, categoria, loja, região, cidades, colaborador, canais, tipo de loja, função, gênero, cor, tamanho | Top5 faturamento/lucro/quantidade, participações, valor médio por unidade, negativos | Ranking e participações; não há série por dimensão | `analise.json`; I de líder de canal_venda/loja/colaborador. Sem página genérica de dimensões |
| Estoque / avaliações / devoluções | Campos de produto esperados pelos consumidores | Há templates de risco de ruptura, excesso, nota e devolução em I/O | **Não produzidos por `analisar_produtos` atual** | Types/cards/templates existem; não contar como capacidade ponta a ponta |
| Qualidade temporal | Datas válidas, ao menos 50 registros | Bloco de anos consecutivos cobrindo ≥95%; exclusão só com evidência forte, bloco multianual e anos externos esparsos | Máscara, intervalo, exemplos, quantidade e confiança da heurística | Dados e aviso temporal; não é detecção de mês de vendas anômalo |
| Coerência financeira | Faturamento + custo + lucro na mesma linha | Resíduo F−C−L; tolerância 0,01; alerta quando <50% reconciliam | Coberturas, somas comparáveis, erros, exemplos | Dados; não remapeia nem recalcula valores para fechar equação |
| Comparação V1.2 | Dois resumos; conceitos numéricos idênticos | Delta, percentual, p.p. para margens; estabilidade <0,5%; duração igual/similar(≤1,1)/diferente | Dois valores, períodos, listas limitadas e qualidade | History; insights próprios; não faz matching novo de entidades |

`forma_pagamento` é conceito de mapping, mas não está em CONFIG_DIMENSOES
nem possui produtor de distribuição nesta continuação. Não prometer análise
de mix de pagamentos só porque a coluna foi reconhecida.

## 3. Problemas comprovados e lacunas

Todos os pontos abaixo são preexistentes, identificados nesta auditoria.
Nenhuma correção foi aplicada nesta etapa.

1. **Conceito trocado em texto:** `insights.py` e `opportunities.py` escrevem
   concentração como faturamento sem consultar `metrica_principal`.
   O snapshot complexo mostra 22,28% “do faturamento”, com faturamento null
   e métrica real Valor Total. `customers.py` usa o conceito correto.
2. **Evidência perdida:** `_normalizar` preserva somente valor/metrica/origem/
   periodo; `para_relatorio` publica categoria/prioridade/mensagem/tipo.
   Identidade de entidade, denominador, referência, cobertura e regra não
   chegam aos cards. `analise.json` guarda mais contexto que o resumo, mas
   não é o mesmo contrato consumido pelo frontend/histórico.
3. **Deduplicação ampla demais:** identidade atual é só categoria. Dois
   produtos diferentes de `produto_crescimento` viram uma conclusão.
   Há também deduplicação por texto exato normalizado e precedência
   risco > oportunidade > destaque/informativo. Relevância desempata por
   prioridade, presença de contexto, dígitos e comprimento de texto,
   não pela materialidade financeira.
4. **Fontes sobrepostas:** queda de faturamento e registros negativos são
   gerados em insights e oportunidades; crescimento/estoque/devolução de
   produtos também possuem dois consumidores. A categoria evita repetição
   nos três grupos globais, mas pode descartar recomendação mais explicativa.
   `insights_clientes` é lista de strings independente: Top5 pode reaparecer
   como outra conclusão. Repetir o mesmo achado em páginas diferentes é
   aceitável; criar identidades independentes para o mesmo evento não é.
5. **Prioridade não é impacto/confiança:** qualquer linha com lucro negativo
   gera prioridade alta em insights. No CSV histórico, uma linha de −5,32
   recebe esse destaque. Não há avaliação da representatividade da perda.
   Status de negócio também pode penalizar tendência e seu alerta novamente;
   sua regra atual não será reaproveitada como confiança do finding.
6. **Proteções temporais heterogêneas:** evolução global bloqueia base zero,
   mudança de sinal e base <5% da mediana das magnitudes não nulas. Monthly
   em temporal só protege zero e divide pela base com sinal; growth mensal
   usa módulo da base e protege zero; comparison divide pela base com sinal.
   Nenhum desses três caminhos mensais/comparativos aplica toda a proteção.
7. **Calendário e tendência diferentes:** temporal exige meses adjacentes;
   growth compara observações adjacentes mesmo com lacuna no calendário.
   Resumo genérico chama qualquer variação positiva de alta, enquanto growth
   usa faixa de estabilidade ±5%. “Tendência” hoje é endpoint, não regressão
   estatística. Máximo não significa excepcional nem necessariamente bom
   (por exemplo, quando a métrica principal é custo).
8. **Períodos parciais:** <5 registros é indício, não comprovação de mês
   incompleto. Não há cobertura operacional/calendário de coleta para
   garantir comparabilidade. O resumo não conserva todas as contagens mensais.
9. **Cobertura incompleta:** clientes exclui identidade nula do numerador,
   mas usa total global no denominador. Não há envelope uniforme de cobertura
   pós-ETL por métrica/entidade; nulos gerais são principalmente pré-ETL.
   Alguns sums de negócio/produto/dimensão usam padrão pandas e podem
   representar grupo todo nulo como zero. Não usar esse zero como evidência
   de ausência real sem contagem de valores válidos.
10. **Comparação de entidades usa rankings truncados:** cliente Top10,
    produto ranking consolidado. Ausência no ranking não prova ausência no
    dataset; “only_left/right” não prova cliente perdido ou novo. Sem ID,
    comparação usa trim/casefold, diferente da identidade textual original.
    Não usar isso para reconciliar decisões de entidades entre análises.
11. **Lacunas de produtores:** produto não calcula estoque, avaliação,
    devolução ou série temporal; consumidores existem sem dados produzidos.
    O resumo pode devolver contagem de estoque zero a partir de lista ausente.
    Isso não é evidência de “nenhum risco de ruptura”.
12. **Oportunidades vazias podem ser corretas:** apenas candidatos do tipo
    oportunidade vão para a seção; alertas viram riscos e observações viram
    insights. Sem produto/faturamento/lucro compatíveis, lista vazia é válida.
    Não preencher com recomendações genéricas para ocupar cards.

Provas pequenas executadas em memória, sem arquivos ou alteração de dados:

| Caso | Resultado observado |
|---|---|
| Série 1 → 100.000 | evolução null/base_muito_baixa; temporal mensal 9.999.900% |
| Janeiro 100 → março 80 | temporal mensal vazio; growth registra março −20% |
| Top5=22,28, conceito valor_total | insight global diz “faturamento total” |
| Dois produtos candidatos A/B | duas oportunidades de origem, uma publicada |
| Lucro −100 → −50 na comparação | direção increase e texto “aumentou −50.00%” |

Essas limitações precisam de testes específicos antes de habilitar novas
recomendações; testes atuais passarem não elimina essas lacunas.

## 4. Referências reais, sem novo upload

Snapshot complexo consultado:
`analysis_20260922_153130140328_c73fc3c7aeea42beb8525ad3e1c1f204`.
Valor Total 8.460.291,78; Valor com Desconto 6.085.829,51; Margem Bruta
3.134.085,11; 11.695 pedidos; 3.325 clientes; Top1 7,47%; Top5 22,28%.
Não possui faturamento/lucro/produto confirmado; oportunidades globais vazias.
Período analítico 2017-01 a 2020-12; 8 datas excluídas apenas do temporal;
evolução endpoint de Valor Total 159,54%; máximo 2020-10: 520.523,12.
Score de qualidade 33 não autoriza dizer que o negócio está ruim, nem torna
automaticamente pouco confiável cada soma. Existem 30,78% de nulos pré-ETL
em Valor com Desconto: confiança deve olhar a métrica específica.

Snapshot convencional consultado:
`analysis_20260918_174805692102_10bcc72f4d5c494daf51f8613cdf0573`,
identificado como `vendas_tratadas.csv`: 3.295 registros, Faturamento
2.778.601,77, Lucro 1.075.124,74, Custo 2.842.340,75; margem 38,69%.
Evolução de faturamento suprimida por base 99,00 muito baixa; campo de maior
crescimento de growth ainda contém 174.467,35%, ilustrando a diferença de regras.

O arquivo físico protegido `data/processed/vendas_tratadas.csv` hoje usa
separador `;` e contém as colunas do dataset complexo (Pedido, Data,
Valor_Total, Valor_Com_Desconto etc.). Não é o mesmo conteúdo do snapshot
convencional citado. Foi apenas lido; nenhum baseline foi regenerado.
SHA-256 preservado:
`400773f1a4f9f130175e3b882c182e2027a91638f98e7f120b69ed2fc935e5a0`.

## 5. Achados defensáveis e dados ainda necessários

| Achado pretendido | O que já permite concluir | Condições / lacunas |
|---|---|---|
| Crescimento/queda global de faturamento, lucro ou outra métrica | Diferença cronológica descritiva entre valores existentes | Conceito explícito; proteção de base/sinal; período e cobertura. Lucro mensal existe em performance, mesmo quando growth não funciona sem faturamento |
| Margem problemática | Margem calculada e lucro negativo são observáveis | “Baixa” exige referência/meta explícita. Sem ela, mostrar valor/negatividade, não inventar benchmark setorial |
| Prejuízo | Lucro agregado/linhas negativas e total da perda | Distinguir prejuízo global, transação negativa e cliente negativo; Margem Bruta negativa não é lucro líquido |
| Concentração de clientes | Top1, Top5 e número de clientes com métrica explícita | Percentual é fato; “elevada/excessiva” exige limiar justificado por regra e cobertura, não usar 20% inversamente como novo limiar de risco |
| Cliente em queda/crescendo | Apenas diferenças nos rankings de dois snapshots hoje | Para conclusão temporal defensável: agregado completo entidade×período, janelas comparáveis, base válida, identidade consistente |
| Cliente perdido/inativo | Ainda não defensável | Janela de observação completa, última compra e regra de inatividade por domínio. Inicialmente dizer “sem registros na janela B”, não “perdido” |
| Concentração de produtos/dimensão | Participações em dimensions e totais compatíveis permitem observação | Top5 não é população completa; validar base não negativa e valores não atribuídos; valor_total ainda não suportado por products/dimensions |
| Produto crescendo/em queda | Não há série por produto | Exige agregado produto×período com conceito e cobertura. “Lucro acima da média” não é evolução temporal |
| Período fraco/forte | Máximo/mínimo da série, com conceito | “Excepcional” requer regra robusta de referência e amostra, ainda inexistente; não confundir maior custo com melhor período |
| Anomalia temporal | Datas isoladas fora do bloco predominante já detectadas | Qualidade temporal, não causa de variação comercial; reaproveitar máscara única |
| Dependência de dimensão | Participações observadas | “Excessiva” depende de critério explícito; nenhuma inferência sobre vulnerabilidade causal |
| Mudança de mix | Ainda falta distribuição por dimensão e período | Agregados completos, denominadores por período, categorias comparáveis; variação em pontos percentuais |
| Contribuição de A/B para queda global | Não recuperável de Top10 truncado | Delta de todas as entidades, total reconciliado, não atribuídos e compensações positivas; mesma métrica/população/janela |

Na contribuição implementada na Etapa 4, distingue-se queda líquida global de soma das
contribuições negativas. Uma participação na queda líquida pode exceder 100%
quando há compensações positivas; não esconder nem chamar isso de causa.
Moeda/unidade não identificada também impede comparação monetária segura.

## 6. Contrato mínimo proposto na Etapa 1

Campo opcional novo no resumo: `achados_analiticos`, lista de dicts.
Versão da regra pertence ao item; não precisa classe, registry ou rule engine.
Exemplo ilustrativo de observação, com confiança ainda limitada por cobertura:

```json
{
  "id": "finding-<hash-deterministico>",
  "regra": "concentracao_clientes",
  "versao_regra": 1,
  "tipo": "informativo",
  "titulo": "Participação dos principais clientes",
  "resumo": "Os cinco maiores clientes representam 22,28% do Valor Total.",
  "metrica": {"conceito": "valor_total", "label": "Valor Total", "unidade": "BRL"},
  "escopo": {"tipo": "carteira", "entidade_id": null, "rotulo": null},
  "periodo": null,
  "impacto": "baixo",
  "confianca": "media",
  "motivos_confianca": ["Cobertura conjunta de cliente e métrica ainda não documentada."],
  "prioridade": "baixa",
  "evidencias": [
    {"campo": "top5_percentual", "valor": 22.28, "unidade": "%", "fonte": "clientes.concentracao_top_5"},
    {"campo": "top1_percentual", "valor": 7.47, "unidade": "%", "fonte": "clientes.participacao_maior_cliente"},
    {"campo": "clientes_distintos", "valor": 3325, "unidade": "entidades", "fonte": "clientes.quantidade_clientes"}
  ],
  "recomendacao": null
}
```

Campos obrigatórios: id, regra, versao_regra, tipo, titulo, resumo, metrica,
escopo, impacto, confianca, motivos_confianca, prioridade, evidencias.
Métrica/unidade podem ser null quando inaplicáveis/desconhecidas; não inferir
BRL universalmente do locale. Evidências importantes nunca podem ficar vazias.
`periodo` e `recomendacao` são opcionais/nullable. Sem evidência suficiente,
não emitir conclusão de negócio apenas com texto e confiança baixa.

Para comparação, adicionar objeto opcional `comparacao` com
`valor_atual`, `valor_referencia`, `variacao_absoluta`, `variacao_percentual`,
`motivo_percentual_indisponivel`, janelas A/B e `comparabilidade`.
Não duplicar esses valores em vários campos nem usar zero para ausência.
Diferença de taxas usa pontos percentuais explicitamente.

Cada evidência é pequena, JSON estrito (sem NaN/Infinity), com valor, unidade
e caminho de origem estável dentro dos resultados. Incluir numerador,
denominador, cobertura e regra/limiar aplicado quando necessários para
reproduzir a afirmação. Não copiar auditoria de linhas ou DataFrame ao achado.
Persistir os valores utilizados, não só um caminho que pode sumir no futuro.

## 7. Confiança, impacto e prioridade

Confiança qualifica a evidência, não é probabilidade estatística nem score
de qualidade dividido por 100. Proposta explícita por regra:

- Alta: conceitos resolvidos, cobertura requerida conhecida, população e
  identidade adequadas, amostra suficiente e comparação aplicável.
- Média: cálculo observável, porém há limitação relevante documentada
  (cobertura desconhecida, mês possivelmente parcial, identidade por texto).
- Baixa: evidência parcial permite apenas descrição restrita/investigação.
  Falta de métrica, referência ou identidade indispensável impede emissão.

Limiar de amostra/cobertura deve ser definido e testado por regra; não criar
um mínimo universal arbitrário nesta etapa. Mapping confirmado garante a
decisão semântica, não a correção dos valores. Qualidade pré-ETL não substitui
cobertura pós-ETL. Só problemas dos campos utilizados limitam o achado:
nulos em coluna não relacionada não reduzem toda a confiança.

Estrutura recuperada não é automaticamente evidência ruim; registrar regiões
ambíguas e cobertura. Fórmula sem cache não vira zero. Bases percentuais
incompatíveis bloqueiam o agregado. Coerência financeira divergente permite
descrever os valores informados, mas limita recomendações sobre relação
receita/custo/lucro. Datas excluídas devem ser explicitadas; achados temporais
usam a mesma máscara dos cards. Decisões pendentes de entidades limitam
interpretação da carteira, sem merge automático ou mudança de score.

Impacto: baixo/médio/alto por regra, separado da confiança. Descrição de
ranking não é automaticamente alto impacto; perda relativa, montante e
abrangência podem sustentá-lo quando há denominador e parâmetro defensável.
Sem referência de materialidade, usar descrição de baixo impacto, sem
rotular risco alto por intuição. Limiares novos exigem validação com fixtures.

Prioridade proposta (tabela explícita, sem score 0–100):

| Impacto \ Confiança | Alta | Média | Baixa |
|---|---|---|---|
| Alto | Alta | Média | Média (investigação com ressalva) |
| Médio | Média | Média | Baixa |
| Baixo | Baixa | Baixa | Baixa |

Ordenar por prioridade, impacto, confiança e id determinístico. Magnitude
só desempata eventos da mesma regra, unidade e referência; não comparar reais
com percentuais ou counts. Confiança baixa não pode produzir recomendação
assertiva. Valores/limiares não existentes permanecem decisão de projeto,
não fatos presumidos sobre o negócio do usuário.

## 8. Identidade, deduplicação e recomendações

Identidade do evento: regra/família canônica + conceito + escopo + identidade
da entidade + janela/referência. ID derivado desses campos e analysis_id por
hash da biblioteca padrão; não usa posição da lista, texto exibido ou valor
da métrica. Mesma análise e evento têm ID estável após recalcular valores.
Nome é label quando existe ID. Sem ID, usar a identidade analítica aprovada
naquela análise, sem normalizar nomes novamente ou unir históricos.

Uma única fonte produz cada evento. Recomendações são anexadas ao achado,
não geram outro card com identidade independente. Famílias sobrepostas atuais
(`tendencia_faturamento`, `resultado_negativo`, `produto_crescimento`) precisam
de associação explícita ao produtor escolhido. Mesmo tipo em entidades
diferentes não deve ser colapsado. Limites visuais são aplicados depois.
Achados de janelas diferentes são distintos; só suprimir redundância entre
extremo e variação quando regra e evidência comprovarem o mesmo evento.

Recomendações: texto determinístico ligado à regra e evidência; null é válido.
Exemplos: “Investigar a redução observada nas compras de X”; “Conferir a
coerência dos campos informados”; “Avaliar a exposição aos principais
clientes”. Não recomendar contato por insatisfação, aumentar estoque sem
dados de giro ou prever recuperação. Não atribuir causa a associação.
Não chamar máximos de lucro/faturamento de causa do desempenho geral.

## 9. Integração e compatibilidade propostas

Adicionar achados após métricas e após montar qualidade/mapping, antes de
salvar o resumo em `continuar_analytics`. Uma função simples recebe dicts já
calculados e um resumo pequeno de cobertura. Não receber/copiar auditoria
gigante nem executar mapper/ETL/detector dentro do gerador de achados.

Primeira entrega é aditiva: campos e três listas legadas permanecem; nenhuma
mudança de endpoint. `analysis_report` pode persistir a mesma lista produzida,
sem recalculá-la. `persistir_resumo` já salva dict completo; índice de history
não deve carregar os achados. API latest/detalhe/POST devolvem o mesmo resumo
com campo opcional. Comparação atual permanece isolada, sem novo matching.

Frontend nesta etapa não muda. Futuramente `achados_analiticos?` no tipo TS:
se ausente, usar listas legadas; se presente e vazio, não inventar achados.
Mapear achados para Insights/Oportunidades/Pontos de atenção existentes,
com evidência expansível, impacto, confiança e recomendação. Durante a
migração, não renderizar simultaneamente versões nova e antiga do mesmo
evento. Customers pode exibir os mesmos IDs em contexto da carteira.

Snapshots antigos abrem como foram produzidos, sem backfill ou execução de
regras novas. Novas decisões sobre análise recalculável atualizam achados
junto dos analytics completos; leitura histórica não recalcula. Comparações
de métricas antigas continuam funcionando mesmo sem achados.

Preservar V1.4: auditoria pesada fora dos attrs, analytics completos e
fallback existente. Primeiras regras percorrem dicts/listas compactos.
O agregado entidade×período foi acrescentado na Etapa 4,
uma vez por conjunto de conceitos, reutilizado por regras. O impacto é medido
contra 1,442 s, sem asserção frágil de tempo, cache ou paralelismo.

## 10. Plano incremental original e critérios de aceite

| Etapa | Entrega limitada | Critério de aceite |
|---|---|---|
| 1 — esta auditoria | Inventário, lacunas, contrato proposto | Nenhum código de produção alterado; limites demonstrados |
| 2 — contrato executável + primeiras regras | Funções simples de concentração/negativos já calculados, evidências, IDs, deduplicação, campo opcional | Preserva conceitos; não colapsa entidades distintas; snapshot/API aditivos; nulos e zero distintos; recomendações investigativas pequenas |
| 3 — temporal defensável | Reuso da evolução protegida; metadados de janelas/cobertura; padronização explicitamente testada dos casos mensais | Zero/base pequena/sinal/lacuna/parcialidade; máscara única; corrigir inconsistências comprovadas sem generalização causal |
| 4 — clientes/produtos/dimensões | Primeiro rankings/concentração já disponíveis; depois agregado entidade×período limitado e aprovado | Identidade estável, cobertura, métricas compatíveis; não inferir perdido de Top10; custos medidos |
| 5 — recomendações e priorização | Revisão por regra da tabela impacto/confiança e textos | Toda ação rastreável; sem causa inventada, previsão ou recomendações genéricas obrigatórias |
| 6 — frontend aditivo | Evidências e confiança nas seções atuais; fallback legado | Sem duplicação visual, sem quebra de históricos/UTF-8/mobile |
| 7 — homologação | Fixtures, dados reais já homologados, suites e tempo de continuação | Totais/qualidade/identidade preservados, JSON estrito, compatibilidade e performance |

**Ordem adotada na implementação:** etapa 2, começando por concentração
de clientes com conceito correto e resultado negativo com população/métrica
explícitas. Reaproveitar `insight_engine` onde aplicável, sem substituí-lo de
uma vez. Congelar contrato em testes e produzir lista aditiva; não iniciar
simultaneamente churn, mix, estoque e série por entidade. Problemas
preexistentes acima recebem testes de reprodução na etapa relacionada.

Critérios de testes implementados nas etapas seguintes: mesma regra em duas entidades; mesmo evento em duas
fontes; mudanças de label sem troca de ID; zero/nulo; sem faturamento mas com
Valor Total; Margem Bruta distinta de Lucro; evidência e unidade; confiança
limitada por cobertura; JSON sem NaN; snapshot sem campo; decisão de merge
atualiza achados de carteira sem alterar totais; matriz temporal completa;
rankings truncados não viram perda de cliente; recomendações sem causalidade.

## 11. Validação desta auditoria

Executados 35 testes existentes: `test_insight_engine`,
`test_growth_evolution` e `test_comparison`; todos passaram.
Cinco sondagens sintéticas em memória documentadas acima, sem criar testes
permanentes nem recalcular o Excel real. CSV e snapshots somente lidos.
Único arquivo criado nesta etapa: este documento. Nenhum arquivo de produção
ou frontend foi modificado. Sem commit, push ou tag.

## 12. Etapa 2 — contrato executável e primeiras regras

Implementação em `src/analytics/findings.py`, com funções e dicts, sem novo
framework ou dependência. `gerar_achados_analiticos` recebe resultados de
clientes/desempenho e `analysis_id`; não recebe DataFrame, não faz mapping,
ETL, leitura de arquivo ou groupby. Clientes reaproveita os agregados completos
já calculados, antes de truncar rankings. Desempenho reaproveita os registros
negativos. Ambos acrescentam apenas estatísticas numéricas compactas de
cobertura, população e magnitude, fora dos attrs.

**Contrato implementado:** chaves em inglês conforme solicitado na Etapa 2:
`id`, `rule`, `rule_version`, `type`, `title`, `summary`, `metric`,
`metric_label`, `unit`, `scope`, `entity`, `impact`, `confidence`,
`confidence_reasons`, `priority`, `evidence`, `period`, `comparison`,
`recommendation`. Todas estão presentes; `unit`, `entity`, `period` e
`comparison` ficam null nestas regras. A unidade monetária não é inferida
como BRL pelo locale. A janela é toda a população analítica, sem novo filtro
temporal. Recomendação pode ser null. `type` identifica a família da regra.
Evidências não ficam vazias; ausência de dados indispensáveis impede emissão.

Cada evidência contém `name`, `value`, `unit`, `source`, `concept`; razões
incluem `numerator` e `denominator`. Sources apontam para analytics do relatório
completo, e os valores também ficam gravados no próprio achado. Quantidades
usam `count`, razões usam `%`; números permanecem números JSON finitos.
Evidências preservam precisão do cálculo, enquanto textos e cards arredondam.

IDs: SHA-256 (24 caracteres hexadecimais) do JSON determinístico de análise,
regra, conceito, escopo, identidade da entidade, período e referência.
ID de entidade prevalece sobre label; sem ID, usa o texto analítico existente.
Valores e summary não participam. Cada regra tem `rule_version: 1` explícito.
A versão é rastreável separadamente, sem mudar a identidade do mesmo evento.
Deduplicação preserva um achado por ID, após ordenar prioridade, impacto,
confiança e ID. Entidades, análises e janelas distintas não são colapsadas.

### Concentração de clientes

`customer_concentration`, escopo `customers`, usa a métrica principal já
escolhida: Faturamento, Valor Total ou Valor com Desconto. Lucro/Margem Bruta
não são usados como volume de carteira. Emite uma observação descritiva mesmo
quando a concentração é baixa; não chama toda concentração de risco.

Evidências: total da métrica, maior cliente e seu valor, soma Top 5,
participações Top 1/Top 5, clientes com métrica válida, registros totais e
registros com identidade + métrica. O total inclui linhas sem cliente quando
existirem; numeradores só incluem clientes identificados, com cobertura explícita.
Denominador zero/ausente/não finito ou qualquer registro negativo da métrica
de volume impede essa regra, evitando interpretar saldo líquido como exposição.

O legado só tinha limiar de baixa concentração (`Top 5 < 20%`), inadequado
para definir alta concentração. Critérios novos, internos ao produto:

| Condição | Impacto |
|---|---|
| Pelo menos 10 clientes válidos e Top 5 ≥ 80% | high |
| Pelo menos 10 clientes válidos e Top 5 ≥ 50%, abaixo de 80% | medium |
| Demais carteiras válidas | low |

50% representa maioria; 80% representa parcela dominante para triagem.
Dez clientes evitam chamar Top 5 trivialmente próximo de 100% em carteira
pequena de alto impacto. São heurísticas testadas, **não padrões universais de
mercado nem probabilidade de perda de clientes**. Recomendação para impacto
médio/alto: monitorar participação e investigar diversificação; baixo: null.

### Resultados negativos

`negative_results`: clientes com Lucro agregado negativo, clientes com Margem
Bruta agregada negativa e, quando disponível, registros com Lucro negativo.
Essas populações são explícitas em `scope` (`customers` ou `records`).
Resultado negativo em registro pode ser compensado no agregado do cliente:
não são o mesmo evento e não são deduplicados entre escopos.

Evidências: contagem negativa, população com valor válido, soma negativa,
soma dos valores absolutos dessa mesma população e cobertura dos registros.
Magnitude relativa = `abs(soma_negativos) / soma_absoluta`. Abrangência =
`negativos / populacao`. Não dividir perda pelo saldo líquido, que pode ser
zero ou cancelado por positivos. Para clientes, o valor absoluto é aplicado
**depois** da agregação por identidade. Nulos não contam como zero válido.

| Condição | Impacto |
|---|---|
| População ≥ 10, negativos ≥ 5, magnitude ≥ 20% e abrangência ≥ 20% | high |
| População ≥ 10, negativos ≥ 2 e magnitude ≥ 5%, sem condição high | medium |
| Demais negativos com evidência suficiente | low |

São limites conservadores de triagem do produto: exigem magnitude e
abrangência, sem limite monetário fixo. Um negativo isolado não ganha impacto
alto automaticamente, mesmo que represente toda uma população minúscula.
Ausência de negativos/métrica/população/magnitude suficiente gera nenhum achado.
Recomendação: revisar valores informados e investigar os resultados negativos;
nunca atribuir causa, insatisfação, intenção ou prever resultados futuros.

### Confiança, prioridade e limites

Confiança parte do conceito já resolvido pelos analytics, e descreve os
valores informados, não certifica a fórmula financeira de origem.
Cobertura conjunta pós-tratamento ≥ 95%, população ≥ 10 e identidade por ID
permitem high. Cobertura desconhecida ou identidade textual limita a medium;
cobertura < 95% ou população < 10 limita a low. Os motivos ficam explícitos.
95% é tolerância operacional de até 5% de linhas sem os campos da regra,
não intervalo estatístico. Score geral de qualidade não participa.
Confirmação do mapping não é confundida com validação do valor informado.

Aplica-se exatamente a matriz da seção 7 (enums `low/medium/high`).
Prioridade high exige impacto high + confiança high. Coerência financeira
não é reinterpretada: os achados descrevem Lucro ou Margem Bruta informados,
sem concluir relação entre Faturamento, Custo e Lucro. Não há causalidade.

### Integração e compatibilidade

`main.continuar_analytics` gera uma única lista após montar os resultados,
qualidade/mapping, antes da persistência. Resumo executivo e `analise.json`
recebem a mesma lista; `[]` é válido. API latest/detalhe/decisão e persistência
existentes preservam o campo sem novo endpoint. Merge recalcula os achados
com os analytics completos; keep_separate conserva os achados existentes.
Snapshots antigos não são migrados, nem recalculados na leitura. Se uma chamada
isolada ao gerador só tiver agregados antigos sem cobertura/magnitude exigida,
não inventa essas evidências e pode retornar `[]`.

Listas legadas permanecem, inclusive suas limitações já auditadas. Frontend,
comparação, detector, IDs, ETL e fórmulas não foram alterados. Ficam para a
Etapa 3: base negativa/pequena, proteção temporal inconsistente e lacunas entre
meses. Não foram implementados clientes perdidos, evolução por entidade, mix,
estoque, forecast ou novos tipos de recomendação.

### Validação da Etapa 2

- 23 testes novos: 20 unitários e 3 API; contrato/JSON, ID, deduplicação,
  conceitos, razões, limites, nulos, população, recomendações, preservação,
  merge, keep_separate, persistência/restart e snapshot antigo.
- Suítes completas: **233 src + 33 API = 266 testes aprovados**. Incluem
  insights, oportunidades, resumo, histórico, comparação, mapping e auditoria.
- Base complexa: reutilizado o CSV tratado de `2017 a 2020.xlsx`, somente
  leitura (11.795 × 12). Confrontados KPIs e clientes com `reports/analise.json`
  existente. Nenhum upload/Excel/ETL repetido.
- Achados: Top 5 **22,28% do Valor Total**, Top 1 **7,47%**, 3.325 clientes;
  **3 clientes com Margem Bruta negativa, soma −40,99**, entre **3.324** com
  essa métrica válida (5 registros sem margem; um cliente sem valor válido).
  Ambos: impacto low, confiança medium (nomes), prioridade low.
- CSV convencional já existente de teste: 3 linhas, 2 clientes; derivações
  originais de Faturamento/Custo/Lucro reutilizadas. Faturamento 900, Top 5
  corresponde aos dois clientes (100%). Impacto/confiança/prioridade low,
  sem negativos; não classificado como alto risco por ter apenas dois clientes.
- Controle comparou funções de clientes/desempenho do HEAD com as novas e
  continuação completa sem/com adições. Removidos apenas os campos novos,
  **todos os resultados são idênticos**. DataFrames e hashes dos CSVs iguais.
- Geração dos achados: cerca de **0,069 ms** na base complexa e **0,039 ms**
  na simples (média de três chamadas). Controle inicial da continuação local:
  complexo **0,140 s / 0,146 s**, simples **0,065 s / 0,063 s**, antes/depois.
  Estes controles usam CSV já tratado sem auditoria pesada carregada, incluem
  escrita de relatórios, e **não equivalem ao POST de 1,442 s da V1.4**.
  Variação cold/warm e de máquina impede atribuir todo delta aos achados.
  Não há assert de tempo, novo cache ou recálculo seletivo.

Evidências reproduzíveis: `reports/validacao_v15_achados.json`, com números
sem arredondamento prematuro e tempos observados. Arquivo protegido preservado:
SHA-256 `400773f1a4f9f130175e3b882c182e2027a91638f98e7f120b69ed2fc935e5a0`.
Sem frontend novo e sem versionamento Git nesta etapa.

## 13. Etapa 3 — comparação e achados temporais

Auditoria incremental de `temporal.py`, `growth.py`, `performance.py`,
`insights.py`, `opportunities.py`, `findings.py`, `executive_summary.py` e
integração em `main.py`. As inconsistências vinham de três fórmulas locais:
temporal mensal dividia pela referência com sinal; growth mensal usava seu
módulo e não verificava lacunas; só evolução total protegia base pequena.
Também havia arredondamento antes de algumas comparações e dois critérios
de tendência (qualquer mudança versus faixa de estabilidade de ±5%).

### Comparação central

`src/analytics/temporal_comparison.py` contém funções pequenas, sem classes,
novas dependências ou DataFrames. `comparar_valores` retorna:

`previous_value`, `current_value`, `previous_period`, `current_period`,
`absolute_change`, `percentage_change`, `direction`, `percentage_valid`,
`comparable`, `reason`, `continuous`, `granularity`, `reference_magnitude`.

Direção é matemática (`increase`, `decrease`, `stable`), não uma avaliação
de negócio. `comparable` indica que os valores e a janela permitem a
comparação solicitada; não garante percentual válido nem calendário completo.

| Caso | Delta | Percentual / motivo |
|---|---:|---|
| 100 → 120 | +20 | +20% |
| 100 → 80 | −20 | −20% |
| 0 → 100 | +100 | null / `zero_reference` |
| 100 → 0 | −100 | −100% |
| 1 → 100000 | +99999 | null / `low_reference_base` |
| −100 → −50 | +50 | null / `negative_reference` |
| −100 → −150 | −50 | null / `negative_reference` |
| −100 → 100 | +200 | null / `negative_reference` |
| 100 → −100 | −200 | null / `sign_change` |
| Valores iguais positivos | 0 | 0% |
| None, NaN, infinito ou delta com overflow | null | null / `invalid_value` |

Base pequena: preservado o limiar de **5%** da mediana das magnitudes não
nulas. A referência usada é o maior valor entre essa mediana da série e a
mediana do par. A proteção local evita que `[1, 1, 1, 100000]` ainda gere um
percentual explosivo só porque a mediana global é 1. Não há limiar monetário
fixo. Base negativa é bloqueada antes de qualquer divisão; não se inventa
percentual usando módulo ou fórmula alternativa. Mudança de sinal partindo
de positivo também bloqueia percentual, preservando o delta.

Granularidades explícitas: `M` (`YYYY-MM`), `Q` (`YYYYQn`) e `Y`/`A`
(`YYYY`). O pipeline atual continua agregando mensalmente. Não foi criada
inferência de granularidade nem agregação trimestral/anual nova. Dezembro →
janeiro é consecutivo; janeiro → março não é. Períodos inválidos, repetidos
ou invertidos invalidam a comparação datada; o delta numérico continua
disponível. `comparar_serie` ordena períodos já agregados e não imputa zeros.
Valores nulos não são removidos para ligar artificialmente os vizinhos.

Comparações periódicas exigem continuidade: lacunas retornam percentual null,
`comparable: false`, `continuous: false`, `non_consecutive_periods`.
Evolução total continua comparando primeiro/último período observado, sem se
apresentar como crescimento mensal. Nesse caso `continuous: false` descreve
a distância entre os extremos, não a presença de lacunas dentro da série.

### Integração e correções

- `temporal.py` publica `comparacoes`, granularidade, contagens por período e
  cobertura. `variacao_mensal` permanece, agora com null nas comparações
  bloqueadas. Agregação por mês e máscara de anomalias existentes preservadas.
- `growth.py` usa o helper para mensal e total. No pipeline recebe as séries
  prontas de temporal/desempenho; chamadas antigas ainda calculam a série
  quando não é fornecida. Sequências de queda param em lacunas/percentuais
  inválidos. Máximos de crescimento/queda só são produzidos com sinal correto.
- Lucro reutiliza sua própria população válida de desempenho, sem depender
  de Faturamento preenchido na mesma linha. Um mês com Lucro todo nulo não
  é convertido em zero. A contagem usa o mesmo objeto GroupBy já existente.
- Séries precisas (`valores_mensais_precisos`, `lucro_mensal_preciso`) evitam
  que `0,004` vire referência zero antes da comparação. Séries arredondadas
  legadas permanecem para apresentação. Comparações/evidências usam precisão
  do agregado; cards legados podem continuar arredondando valores em centavos.
- Resumo usa a mesma proteção e faixa de estabilidade de ±5%, conservando
  os aliases antigos (`base_zero`, `base_muito_baixa`, `mudanca_de_sinal`) e
  acrescentando `base_negativa`. Não permite que um percentual antigo
  fornecido no dict sobreponha a comparação segura calculada da série.
- Insights/oportunidades deixam claro que evolução se refere aos extremos
  observados. Percentuais indisponíveis não entram nos textos mensais.
  Aumento/máximo de Custo é informativo, não um insight positivo.
  Logs não exibem `None%`.
- Contratos legados, persistência, history/comparison e frontend permanecem.
  Leitura de histórico não executa a regra atual nem migra snapshots.

### Achados temporais

`temporal_growth` e `temporal_decline`, versão 1, entram aditivamente em
`achados_analiticos`. A Etapa 2 e sua matriz de prioridade permanecem intactas.
Usam a série da métrica temporal principal (Faturamento, Valor Total, Valor
com Desconto, Margem Bruta, Lucro ou Custo) e a série de Lucro quando disponível,
sem gerar duas vezes o mesmo Lucro. Não criam séries por entidade ou para
todas as colunas monetárias. Custo recebe descrição de aumento/redução, sem
afirmar melhora, oportunidade ou causa. ID inclui conceito e os dois períodos.

Só há achado com dois períodos consecutivos numericamente válidos e delta
material. Evidências incluem comparação completa (inclusive motivo de null),
registros por período, cobertura conhecida, número de períodos, conceito,
fonte e razão de materialidade com numerador/denominador. Moeda desconhecida
continua null. Não se infere calendário completo da simples presença de linhas.

Critério de triagem explícito: `abs(delta) / referência_de_magnitude >= 20%`.
A referência é o máximo entre mediana da série e do par, também registrado.
Impacto medium para os eventos que passam esse filtro. Impacto high exige,
adicionalmente: magnitude ≥50%, percentual válido de pelo menos 20% em módulo,
três períodos observados, cinco registros válidos em cada extremo e cobertura
dos campos ≥95%. São limites internos do produto, não padrões de mercado.
Sem percentual válido, um salto material pode ser descrito, com impacto no
máximo medium; não se transforma automaticamente em alerta alto.

Confiança medium quando há cobertura ≥95%, contagens ≥5 nos dois períodos e
ao menos três períodos; caso contrário low. **Não se emite confiança high**
nesta etapa porque a cobertura do calendário operacional é desconhecida.
Motivos e limitações ficam explícitos. Prioridade usa a matriz da Etapa 2;
qualidade geral não vira confiança. Recomendações apenas investigam os
componentes da variação observada e pedem conferir cobertura, sem atribuir
queda a clientes, satisfação, estoque ou demanda futura.

### Testes, evidências e limites

Adicionados **26 testes src + 1 API**, cobrindo valores, nulos/infinito,
overflow, sinal, base pequena, meses/anos/trimestres, lacunas, ordenação,
agregação, precisão, textos, evidência, materialidade, confiança, prioridade,
deduplicação, reuso sem groupby/mapping e persistência. Um teste antigo de
evolução que aceitava percentual sobre base negativa foi atualizado: agora
espera null com delta preservado. Nenhum teste foi alterado para aceitar o bug.
Resultado final: **259 src + 34 API = 293 testes aprovados**, Python compile
aprovado. As suítes incluem histórico, comparação, insights, oportunidades,
resumo executivo e os testes da Etapa 2.

Validação real sem upload/Excel/ETL: reutilizado CSV tratado existente e
confrontado com `reports/analise.json`. Totais mensais e KPIs idênticos;
DataFrame, CSV e relatório histórico preservados por igualdade/hash.

| Base | Resultado |
|---|---|
| 2017–2020 | 11.795 linhas originais, 11.787 após filtro de oito anomalias; 48 meses, 2017-01 a 2020-12 |
| Extremos | 100079,67 → 259742,75; delta +159663,08; evolução total +159,54% |
| Continuidade | Sem lacunas nos 47 pares mensais; nenhum percentual bloqueado nesta série |
| Achados reais | 14: oito aumentos e seis reduções de Valor Total |
| Exemplo | 2019-12 → 2020-01: +88321,32 / +91,17%; impacto high, confiança medium, prioridade medium |
| Exemplo | 2019-11 → 2019-12: −65245,26 / −40,24%; impacto medium, confiança medium, prioridade medium |
| CSV convencional existente | 3 registros; 2025-01 a 2025-03; Faturamento 200 → 100, evolução total −50%; quatro achados (Faturamento/Lucro), confiança low |

Sondagem somente em memória do snapshot antigo: mesmos 14 candidatos, mas
confiança low por falta das novas contagens/cobertura. O arquivo antigo não
recebeu achados nem foi modificado. Isso não é comportamento automático de history.

Custo médio de três medições: comparação dos 47 pares reais **0,314 ms**;
geração dos 14 findings **0,213 ms**. Na fixture simples: **0,026 ms** e
**0,082 ms**, respectivamente. Analytics temporais completos dessa validação:
aproximadamente 31 ms / 15 ms. Não são tempos de POST/upload nem promessa de
latência; não há assert rígido, profiler pesado, cache ou novos attrs.
Relatório: `reports/validacao_v15_temporal.json`.

Problemas de validação identificados e separados do escopo:

- Fixture inicial de Custo usava header não reconhecido; mudou para
  `Total_custo`, sem alterar o mapper.
- Parser preexistente do ETL com `dayfirst=True` interpretou `2026-01-10` e
  `2026-02-10` como datas em outubro nesta versão do pandas. Registrado como
  limitação de ingestão a tratar separadamente; a fixture API usa
  `15/01/2026` e `15/02/2026`. Não houve alteração de ETL/ingestão nesta etapa.
- Leitura temporária do CSV tratado precisava de `format="mixed"` para
  preservar datas com e sem horário. Corrigido somente o script de validação
  antes da conferência com o relatório histórico; script removido ao final.

Sem anomalia estatística, previsão, decomposição causal, clientes/produtos por
entidade, novo frontend ou migração histórica. Calendário completo e qualidade
da coleta ainda não são conhecidos. O helper garante a comparação matemática
dos valores/períodos recebidos, não certifica a origem desses dados.

## 14. Etapa 4 — inteligência por clientes e produtos

### Agregação e identidade

Auditoria: `customers`, `products` e `dimensions` tinham totais/rankings por
entidade, mas não entidade × período. `enricher` agrega avaliações, estoque
e devoluções sem a janela necessária. Rankings truncados não são população.
Reutilizamos mapping, séries globais precisas de temporal/performance,
filtro temporal, aliases, comparação central e contrato de findings.

`entity_evolution.py` contém duas funções: `agregar_entidades_periodo` cria
um agrupamento por tipo (cliente/produto), reutilizado para somas com
`min_count=1`, contagens válidas e tamanho; `comparar_entidades` percorre
pares consecutivos. As métricas selecionadas são agregadas juntas. O pipeline
usa a métrica temporal principal e Lucro quando disponível. `main` conecta
os agregados após aplicar aliases e filtrar datas. Não repete mapping, ETL,
ingestão ou fuzzy. Agregados são temporários, fora de attrs e snapshots.

ID estável tem prioridade; nome é label (primeiro não nulo por ID). IDs
distintos com mesmo nome permanecem distintos. ID nulo não usa nome como
fallback. Sem ID, texto analítico exato, incluindo alias já confirmado.
`identity_source`: `stable_id`, `text`, `confirmed_alias`. Keep separate
mantém identidades separadas. Confirmação de alias não cria ID estável.

Recebe datas já tratadas, sem reinterpretar ISO. Nulos/infinitos não são zero.
Grupo sem métrica válida não é comparável. Nulos parciais/datas ausentes
entram na cobertura. Apenas entidades observadas nos dois meses recebem
delta/finding. `newly_observed` e `not_observed_current` contam presença
na janela; não significam novo cliente, perda, inatividade ou churn.
Não emitimos findings de ausência sem cobertura operacional demonstrável.

### Contribuição e evidências

Antes de comparar, todos os grupos, inclusive sem identidade, devem somar
o total global da mesma população. Divergência impede emissão no par;
tolerância de ponto flutuante: `rel_tol=1e-9`, `abs_tol=1e-6`.
Lacunas/bases zero, pequenas, negativas e mudança de sinal usam a Etapa 3.

```
delta = atual - anterior
contribution = delta / global_net_change * 100  # somente mesma direção
gross_negative_change_matched = soma dos módulos dos deltas negativos
gross_positive_change_matched = soma dos deltas positivos
share_of_gross_direction_matched = abs(delta) / bruto_da_direção * 100
unexplained_by_matched_pairs = global_net_change - soma dos deltas comparáveis
```

Fixture: A 50→20, B 30→20, C 20→30. Queda líquida 30, bruta 40;
A representa 100% da líquida e 75% da bruta. Outro teste verifica 250% de
contribuição líquida: compensações permitem exceder 100%, sem truncamento.
Brutos referem-se somente a pares observados nos dois meses. Residual inclui
entidades de um único mês e valores não atribuídos. Não é decomposição
perfeita nem causa comercial. Participações mensais ficam nulas se total
não positivo ou houver grupos negativos, evitando participação em saldo enganoso.

Evidência persiste identidade/label/origem, conceito, comparação, participações
e denominadores, delta global, contribuição, brutos, participação no bruto,
residual, contagens, cobertura, ausências e limiares. Só JSON, sem pandas.

### Regras, materialidade e limites

Versão 1: `customer_decline`, `customer_growth`,
`customer_contributor_decline`, `customer_contributor_growth`, e equivalentes
`product_*`. Contribuinte substitui o finding individual do mesmo evento;
o global pode coexistir por responder outra pergunta. Custo permanece
descritivo, sem interpretar aumento como melhora.

Critérios internos de triagem, não padrões universais:

| Critério | Regra |
|---|---|
| Referência | Maior entre mediana absoluta da série global e referência do par global |
| Emissão individual | Módulo do delta ≥2% da referência |
| Contribuinte | Mesma direção; delta global ≥10% da referência; contribuição ≥10%; cobertura suficiente |
| Cobertura suficiente | ≥95% identidade+métrica em cada mês e ≥95% das linhas de entrada com data |
| Impacto padrão | medium |
| Impacto high | Confiança medium e (delta ≥20% da referência ou contribuição ≥30%) |
| Confiança medium | Cobertura suficiente e ≥5 registros válidos, sem nulos da métrica, por entidade em cada mês |
| Confiança low | Amostra/cobertura insuficiente |

Não há confiança high: calendário operacional completo é desconhecido.
Limitação de identidade textual/alias fica explícita. Percentual indisponível
conserva delta e motivo. Prioridade usa a matriz anterior. ID do finding
inclui regra, conceito, escopo, entidade, janela e análise.

Até cinco por regra/métrica/período e **100 por tipo de entidade** na análise,
compartilhados entre métricas. Ordenação: prioridade, impacto, módulo do delta
e ID determinístico. Toda a população é consultada antes dos cortes.
Não é inventário exaustivo: períodos com finding global podem ter achados
individuais omitidos pelo corte. Recomendações apenas orientam investigar
variação observada e conferir cobertura, sem causa, insatisfação ou previsão.

### Validação real

Relatório: `reports/validacao_v15_entidades.json`. Sem novo upload de Excel.
CSV tratado 2017–2020: 11.795 linhas, 11.787 após filtro temporal existente.
Conceito Valor Total; sem dimensão produto identificada. Séries mensais
conferidas com relatório histórico anterior.

**2019-11 → 2019-12:** 162.125,00→96.879,74; delta −65.245,26.
29 clientes com observações nos dois meses. Principais reduções comparáveis:

| Cliente | Delta | Equivalência na queda líquida |
|---|---:|---:|
| COLEGIO AUGUSTO LARANJA | −8.116,02 | 12,44% |
| OSEIAS | −4.763,40 | 7,30% |
| DEPOSITO SANTO ANTONIO | −3.548,91 | 5,44% |
| GILVAN / JEFERSON / CILENE | −3.505,06 | 5,37% |
| AABM | −2.847,91 | 4,36% |

Queda bruta comparável 29.993,03; aumento bruto 16.072,17; residual −51.324,40.
81 identidades somente no mês atual e 114 somente no anterior. Não atribuir
o residual aos pares listados nem chamar ausência de churn.

**2019-12 → 2020-01:** delta +88.321,32; 26 pares comparáveis.
PRIMOSUL +4.630,75 (5,24%); PANORAMA +3.706,50 (4,20%);
EDSON +684,05 (0,77%). Aumento bruto 11.210,39; queda bruta 10.393,24;
residual +87.504,17. 106 identidades só no atual, 84 só no anterior.
Nenhum par atingiu contribuição de 10% nesse intervalo; não baixar limiar
para forçar achado nem imputar zero para explicar a alta.

100 achados selecionados: 14 contribuintes de queda, 12 de crescimento,
42 reduções e 32 aumentos individuais. As listas acima são cálculos de
validação antes do corte global, não todos cards finais. O JSON discrimina
os selecionados por intervalo. Portanto limite/materialidade podem omitir
alguns dos contribuintes calculados acima da saída final.

Merge real em memória com candidato persistido: MINERAÇÃO CAIEIRAS +
MINERAÇAO CAIEIRAS, 3.325→3.324 clientes; 632.033,34→650.591,83.
KPIs e série temporal iguais. Doze achados selecionados usam o label
canônico, nenhum usa a variante absorvida. Keep separate preservou exatamente
os achados. Sem detector e sem modificar snapshots originais da validação.

Produtos reais: `data/samples/Historico_Vendas.csv`, 10.000 linhas, Produto_ID
e Faturamento derivado pela regra existente Quantidade × Preço Unitário.
100 achados: 43 reduções, 29 aumentos, 17 contribuintes de crescimento e 11
de queda. Exemplo: ID 253, −61.416,36 entre 2018-02 e 2018-03. Nome não
inventado quando só havia ID. Fixture API valida mesmo ID com nomes diferentes.
CSV simples existente, três linhas: nenhum finding por entidade porque não
há pares consecutivos observados para a mesma identidade.

### Performance, testes e compatibilidade

Médias de três execuções, sem assert rígido de tempo:

| Base/tipo | Agregação | Comparação + findings | Adicional total |
|---|---:|---:|---:|
| 2017–2020 / clientes | 21,00 ms | 21,86 ms | 42,86 ms |
| Histórico de vendas / produtos | 32,12 ms | 21,22 ms | 53,34 ms |
| CSV simples / ambos | 5,37 ms | 0,10 ms | 5,47 ms |

Tempos isolam lógica adicional; não são benchmark HTTP. Sem dependências,
cache, paralelismo ou auditoria em attrs. Iteração direta sobre os agregados,
sem indexação pandas repetida para cada célula.

25 testes novos de src e dois de API. **284 src + 36 API = 320 aprovados**;
Python compile aprovado. Cobrem IDs, aliases, keep separate, nulos/infinitos,
datas ausentes, compensações, bases problemáticas, lacunas, população,
materialidade, limites, contrato, recomendações, deduplicação e persistência
após recriar API. Passaram suítes existentes de temporal/findings/clientes/
produtos/history/comparison/resolução de entidades.

Correções na implementação nova: atribuição nula em seleção vazia convertia
IDs inteiros em float; agora ocorre somente quando existe texto vazio.
Corrigida concordância: “redução observada” / “aumento observado”.

Integração aditiva; histórico não recalcula findings; snapshots antigos não
exigem migração/campos novos. Comparação usa o snapshot final sem matching
novo. Frontend intacto. Limites: calendário desconhecido, variantes textuais,
ausência não prova zero; sem churn/RFM, outras dimensões ou previsão.
Limitação ISO preexistente não alterada. CSV protegido e fontes/relatórios
originais preservados por SHA-256.

## 15. Etapa 5 — seleção executiva dos achados

### Auditoria e contrato aditivo

`insight_engine` deduplica o legado por categoria e texto, prioriza destino
risco/oportunidade/destaque e publica cinco riscos, cinco oportunidades e oito
insights. Sua diversidade antecede o preenchimento por relevância. Isso não
serve como identidade para findings de entidades/janelas distintas.
`findings` já deduplica por evento e ordena prioridade/impacto/confiança/ID;
a Etapa 4 seleciona por materialidade e limita entidades. Esses cálculos,
limiares e limites permanecem intactos, inclusive 100 achados por tipo.

`finding_selection.py` opera somente sobre a lista pronta, sem DataFrame,
groupby, mapping, ETL, fuzzy ou dependência nova. Reutiliza a ordem de níveis
e a deduplicação por ID. Novo campo: **`achados_principais`**, com no máximo
**oito itens**, coerente com os oito insights da apresentação atual.
`achados_analiticos` permanece completo dentro dos limites das regras existentes.
`main` seleciona após gerar todos os achados; resumo e relatório detalhado
armazenam ambos. Nenhum contrato legado foi removido ou frontend alterado.

Cada item executivo mantém todos os campos originais, inclusive evidência,
recomendação e razões de confiança. Acrescenta:

```
selection_reason: {
  priority, impact, confidence, materiality, family,
  policy: "diversity_within_same_rank"
}
show_recommendation: true | false
recommendation_reference: id do primeiro selecionado com o mesmo texto | null
```

`materiality` é razão existente nas evidências, nunca relevance score ou
pontuação nova. Para temporal usa `materialidade_absoluta`; para entidade,
numerador/denominador de `materiality`; para concentração, Top 5/100; para
negativos, participação da magnitude negativa/100. Ausência fica null e
perde desempate para evidência conhecida. Não compara deltas monetários
brutos de conceitos diferentes e não recalcula materialidade analítica.

### Ordem, diversidade e sobreposição

1. Deduplicar IDs, com desempate determinístico até para cópias conflitantes
   do mesmo ID, pela representação JSON ordenada.
2. Resolver somente sobreposição conhecida: individual e contribuinte da
   mesma entidade, conceito, escopo, janela e referência. Contribuinte é
   mantido por conter a explicação adicional. Não unir entidades/janelas.
3. Prioridade, impacto e confiança, nessa ordem, definem faixas estritas.
4. Dentro da mesma faixa, alternar famílias com menos itens já escolhidos.
   Dentro dessa escolha, maior materialidade conhecida e depois ID.
5. Parar em oito; não preencher com informação artificial.

Famílias: temporal, clientes, produtos, concentração, resultados negativos
e outros como fallback. Diversidade não atravessa faixas para promover um
achado inferior. Dez clientes podem dominar se forem efetivamente de faixa
superior; com relevância equivalente, famílias alternam. Isso evita prometer
diversidade que exigiria reduzir qualidade da evidência.

Se houver achados de impacto medium/high, os de impacto low ficam somente
na coleção completa. Se todos forem low, mostrar no máximo dois. Quando
há candidatos de confiança maior, os low confidence selecionados não podem
exceder dois nem a quantidade disponível de maior confiança. Se só houver
low confidence, podem aparecer até o limite, devidamente identificados.
Lista menor ou vazia é válida. Nenhuma classificação original é alterada.

Global e entidade da mesma janela podem coexistir: o primeiro descreve a
mudança; o segundo localiza parte dela. Não foi criado `related_finding_id`:
conceito e janela já permitem contextualizar os dois. Relação explícita fica
adiada até necessidade comprovada da apresentação, sem grafo de dependências.

### Recomendações e integração com o frontend

Revisadas as recomendações de concentração, negativos, temporal e entidades:
monitorar participação, revisar valores e investigar variações/cobertura.
Não afirmam causa, intenção ou previsão. O legado de insights/oportunidades
continua separado: inclui templates de estoque e avaliação condicionados a
entradas específicas, mas não é convertido automaticamente em findings nem
misturado à seleção. Nenhuma recomendação legada foi promovida para esta lista.

Recomendação continua anexada ao finding. Texto repetido, comparado após
normalizar somente espaços e caixa, recebe `show_recommendation=false` e
referência ao primeiro item executivo. `recommendation` original e evidência
não são removidos, nem há segunda lista de recomendações.

A Etapa 6 implementou os seguintes critérios:
- usar a ordem persistida de `achados_principais` para cards executivos;
- respeitar `show_recommendation` e, se útil, a referência para não repetir texto;
- permitir explorar `achados_analiticos` separadamente, preservando evidências;
- distinguir campo ausente (snapshot anterior) de lista vazia (seleção executada);
- em snapshots antigos, manter apresentação legada, sem fabricar seleção;
- não mostrar simultaneamente todas as listas legadas e novas sobre o mesmo
  assunto como se fossem conclusões independentes.

### API, persistência e compatibilidade

Novo campo passa aditivamente por POST analysis, GET latest e detalhe do
histórico. History list continua sendo índice, não uma cópia de todas as
evidências. Merge recalcula findings e seleção na continuação existente;
keep separate preserva a seleção correspondente. Recriar a API não a altera.
Leitura histórica não executa seletor: snapshots sem o campo continuam sem
ele. Sem migração. Comparação continua independente, sem comparar findings
ou fazer matching entre análises.

### Validação real e performance

Relatório: `reports/validacao_v15_selecao.json`. Usa fontes existentes,
sem upload pesado. Mede somente seleção, cinco execuções por base.

| Base | Coleção completa | Famílias completas | Prioridades | Seleção |
|---|---:|---|---|---:|
| 2017–2020 | 116 | 100 clientes, 14 temporais, 1 concentração, 1 negativos | 80 medium, 36 low | 8: 2 temporais, 6 clientes |
| Historico_Vendas.csv | 231 | 100 clientes, 100 produtos, 30 temporais, 1 concentração | 30 medium, 201 low | 8 temporais |
| CSV simples | 5 | 4 temporais, 1 concentração | 5 low | 4 temporais |

Na base de produtos, achados de entidades possuem confiança/prioridade
inferiores aos temporais. Não foram promovidos somente para representar
famílias. Nos testes sintéticos de mesma faixa, clientes/produtos/temporal
alternam corretamente. No CSV simples, quatro achados têm confiança low;
essa limitação é mantida, não há preenchimento até oito.

Seleção 2017–2020, na ordem (todos prioridade medium/confiança medium):

| Achado | Janela | Delta de Valor Total | Impacto |
|---|---|---:|---|
| Aumento temporal | 2019-12 → 2020-01 | +88.321,32 | high |
| TRIVU, contribuinte da queda (65,42%) | 2017-05 → 2017-06 | −12.733,47 | high |
| TRIVU, contribuinte da queda (52,96%) | 2017-08 → 2017-09 | −10.824,82 | high |
| ALFA, contribuinte do aumento (43,19%) | 2020-02 → 2020-03 | +9.486,26 | high |
| CHARLES, contribuinte da queda (34,80%) | 2018-10 → 2018-11 | −9.141,24 | high |
| ALFA, contribuinte da queda (35,39%) | 2017-08 → 2017-09 | −7.233,60 | high |
| Aumento temporal | 2020-09 → 2020-10 | +193.977,60 | medium |
| SALVADOR, aumento individual | 2018-04 → 2018-05 | +21.742,01 | medium |

IDs completos, títulos, evidências e `selection_reason` estão no JSON.
Mesmo cliente em janelas diferentes permanece evento distinto. Não há
preferência por recência nesta etapa: todo o histórico analisado é elegível.
Concentração Top 5 22,28% e três clientes com Margem Bruta negativa (−40,99
em população 3.324) permanecem low impact na coleção completa, fora da seleção.

Tempo médio: **6,17 ms** para 116 achados; **15,50 ms** para 231 achados;
**0,22 ms** para cinco achados. Sem assert rígido, novo benchmark HTTP ou
impacto em cálculos. Coleções completas conferidas antes/depois; seleção
idêntica para entrada invertida. Fontes, CSV protegido e relatórios anteriores
conferidos por hash. Sem estruturas pesadas em attrs.

### Testes e fechamento da etapa

17 testes novos de seleção e dois novos de API; testes existentes de merge,
keep separate e snapshots foram estendidos. Cobertura: vazio/um/poucos/muitos,
famílias, faixas de prioridade/impacto/confiança, materialidade desconhecida,
baixo impacto, baixa confiança, entrada embaralhada, duplicatas, coexistência
global/entidade, preservação de evidências, recomendações e seleção aditiva.
API verifica analysis/latest/detail, relatório detalhado e leitura de snapshot
da Etapa 4 sem executar seleção retroativa.

Python compile aprovado; **301 testes src + 38 API = 339 testes permanentes
aprovados**. Incluem as suítes anteriores de analytics, resolução de entidades,
histórico e comparação. Nenhuma regressão encontrada nas validações executadas.
Frontend não alterado nem revalidado nesta etapa.

Limitações: seleção não certifica causas nem calendário operacional; não
prioriza recência; diversidade não promove evidência inferior; textos de
recomendação distintos permanecem distintos, sem deduplicação por NLP.
Não corrige ingestão ISO, não migra snapshots e não relaciona achados entre
análises. Limite de 100 por tipo na coleção completa permanece deliberadamente
intacto. Nenhum score, LLM, nova dependência ou otimização paralela.

## 16. Etapa 6 — frontend de inteligência analítica

### Apresentação e contrato

A Visão Geral apresenta **Principais Achados logo após os KPIs**, na ordem
armazenada em achados_principais. O contador informa principais/coleção
completa; a interface não escolhe nem recalcula achados. O link **Ver todos
os achados** leva à página Oportunidades existente, que acomoda a exploração
sem nova rota ou alteração da sidebar. Os KPIs e o tema permanecem intactos.

types/findings.ts descreve o JSON real: evidências, comparação, entidade,
janela, níveis, recomendação e metadados de seleção. Os dois campos são
opcionais em ExecutiveSummary. AnalysisContext e serviço já transportavam
o JSON sem remover campos; não precisaram de alteração. Nenhuma mudança
no backend, regra, contrato público ou dependência nesta etapa.

Componentes pequenos:
- AnalyticalFindingCard: título, resumo, família, prioridade, impacto,
  confiança, conceito, entidade/janela e variação.
- FindingEvidenceDetails: expansão inline com valores anteriores/atuais,
  delta, participação, contribuição e seu denominador, população/cobertura
  disponível e razões de confiança. Não renderiza objetos crus ou limiares
  internos. A contribuição líquida não é apresentada como decomposição perfeita.
- AnalyticalFindingsExplorer: filtros combinados por família, prioridade,
  impacto e confiança, dez cards por página; mudança de filtro volta à primeira.
- utils/findings.ts: labels, famílias pela regra/escopo e formatação segura.

Conceitos usam metric_label, preservando Valor Total e Margem Bruta.
Unidade BRL explícita usa formatter existente; outra moeda ISO explícita usa
Intl. Sem moeda declarada, exibe número pt-BR sem assumir reais. Percentual
é exibido somente quando válido e finito; null não vira zero. Motivos de
base pequena, negativa ou zero são traduzidos. A direção não é reinterpretada
como causa, churn, demanda ou previsão.

Recomendações são exibidas quando há texto e show_recommendation != false.
A referência não aparece como ID técnico. selection_reason recebe uma frase
curta com os níveis persistidos, no detalhe. Não há score novo nem JSON visual.

### Compatibilidade e acessibilidade

Campo achados_principais presente (inclusive vazio) ativa a experiência
V1.5 em Overview/Oportunidades e evita duplicação das três listas legadas
nesses locais. Ausência do campo mantém a apresentação anterior, sem fabricar
findings. Lista vazia comunica insuficiência de evidências, não ausência de
problemas. Históricos usam seu snapshot e preservam HistoricalAnalysisNotice.

Merge e keep separate atualizam o resumo recebido no POST pelo contexto
existente, sem GET redundante de latest. Paginação, filtros e expansão usam
controles nativos; expansão possui aria-expanded/aria-controls, filtros têm
labels explícitos, foco visível e níveis escritos, sem depender de cor. Novos
ícones são Lucide React. Evidências só são montadas quando abertas.

### Validação e limites

reports/validacao_v15_frontend.json consolida os testes e a inspeção visual.
Três resultados reais reconstruídos a partir das fontes já existentes, sem
upload pesado e sem escrever nas fontes, foram servidos por interceptação
da API no navegador Edge. Essa validação verifica os cards reais; não é um
novo benchmark HTTP ou nova homologação da ingestão. O restante do resumo
na sessão visual usa a fixture de layout.

| Base | Coleção | Principais | Cards por página de exploração |
|---|---:|---:|---:|
| 2017–2020 | 116 | 8 | 10 |
| Histórico de Vendas | 231 | 8 | 10 |
| CSV simples | 5 | 4 | 5 |

Os três cenários passaram em 1440, 390 e 320 px, sem overflow horizontal ou
erro JavaScript. Inspeção das capturas confirmou textos legíveis, acentos e
evidências. Concentração/negativos low da base complexa permanecem fora dos
principais, conforme backend. Nenhuma alteração da seleção para atender à UI.

Doze testes permanentes novos cobrem cards, expansão por teclado, lista
vazia, legado, três bases com percentual bloqueado, filtros, paginação,
conceitos, contribuição, histórico, merge e keep separate sem latest extra.
Não houve redesign ou migração de snapshots. Limites: a tela usa os limites
analíticos existentes e não oferece busca avançada; evidências futuras com
novos formatos precisarão de apresentação explícita. O legado pode manter
seus textos históricos, sem correção destrutiva. A limitação ISO e os limites
analíticos das etapas anteriores continuam fora deste escopo.

Validação final: TypeScript e Vite build aprovados; 94 testes Playwright e
38 testes API aprovados, total de 132 testes permanentes nesta etapa. Os
12 novos estão incluídos nos 94. Três cenários visuais temporários (nove
combinações de base/largura) não entram nesse total. Uma falha transitória
no teste legado de Dados ocorreu na primeira suíte: os nove testes da área
passaram isoladamente e a suíte completa seguinte passou sem alteração
de produção nessa área. Não foi possível atribuir a falha a uma causa
específica. Os scripts temporários foram removidos após consolidar evidências.

## 17. Homologação final da V1.5

A homologação integrada da release candidate foi concluída na branch
`feature/v1.5-analytical-intelligence`. A validação cobriu backend, API,
frontend, histórico, comparação, resolução de entidades e os três cenários
de dados usados nas etapas anteriores.

O cenário complexo de 2017 a 2020 produziu 11.795 linhas normalizadas,
11.787 linhas analíticas, 48 meses, 116 achados completos e 8 achados
principais. O histórico de vendas produziu 231 achados completos e 8
principais. O CSV simples produziu 5 achados e 4 principais. A seleção foi
determinística, preservou diversidade sem promover concentração ou negativos
de baixo impacto e não recalculou dados no frontend.

O fluxo real de resolução confirmou merge, keep separate e idempotência. O
merge de MINERAÇÃO CAIEIRAS com MINERAÇAO CAIEIRAS manteve os dados de origem,
recalculou a camada analítica e atualizou os achados pela resposta do POST,
sem GET redundante de `/latest`. Histórico V1.5, snapshot antigo e comparação
abriram sem migração ou recálculo retroativo. O mapping assistido, a auditoria
de ingestão/transformações e o fallback legado permaneceram disponíveis.

Na medição integrada, a resposta HTTP do merge levou 1,647 s e a atualização
visível levou 1,792 s; analytics consumiram aproximadamente 0,825 s. A
agregação, geração e seleção de achados somaram cerca de 65 ms no cenário
complexo. Isso preserva o ganho da V1.4 (baseline de 18,976 s para 1,442 s
médio) sem introduzir estruturas pesadas em `DataFrame.attrs`.

Foram aprovados compile Python, 301 testes permanentes de `src`, 38 testes
permanentes de API, TypeScript, build Vite, 94 testes Playwright da suíte
principal e 7 testes da suíte permanente de upload, totalizando 440 testes
permanentes. A falha transitória observada na etapa anterior não se repetiu
na suíte completa final. A única ocorrência de console no navegador foi o
404 do `favicon.ico`, artefato cosmético preexistente sem impacto no fluxo;
não há exceções React ou erros HTTP inesperados.

As limitações mantidas são: interpretação ISO/dayfirst preexistente, ausência
de churn, previsão e causalidade, ausência de LLM, paginação de servidor e
busca avançada, além de heurísticas internas de materialidade e ausência de
matching de findings entre históricos. Elas não bloqueiam a release porque
estão fora do escopo homologado.
