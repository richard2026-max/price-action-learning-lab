import type {
  CreateReplaySessionRequest,
  ReplayMode,
  ReplaySessionDetailDto,
  ReplaySessionSummary,
} from '@price-action/api-contracts'
import type {
  Bar,
  JudgmentGrade,
  JudgmentPayload as DomainJudgmentPayload,
  KeyLevels,
  MarketContext,
  TernaryAnswer,
  TradeDirection,
} from '@price-action/domain'

export type ContextLabel = MarketContext
export type Direction = TradeDirection
export type Grade = JudgmentGrade
export type Ternary = TernaryAnswer
export type { ReplayMode }
export type MarketBar = Bar
export type ReplaySession = ReplaySessionDetailDto
export type SessionSummary = ReplaySessionSummary
export type JudgmentPayload = DomainJudgmentPayload
export type { KeyLevels }

export interface CreateSessionPayload extends CreateReplaySessionRequest {
  instrument_id: string
  provider: 'synthetic' | 'hfdl'
  timeframe: string
  mode: ReplayMode
  warmup_bars: number
  context_days: number
}
