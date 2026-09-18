import { AlertTriangle, ArrowRight, Copy, ShieldCheck, TableProperties } from 'lucide-react'
import type { DataQuality, IngestionInfo } from '../../types/dataAgent'
import { formatInteger, formatPercentage } from '../../utils/formatters'
import { KpiCard } from '../cards/KpiCard'
import { AnalysisSection } from './AnalysisSection'
import { EmptyState } from './EmptyState'
import { Badge } from './Badge'

const labels: Record<string, string> = { excelente: 'Excelente', boa: 'Boa', atencao: 'Atenção', critica: 'Crítica', alta: 'Alta', media: 'Média', baixa: 'Baixa' }
const priority: Record<string, number> = { alta: 0, media: 1, baixa: 2 }
const conceptLabels: Record<string, string> = { valor_total: 'Valor Total', valor_com_desconto: 'Valor com Desconto', margem_bruta: 'Margem Bruta', margem_bruta_percentual: 'Margem Bruta %', forma_pagamento: 'Forma de pagamento', pedido: 'Pedido', cliente: 'Cliente', data: 'Data' }
const sourceLabels: Record<string, string> = { nome_coluna: 'Cabeçalho da coluna', conteudo: 'Inferido pelo conteúdo', cabecalho_posterior: 'Cabeçalho posterior compatível', cabecalho_repetido: 'Cabeçalho repetido compatível', usuario: 'Confirmado pelo usuário', derivado: 'Derivado pelo DataAgent' }

function Structure({ info, name }: { info: IngestionInfo; name: string }) {
  const normalization = info.normalizacao
  return <div className="min-w-0 rounded-xl border border-line bg-surface p-5">
    <h3 className="break-all font-medium">{info.arquivo ?? name}</h3>
    {info.aba && <p className="mt-2 text-sm text-muted">Aba: {info.aba}</p>}
    {normalization && <div className="mt-4">
      {normalization.status === 'partial' && <div role="status" className="mb-4 rounded-lg border border-amber-400/40 bg-amber-400/5 p-4 text-sm">
        <p className="flex items-center gap-2 font-medium text-amber-200"><AlertTriangle aria-hidden="true" className="size-4 shrink-0" />Estrutura recuperada parcialmente</p>
        <p className="mt-2 leading-6 text-muted">{formatPercentage(normalization.coverage_transaction_rows)} das linhas do arquivo foram reconhecidas como transacoes. {formatInteger(normalization.linhas_desconhecidas)} linhas ambiguas permanecem registradas na auditoria.</p>
      </div>}
      <p className="text-sm font-medium">{normalization.estrutura_detectada === 'relatorio_operacional' ? 'Relatório operacional normalizado' : normalization.estrutura_detectada}</p>
      <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">{[
        ['Confiança estrutural', formatPercentage(normalization.confianca_estrutural)],
        ['Linhas originais', formatInteger(normalization.linhas_originais)],
        ['Registros identificados', formatInteger(normalization.registros_extraidos)],
        ['Linhas separadas dos registros', formatInteger(normalization.linhas_separadas)],
        ['Linhas de resumo', formatInteger(normalization.linhas_resumo)],
        ['Separadores de período', formatInteger(normalization.linhas_periodo)],
        ['Blocos identificados', formatInteger(normalization.quantidade_blocos)],
        ['Linhas desconhecidas', formatInteger(normalization.linhas_desconhecidas)],
      ].map(([label, value]) => <div key={label}><dt className="text-muted">{label}</dt><dd className="mt-1">{value}</dd></div>)}</dl>
      <p className="mt-4 text-sm leading-6 text-muted">Linhas separadas e transformações preservadas no diagnóstico de ingestão. A confiança estrutural é uma heurística, não uma avaliação do negócio.</p>
    </div>}
    {info.cabecalho_detectado === false && <p className="mt-3 text-sm leading-6 text-amber-300">Colunas genéricas utilizadas. Sem cabeçalhos identificáveis, alguns KPIs podem estar indisponíveis.</p>}
    <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
      {[
        ['Cabeçalho detectado', info.cabecalho_detectado == null ? 'Não disponível' : info.cabecalho_detectado ? 'Sim' : 'Não'],
        ['Linha do cabeçalho', formatInteger(info.linha_cabecalho)],
        ['Confiança do cabeçalho', formatPercentage(info.confianca_cabecalho)],
        ['Linhas vazias removidas', formatInteger(info.linhas_vazias_removidas)],
        ['Colunas vazias removidas', formatInteger(info.colunas_vazias_removidas)],
      ].map(([label, value]) => <div key={label}><dt className="text-muted">{label}</dt><dd className="mt-1">{value}</dd></div>)}
    </dl>
    {!!info.colunas_renomeadas?.length && <div className="mt-5"><p className="text-sm font-medium">Colunas renomeadas</p><ul className="mt-2 space-y-2 text-sm text-muted">{info.colunas_renomeadas.map((item, index) => <li key={index} className="flex flex-wrap items-center gap-2 break-all"><span>{item.original || `Coluna sem nome na posição ${item.posicao}`}</span><ArrowRight aria-hidden="true" className="size-4 shrink-0" /><span>{item.novo}</span></li>)}</ul></div>}
    {!!Object.keys(info.colunas_muitos_nulos ?? {}).length && <div className="mt-5 text-sm"><p>Colunas esparsas preservadas</p><ul className="mt-2 space-y-1 text-muted">{Object.entries(info.colunas_muitos_nulos ?? {}).map(([name, percent]) => <li className="break-all" key={name}>{name}: {formatPercentage(percent)} de nulos</li>)}</ul></div>}
  </div>
}

export function DataQualityPanel({ data }: { data: DataQuality }) {
  const issues = (data.problemas ?? []).map(item => typeof item === 'string' ? { mensagem: item } : item)
    .sort((a, b) => (priority[a.nivel ?? a.severidade ?? ''] ?? 3) - (priority[b.nivel ?? b.severidade ?? ''] ?? 3))
  const ingestion = data.ingestao
  const structures: [string, IngestionInfo][] = !ingestion ? [] : typeof ingestion.cabecalho_detectado === 'boolean'
    ? [['Arquivo', ingestion as IngestionInfo]] : Object.entries(ingestion) as [string, IngestionInfo][]
  return <>
    <div className="rounded-xl border border-line bg-surface p-5 text-sm">
      <p>{data.status === 'concluida' ? 'Análise concluída' : data.status ?? 'Status não disponível'}</p>
      <p className="mt-2 text-muted">{formatInteger(data.quantidade_arquivos)} arquivos; {formatInteger(data.quantidade_linhas)} linhas; {formatInteger(data.quantidade_colunas)} colunas</p>
      {data.escopo && <p className="mt-3 leading-6 text-muted">{data.escopo}</p>}
      {data.anomalias_temporais?.quantidade ? <div role="status" className="mt-4 rounded-lg border border-amber-400/40 bg-amber-400/5 p-4">
        <p className="text-sm font-medium">Datas fora do período predominante</p>
        <p className="mt-2 text-sm leading-6 text-muted">
          {formatInteger(data.anomalias_temporais.quantidade)} datas foram desconsideradas somente da análise temporal. O dado original foi preservado.
          {data.anomalias_temporais.periodo_predominante ? ' Período predominante: ' + data.anomalias_temporais.periodo_predominante.inicio + ' a ' + data.anomalias_temporais.periodo_predominante.fim + '.' : ''}
        </p>
        {!!data.anomalias_temporais.datas_exemplos?.length && <p className="mt-2 text-xs text-muted">Exemplos: {data.anomalias_temporais.datas_exemplos.join(', ')}</p>}
      </div> : null}
    </div>
    <AnalysisSection title="Arquivos analisados">
      {data.arquivos?.length ? <ul className="grid gap-3 sm:grid-cols-2">{data.arquivos.map((file, index) => <li key={index} className="min-w-0 rounded-xl border border-line bg-surface p-5"><p className="break-all text-sm font-medium">{file.nome}</p><p className="mt-2 text-sm text-muted">{formatInteger(file.linhas)} linhas; {formatInteger(file.colunas)} colunas</p></li>)}</ul> : <EmptyState title="Arquivos não informados" description="Este relatório não contém a lista de arquivos." />}
    </AnalysisSection>
    <AnalysisSection title="Qualidade dos dados">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="Score de qualidade" icon={ShieldCheck} value={data.score_qualidade == null ? null : `${data.score_qualidade} / 100`} detail={labels[data.classificacao_qualidade ?? ''] ?? 'Classificação não disponível'} />
        <KpiCard title="Valores nulos" icon={TableProperties} value={formatInteger(data.total_valores_nulos)} detail={`${formatPercentage(data.percentual_nulos_geral)} das células`} />
        <KpiCard title="Linhas duplicadas" icon={Copy} value={formatInteger(data.linhas_duplicadas)} />
        <KpiCard title="Problemas encontrados" icon={AlertTriangle} value={formatInteger(data.quantidade_problemas)} />
      </div>
      {data.score_qualidade != null && <div role="meter" aria-label="Score de qualidade" aria-valuemin={0} aria-valuemax={100} aria-valuenow={data.score_qualidade} className="mt-5 h-2 overflow-hidden rounded-full bg-line"><div className="h-full bg-accent" style={{ width: `${data.score_qualidade}%` }} /></div>}
    </AnalysisSection>
    <AnalysisSection title="Problemas encontrados">
      {issues.length ? <ul className="space-y-3">{issues.map((issue, index) => {
        const level = issue.nivel ?? issue.severidade ?? ''
        return <li key={index} className={`min-w-0 rounded-xl border bg-surface p-5 ${level === 'alta' ? 'border-amber-400/40' : 'border-line'}`}>{issue.tipo === 'incoerencia_metricas_financeiras' && <p className="mb-2 text-sm font-medium">Coerência de métricas</p>}{issue.tipo === 'incoerencia_metricas_financeiras' ? <Badge>Atenção</Badge> : <Badge>{labels[level] ?? 'Nível não informado'}</Badge>}{issue.coluna && <p className="mt-3 break-all text-sm font-medium">{issue.coluna}</p>}<p className="mt-2 break-words text-sm leading-6 text-muted">{issue.mensagem}</p></li>
      })}</ul> : <EmptyState title={data.problemas ? 'Nenhum problema encontrado' : 'Problemas não informados'} description="Diagnóstico da análise atual." />}
    </AnalysisSection>
    <AnalysisSection title="Transformações realizadas">
      {data.transformacoes?.length ? <ul className="space-y-3">{data.transformacoes.map((item, index) => <li key={index} className="min-w-0 rounded-xl border border-line bg-surface p-5 text-sm"><p className="break-all font-medium">{item.coluna}</p>{item.antes != null && item.depois != null && <p className="mt-2 flex flex-wrap items-center gap-2 break-all text-muted"><span>{item.antes}</span><ArrowRight aria-hidden="true" className="size-4 shrink-0" /><span>{item.depois}</span></p>}<p className="mt-2 break-words leading-6 text-muted">{item.descricao}</p></li>)}</ul> : <EmptyState title={data.transformacoes ? 'Nenhuma transformação realizada' : 'Transformações não informadas'} description="Nenhuma transformação foi registrada neste relatório." />}
    </AnalysisSection>
    {data.mapeamento_semantico && <AnalysisSection title="Mapeamento utilizado">
      {Object.keys(data.mapeamento_semantico.automatico ?? {}).length + Object.keys(data.mapeamento_semantico.confirmado_pelo_usuario ?? {}).length
        ? <ul className="grid gap-3 sm:grid-cols-2">{[
            ...Object.entries(data.mapeamento_semantico.automatico ?? {}).map(([column, concept]) => ({ column, concept, source: data.mapeamento_semantico?.origens?.[column]?.origem ?? 'conteudo' })),
            ...Object.entries(data.mapeamento_semantico.confirmado_pelo_usuario ?? {}).map(([column, concept]) => ({ column, concept, source: 'usuario' })),
          ].map(({ column, concept, source }) => <li key={`${source}-${column}`} className="min-w-0 rounded-xl border border-line bg-surface p-4 text-sm">
            <p className="font-medium">{conceptLabels[concept] ?? concept.replaceAll('_', ' ')}</p>
            <p className="mt-1 break-all text-xs text-muted">Coluna original: {column}</p>
            <p className="mt-2 text-xs text-muted">{sourceLabels[source] ?? 'Identificado automaticamente'}{data.mapeamento_semantico?.origens?.[column]?.confianca != null ? ` ? ${formatPercentage((data.mapeamento_semantico.origens[column].confianca ?? 0) * 100)}` : ''}</p>
          </li>)}</ul>
        : <EmptyState title="Nenhum mapeamento semântico registrado" description="Os nomes das colunas foram utilizados diretamente." />}
    </AnalysisSection>}
    <AnalysisSection title="Estrutura do arquivo">
      {structures.length ? <div className="space-y-4">{structures.map(([name, info]) => <Structure key={name} name={name} info={info} />)}</div> : <EmptyState title="Ingestão não informada" description="Análises antigas podem não conter o diagnóstico estrutural." />}
    </AnalysisSection>
  </>
}
