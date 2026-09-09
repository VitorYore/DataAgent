import { TriangleAlert } from 'lucide-react'
import type { Risk } from '../../types/dataAgent'
import { FindingCard } from './FindingCard'

export function RiskCard({ risk }: { risk: Risk }) {
  return <FindingCard title="Risco" icon={TriangleAlert} {...risk} />
}
