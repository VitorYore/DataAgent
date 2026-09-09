# V0.9 — validação concluída

A ingestão continua retornando DataFrames. Os loaders único e multitabela
compartilham a inspeção estrutural, sem alteração nas regras analíticas.
Não há repositório `.git` nesta pasta; o estado foi revisado pelos arquivos
existentes e comparado com o baseline de `.validation-v09/before`.

## Estrutura

São inspecionadas até 20 linhas sem cabeçalho. A pontuação combina proporção de
texto, preenchimento, diversidade dos nomes, termos comuns e contraste de tipos
com até cinco linhas seguintes. Confiança mínima: 70/100. A confiança é uma
heurística, não uma probabilidade. A linha de cabeçalho no diagnóstico começa em 1.
Números, datas e códigos não são considerados bons labels. Acentos são ignorados
somente na comparação interna dos termos; permanecem nos nomes resultantes.

Sem evidência suficiente, todas as linhas são preservadas com nomes `coluna_N`.
Uma exceção para arquivos contendo apenas uma linha de labels foi restringida a
essa condição: antes, podia selecionar erroneamente a última linha de uma tabela
textual. A correção tem teste de regressão, inclusive no limite da amostra.

Removem-se somente linhas e colunas inteiramente nulas ou em branco. Colunas com
95% ou mais de nulos são registradas, mas permanecem se houver algum dado.
`Unnamed` com dados recebe um nome genérico; `Unnamed` vazio é removido.
Nomes recebem `str(...).strip()` e sufixos únicos, como `Valor_2`. Colisões com
nomes já existentes são evitadas. Renomeações são uma lista com posição, original
e novo nome, para registrar corretamente várias ocorrências de um nome duplicado.

CSV aceita separadores comuns (vírgula, ponto e vírgula, tabulação e barra
vertical), UTF-8/BOM e fallback Latin-1. XLSX e XLS usam os leitores existentes.
O relatório fica em `df.attrs['ingestao']` e em `diagnostico.ingestao`; no modo
multitabela, há um relatório independente para cada tabela.

## Resultados reais

### vendas_tratadas.csv

3.295 linhas, nove colunas, mesmos nomes, tipos e valores. Cabeçalho na linha 1,
confiança 93,33, separador `;`. Nenhuma linha ou coluna removida.
KPIs e resumo executivo integralmente iguais à leitura anterior correta com `sep=';'`:

- Faturamento: 2.778.601,77.
- Lucro: 1.075.124,74.
- Custo: 2.842.340,75.
- Margem: 38,69%; ticket: 855,48; pedidos: 3.248.
- Quantidade vendida: null, como anteriormente.

### PLANILHA VITOR.xlsx

Arquivo validado: `C:\Users\User\Downloads\PLANILHA VITOR.xlsx`, primeira aba.
A primeira linha contém dados; nenhum cabeçalho real foi detectado na amostra.
A leitura antiga consumia a primeira transação como cabeçalho e falhava ao
serializar o diagnóstico com uma chave datetime. A leitura nova preserva a
transação 20686 e termina o pipeline com nomes genéricos, sem inventar semântica.

Antes: 3.508 linhas e 14 colunas, pois a primeira linha era consumida.
Depois: 3.385 linhas e 11 colunas — 3.509 linhas originais menos 124 vazias,
com três colunas inteiramente vazias removidas. A igualdade de todas as células
restantes foi verificada contra a leitura bruta com `header=None`.

`coluna_9`, `coluna_10` e `coluna_14` permaneceram, apesar de 98,49%, 99,89% e
99,97% de nulos. Os KPIs nulos pertencem a este arquivo: nomes genéricos não
identificam faturamento/lucro para o mapeamento semântico atual. Isso é esperado;
não foram inventados mapeamentos nem modificados os módulos analíticos.

### 14 arquivos de data/samples

Pipeline multitabela completo executado; resumo executivo idêntico ao baseline
anterior à V0.9. Confirmados os 14 relatórios independentes de ingestão.

## Testes e evidências

57 testes Python passaram: 40 existentes e 17 de ingestão. Cobertura inclui CSV,
XLSX, XLS, títulos antes do cabeçalho, tabelas sem cabeçalho, colunas vazias,
Unnamed com dados, duplicados, linhas parciais, codificações, múltiplas tabelas,
diagnóstico, API e regressões analíticas.

```powershell
.venv\Scripts\python.exe -m unittest src.ingestion.test_structure_inspector src.analytics.test_insight_engine src.analytics.test_customers api.test_app api.test_upload
.venv\Scripts\python.exe -c "import runpy; runpy.run_path('.validation-v09/validate.py')"
```

Comparação completa: `docs/v09-validacao.json`. Saídas de validação permanecem
isoladas em `.validation-v09`; os relatórios ativos e arquivos originais não
foram sobrescritos. Nenhuma regressão permaneceu nos casos testados. Nenhuma
dependência, funcionalidade de frontend ou regra analítica foi adicionada.

Exemplo abreviado do diagnóstico real:

```json
{
  "arquivo": "PLANILHA VITOR.xlsx",
  "cabecalho_detectado": false,
  "linha_cabecalho": null,
  "confianca_cabecalho": 0.0,
  "linhas_vazias_removidas": 124,
  "colunas_vazias_removidas": 3,
  "colunas_muitos_nulos": {
    "coluna_9": 98.49,
    "coluna_10": 99.89,
    "coluna_14": 99.97
  }
}
```
