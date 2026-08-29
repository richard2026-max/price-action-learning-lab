export interface AnalyticsOverview {
  behavior: {
    total_sessions: number
    completed_sessions: number
    total_judgments: number
    total_annotations: number
    total_reviewed_candidates: number
    total_confirmed_positives: number
    total_rejected_negatives: number
    total_favorites: number
    total_mistakes: number
  }
  judgment: {
    context_breakdown: Record<string, number>
    trade_decision_breakdown: Record<string, number>
    confidence_breakdown: Record<string, number>
    probability_breakdown: Record<string, number>
  }
  rejections: { reason_counts: Record<string, number> }
  recent_mistakes: Array<Record<string, unknown>>
  recent_favorites: Array<Record<string, unknown>>
}
