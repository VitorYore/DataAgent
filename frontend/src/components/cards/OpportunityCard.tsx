import { Lightbulb } from 'lucide-react'
import type { Opportunity } from '../../types/dataAgent'
import { FindingCard } from './FindingCard'

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  return <FindingCard title="Oportunidade" icon={Lightbulb} {...opportunity} />
}
