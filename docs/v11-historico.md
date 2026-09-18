# V1.1: histórico e comparação

O POST existente executa o mesmo pipeline, valida o JSON, publica o resumo e conclui a limpeza temporária. Só então grava um snapshot em `data/analysis_history/`. Não há importação automática de relatórios anteriores nem alteração da execução manual do CLI. O histórico começa com os próximos uploads bem-sucedidos pela API.

Cada JSON guarda apenas ID, data UTC, nomes dos arquivos, sete KPIs existentes e score/status executivo (não o score de qualidade). Timestamp com microssegundos e UUID evita colisões. A gravação usa arquivo temporário e substituição atômica no mesmo diretório. O diretório não é versionado; preserve-o ao fazer backup. Reiniciar a API mantém os registros.

`src/history/analysis_history.py` concentra salvar, listar, obter por ID, obter última análise e comparar. O runner da API chama somente a persistência, sem duplicar o pipeline. IDs inválidos não permitem acesso fora do diretório.

## Endpoints

- `GET /api/analysis/history`: lista da mais recente à mais antiga; sem registros, `[]`.
- `GET /api/analysis/history/{analysis_id}`: snapshot; inexistente retorna 404.
- `GET /api/analysis/compare`: compara as duas mais recentes. Com zero ou uma, retorna 200, `status: "insuficiente"`, mensagem e `metricas: {}`.
- Health, latest, status e POST permanecem com os contratos existentes.

A variação é `((atual - anterior) / anterior) * 100`, arredondada a duas casas. Margem usa diferença em pontos percentuais. Denominador zero ou valor indisponível gera variação `null`. Métricas ausentes dos dois registros são omitidas. Nenhum KPI é recalculado. A comparação não garante que arquivos/períodos sejam equivalentes; a interface informa isso.

## Interface

A página Dados mantém o upload e a qualidade. `AnalysisHistoryPanel` consulta o serviço ao abrir a página ou mudar a análise, apresenta tabela com rolagem horizontal e quatro cards de comparação. Datas são exibidas no fuso do navegador. Valores ausentes aparecem como “Não disponível”. Há carregamento, erro com nova tentativa, histórico vazio e comparação insuficiente. Não há cálculo analítico no React.

## Execução e validação

Terminal 1, na raiz: `.venv/Scripts/python.exe -m uvicorn api.app:app --reload`.

Terminal 2: `cd frontend` e `npm run dev`. A configuração existente `VITE_API_URL=http://localhost:8000` permanece.

Na página Dados envie um arquivo, execute, retorne a Dados e confira o histórico. Repita com outro conjunto e confira a comparação. Reinicie a API e consulte novamente os endpoints.

Validação: 82 testes Python, 50 testes de navegador e 4 testes de upload real passaram. TypeScript/build passaram. Os testes incluem erro sem registro, persistência, IDs, ordenação, métricas ausentes, zero, margem, estados vazios, desktop/tablet/mobile, atualização sem reload e regressão da V1.0. Mocks antigos do módulo de serviço foram atualizados para incluir as duas novas funções.

Um POST real com XLSX retornou 200 em aproximadamente 0,29 s; outro com os 14 CSVs completos de samples retornou 200 em 8,28 s. Após reiniciar o processo FastAPI, histórico e comparação permaneceram exatamente iguais. Os testes React também executaram dois uploads consecutivos e um conjunto de três CSVs relacionados. Os exemplos reais completos estão em [v11-validacao.json](v11-validacao.json). A grande variação desse exemplo é consequência de comparar conjuntos de tamanhos diferentes, não uma conclusão sobre crescimento do negócio.

## Limitações

Histórico local, sem paginação, retenção ou restauração do dashboard para uma execução antiga. O GET por ID retorna o snapshot compacto. Mantém-se uma análise por vez no processo da API; executar com um único worker. Arquivo histórico corrompido gera erro explícito, sem fallback silencioso. Cada arquivo é publicado atomicamente, mas não há transação entre resumo e histórico: uma falha de disco ao gravar o histórico retorna erro e pode deixar o resumo latest já atualizado, sem uma nova entrada histórica.

Nenhuma dependência adicionada. Nenhum cálculo analítico, layout de outra página, commit ou tag foi alterado.
