# DataAgent V0.7: upload e análise

## Executar localmente

Na raiz, em um terminal PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn api.app:app --reload
```

Em outro terminal:

```powershell
cd frontend
npm ci
# Na primeira configuração, se ainda não existir:
Copy-Item .env.example .env.local
npm run dev
```

O frontend usa VITE_API_URL=http://localhost:8000 (também é o padrão). Reinicie o Vite após alterar a variável. CORS permite localhost:5173 e 127.0.0.1:5173, GET e POST, sem credenciais. Use somente um processo/worker da API nesta versão.

## Endpoints

- GET /api/health: disponibilidade.
- GET /api/analysis/latest: último resumo salvo; 404 se não existir, 500 se inválido.
- GET /api/analysis/status: idle, processing, completed ou error. Estado em memória, reiniciado junto com o servidor.
- POST /api/analysis: multipart/form-data, campo repetido files, aceita CSV/XLSX/XLS.

Resposta de sucesso: status "success", files_processed e summary (objeto JSON). O frontend utiliza o summary do POST diretamente, sem exigir outro GET.

Erros: 400 para requisição vazia, extensão, nome, tabela duplicada ou arquivo de zero bytes; 422 para arquivos ilegíveis, sem linhas ou dados/relacionamentos não processáveis; 409 se outra análise estiver em andamento; 500 para erro interno inesperado. Detalhes técnicos ficam no log do backend.

## Testar pelo Swagger

Abra http://localhost:8000/docs, expanda POST /api/analysis, clique em Try it out e adicione um ou mais arquivos no campo files. Execute e confira files_processed e summary. GET /api/analysis/latest deve apresentar o mesmo resumo.

## Testar pelo frontend

Em Dados, selecione todos os arquivos do conjunto (por exemplo Historico_Vendas.csv, Produtos.csv e Clientes.csv). Clique em Analisar Dados. Durante o processamento o envio, seleção e remoção ficam bloqueados. Ao concluir, a Overview abre automaticamente com a resposta do POST. As outras páginas usam o mesmo resumo via AnalysisContext.

Em falha, a página mantém a seleção e permite tentar novamente; o resumo anterior permanece no contexto e no arquivo principal. Não existe fallback para mock. Campos indisponíveis aparecem como "Não disponível", sem preencher com zeros.

## Pipeline compartilhado

main.py expõe executar_dataagent(diretorio_dados, diretorio_saida, estrito=False). A CLI continua chamando a mesma função com data/samples; a API chama com uma pasta isolada e estrito=True. Não há subprocesso de main.py nem captura de stdout para produzir a resposta.

A função reutiliza os loaders, detector, merger, enricher, ETL e todos os módulos analíticos originais. Os únicos ajustes no pipeline são diretórios parametrizados, retorno estruturado e propagação de erros. No modo estrito, uma falha de leitura de qualquer tabela rejeita o conjunto. A inferência existente passou a aceitar o dtype de texto do pandas 3 além de object, sem alterar critérios, limites ou fórmulas.

## Arquivos e isolamento

Cada POST cria data/uploads/analysis-<identificador>/input e grava ali somente os arquivos dessa requisição. Os nomes são validados, caminhos são rejeitados e tabelas com o mesmo nome-base são recusadas para evitar substituição silenciosa pelo multi_loader. Nenhum arquivo de data/samples ou de uploads anteriores é incluído.

A saída do pipeline é gerada no mesmo diretório temporário. Após sucesso, os relatórios e CSV tratado são publicados nos caminhos habituais. reports/resumo_executivo.json é substituído atomicamente, por último; GET nunca deve ler um resumo pela metade. Em erro do pipeline, o resumo anterior permanece.

A pasta temporária da requisição é removida ao finalizar, com sucesso ou erro. Pastas deixadas por encerramento abrupto do processo nunca são reutilizadas. Não existe histórico. O lock em memória impede análises simultâneas nesta única instância. Não execute a CLI e a API simultaneamente escrevendo nos mesmos relatórios.

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest api.test_app api.test_upload
cd frontend
npm run build
npm run test:e2e
npm run test:upload
```

Testes exigem portas 8000/5173 livres e Edge instalado. test:upload usa api.test_upload_server e diretório temporário separado, preservando os relatórios reais. O teste multitabela usa amostras existentes de data/samples. xlwt é apenas uma dependência de teste para gerar um XLS; xlrd faz a leitura real de XLS.

## Limitações

Processamento síncrono, uma análise por vez, uma instância de Uvicorn. Sem filas, autenticação, histórico ou processamento em segundo plano. O POST aguarda o pipeline; fechar o navegador não garante cancelamento no servidor. Se a conexão cair, consulte o status antes de reenviar.

O conteúdo e os relacionamentos ainda precisam ser reconhecidos pelos loaders e regras existentes. Os leitores de Excel mantêm o comportamento atual (primeira aba por arquivo). Não há limite de tamanho de upload configurado nesta versão local; conjuntos muito grandes consomem memória e disco. Nenhum cálculo é feito na API ou no frontend.
