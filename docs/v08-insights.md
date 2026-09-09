# V0.8 — organização de insights

O fluxo continua sendo módulos analíticos → resumo executivo → API → frontend.
`src/analytics/insight_engine.py` centraliza normalização, deduplicação, seleção
e conversão para o contrato público. Não calcula KPIs nem executa consultas externas.

## Modelo e compatibilidade

O motor usa dicionários com `categoria`, `tipo`, `prioridade`, `texto` e contexto
opcional (`valor`, `metrica`, `origem`, `periodo`). Os tipos internos são `risco`,
`oportunidade`, `destaque` e `informativo`. Os geradores mantêm também os campos
legados para os consumidores de `analise.json`, logs do CLI e cálculo do score.

O contrato real do frontend é uma lista de **objetos**, não de strings:
`mensagem`, `categoria`, `prioridade` e, nos insights gerais, `tipo`.
Esse contrato foi preservado, incluindo `atencao` e `positivo` na saída pública.
Converter as listas para strings quebraria os cards e filtros existentes.
O modelo interno e seus campos adicionais não são exigidos pelo frontend.

## Categorias

- Temporal: `tendencia_faturamento`, `tendencia_lucro`,
  `sequencia_quedas_faturamento`, `melhor_periodo`, `maior_crescimento`, `maior_queda`.
- Resultado: `resultado_negativo`.
- Clientes: `cliente_concentracao`, `cliente_destaque`.
- Produtos: `produto_volume`, `produto_faturamento`, `produto_rentabilidade`,
  `produto_crescimento`, `produto_devolucao`, `produto_avaliacao_positiva`,
  `produto_avaliacao_negativa`.
- Estoque: `estoque_ruptura`, `estoque_excessivo`.
- Dimensões: `canal_desempenho`, `loja_desempenho`, `colaborador_desempenho`.

Os destaques dimensionais usam rankings existentes e não classificam pequenas
diferenças como oportunidades. Valores ausentes não são substituídos por zero.

## Seleção

1. `organizar_listas` reúne todas as fontes e resolve globalmente uma conclusão
   por categoria. Em conflito de classificação, risco precede oportunidade,
   que precede destaque/informativo.
2. Dentro dessa precedência, maior prioridade vence: alta, média, baixa. Preservam-se as prioridades
   analíticas existentes; os destaques dimensionais complementares são baixos.
3. Em empate, vence a quantidade de campos de contexto preenchidos
   (`valor`, `metrica`, `periodo`), seguida pela presença de número no texto
   e pelo comprimento da mensagem. Esse último é apenas um desempate simples,
   não uma interpretação semântica. Empates completos mantêm a primeira origem.
4. Uma segunda proteção remove textos iguais após normalizar espaços e caixa,
   inclusive quando suas categorias são diferentes. Somente depois separam-se
   riscos, oportunidades e destaques/informativos. Um evento tem um único destino;
   itens além do limite não reaparecem em outra seção.
5. Riscos e oportunidades têm até cinco itens cada. Os insights gerais contêm
   somente destaques/informativos e escolhem primeiro assuntos distintos (temporal, clientes, produtos,
   estoque e demais categorias), completa até oito por relevância e ordena a
   seleção por prioridade/contexto. Com poucos fatos, retorna menos de oito.

A deduplicação por categoria é intencionalmente conservadora: vários produtos
na mesma categoria de oportunidade originam uma conclusão no resumo. Os detalhes
analíticos permanecem disponíveis no relatório completo. Listas específicas,
como `clientes.insights_clientes`, são preservadas; o gerador de clientes já
emite frases distintas por métrica. O score continua recebendo os alertas
originais, antes da seleção executiva.

## Validação

Executado no ambiente local:

```powershell
.venv\Scripts\python.exe -m unittest src.analytics.test_insight_engine src.analytics.test_customers api.test_app api.test_upload
cd frontend
npm run build
```

Resultado: 34 testes Python passaram (16 novos e 18 existentes). Build, incluindo
TypeScript, passou. Nenhuma dependência ou código frontend foi alterado.

Foram executadas análises completas dos 14 CSVs em `data/samples` antes e depois,
com saídas isoladas, sem sobrescrever os relatórios usados pela aplicação.
KPIs, análise temporal, clientes, desempenho, crescimento, dimensões, produtos
e status executivo ficaram idênticos. A comparação das listas está em
`v08-comparacao.json`; esse arquivo é uma evidência de teste, não um recurso de
histórico de análises.

Exemplo observado: as duas mensagens sobre 604 registros negativos foram
reduzidas à de prioridade alta. Os riscos passaram de quatro para três;
oportunidades de três para uma; insights gerais de seis para oito, com maior
diversidade. Não houve inferência de fatos por similaridade textual ou IA.

Relatórios já salvos continuam legíveis. Gere uma nova análise para obter as
listas organizadas pela V0.8 na aplicação.

## Correção da deduplicação entre seções

A implementação inicial ainda incluía riscos e oportunidades nos insights gerais,
e a página Oportunidades misturava riscos e insights em Pontos de Atenção.
Agora o resumo usa uma chamada central a `organizar_listas`, e a página apresenta
cada lista em sua seção. Labels de categorias são apenas formatação de apresentação.

Validação adicional: 40 testes Python e 37 testes de navegador passaram;
build/TypeScript passaram.
`v08-deduplicacao-global.json` contém as listas reais obtidas com
`data/processed/vendas_tratadas.csv`: três riscos, nenhuma oportunidade e quatro
insights. Nenhuma categoria ou texto se repete entre as listas.

O arquivo local usa ponto e vírgula. A validação o leu com `pd.read_csv(..., sep=';')`
e executou `executar_pipeline_analitico` com saída temporária. O loader de uploads
atual espera vírgulas e falha para esse arquivo; esse problema preexistente de
ingestão não foi modificado nesta correção de insights. O resultado local de maior
queda foi 2020-04 (36,34%), diferente do exemplo 2020-11 (46,05%) do pedido.
Os cálculos existentes foram preservados. Para corrigir também a exibição atual,
somente as três listas de `reports/resumo_executivo.json` foram reorganizadas a
partir dos candidatos existentes em `reports/analise.json`, após conferir que os
KPIs dos dois arquivos correspondiam. Os demais blocos foram preservados. O
relatório ativo mantém a queda de 2020-11 (46,05%) já calculada anteriormente.
