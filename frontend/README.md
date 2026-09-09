# DataAgent frontend

Base de apresentação em React, TypeScript e Vite. O backend Python permanece responsável por toda a inteligência e regras de negócio.

## Executar

Requer Node.js 22 (validado com 22.14.0) e npm.

```powershell
cd frontend
npm ci
npm run dev
```

Abra o endereço informado pelo Vite, normalmente http://localhost:5173.

Na V0.7, inicie também a API conforme [api/README.md](../api/README.md). Copie .env.example para .env.local para configurar VITE_API_URL (padrão http://localhost:8000). Reinicie o Vite após alterações.

- `npm run typecheck`: verifica TypeScript.
- `npm run build`: verifica tipos e gera produção em dist/.
- `npm run preview`: serve o build localmente.
- `npm run test:e2e`: testa as páginas no Edge instalado, sem janela, com Playwright. Requer a porta 5173 livre. Verifica desktop (1440 px), tablet (768 px), mobile (390 e 320 px), dados, navegação, carregamento e recuperação de erro.

## Organização

- `src/components/layout`: sidebar, header e shell responsivo.
- `src/components/common`: elementos visuais, seções e ExecutiveSummaryPage, que centraliza o acesso ao serviço e os estados de carregamento e erro.
- `src/components/cards`: StatusCard, KpiCard e cards de oportunidades, riscos e insights.
- `src/pages`: Overview e páginas analíticas apresentam o resumo; Dados envia múltiplos arquivos para análise.
- `src/contexts/AnalysisContext.tsx`: resumo compartilhado, carregamento e atualização com a resposta do POST.
- `src/App.tsx`: rotas e página de endereço não encontrado.
- `src/services`: getExecutiveSummary() consulta GET /api/analysis/latest e retorna o resumo real, ou null em HTTP 404.
- `src/types`: contratos do resumo executivo fornecido pelo Python.
- `src/mocks`: dados de exemplo fornecidos para o resumo executivo.
- `src/utils`: formatação visual BRL, percentual, números compactos e inteiros.
- `src/styles.css`: Tailwind CSS 4 e tokens do tema escuro.

As páginas consomem HTTP somente por meio do serviço. AnalysisContext mantém o resumo compartilhado e ExecutiveSummaryPage apresenta os estados de leitura. Falhas nunca usam mocks automaticamente. Os mocks são usados apenas por testes isolados.

Oportunidades separa oportunidades de pontos de atenção (riscos e insights). Os filtros de prioridade e categoria apenas selecionam resultados existentes e usam as classificações originais do resumo.

Dados aceita múltiplos arquivos CSV, XLS e XLSX por seleção ou drag-and-drop. Analisar Dados chama analyzeFiles(), que envia todos no mesmo FormData para POST /api/analysis, sem definir Content-Type manualmente. Durante o processamento, envio, seleção e remoção ficam bloqueados. Em sucesso, o contexto recebe o summary do POST e abre a Overview sem reload ou GET adicional. Em erro, a seleção e a análise anterior são preservadas.

`npm run test:upload` valida o fluxo completo com API real isolada e pipeline compartilhado, sem alterar os relatórios existentes. Consulte api/README.md para limites e comandos.

Desempenho apresenta kpis e temporal; Produtos apresenta produtos; Clientes apresenta clientes. A barra Top 5 usa diretamente o percentual fornecido pelo backend. Histórico e rankings exibem as listas retornadas pela API, mantendo estados vazios quando elas não estão disponíveis.

Os testes agora iniciam API e Vite; mantenha as portas 8000 e 5173 livres. Eles usam .venv/Scripts/python.exe na raiz. api-integration.spec.ts verifica a integração real; fixtures.ts intercepta HTTP exclusivamente nos testes de apresentação.

Os formatadores retornam strings e não alteram os dados: formatCurrency(valor) exibe BRL completo e formatCurrency(valor, true) exibe BRL compacto. formatPercentage(93.98) exibe 93,98%, sem multiplicar por 100. formatCompactNumber e formatInteger cuidam apenas da apresentação numérica.

Tailwind é configurado pelo plugin oficial de Vite e pelo CSS, sem necessidade de tailwind.config.js ou PostCSS separado. Vite 6 foi selecionado para compatibilidade com o Node 22.14.0 instalado.

Rotas: /, /performance, /products, /customers, /opportunities e /data.
Em produção, o servidor estático deve encaminhar rotas da aplicação para index.html (fallback de SPA). O servidor de desenvolvimento do Vite já faz isso.
