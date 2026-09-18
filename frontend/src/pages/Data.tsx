import { useRef, useState } from 'react'
import { FileSpreadsheet, Info, Trash2, Upload, LoaderCircle } from 'lucide-react'
import { SectionHeader } from '../components/common/SectionHeader'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { useAnalysis } from '../contexts/AnalysisContext'
import { useNavigate } from 'react-router'
import { formatInteger } from '../utils/formatters'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { DataQualityPanel } from '../components/common/DataQualityPanel'
import { EmptyState } from '../components/common/EmptyState'
import { AnalysisHistoryPanel } from '../components/common/AnalysisHistoryPanel'
import { SemanticMappingPanel } from '../components/common/SemanticMappingPanel'

interface SelectedFile {
  id: string
  file: File
}

export default function Data() {
  const { analyzeFiles, processing, mappingRequest, confirmMapping, error: contextError } = useAnalysis()
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<SelectedFile[]>([])
  const [dragging, setDragging] = useState(false)
  const [fileError, setFileError] = useState('')
  const [analysisMessage, setAnalysisMessage] = useState('')

  function addFiles(incoming: File[]) {
    if (processing) return
    const accepted = incoming.filter((file) => /\.(csv|xlsx|xls)$/i.test(file.name))
    setFiles((current) => [...current, ...accepted.map((file) => ({ id: crypto.randomUUID(), file }))])
    setFileError(accepted.length !== incoming.length ? 'Alguns arquivos não foram adicionados. Selecione apenas CSV, XLS ou XLSX.' : '')
    setAnalysisMessage('')
  }

  async function handleAnalyze() {
    if (processing) return
    setAnalysisMessage('')
    try {
      const completed = await analyzeFiles(files.map(({ file }) => file))
      if (completed) navigate('/')
    } catch (error: unknown) {
      setAnalysisMessage(error instanceof Error ? error.message : 'Não foi possível conectar ao backend.')
    }
  }

  async function handleConfirmMapping(mappings: Record<string, string>) {
    await confirmMapping(mappings)
    navigate('/')
  }

  return (
    <>
      <SectionHeader title="Dados" description="Selecione os arquivos que serão utilizados na análise." />
      <div className="space-y-8">
        {mappingRequest && <SemanticMappingPanel request={mappingRequest} processing={processing} error={contextError} onConfirm={handleConfirmMapping} />}
        <div className="flex items-start gap-3 rounded-xl border border-line bg-surface p-5 text-sm leading-6 text-muted">
          <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <p id="connection-notice">Envie os arquivos desta análise juntos. O DataAgent processará somente este conjunto, sem incluir arquivos de análises anteriores.</p>
        </div>
        <div
          onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
          onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false) }}
          onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(Array.from(event.dataTransfer.files)) }}
          className={`rounded-xl border border-dashed p-8 text-center ${dragging ? 'border-accent bg-accent/10' : 'border-line bg-surface'}`}>
          <Upload aria-hidden="true" className="mx-auto mb-5 size-7 text-muted" strokeWidth={1.5} />
          <h2 className="text-base font-medium">Arraste seus arquivos para esta área</h2>
          <p className="mt-2 text-sm leading-6 text-muted">Selecione um ou mais arquivos CSV ou Excel (.csv, .xls, .xlsx).</p>
          <input ref={input} disabled={processing} type="file" multiple accept=".csv,.xls,.xlsx" aria-label="Selecionar arquivos CSV ou Excel"
            className="hidden" onChange={(event) => { addFiles(Array.from(event.target.files ?? [])); event.target.value = '' }} />
          <button type="button" disabled={processing} onClick={() => input.current?.click()} className="mt-5 rounded-lg border border-line px-4 py-3 text-sm text-accent hover:bg-white/5">Selecionar arquivos</button>
        </div>
        {fileError && <p role="alert" className="text-sm text-muted">{fileError}</p>}
        <AnalysisSection title="Arquivos selecionados">
          <p role="status" className="mb-4 text-sm text-muted">Quantidade de arquivos selecionados: {formatInteger(files.length)}</p>
          {files.length === 0
            ? <p className="rounded-xl border border-line bg-surface p-6 text-sm text-muted">Nenhum arquivo selecionado.</p>
            : <ul className="space-y-3">
                {files.map(({ id, file }) => (
                  <li key={id} className="flex min-w-0 items-center gap-3 rounded-xl border border-line bg-surface p-4 sm:p-5">
                    <FileSpreadsheet aria-hidden="true" className="size-5 shrink-0 text-muted" />
                    <div className="min-w-0 flex-1">
                      <p className="break-all text-sm font-medium">{file.name}</p>
                      <p className="mt-1 text-xs text-muted">{formatInteger(file.size)} bytes</p>
                    </div>
                    <button type="button" disabled={processing} aria-label={`Remover ${file.name}`} className="shrink-0 rounded-lg p-3 text-muted hover:bg-white/5 hover:text-white"
                      onClick={() => { setFiles((current) => current.filter((item) => item.id !== id)); setAnalysisMessage('') }}>
                      <Trash2 aria-hidden="true" className="size-5" />
                    </button>
                  </li>
                ))}
              </ul>}
        </AnalysisSection>
        <div>
          <button type="button" disabled={files.length === 0 || processing} aria-describedby="connection-notice"
            onClick={handleAnalyze} className="rounded-lg border border-line bg-accent/10 px-5 py-3 text-sm font-medium text-accent hover:bg-accent/15 disabled:cursor-not-allowed disabled:opacity-40">{processing ? <span className="inline-flex items-center gap-2"><LoaderCircle aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" />Analisando dados...</span> : 'Analisar Dados'}</button>
          {processing && <p role="status" className="mt-4 text-sm text-muted">Analisando dados. Aguarde a conclusão.</p>}
          {analysisMessage && <p role="alert" className="mt-4 text-sm leading-6 text-muted">{analysisMessage}</p>}
        </div>
        <ExecutiveSummaryPage title="Última análise" description="Qualidade e preparação dos dados da análise atual.">
          {summary => summary.dados
            ? <DataQualityPanel data={summary.dados} />
            : <EmptyState title="Qualidade não disponível" description="Esta análise não contém informações de qualidade. Execute uma nova análise para gerar o diagnóstico." />}
        </ExecutiveSummaryPage>
        <AnalysisHistoryPanel />
      </div>
    </>
  )
}
