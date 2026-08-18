/** API 客户端（Phase 0 数据管理 + MVP-A 回放训练 + MVP-D 扫描工作台）。 */

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
  bar_index: number;
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
) {
  return fetch(`${BASE}/replay/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ day, mode, warmup_bars: warmupBars, provider }),
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

export const addAnnotation = (id: string, provider: Provider, barIndex: number, kind: "label" | "note", label: string | null, text: string | null) =>
  fetch(`${BASE}/replay/sessions/${id}/annotations?${q(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bar_index: barIndex, kind, label, text }),
  }).then((r) => j<Annotation>(r));

export const listAnnotations = (id: string, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${id}/annotations?${q(provider)}`).then((r) => j<Annotation[]>(r));

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
