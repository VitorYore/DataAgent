import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import type { TemporalPoint } from '../../types/dataAgent'
import { formatCurrency } from '../../utils/formatters'

export default function PerformanceChart({ data }: { data: TemporalPoint[] }) {
  return (
    <div className="min-w-0 rounded-xl border border-line bg-surface p-3 sm:p-6" aria-label="Gráfico de faturamento e lucro">
      <LineChart responsive style={{ width: '100%', height: 320 }} data={data}
        margin={{ top: 12, right: 12, bottom: 8, left: 0 }} accessibilityLayer>
        <CartesianGrid stroke="var(--color-line)" vertical={false} />
        <XAxis dataKey="periodo" stroke="var(--color-muted)" tick={{ fontSize: 11 }} tickLine={false} minTickGap={24} />
        <YAxis width={85} stroke="var(--color-muted)" tick={{ fontSize: 11 }} tickLine={false} axisLine={false}
          tickFormatter={(value: number) => formatCurrency(value, true)} />
        <Tooltip isAnimationActive={false}
          contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: '#edf2f8' }}
          formatter={(value) => typeof value === 'number' ? formatCurrency(value) : 'Não disponível'} />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
        <Line name="Faturamento" dataKey="faturamento" type="linear" stroke="var(--color-accent)" strokeWidth={2}
          dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
        <Line name="Lucro" dataKey="lucro" type="linear" stroke="#a3b8ad" strokeDasharray="5 3" strokeWidth={2}
          dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
      </LineChart>
    </div>
  )
}
