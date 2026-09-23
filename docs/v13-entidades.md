# V1.3 — Qualidade e resolução de entidades

## Detecção homologada (Etapa 1)

O detector em `src/quality/entity_resolution.py` sugere nomes semelhantes sem
alterar dados. A Etapa 2 não mudou suas regras:

- normalização de espaços, caixa e acentos somente para comparação;
- `SequenceMatcher`: mínimo 0,92; similaridade alta a partir de 0,97;
- fuzzy para nomes com dez caracteres ou mais, prefixo comum, diferença de
  tamanho de até 12% e janela de vinte vizinhos;
- proteção para números, unidades e sufixos empresariais diferentes;
- prioridade para IDs estáveis.

São considerados clientes, produtos, categorias, lojas e colaboradores
semanticamente identificados. Similaridade não comprova identidade.
O relatório guarda até 500 candidatos; as contagens incluem todos os encontrados.

## Revisão e decisão (Etapa 2)

Em Dados, o usuário filtra por entidade e estado: Pendentes, Unidas ou
Mantidas separadas. São exibidos dez cards por página. A união exige uma
confirmação adicional; nenhuma ação acontece automaticamente.

`src/quality/entity_decisions.py` contém funções simples para preparar os
candidatos, validar/registrar decisões, atualizar contadores e aplicar aliases.

- `candidate_id`: SHA-256 abreviado de análise, tipo, coluna e variantes
  ordenadas. Não depende da posição na lista.
- Label recomendado: variante mais frequente; empate usa a primeira ocorrência.
- `merge`: aplica aliases numa cópia analítica.
- `keep_separate`: registra a escolha sem recalcular analytics.
- Repetir a mesma decisão é idempotente.
- Trocar uma decisão ou unir pares que compartilham uma variante já unida
  retorna erro claro. Não há união transitiva ou undo.

## API

`GET /api/analysis/{analysis_id}/entities` retorna candidatos, decisões,
contadores por tipo e `can_decide`.

`POST /api/analysis/{analysis_id}/entities` recebe:

```json
{"candidate_id": "...", "decision": "merge"}
```

A alternativa é `"decision": "keep_separate"`. O backend escolhe o label.
Valida análise, candidato, variantes presentes, decisão, label e conflitos.
O POST retorna o resumo atualizado no formato normal de sucesso.

## Preservação e persistência

O pipeline salva internamente o DataFrame após ETL/métricas derivadas e o
contexto em `data/analysis_history/working/{analysis_id}/entity_analysis.pkl`.
Esse arquivo é criado pelo sistema; uploads de pickle não são aceitos.

`main.continuar_analytics()` reutiliza a continuação analítica existente.
Não relê Excel, não repete ETL e não executa novamente o detector.
O DataFrame salvo, o CSV processado e o arquivo original permanecem intactos.

A decisão registra variantes, coluna, label, data/hora e
`origin = user_confirmation` em `dados.entity_resolution.decisions`.
Os estados são `pending`, `merged` e `kept_separate`.

O snapshot completo e o índice do histórico são atualizados preservando o ID
e a data original. Alterar uma análise antiga não substitui a análise mais
recente. O histórico reabre o resultado salvo; não reaplica regras futuras.
Snapshots sem diagnóstico continuam abrindo. Sem intermediário persistido,
uma análise antiga fica disponível somente para consulta.

A união pode alterar quantidade, rankings, concentração e insights da entidade.
KPIs gerais e série temporal são conferidos antes da publicação; uma mudança
nesses indicadores interrompe a decisão. Qualidade usa o DataFrame original,
sem penalização nova. A comparação continua usando os snapshots disponíveis,
sem matching novo entre análises.

## Limitações e validação

Homônimos continuam ambíguos; o bloqueio pode perder alguns pares.
Não há merge em lote, edição manual do label ou reversão de decisões.
No caso real homologado, o detector levou cerca de 0,07 s e o merge 18,3 s
(17,7 s de analytics). Melhorar esse tempo fica como oportunidade para V1.4;
não existe cache novo nesta versão.
A persistência segue a arquitetura local de arquivos e uma análise por vez.

Testes cobrem preservação, IDs, labels, conflitos, idempotência, payloads
inválidos, reinicialização, histórico antigo, UI desktop/mobile e uploads.
Os resultados reais estão em `reports/validacao_v13_etapa2.json`.
