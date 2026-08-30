/** API 客户端（Phase 0 数据管理 + MVP-A 回放训练 + MVP-D 扫描工作台 + Analytics 学习分析 + SimTrade 模拟交易）。
 *
 * 回放与判断的 DTO 统一来自 @price-action/api-contracts / @price-action/domain，
 * 与微信小程序共享同一契约；桌面端新增字段时先更新 packages，两端同步获得类型。
 */

import type {
  AnnotationDto,
  JudgmentDto,
  ReplayCandidate,
  ReplaySessionSummary,
  SessionDetail,
} from "@price-action/api-contracts";
import type { JudgmentPayload, Provider } from "@price-action/domain";

const BASE = "/api/v1";

/** 常见后端字段的中文名（用于校验错误信息）。 */
const FIELD_ZH: Record<string, string> = {
  context_days: "预热天数（前N日背景）",
  warmup_bars: "当日开盘预热K线数",
  day: "交易日",
  mode: "训练模式",
  provider: "行情数据源",
  instrument_id: "标的",
  direction: "方向",
  stop_price: "止损价",
  target_price: "目标价",
  planned_entry_price: "计划入场价",
};

/** 把 pydantic 校验消息翻译成人话（中文字段名 + 约束）。 */
function humanizeValidationItem(item: {
  msg?: string;
  loc?: unknown[];
  ctx?: Record<string, unknown>;
}): string {
  const locs = (item.loc ?? []).filter((l): l is string => typeof l === "string" && l !== "body");
  const field = locs.length ? FIELD_ZH[locs[locs.length - 1]] ?? locs[locs.length - 1] : "输入";
  const ctx = item.ctx ?? {};
  const msg = item.msg ?? "";
  let constraint = "";
  if (msg.includes("less than or equal to")) {
    constraint = `不能超过 ${ctx.le ?? "?"}`;
  } else if (msg.includes("greater than or equal to")) {
    constraint = `不能小于 ${ctx.ge ?? "?"}`;
  } else if (msg.includes("less than")) {
    constraint = `必须小于 ${ctx.lt ?? "?"}`;
  } else if (msg.includes("greater than")) {
    constraint = `必须大于 ${ctx.gt ?? "?"}`;
  } else if (msg.includes("valid integer") || msg.includes("valid number")) {
    constraint = "必须是有效数字";
  } else if (msg.includes("Value error")) {
    return msg.replace(/^Value error,\s*/i, "").trim();
  }
  if (constraint) return `${field}${constraint}`;
  return msg.replace(/^Value error,\s*/i, "").trim();
}

/** 把 FastAPI 校验错误（detail 为数组/对象）解析成人话，避免把整坨 JSON 抛给用户。 */
function friendlyDetail(raw: unknown): string {
  if (typeof raw === "string") {
    // 兼容被二次序列化的 JSON 字符串
    if (raw.startsWith("{") || raw.startsWith("[")) {
      try {
        return friendlyDetail(JSON.parse(raw));
      } catch {
        return raw;
      }
    }
    return raw;
  }
  if (Array.isArray(raw)) {
    return raw
      .map((item) =>
        item && typeof item === "object"
          ? humanizeValidationItem(item as { msg?: string; loc?: unknown[]; ctx?: Record<string, unknown> })
          : String(item),
      )
      .filter(Boolean)
      .join("；");
  }
  if (raw && typeof raw === "object") {
    const obj = raw as { msg?: string; detail?: unknown; type?: string; loc?: unknown[]; ctx?: Record<string, unknown> };
    if (typeof obj.msg === "string" && obj.type) return humanizeValidationItem(obj as never);
    if (typeof obj.msg === "string") return obj.msg.replace(/^Value error,\s*/i, "").trim();
    if (obj.detail !== undefined) return friendlyDetail(obj.detail);
  }
  return JSON.stringify(raw);
}

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = `${r.status}`;
    try {
      const body = await r.json();
      detail = body.detail !== undefined ? friendlyDetail(body.detail) : `${r.status}`;
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

export type {
  Bar,
  KeyLevels,
  SessionDetail,
  SessionInfo,
  ReplaySessionSummary,
} from "@price-action/api-contracts";
export type { JudgmentPayload, Provider } from "@price-action/domain";

/** 兼容别名：桌面端既有代码使用的名称。 */
export type Candidate = ReplayCandidate;
export type Judgment = JudgmentDto;
export type Annotation = AnnotationDto;

const q = (provider: Provider) => `provider=${provider}&instrument_id=SPY`;

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

export const listSessions = (limit = 100) =>
  fetch(`${BASE}/replay/sessions?limit=${limit}`).then((r) => j<ReplaySessionSummary[]>(r));

export const deleteJudgment = (sessionId: string, judgmentId: number, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${sessionId}/judgments/${judgmentId}?${q(provider)}`, {
    method: "DELETE",
  }).then((r) => j<{ status: string; deleted_judgment_id: number }>(r));

export const deleteSession = (sessionId: string, provider: Provider) =>
  fetch(`${BASE}/replay/sessions/${sessionId}?${q(provider)}`, {
    method: "DELETE",
  }).then((r) => j<{ status: string; deleted_session_id: string }>(r));

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

export const listSessionTrades = (sessionId: string, provider: Provider) =>
  fetch(`${BASE}/trades/sessions/${sessionId}?${q(provider)}`).then((r) => j<SimTrade[]>(r));

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
