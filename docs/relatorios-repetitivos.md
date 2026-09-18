# Relatórios repetitivos sem cabeçalho: diagnóstico e correção

## Evidência anterior à alteração

O diagnóstico existente foi lido antes de modificar o código e preservado em `.validation-repetition/diagnostico-antes.json`. O original foi encontrado em Downloads; o relatório salvo identifica o mesmo arquivo, `2017 a 2020.xlsx`. Há uma aba, Planilha1, lida com `header=None`: 12.681 linhas e 14 colunas. A formatação se estende além dessas colunas, mas não constitui dados. Foram inspecionadas as primeiras linhas, o meio e o final, mesclagens, fórmulas, tipos e padrões.

- 12.161 linhas com conteúdo e 520 vazias.
- 214 regiões mescladas; 9.027 fórmulas, 73 sem resultado disponível na leitura.
- Tipos de células da leitura raw: 52.466 números, 11.792 datas, 24.100 textos e 89.176 vazios.
- Início: separador mensal e registros com identificador, data nativa, valores e descrições. Meio: mesma estrutura com dois campos numéricos opcionais preenchidos. Final: meta diária, dias úteis, indicadores e vazios.
- O padrão `N D N N T T N N` ocorre 7.964 vezes. Uma variante com campos opcionais vazios ocorre 3.132 vezes. A moeda exibida nesse arquivo é majoritariamente formatação numérica do Excel, não texto em coluna separada.
- Há um cabeçalho real na linha 3.956. Não foi usado para atribuir retroativamente significado aos registros anteriores.

A confiança antiga era **98,94%**, com 11.812 registros candidatos, 144 resumos, 46 períodos, 127 desconhecidas e dois blocos. O limiar principal de linha era 80%, mas o bloqueio final exigia zero desconhecidas. Portanto, não era simplesmente falta de cabeçalho ou baixa confiança.

Das desconhecidas, 73 eram linhas com fórmulas sem resultado; outras incluíam rótulos com número antes do texto, como dias úteis, indicadores isolados e observações. A similaridade anterior também contava vazios como concordância, favorecendo linhas esparsas. Totais sem rótulo, contendo fórmulas de soma de intervalos, chegaram a ser classificados como registros. Era necessário corrigir isso antes de permitir o arquivo.

## Estratégia implementada

`row_patterns.py` calcula assinaturas sem nomes de negócio, identifica possíveis IDs por valores inteiros predominantemente únicos e mede repetição global e por blocos. Datas reforçam a evidência, mas não são obrigatórias. Campos opcionais podem estar vazios; colunas vazias não contribuem artificialmente para a compatibilidade.

O caminho adicional exige **pelo menos 20 registros compatíveis por bloco**, **95% de compatibilidade**, ausência de blocos fortes incompatíveis e presença suficiente de campos. O threshold antigo não foi reduzido. Os testes pequenos anteriores continuam usando as regras conservadoras existentes.

Períodos aceitam meses completos/abreviados em português e inglês, combinações com ano, anos e trimestres. A posição é irrelevante. Resumos encerram sequências de registros, sem invalidar automaticamente os próximos blocos. Totais com fórmulas agregadoras e ausência das âncoras de registro são separados mesmo sem rótulo. Linhas numéricas ou descrições com valores, esparsas e dentro de uma região já reconhecida como resumo, são preservadas nessa região, sem gerar métricas.

Continuações com padrão físico comprovado podem ser reunidas. Se uma parte não tinha cabeçalho, a combinação conserva nomes neutros; o cabeçalho encontrado mais adiante permanece na auditoria. Nenhum valor passa a ser chamado de faturamento ou lucro por sua posição.

## Resíduos e fórmulas: limites explícitos

Resíduos só podem permanecer fora dos registros sem bloquear o arquivo quando:

- há blocos fortes compatíveis;
- cobertura classificada é pelo menos 99%;
- desconhecidos são no máximo 0,5% das linhas com conteúdo;
- cada resíduo tem no máximo dois campos preenchidos;
- não há data ou identificador compatível com os registros.

Todos os valores e coordenadas continuam na auditoria. Uma linha incompleta com ID, blocos incompatíveis, desconhecidos numerosos ou padrão fraco continuam exigindo revisão. Não há tratamento especial pelo nome do arquivo, mês, ano ou posição de coluna.

Uma fórmula sem resultado pode permanecer como valor nulo somente em coluna com pelo menos 20 fórmulas e 95% de resultados disponíveis, dentro de linha pertencente a bloco forte. Sua expressão original é preservada; nada é recalculado. Fórmulas indisponíveis em massa continuam bloqueando. A qualidade informa essas células e os resíduos explicitamente.

## API e frontend

O POST existente mantém a resposta de sucesso. Em revisão, `detail` agora contém `mensagem`, `confianca` em percentual de 0 a 100, `motivo`, contagens quando disponíveis e o nome seguro `diagnostico_estrutural.json`. O diagnóstico completo permanece no campo existente e no arquivo. Não são incluídos caminhos absolutos no detalhe público.

O serviço React aceita o novo objeto e preserva os erros textuais antigos. A página Dados mostra mensagem, confiança, motivo e HTTP 422 pelo tratamento existente. Isso não é classificado como falha de conexão; os arquivos selecionados permanecem disponíveis para nova tentativa.

O terminal deixou de imprimir toda a auditoria por linha: ela gerava dezenas de megabytes de saída. Somente o log mudou; o diagnóstico completo continua salvo em JSON. Nenhum módulo analítico, cálculo, ETL ou regra de relacionamento foi modificado.

## Resultado real

O POST HTTP completo, usando FastAPI/Uvicorn em armazenamento isolado, retornou **200 em 91,18 segundos**. Foram extraídos:

| Informação | Resultado |
|---|---:|
| Linhas originais | 12.681 |
| Linhas com conteúdo | 12.161 |
| Registros | 11.795 |
| Blocos transacionais repetitivos | 48 |
| Resumos | 316 |
| Períodos | 46 |
| Vazias | 520 |
| Desconhecidas preservadas | 3 |
| Cabeçalhos preservados | 1 |
| Cobertura classificada | 99,97% |
| Confiança do arquivo (medida existente) | 99,97% |
| Compatibilidade global de padrões candidatos | 98,69% |
| Menor compatibilidade entre blocos fortes | 96,67% |

A assinatura principal é `I D N N T T N N`, seguida de posições vazias. `I` significa identificador provável, não pedido. As três linhas residuais são duas observações esparsas com valor e uma observação de transferência para outro período. As 73 fórmulas sem resultado ficam auditadas com células nulas.

Os KPIs retornaram `null`: a estrutura foi recuperada com nomes neutros e a semântica financeira não foi inventada. Há três registros com conteúdo de data não reconhecido como data; os valores originais foram preservados, sem corrigir datas por suposição. Os resumos, períodos e vazios não integram os registros.

## Testes e regressão

Foram acrescentados 19 testes Python de repetição e um teste de frontend para o 422 estruturado. A regressão cobre CSV/Excel convencional, arquivos sem cabeçalho, várias ordens e quantidades de colunas, com/sem data, IDs em outra posição, blocos compatíveis/incompatíveis, fórmulas e resíduos, relatórios ambíguos, API, histórico e qualidade. Os cinco testes de upload real existentes continuam sendo executados.

Os 14 datasets de samples e vendas_tratadas.csv mantiveram shape, nomes de colunas e hash dos valores em relação ao baseline anterior. Exemplos e contagens completos estão em [relatorios-repetitivos-validacao.json](relatorios-repetitivos-validacao.json).

Resultado final: **212 testes aprovados** (154 Python, 53 de interface e 5 de upload real). TypeScript e build passaram. Nenhuma regressão encontrada nas verificações executadas.

Limitações: confiança estrutural não prova completude financeira; resíduos permanecem disponíveis para revisão humana. Não há inferência de significado financeiro, correção automática de datas, avaliação de fórmulas ou conversão de moeda. A auditoria detalhada aumenta o tamanho da resposta e o custo de processamento. Nenhum commit, push ou tag foi realizado.
