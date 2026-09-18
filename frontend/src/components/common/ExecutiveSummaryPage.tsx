import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { useAnalysis } from '../../contexts/AnalysisContext'
import type { ExecutiveSummary } from '../../types/dataAgent'
import { SectionHeader } from './SectionHeader'
import { EmptyState } from './EmptyState'

export function ExecutiveSummaryPage({ title, description, children }: {
  title: string
  description: string
  children: (summary: ExecutiveSummary) => ReactNode
}) {
  const { summary, status, error, processing, refreshSummary } = useAnalysis()
  useEffect(() => {
    if (status === 'idle' && !processing) void refreshSummary()
  }, [status, processing, refreshSummary])

  return (
    <>
      <SectionHeader title={title} description={description} />
      {(status === 'loading' || status === 'idle') && <div role="status"><EmptyState title="Carregando análise" description="Aguarde enquanto os dados são carregados." /></div>}
      {status === 'empty' && (
        <div role="status">
          <EmptyState title="Nenhuma análise disponível" description="Ainda não há um resumo executivo disponível no backend." />
          <button type="button" className="mt-4 rounded-lg border border-line px-4 py-2 text-sm text-accent hover:bg-white/5"
            onClick={() => void refreshSummary()}>Tentar novamente</button>
        </div>
      )}
      {status === 'error' && (
        <div role="alert">
          <EmptyState title="Não foi possível carregar a análise" description={error} />
          <button type="button" className="mt-4 rounded-lg border border-line px-4 py-2 text-sm text-accent hover:bg-white/5"
            onClick={() => void refreshSummary()}>Tentar novamente</button>
        </div>
      )}
      {status === 'mapping_required' && <div role="status"><EmptyState title="Análise aguardando confirmação de campos" description="A estrutura foi recuperada. Confirme os significados na página Dados para continuar a análise." /></div>}
      {summary && status !== 'empty' && <div className="space-y-8">{children(summary!)}</div>}
    </>
  )
}
