/** API 客户端（Phase 0 数据管理 + MVP-A 回放训练 + MVP-D 扫描工作台 + Analytics 学习分析 + SimTrade 模拟交易）。 */

const BASE = "/api/v1";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = `${r.status}`;
    try {
      const body = await r.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

// ---------- 数据管理 ----------

export interface Dataset {
  provider: string;
  feed: string;
  instrument_id: string;
  timeframe: string;
  start: string | null;
  end: string | null;
  row_count: number;
  duplicate_count: number;
  missing_bar_count: number;
  checksum: string;
  generated_at: string;
}

export const getHealth = () => fetch(`${BASE}/health`).then((r) => j<{ status: string; version: string }>(r));
export const getDatasets = () => fetch(`${BASE}/data/datasets`).then((r) => j<Dataset[]>(r));
export const seedDemo = (start: string, end: string) =>
  fetch(`${BASE}/data/seed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, end }),
  }).then((r) => j<{ days: number; bars_5m: number }>(r));

// ---------- 回放 ----------

export type Provider = "synthetic" | "hfdl";

const q = (provider: Provider) => `provider=${provider}&instrument_id=SPY`;

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

export interface SessionInfo {
  day: string;
  provider: string;
  session_name: string;
  bar_index: number;  // 训练日内K线下标（不含上下文）
  context_bar_count: number;  // 前N日上下文K线数量
  market_time_utc: string;
  session_close_utc: string | null;
  is_completed: boolean;
  mode: string;
  sampling_mode: string;
}

export interface Candidate {
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
  ema20: (number | null)[];
  key_levels: KeyLevels;
  info: SessionInfo;
  candidates?: Candidate[];
}

export interface Judgment {
  id: number;
  session_id: string;
  bar_index: number;
  bar_time_utc: string;
  payload: JudgmentPayload;
  submitted_at: string;
}

export interface JudgmentPayload {
  context_label: string;
  structure_note: string;
  pullback_present: string;
  bar_counting_note: string;
  considering_trade: boolean;
  direction: string;
  reasons: string[];
  entry: number | null;
  stop: number | null;
  target: number | null;
  probability_estimate: string;
  confidence: string;
}

export interface Annotation {
  id: number;
  session_id: string;
  bar_index: number;
  bar_time_utc: string;
  kind: string;
  label: string | null;
  text: string | null;
  created_at: string;
}

export const listDays = (provider: Provider = "synthetic", includeSealed: boolean = false) =>
  fetch(`${BASE}/replay/days?${q(provider)}&include_sealed=${includeSealed}`)
    .then((r) => j<{ days: string[] }>(r))
    .then((x) => x.days);

export const randomDay = (seed: number, provider: Provider = "synthetic", forExam: boolean = false) =>
  fetch(`${BASE}/replay/random-day?seed=${seed}&${q(provider)}&for_exam=${forExam}`)
    .then((r) => j<{ day: string }>(r))
    .then((x) => x.day);

export function createSession(
  day: string,
  mode: "free" | "hidden_answer" | "exam" = "free",
  warmupBars = 6,
  provider: Provider = "synthetic",
  contextDays = 2,
) {
  return fetch(`${BASE}/replay/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ day, mode, warmup_bars: warmupBars, provider, context_days: contextDays }),
  }).then((r) => j<SessionDetail>(r));
}

export const getSession = (id: string, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${id}?${q(provider)}`).then((r) => j<SessionDetail>(r));

export const advance = (id: string, provider: Provider, n = 1) =>
  fetch(`${BASE}/replay/sessions/${id}/advance?${q(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n }),
  }).then((r) => j<SessionDetail>(r));

export const goBack = (id: string, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${id}/back?${q(provider)}`, { method: "POST" })
    .then((r) => j<SessionDetail>(r));

export const submitJudgment = (id: string, provider: Provider, payload: JudgmentPayload) =>
  fetch(`${BASE}/replay/sessions/${id}/judgments?${q(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => j<Judgment>(r));

export const listJudgments = (id: string, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${id}/judgments?${q(provider)}`).then((r) => j<Judgment[]>(r));

// ---------- AI 对照复盘 ----------

export interface CoachConfig {
  enabled: boolean;
  configured: boolean;
  provider: string;
  model: string;
  temperature: number;
}

export interface CoachReference {
  book?: string;
  pdf_page?: number;
  print_page?: string | null;
  chunk_id?: string;
  chunk_hash?: string;
  source_type?: string;
  source_file?: string;
  content?: string;
  image_url?: string;
}

export interface CoachReview {
  source_grounded: string;
  mechanical_approx: string;
  coach_interpretation: string;
  references: CoachReference[];
  insufficient_evidence: boolean;
}

export const getCoachConfig = () =>
  fetch(`${BASE}/coach/config`).then((r) => j<CoachConfig>(r));

export const reviewJudgmentWithCoach = (sessionId: string, judgmentId: number, refresh = false) =>
  fetch(`${BASE}/coach/sessions/${sessionId}/judgments/${judgmentId}/review?refresh=${refresh}`, {
    method: "POST",
  }).then((r) => j<CoachReview>(r));

export interface AnalogBar {
  open: number;
  high: number;
  low: number;
  close: number;
  time: string;
}

export interface AnalogMatch {
  date: string;
  start_time: string;
  end_time: string;
  similarity: number;
  distance: number;
  pattern_label: string;
  forward_direction: string;
  forward_result: string;
  forward_return: number | null;
  window_bars?: AnalogBar[];
  forward_bars?: AnalogBar[];
  chart_image_url?: string;
}

export const searchJudgmentAnalogs = (
  sessionId: string,
  judgmentId: number,
  filters?: { target_date?: string; start_date?: string; end_date?: string },
) => {
  const params = new URLSearchParams();
  if (filters?.target_date) params.set("target_date", filters.target_date);
  if (filters?.start_date) params.set("start_date", filters.start_date);
  if (filters?.end_date) params.set("end_date", filters.end_date);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return fetch(`${BASE}/coach/sessions/${sessionId}/judgments/${judgmentId}/analogs${qs}`).then((r) =>
    j<{ session_id: string; judgment_id: number; matches: AnalogMatch[] }>(r),
  );
};

export const addAnnotation = (id: string, provider: Provider, barIndex: number, kind: "label" | "note", label: string | null, text: string | null) =>
  fetch(`${BASE}/replay/sessions/${id}/annotations?${q(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bar_index: barIndex, kind, label, text }),
  }).then((r) => j<Annotation>(r));

export const listAnnotations = (id: string, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${id}/annotations?${q(provider)}`).then((r) => j<Annotation[]>(r));

// ---------- SimTrade (Phase 2 模拟交易) ----------

export interface SimTrade {
  id: string;
  session_id: string;
  instrument_id: string;
  provider: string;
  day: string;
  side: "long" | "short";
  order_type: "market" | "limit" | "stop";
  status: "pending" | "open" | "closed" | "cancelled";
  order_bar_index: number;
  order_time_utc: string;
  planned_entry_price: number;
  actual_entry_price: number | null;
  entry_bar_index: number | null;
  entry_time_utc: string | null;
  stop_price: number;
  target_price: number;
  initial_risk: number;
  exit_price: number | null;
  exit_bar_index: number | null;
  exit_time_utc: string | null;
  exit_reason: "target" | "stop" | "manual" | "eod" | null;
  pnl: number | null;
  pnl_in_r: number | null;
  mfe_price: number | null;
  mfe_in_r: number | null;
  mae_price: number | null;
  mae_in_r: number | null;
  setup_notes: string | null;
  reasons: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateSimTradePayload {
  side: "long" | "short";
  order_type?: "market" | "limit" | "stop";
  planned_entry_price: number;
  stop_price: number;
  target_price: number;
  setup_notes?: string | null;
  reasons?: string[];
}

export const createSimTrade = (sessionId: string, provider: Provider, payload: CreateSimTradePayload) =>
  fetch(`${BASE}/trades/sessions/${sessionId}?${q(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => j<SimTrade>(r));

export const listSessionTrades = (sessionId: string) =>
  fetch(`${BASE}/trades/sessions/${sessionId}`).then((r) => j<SimTrade[]>(r));

export const manualExitTrade = (tradeId: string, sessionId: string, provider: Provider, notes?: string) =>
  fetch(`${BASE}/trades/${tradeId}/exit?session_id=${sessionId}&${q(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  }).then((r) => j<SimTrade>(r));

// ---------- Scanner (MVP-D) ----------

export interface ScanTask {
  id: string;
  instrument_id: string;
  provider: string;
  timeframe: string;
  start_day: string;
  end_day: string;
  detector_ids: string[];
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  total_days: number;
  scanned_days: number;
  scanned_bars: number;
  candidate_count: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface CandidateRecord {
  id: string;
  task_id: string;
  instrument_id: string;
  provider: string;
  day: string;
  bar_index: number;
  bar_time_utc: string;
  detector_id: string;
  detector_version: string;
  result_type: string;
  result: unknown;
  evidence: Record<string, unknown>;
  rule_source: string;
  provenance: string;
  review_status: "unreviewed" | "confirmed" | "rejected" | "uncertain" | "needs_review";
  rejection_reason: string | null;
  review_notes: string | null;
  is_favorite: boolean;
  is_mistake_notebook: boolean;
  reviewed_at: string | null;
  created_at: string;
}

export interface CreateScanTaskPayload {
  instrument_id?: string;
  provider?: Provider;
  start_day: string;
  end_day: string;
  timeframe?: string;
  detector_ids?: string[];
  include_sealed?: boolean;
}

export interface ReviewCandidatePayload {
  review_status: "confirmed" | "rejected" | "uncertain" | "needs_review";
  rejection_reason?: string | null;
  review_notes?: string | null;
  is_favorite?: boolean | null;
  is_mistake_notebook?: boolean | null;
}

export const createScanTask = (payload: CreateScanTaskPayload) =>
  fetch(`${BASE}/scan/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => j<ScanTask>(r));

export const listScanTasks = () => fetch(`${BASE}/scan/tasks`).then((r) => j<ScanTask[]>(r));

export const getScanTask = (id: string) => fetch(`${BASE}/scan/tasks/${id}`).then((r) => j<ScanTask>(r));

export const listCandidates = (params: {
  task_id?: string;
  detector_id?: string;
  review_status?: string;
  only_favorites?: boolean;
  only_mistakes?: boolean;
  limit?: number;
}) => {
  const sp = new URLSearchParams();
  if (params.task_id) sp.set("task_id", params.task_id);
  if (params.detector_id) sp.set("detector_id", params.detector_id);
  if (params.review_status) sp.set("review_status", params.review_status);
  if (params.only_favorites) sp.set("only_favorites", "true");
  if (params.only_mistakes) sp.set("only_mistakes", "true");
  if (params.limit) sp.set("limit", String(params.limit));
  return fetch(`${BASE}/scan/candidates?${sp.toString()}`).then((r) => j<CandidateRecord[]>(r));
};

export const reviewCandidate = (id: string, payload: ReviewCandidatePayload) =>
  fetch(`${BASE}/scan/candidates/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => j<CandidateRecord>(r));

export interface RegisteredDetector {
  detector_id: string;
  version: string;
  result_type: string;
  label: string;
  spec: string;
  provenance: string;
}

export const listDetectors = () =>
  fetch(`${BASE}/detectors`).then((r) => j<{ profile_version: string; detectors: RegisteredDetector[] }>(r));

// ---------- Analytics & Blind Recheck ----------

export interface BehaviorStats {
  total_sessions: number;
  completed_sessions: number;
  total_judgments: number;
  total_annotations: number;
  total_reviewed_candidates: number;
  total_confirmed_positives: number;
  total_rejected_negatives: number;
  total_favorites: number;
  total_mistakes: number;
}

export interface JudgmentDistribution {
  context_breakdown: Record<string, number>;
  trade_decision_breakdown: Record<string, number>;
  confidence_breakdown: Record<string, number>;
  probability_breakdown: Record<string, number>;
}

export interface AnalyticsOverview {
  behavior: BehaviorStats;
  judgment: JudgmentDistribution;
  rejections: { reason_counts: Record<string, number> };
  recent_mistakes: Array<{
    id: string;
    day: string;
    bar_index: number;
    detector_id: string;
    rejection_reason: string | null;
    notes: string | null;
    reviewed_at: string | null;
  }>;
  recent_favorites: Array<{
    id: string;
    day: string;
    bar_index: number;
    detector_id: string;
    notes: string | null;
    reviewed_at: string | null;
  }>;
}

export interface BlindRecheckItem {
  candidate_id: string;
  instrument_id: string;
  provider: string;
  day: string;
  bar_index: number;
  bar_time_utc: string;
  detector_id: string;
  evidence: Record<string, unknown>;
}

export interface RecheckCompareResult {
  candidate_id: string;
  original_status: string;
  recheck_status: string;
  is_consistent: boolean;
  original_reviewed_at: string | null;
  rechecked_at: string;
  original_notes: string | null;
  recheck_notes: string | null;
}

export const getAnalyticsOverview = () =>
  fetch(`${BASE}/analytics/overview`).then((r) => j<AnalyticsOverview>(r));

export const getRecheckQueue = (limit: number = 20) =>
  fetch(`${BASE}/analytics/recheck-queue?limit=${limit}`).then((r) => j<BlindRecheckItem[]>(r));

export const submitRecheck = (candidateId: string, recheckStatus: string, recheckNotes?: string) =>
  fetch(`${BASE}/analytics/recheck`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_id: candidateId,
      recheck_status: recheckStatus,
      recheck_notes: recheckNotes,
    }),
  }).then((r) => j<RecheckCompareResult>(r));
