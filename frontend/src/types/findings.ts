export type FindingLevel = 'high' | 'medium' | 'low'
export type EvidenceValue = string | number | boolean | null | EvidenceValue[] | { [key: string]: EvidenceValue }

export interface FindingEvidence {
  name: string
  value: EvidenceValue
  unit: string | null
  source: string
  concept: string
  numerator?: number | null
  denominator?: number | null
}

export interface FindingComparison {
  previous_value: number | null
  current_value: number | null
  previous_period: string | null
  current_period: string | null
  absolute_change: number | null
  percentage_change: number | null
  direction: 'increase' | 'decrease' | 'stable' | null
  percentage_valid: boolean
  comparable: boolean
  reason: string | null
  continuous: boolean | null
  granularity: string
  reference_magnitude: number | null
}

export interface AnalyticalFinding {
  id: string
  rule: string
  rule_version: number
  type: string
  title: string
  summary: string
  metric: string
  metric_label: string
  unit: string | null
  scope: string
  entity: { id: string | null; value: string; label: string; identity_source: string } | null
  impact: FindingLevel
  confidence: FindingLevel
  confidence_reasons: string[]
  priority: FindingLevel
  evidence: FindingEvidence[]
  period: { start: string; end: string; granularity: string } | null
  comparison: FindingComparison | null
  recommendation: string | null
  selection_reason?: {
    priority: FindingLevel
    impact: FindingLevel
    confidence: FindingLevel
    materiality: number | null
    family: string
    policy: string
  }
  show_recommendation?: boolean
  recommendation_reference?: string | null
}
