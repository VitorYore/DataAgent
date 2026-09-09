# V1.0 — qualidade na página Dados

O resumo passa a incluir `dados`, automaticamente entregue pelo POST de análise
e pelo GET da última análise. Nenhum endpoint ou dependência foi adicionado.
O upload, bloqueio durante processamento, tratamento de erros, atualização do
contexto e navegação para Overview continuam iguais. Ao voltar a Dados, a
qualidade da análise nova já está disponível sem outro GET.

## Contrato

`dados` contém arquivos (nome, linhas, colunas), quantidade de arquivos, status,
escopo, quantidade de linhas/colunas, duplicadas, total de nulos, percentual geral
de nulos, quantidade de problemas, score/classificação, problemas, transformações
e ingestão. O diagnóstico é da tabela analítica após limpeza estrutural e antes
do ETL, inclusive em multitabela. Os tamanhos por arquivo são os de cada tabela
carregada após inspeção estrutural. Não se informam tamanhos em bytes inexistentes.

Problemas reutilizam `gerar_problemas`, mantendo os campos existentes e expondo
`nivel` a partir de `severidade`; são apresentados em ordem alta, média, baixa.
Transformações vêm exclusivamente de `logs_etl`: tipo, coluna, antes, depois e
descrição dos detalhes originais. O timestamp técnico não aparece na interface.
Ingestão vem de `diagnostico.ingestao`, por arquivo quando houver múltiplas tabelas.

## Score de qualidade

Começa em 100. Subtrações:

- Nulos: `min(30, total_nulos / total_celulas * 100)`.
- Duplicadas: `min(20, linhas_duplicadas / quantidade_linhas * 100)`.
- Severidade: 10 por problema alto e 5 por médio, limitados a 30 no total.
- Cabeçalho: 10 se algum arquivo teve `cabecalho_detectado = false`.
- Colunas vazias removidas: 1 por coluna, limitados a 10 no total.

Limita-se o resultado entre 0 e 100 e arredonda-se a duas casas. Classificação:
excelente >= 90, boa >= 75, atenção >= 50, crítica < 50. Tabela sem células não
recebe score nem percentual inventados. Campos de ingestão ausentes não geram
penalidades presumidas. Esse indicador mede qualidade pré-ETL; não modifica o
score executivo nem qualquer análise de negócio.

## Página Dados

Upload preservado no topo; abaixo ficam Última análise, Arquivos analisados,
Qualidade dos dados, Problemas encontrados, Transformações realizadas e Estrutura
do arquivo. Há barra simples para o score e aviso de colunas genéricas quando não
foi detectado cabeçalho. Relatórios antigos sem `dados` exibem estado vazio seguro.
Listas vazias e informações ausentes são distinguidas, sem inventar valores.

## Validação final

66 testes Python, 42 testes de navegador da suíte geral e três testes de upload
real passaram: **111 testes**. Build/TypeScript passaram. Uploads foram testados
com CSV, XLSX, XLS e múltiplas tabelas. `docs/v10-validacao.json` registra os
resultados reais do POST/GET e da execução dos 14 arquivos de exemplo.

| Entrada atual | Linhas | Colunas | Nulos | Duplicadas | Problemas | Transformações | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| vendas_tratadas.csv | 3385 | 11 | 10629 | 6 | 15 | 3 | 51,28 |
| PLANILHA VITOR.xlsx | 3385 | 11 | 10629 | 6 | 15 | 3 | 38,28 |
| 14 arquivos de exemplo | 20000 | 48 | 49032 | 0 | 8 | 1 | 89,89 |

O CSV atual foi gerado da PLANILHA VITOR e contém nomes genéricos. Não é mais o
CSV semântico de 3.295 linhas usado anteriormente na V0.9. Sem nomes semânticos,
os KPIs financeiros continuam indisponíveis; não houve inferência de mapeamento.
No XLSX, o cabeçalho ausente e três colunas vazias removidas explicam a diferença
de score em relação ao CSV já exportado.

Nos 14 exemplos, todos os campos anteriores do resumo executivo ficaram idênticos
ao baseline: somente `dados` foi acrescentado.

Correção mínima adicional: o inspetor agora reconhece nomes `coluna_N` exportados
pelo próprio DataAgent como labels estruturais, evitando consumir o cabeçalho
como uma linha de dados na releitura. Isso não atribui semântica a essas colunas.
Um teste existente foi ajustado para análises legitimamente sem insights, e o
teste de upload distingue o GET inicial de Dados de chamadas após o POST.

Durante uma primeira tentativa de teste de navegador, uma rota escapou do servidor
isolado e publicou dados sintéticos no servidor ativo. Os quatro arquivos de
relatório/dataset foram restaurados da cópia preservada da PLANILHA VITOR na
validação V0.9. A igualdade byte a byte foi conferida antes e depois da repetição
isolada, que passou. Nenhum dado sintético permaneceu como análise ativa.

Análises antigas continuam válidas; execute uma nova análise para obter `dados`.
Não foram alterados módulos analíticos, motor de insights, relacionamentos ou API.
