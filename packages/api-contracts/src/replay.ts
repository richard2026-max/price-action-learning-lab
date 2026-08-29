import type { Bar, JudgmentPayload, KeyLevels, Provider } from "@price-action/domain";

export type ReplayMode = "free" | "hidden_answer" | "exam";
export type ReplaySamplingMode = "sequential" | "random" | string;

export interface SessionInfo {
  day: string;
  provider: string;
  session_name: string;
  bar_index: number;
  cursor_version: number;
  context_bar_count: number;
  market_time_utc: string;
  session_close_utc: string | null;
  is_completed: boolean;
  mode: string;
  sampling_mode: string;
}

export interface ReplayCandidate {
  detector_id: string;
  detector_version: string;
  bar_index: number;
  ts_event: string;
  ts_knowable: string;
  knowable_precision: string;
  result_type: string;
  result: unknown;
  evidence: Record<string, unknown>;
  rule_source: string;
  provenance: string;
}

export interface SessionDetail {
  session_id: string;
  bars: Bar[];
  ema20: Array<number | null>;
  /** Brooks 近似：15 分钟 20 bar EMA 投影到 5m 图（每 3 根更新一次，桶内持平；服务端无前视计算） */
  ema15?: Array<number | null>;
  /** Brooks 近似：60 分钟 20 bar EMA 投影到 5m 图（每 12 根更新一次，桶内持平） */
  ema60?: Array<number | null>;
  key_levels: KeyLevels;
  info: SessionInfo;
  candidates?: ReplayCandidate[];
}

export interface CreateReplaySessionRequest {
  day: string;
  mode?: ReplayMode;
  warmup_bars?: number;
  provider?: Provider;
  context_days?: number;
  instrument_id?: string;
}

export interface AdvanceReplayRequest {
  n: number;
  expected_cursor_version?: number;
  request_id?: string;
}

export interface ReplayDaysResponse {
  days: string[];
}

export interface RandomReplayDayResponse {
  day: string;
}

export interface JudgmentDto {
  id: number;
  session_id: string;
  bar_index: number;
  bar_time_utc: string;
  payload: JudgmentPayload;
  submitted_at: string;
}

export interface ReplaySessionSummary {
  session_id: string;
  day: string;
  provider: string;
  instrument_id: string;
  mode: string;
  state: string;
  cursor_index: number;
  cursor_version?: number;
  judgment_count: number;
  created_at: string;
}

export interface AnnotationDto {
  id: number;
  session_id: string;
  bar_index: number;
  bar_time_utc: string;
  kind: string;
  label: string | null;
  text: string | null;
  created_at: string;
  updated_at?: string;
}

export interface DeleteJudgmentResponse {
  status: string;
  deleted_judgment_id: number;
}

export interface DeleteSessionResponse {
  status: string;
  deleted_session_id: string;
}

export type SubmitJudgmentRequest = JudgmentPayload & { client_request_id?: string };
export type ReplaySessionDetailDto = SessionDetail;
export type ReplayBarDto = Bar;
export type ReplayKeyLevelsDto = KeyLevels;
