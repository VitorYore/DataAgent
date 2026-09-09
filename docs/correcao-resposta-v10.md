# Diagnóstico do POST após a V1.0

## Causa comprovada

O Vite estava escutando em `localhost:5174`, enquanto `api/app.py` permitia CORS
somente para localhost/127.0.0.1 na porta 5173. O multipart enviado por fetch
chegava ao servidor, que concluía o pipeline e respondia HTTP 200. O navegador,
porém, não disponibilizava a resposta ao JavaScript por falta do cabeçalho
`Access-Control-Allow-Origin` correspondente à porta 5174.

Reprodução pelo Edge:

```text
Access to fetch ... from origin 'http://localhost:5174' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
net::ERR_FAILED
```

Esse erro rejeitava o fetch e disparava a mensagem de conexão interrompida em
`dataAgentService.analyzeFiles()`. Não houve traceback de serialização no POST
real. O endpoint não possui response_model, e o POST do frontend não tem timeout
manual. O timeout de 15 segundos existente se aplica somente ao GET inicial.

## Evidências e reprodução

Foram usados os 14 CSVs completos de `data/samples`, correspondentes à análise
multitabela disponível no projeto. Os testes HTTP reais usaram Uvicorn na porta
8001 com diretório próprio em `.validation-http`; os testes pelo Edge mantiveram
a origem real `http://localhost:5174`, redirecionando apenas a API para o servidor
isolado. Os relatórios ativos não foram substituídos pelos testes.

- Antes: HTTP 200 em 8,37 s; sem `Access-Control-Allow-Origin` para 5174.
- Edge antes: erro CORS e a mensagem exata relatada pelo usuário em 8,78 s.
- Depois: Edge recebeu HTTP 200 em 8,73 s, navegou à Overview e exibiu o score da
  V1.0 ao retornar a Dados. Nenhuma falha de requisição ou alerta.
- Resumo antes/depois idêntico; `json.dumps(..., allow_nan=False)` passou.
- Log após o pipeline: resumo publicado, resposta preparada com 14 arquivos,
  `POST /api/analysis HTTP/1.1 200 OK`.

Evidências locais: `.validation-http/response-before.json`, `browser-before.json`,
`browser-after.json`, `uvicorn.log`, `uvicorn-after.log` e `tests.log`. Não existe
traceback do caso real para registrar porque o servidor respondeu com sucesso.

## Correção mínima

Adicionadas explicitamente as origens localhost e 127.0.0.1 na porta 5174,
preservando 5173 e sem permitir origens arbitrárias. Servidores iniciados sem
`--reload` precisam ser reiniciados para carregar a alteração.

O serviço frontend passou a preservar o código HTTP e o detalhe da API inclusive
quando uma resposta de erro não contém JSON. Falhas de rede e HTTP registram
informações em desenvolvimento; o usuário não recebe stack trace. O POST continua
sem timeout artificial. Nenhuma alteração em analytics, ETL, relacionamentos,
API runner, serializer ou schema de resposta foi necessária.

## Validação

**115 testes passaram:** 71 Python e 44 de navegador. Build/TypeScript passaram.
Foram adicionados cinco testes Python (CORS POST/GET/preflight nas quatro origens,
origem não permitida, multitabela real, NumPy/Pandas no bloco dados, NaN/Inf) e dois
testes de navegador (demora de cinco minutos simulados sem cancelamento e
HTTP 400/409/422/500, inclusive corpo não JSON).

NumPy/Pandas são tratados pelo encoder existente. NaN e infinitos injetados
artificialmente continuam sendo rejeitados pela validação estrita com HTTP 422
e corpo JSON de erro; a análise anterior permanece disponível. Não foram
convertidos em sucesso falso ou dados inventados. Nenhum valor não finito foi
encontrado na resposta real testada.

```powershell
.venv\Scripts\python.exe -m uvicorn api.app:app --reload
```

Em outro terminal:

```powershell
cd frontend
npm run dev
```

Abra a URL informada pelo Vite (5173 ou 5174), envie os arquivos juntos em Dados
e confira o POST em Network. Deve retornar 200, atualizar a Overview e mostrar a
qualidade da mesma análise ao voltar a Dados.
