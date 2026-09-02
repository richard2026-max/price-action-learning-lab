export type Provider = "synthetic" | "hfdl";

export interface Bar {
  ts_open_utc: string;
  ts_close_utc: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  session: string;
  is_complete: boolean;
}

export interface KeyLevels {
  prev_day_open: number | null;
  prev_day_high: number | null;
  prev_day_low: number | null;
  prev_day_close: number | null;
  today_open: number | null;
  premarket_high: number | null;
  premarket_low: number | null;
  gap: number | null;
}

export type MarketContext = "trend_up" | "trend_down" | "trading_range" | "transition";
export type TernaryAnswer = "unknown" | "yes" | "no";
export type TradeDirection = "none" | "long" | "short";
export type JudgmentGrade = "good" | "okay" | "bad";

export interface JudgmentPayload {
  context_label: MarketContext;
  structure_note: string;
  pullback_present: TernaryAnswer;
  bar_counting_note: string;
  considering_trade: boolean;
  direction: TradeDirection;
  reasons: string[];
  entry: number | null;
  stop: number | null;
  target: number | null;
  probability_estimate: JudgmentGrade;
  confidence: JudgmentGrade;
  /** 提交判断那一刻的图表画线快照（结构自由 JSON；复盘时原样叠加） */
  drawings_snapshot?: unknown[];
}
