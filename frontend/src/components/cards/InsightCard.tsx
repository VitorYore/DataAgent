import { Info } from 'lucide-react'
import type { Insight } from '../../types/dataAgent'
import { FindingCard } from './FindingCard'

export function InsightCard({ insight }: { insight: Insight }) {
  return <FindingCard title="Insight" icon={Info} {...insight} />
}
