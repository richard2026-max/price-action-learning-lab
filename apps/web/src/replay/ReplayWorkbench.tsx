/**
 * MVP-A/Phase 2/Phase 3 回放工作台（整合 Level 1-5 全阶价格行为形态、前N日走势上下文背景与模拟交易）。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CandleChart, {
  KEY_LEVEL_ITEMS,
  normalizeOverlays,
  type ChartMarker,
  type ChartOverlays,
  type LevelKey,
  type TradeLine,
} from "../chart/CandleChart";
import JudgmentForm from "./JudgmentForm";
import {
  addAnnotation,
  advance,
  createSession,
  createSimTrade,
  getSession,
  goBack,
  listDays,
  listJudgments,
  listSessions,
  deleteJudgment,
  deleteSession,
  listSessionTrades,
  manualExitTrade,
  randomDay,
  submitJudgment,
  getCoachConfig,
  reviewJudgmentWithCoach,
  searchJudgmentAnalogs,
  type AnalogBar,
  type AnalogMatch,
  type Candidate,
  type CoachConfig,
  type CoachReview,
  type Judgment,
  type JudgmentPayload,
  type Provider,
  type ReplaySessionSummary,
  type SessionDetail,
  type SimTrade,
} from "../api/client";

const SPEEDS = [
  ["2000", "2.0s / 根"],
  ["1000", "1.0s / 根"],
  ["500", "0.5s / 根"],
  ["200", "0.2s / 根"],
] as const;

const LAST_SESSION_KEY = "pall.lastReplaySessionId";

const fmtCell = (c: Candidate | undefined): string => {
  if (!c) return "—";
  if (c.result_type === "boolean") return c.result === true ? "✓ 是" : c.result === false ? "✗ 否" : "—";
  if (c.result_type === "categorical") return String(c.result);
  return "证据";
};

const curProvider = (d: SessionDetail): Provider =>
  d.info.provider === "hfdl" ? "hfdl" : "synthetic";

const fmtET = (iso: string) =>
  new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));

const fmtSH = (iso: string) =>
  new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));

const CONTEXT_ZH: Record<string, string> = {
  trend_up: "多头趋势 (Trend Up)",
  trend_down: "空头趋势 (Trend Down)",
  trading_range: "交易区间 (Range)",
  transition: "过渡 / 不确定",
};

function cleanLayerText(text: string | undefined | null, fieldKey: string): string {
  if (!text) return "";
  let clean = text.trim();

  // 举一反三防御 1：若文本是 ```json ... ``` 代码块包裹
  if (clean.includes("```")) {
    const m = clean.match(/```(?:json|JSON)?\s*([\s\S]*?)\s*```/);
    if (m) clean = m[1].trim();
  }

  // 举一反三防御 2：若文本是整个 JSON 串（如意外包含了 "source_grounded":）
  if (clean.startsWith("{") && clean.includes(`"${fieldKey}"`)) {
    try {
      const obj = JSON.parse(clean);
      if (obj[fieldKey]) return String(obj[fieldKey]).trim();
    } catch {
      const reg = new RegExp(`"${fieldKey}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"`);
      const matched = clean.match(reg);
      if (matched) {
        try {
          return JSON.parse(`"${matched[1]}"`);
        } catch {
          return matched[1].replace(/\\"/g, '"').replace(/\\n/g, "\n");
        }
      }
    }
  }

  // 剥离两端可能残留的代码块符号
  clean = clean.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();
  return clean;
}

function renderLayerBody(rawText: string | undefined, fieldKey: string, emptyFallback: string) {
  const text = cleanLayerText(rawText, fieldKey);
  if (!text) return <p className="coach-empty-text">{emptyFallback}</p>;

  const paragraphs = text
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  if (paragraphs.length <= 1) {
    return <p>{text}</p>;
  }

  return (
    <div className="coach-paragraphs">
      {paragraphs.map((p, idx) => (
        <p key={idx}>{p}</p>
      ))}
    </div>
  );
}

function MiniCandleChart({
  windowBars = [],
  forwardBars = [],
}: {
  windowBars?: AnalogBar[];
  forwardBars?: AnalogBar[];
}) {
  const allBars = [...windowBars, ...forwardBars];
  if (allBars.length === 0) return null;

  const minP = Math.min(...allBars.map((b) => b.low));
  const maxP = Math.max(...allBars.map((b) => b.high));
  const range = maxP - minP || 1.0;
  const padding = range * 0.08;
  const low = minP - padding;
  const high = maxP + padding;
  const totalRange = high - low;

  const width = 360;
  const height = 95;
  const padLeft = 6;
  const padRight = 6;
  const plotWidth = width - padLeft - padRight;
  const n = allBars.length;
  const barW = Math.max(3, Math.min(7, (plotWidth / n) * 0.65));
  const step = plotWidth / n;

  const getY = (val: number) => height - ((val - low) / totalRange) * height;
  const splitX = padLeft + windowBars.length * step;

  return (
    <div className="mini-candle-wrap">
      <div className="mini-candle-legend">
        <span>历史匹配形态 20 根</span>
        <span className="legend-forward">后续 10 根演化走向</span>
      </div>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="mini-candle-svg">
        {forwardBars.length > 0 && (
          <rect
            x={splitX}
            y={0}
            width={width - splitX - padRight}
            height={height}
            fill="rgba(41, 121, 255, 0.08)"
            rx={2}
          />
        )}
        <line
          x1={splitX}
          y1={0}
          x2={splitX}
          y2={height}
          stroke="rgba(240, 185, 11, 0.55)"
          strokeDasharray="3 2"
          strokeWidth={1}
        />
        {allBars.map((b, i) => {
          const isBull = b.close >= b.open;
          const color = isBull ? "#26a69a" : "#ef5350";
          const cx = padLeft + i * step + step / 2;
          const yHigh = getY(b.high);
          const yLow = getY(b.low);
          const yOpen = getY(b.open);
          const yClose = getY(b.close);
          const bodyY = Math.min(yOpen, yClose);
          const bodyH = Math.max(1.5, Math.abs(yClose - yOpen));

          return (
            <g key={i}>
              <line x1={cx} y1={yHigh} x2={cx} y2={yLow} stroke={color} strokeWidth={1} />
              <rect
                x={cx - barW / 2}
                y={bodyY}
                width={barW}
                height={bodyH}
                fill={color}
                stroke={color}
                strokeWidth={0.5}
                rx={0.5}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function getStoredReview(sessionId: string, judgmentId: number): CoachReview | null {
  try {
    const raw = localStorage.getItem(`pall_coach_review_${sessionId}_${judgmentId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function storeReview(sessionId: string, judgmentId: number, review: CoachReview): void {
  try {
    localStorage.setItem(`pall_coach_review_${sessionId}_${judgmentId}`, JSON.stringify(review));
  } catch {
    /* ignore */
  }
}

function getStoredAnalogs(sessionId: string, judgmentId: number): AnalogMatch[] | null {
  try {
    const raw = localStorage.getItem(`pall_coach_analogs_${sessionId}_${judgmentId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function storeAnalogs(sessionId: string, judgmentId: number, analogs: AnalogMatch[]): void {
  try {
    localStorage.setItem(`pall_coach_analogs_${sessionId}_${judgmentId}`, JSON.stringify(analogs));
  } catch {
    /* ignore */
  }
}

const MODE_ZH: Record<string, string> = {
  free: "自由训练",
  hidden_answer: "严格训练",
  exam: "封存盲测",
};

function SessionsManager({
  onResume,
}: {
  onResume: (sessionId: string, provider: Provider, day: string) => void | Promise<void>;
}) {
  const [sessions, setSessions] = useState<ReplaySessionSummary[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [batchBusy, setBatchBusy] = useState(false);

  const load = useCallback(() => {
    listSessions(100)
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const cleanupLocal = (sid: string) => {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.includes(sid)) localStorage.removeItem(k);
    }
  };

  const handleDelete = async (sid: string) => {
    if (!window.confirm("确定彻底删除该历史训练会话吗？\n其全部判断记录、模拟交易与笔记将被级联清空。")) return;
    try {
      const target = sessions.find((s) => s.session_id === sid);
      await deleteSession(sid, (target?.provider as Provider) ?? "synthetic");
      cleanupLocal(sid);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(sid);
        return next;
      });
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
    } catch (e) {
      alert(`删除失败：${e}`);
    }
  };

  const toggleSelect = (sid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(sid)) next.delete(sid);
      else next.add(sid);
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelected((prev) => (prev.size === sessions.length ? new Set() : new Set(sessions.map((s) => s.session_id))));
  };

  const handleBatchDelete = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    const byId = new Map(sessions.map((s) => [s.session_id, s]));
    const summary = ids
      .map((id) => {
        const s = byId.get(id);
        return s ? `${s.day}（${MODE_ZH[s.mode] ?? s.mode}）` : id;
      })
      .join("、");
    if (
      !window.confirm(
        `确定批量删除选中的 ${ids.length} 个训练会话吗？\n${summary}\n\n其全部判断记录、模拟交易与笔记将被级联清空，且不可恢复。`,
      )
    ) {
      return;
    }
    setBatchBusy(true);
    const failed: string[] = [];
    for (const sid of ids) {
      try {
        const target = byId.get(sid);
        await deleteSession(sid, (target?.provider as Provider) ?? "synthetic");
        cleanupLocal(sid);
      } catch {
        failed.push(byId.get(sid)?.day ?? sid);
      }
    }
    setBatchBusy(false);
    setSelected(new Set());
    load();
    if (failed.length) alert(`以下会话删除失败：${failed.join("、")}`);
  };

  const allSelected = sessions.length > 0 && selected.size === sessions.length;

  return (
    <div className="sessions-manager">
      <div className="sessions-header" onClick={() => setExpanded((v) => !v)}>
        <span className="coach-section-label">
          🗂️ 历史训练会话管理 <span className="pill blue">{sessions.length}</span>
        </span>
        <span className="hint">{expanded ? "收起 ▲" : "展开查看与删除 ▼"}</span>
      </div>
      {expanded && (
        <>
          {sessions.length > 0 && (
            <div className="sessions-batch-bar">
              <label className="overlay-item">
                <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} />
                全选
              </label>
              <span className="hint">已选 {selected.size} / {sessions.length}</span>
              <button
                className="small ghost session-delete-btn"
                onClick={handleBatchDelete}
                disabled={selected.size === 0 || batchBusy}
                title="批量删除选中的会话（级联清空其全部关联数据）"
              >
                {batchBusy ? "删除中…" : `🗑️ 删除选中 (${selected.size})`}
              </button>
            </div>
          )}
          <div className="sessions-list">
            {sessions.length === 0 ? (
              <p className="hint">暂无历史训练会话记录。</p>
            ) : (
              sessions.map((s) => (
                <div key={s.session_id} className={`session-item ${selected.has(s.session_id) ? "session-selected" : ""}`}>
                  <label className="session-check">
                    <input
                      type="checkbox"
                      checked={selected.has(s.session_id)}
                      onChange={() => toggleSelect(s.session_id)}
                    />
                  </label>
                  <div className="session-info">
                    <b>
                      {s.day} · {MODE_ZH[s.mode] ?? s.mode}
                    </b>
                    <small>
                      {s.provider} · {s.judgment_count} 条判断 · 进度第 {s.cursor_index + 1} 根 ·{" "}
                      {s.state === "completed" ? "已完成" : "进行中"} ·{" "}
                      {new Date(s.created_at).toLocaleString()}
                    </small>
                  </div>
                  <div className="session-actions">
                    <button
                      className="small secondary"
                      onClick={() => onResume(s.session_id, s.provider as Provider, s.day)}
                      title="恢复并继续该历史训练会话"
                    >
                      ↩ 恢复训练
                    </button>
                    <button
                      className="small ghost session-delete-btn"
                      onClick={() => handleDelete(s.session_id)}
                      title="彻底删除该会话（级联清空全部关联数据）"
                    >
                      🗑️ 删除
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function ReplayWorkbench() {
  const [days, setDays] = useState<string[]>([]);
  const [provider, setProvider] = useState<Provider>("synthetic");
  const [day, setDay] = useState("");
  const [mode, setMode] = useState<"free" | "hidden_answer" | "exam">("free");
  const [warmup, setWarmup] = useState(6);
  const [contextDays, setContextDays] = useState(2);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(1000);
  const [judgmentOpen, setJudgmentOpen] = useState(false);
  const [judgments, setJudgments] = useState<Judgment[]>([]);
  const [trades, setTrades] = useState<SimTrade[]>([]);
  const [tradeFormOpen, setTradeFormOpen] = useState(false);
  const [tradeSide, setTradeSide] = useState<"long" | "short">("long");
  const [tradeOrderType, setTradeOrderType] = useState<"market" | "limit" | "stop">("market");
  const [tradeEntry, setTradeEntry] = useState("");
  const [tradeStop, setTradeStop] = useState("");
  const [tradeTarget, setTradeTarget] = useState("");
  const [tradeNotes, setTradeNotes] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [coachOpen, setCoachOpen] = useState(false);
  const [coachLoading, setCoachLoading] = useState(false);
  const [coachConfig, setCoachConfig] = useState<CoachConfig | null>(null);
  const [coachReview, setCoachReview] = useState<CoachReview | null>(null);
  const [reviewCache, setReviewCache] = useState<Record<number, CoachReview>>({});
  const [analogCache, setAnalogCache] = useState<Record<number, AnalogMatch[]>>({});
  const [analogMatches, setAnalogMatches] = useState<AnalogMatch[]>([]);
  const [analogStartDate, setAnalogStartDate] = useState("");
  const [analogEndDate, setAnalogEndDate] = useState("");
  const [analogLoading, setAnalogLoading] = useState(false);
  const [coachJudgment, setCoachJudgment] = useState<Judgment | null>(null);
  const [coachError, setCoachError] = useState("");
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [showMarkers, setShowMarkers] = useState(true);
  const [overlays, setOverlays] = useState<ChartOverlays>(() => {
    try {
      const raw = localStorage.getItem("pall.chartOverlays");
      if (raw) return normalizeOverlays(JSON.parse(raw));
    } catch {
      /* ignore */
    }
    return normalizeOverlays(null);
  });
  const [overlaysOpen, setOverlaysOpen] = useState(false);
  const advLock = useRef(false);
  const msgTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem("pall.chartOverlays", JSON.stringify(overlays));
    } catch {
      /* ignore */
    }
  }, [overlays]);

  // 全局消息统一自动消失：错误 8 秒、普通提示 3 秒（由 setMsg 的既有时序控制），兜底防止永久残留
  useEffect(() => {
    if (!msg) return;
    if (msgTimer.current) clearTimeout(msgTimer.current);
    const isError = /失败|错误|Error|不可用|必须|请填/.test(msg);
    msgTimer.current = setTimeout(() => setMsg(""), isError ? 12000 : 3000);
    return () => {
      if (msgTimer.current) clearTimeout(msgTimer.current);
    };
  }, [msg]);

  useEffect(() => {
    listDays(provider).then(setDays).catch((e) => setMsg(`获取日期失败：${e}`));
  }, [provider]);

  const [tradesError, setTradesError] = useState("");
  const lastRefreshAt = useRef(0);

  const refreshData = useCallback((sid: string, p: Provider, force = false) => {
    // 播放时每根K线都会推进，这里节流到 ≥3s 一次；下单/平仓/提交判断等主动操作用 force 立即刷新
    const now = Date.now();
    if (!force && now - lastRefreshAt.current < 3000) return;
    lastRefreshAt.current = now;
    // 后台刷新失败绝不弹全局提示（否则播放时提示反复出现），只在仓位卡内联显示并可手动重试
    listJudgments(sid, p)
      .then((rows) => {
        setJudgments(rows);
      })
      .catch(() => {
        /* 判断列表失败静默保留旧数据：数据源瞬时不可用时下轮推进自动重试 */
      });
    listSessionTrades(sid, p)
      .then((rows) => {
        setTrades(rows);
        setTradesError("");
      })
      .catch((e) => {
        setTradesError(`仓位列表加载失败：${e}`);
      });
  }, []);

  const apply = useCallback((d: SessionDetail) => {
    setDetail(d);
    localStorage.setItem(LAST_SESSION_KEY, d.session_id);
    if (d.info.is_completed) setPlaying(false);
  }, []);

  useEffect(() => {
    const last = localStorage.getItem(LAST_SESSION_KEY);
    if (!last) return;
    getSession(last, "synthetic")
      .then((d) => {
        setDetail(d);
        setDay(d.info.day);
        setProvider((d.info.provider as Provider) ?? "synthetic");
        refreshData(d.session_id, (d.info.provider as Provider) ?? "synthetic");
      })
      .catch(() =>
        getSession(last, "hfdl")
          .then((d) => {
            setDetail(d);
            setDay(d.info.day);
            setProvider("hfdl");
            refreshData(d.session_id, "hfdl");
          })
          .catch(() => localStorage.removeItem(LAST_SESSION_KEY)),
      );
  }, [refreshData]);

  const start = async (d: string) => {
    if (!d) return;
    setBusy(true);
    setPlaying(false);
    try {
      const det = await createSession(d, mode, warmup, provider, contextDays);
      apply(det);
      setDay(d);
      refreshData(det.session_id, curProvider(det));
      setMsg("");
    } catch (e) {
      setMsg(`创建会话失败：${e}`);
    } finally {
      setBusy(false);
    }
  };

  const startRandom = async () => {
    const seed = Math.floor(Math.random() * 1_000_000);
    try {
      const d = await randomDay(seed, provider, mode === "exam");
      await start(d);
    } catch (e) {
      setMsg(`随机日抽取失败：${e}`);
    }
  };

  const doAdvance = useCallback(async () => {
    if (!detail || advLock.current) return;
    if (detail.info.is_completed) {
      setPlaying(false);
      return;
    }
    advLock.current = true;
    try {
      const prov = curProvider(detail);
      apply(await advance(detail.session_id, prov, 1));
      refreshData(detail.session_id, prov);
    } catch (e) {
      setMsg(String(e));
      setPlaying(false);
    } finally {
      advLock.current = false;
    }
  }, [detail, apply, refreshData]);

  const doBack = useCallback(async () => {
    if (!detail || mode !== "free") return;
    try {
      const prov = curProvider(detail);
      apply(await goBack(detail.session_id, prov));
      refreshData(detail.session_id, prov);
    } catch (e) {
      setMsg(String(e));
    }
  }, [detail, apply, mode, refreshData]);

  useEffect(() => {
    if (!playing || !detail || detail.info.is_completed || judgmentOpen || tradeFormOpen) return;
    const t = setInterval(doAdvance, speedMs);
    return () => clearInterval(t);
  }, [playing, speedMs, detail, doAdvance, judgmentOpen, tradeFormOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || judgmentOpen || tradeFormOpen) return;
      if (!detail) return;
      if (e.code === "Space") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        doAdvance();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        doBack();
      } else if (e.key === "j" || e.key === "J") {
        e.preventDefault();
        setJudgmentOpen(true);
      } else if (e.key === "t" || e.key === "T") {
        e.preventDefault();
        setTradeFormOpen(true);
      } else if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        setNoteOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [detail, doAdvance, doBack, judgmentOpen, tradeFormOpen]);

  const openCoachReview = async (judgment: Judgment, forceRefresh = false) => {
    if (!detail) return;
    setCoachJudgment(judgment);
    setCoachError("");
    setCoachOpen(true);
    setAnalogStartDate("");
    setAnalogEndDate("");

    const sid = detail.session_id;
    const jid = judgment.id;

    // 若非强制重新分析，优先使用已记忆的复盘结论，实现秒开且不重复消耗 Token
    if (!forceRefresh) {
      const cachedR = reviewCache[jid] || getStoredReview(sid, jid);
      const cachedA = analogCache[jid] || getStoredAnalogs(sid, jid);
      if (cachedR) {
        setCoachReview(cachedR);
        setAnalogMatches(cachedA || []);
        setCoachLoading(false);
        return;
      }
    }

    setCoachReview(null);
    setAnalogMatches([]);
    setCoachLoading(true);
    try {
      const config = await getCoachConfig();
      setCoachConfig(config);
      const analogPromise = searchJudgmentAnalogs(sid, jid)
        .then((result) => {
          setAnalogMatches(result.matches);
          setAnalogCache((prev) => ({ ...prev, [jid]: result.matches }));
          storeAnalogs(sid, jid, result.matches);
        })
        .catch(() => setAnalogMatches([]));

      if (!config.configured || !config.enabled) {
        await analogPromise;
        return;
      }

      const [review] = await Promise.all([
        reviewJudgmentWithCoach(sid, jid, forceRefresh),
        analogPromise,
      ]);
      setCoachReview(review);
      setReviewCache((prev) => ({ ...prev, [jid]: review }));
      storeReview(sid, jid, review);
    } catch (e) {
      setCoachError(String(e));
    } finally {
      setCoachLoading(false);
    }
  };

  const handleFetchAnalogsByRange = async (start?: string, end?: string) => {
    if (!detail || !coachJudgment) return;
    setAnalogLoading(true);
    try {
      const res = await searchJudgmentAnalogs(detail.session_id, coachJudgment.id, {
        start_date: start || undefined,
        end_date: end || undefined,
      });
      setAnalogMatches(res.matches);
    } catch {
      setAnalogMatches([]);
    } finally {
      setAnalogLoading(false);
    }
  };

  const onSubmitJudgment = async (p: JudgmentPayload) => {
    if (!detail) return;
    const prov = curProvider(detail);
    await submitJudgment(detail.session_id, prov, p);
    setJudgmentOpen(false);
    refreshData(detail.session_id, prov, true);
    try {
      apply(await getSession(detail.session_id, prov));
    } catch {
      /* ignore */
    }
    setMsg("判断已锁定，系统候选已揭晓 ✓");
    setTimeout(() => setMsg(""), 3000);
  };

  const handleDeleteJudgment = async (judgmentId: number) => {
    if (!detail) return;
    if (!window.confirm("确定删除该条判断记录及其关联的 AI 复盘和形态缓存吗？")) return;
    try {
      const prov = curProvider(detail);
      await deleteJudgment(detail.session_id, judgmentId, prov);
      setJudgments((prev) => prev.filter((j) => j.id !== judgmentId));
      setReviewCache((prev) => {
        const next = { ...prev };
        delete next[judgmentId];
        return next;
      });
      setAnalogCache((prev) => {
        const next = { ...prev };
        delete next[judgmentId];
        return next;
      });
      localStorage.removeItem(`pall_coach_review_${detail.session_id}_${judgmentId}`);
      localStorage.removeItem(`pall_coach_analogs_${detail.session_id}_${judgmentId}`);
      if (coachJudgment?.id === judgmentId) {
        setCoachOpen(false);
        setCoachJudgment(null);
        setCoachReview(null);
        setAnalogMatches([]);
      }
      try {
        apply(await getSession(detail.session_id, prov));
      } catch {
        /* ignore */
      }
      setMsg("判断记录及关联复盘已安全清除 ✓");
      setTimeout(() => setMsg(""), 3000);
    } catch (e) {
      setMsg(`删除失败：${e}`);
    }
  };

  const handleDeleteCurrentSession = async () => {
    if (!detail) return;
    if (
      !window.confirm(
        "确定彻底删除本次训练会话吗？\n该会话下的所有判断记录、模拟交易持仓和笔记都将被清空，且不计入学习分析统计。"
      )
    ) {
      return;
    }
    try {
      const prov = curProvider(detail);
      await deleteSession(detail.session_id, prov);
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const k = localStorage.key(i);
        if (k && k.includes(detail.session_id)) {
          localStorage.removeItem(k);
        }
      }
      localStorage.removeItem(LAST_SESSION_KEY);
      setDetail(null);
      setJudgments([]);
      setTrades([]);
      setCoachOpen(false);
      setCoachJudgment(null);
      setCoachReview(null);
      setAnalogMatches([]);
      setMsg("本次测试会话已彻底删除清理 ✓");
      setTimeout(() => setMsg(""), 3000);
    } catch (e) {
      setMsg(`删除会话失败：${e}`);
    }
  };

  const handleCreateTrade = async () => {
    if (!detail) return;
    const prov = curProvider(detail);
    const e = Number(tradeEntry), s = Number(tradeStop), t = Number(tradeTarget);
    if (!tradeEntry || !tradeStop || !tradeTarget) {
      setMsg("请填写完整的计划价格");
      return;
    }
    if (![e, s, t].every((v) => Number.isFinite(v) && v > 0)) {
      setMsg("价格必须是有效的正数");
      return;
    }
    // 前端预校验价格次序，避免整坨后端 JSON 报错（多头：止损<入场<目标；空头：目标<入场<止损）
    if (tradeSide === "long" && !(s < e && e < t)) {
      setMsg("做多订单需满足：止损位 < 计划入场 < 目标位（当前止损应低于入场、目标高于入场）");
      return;
    }
    if (tradeSide === "short" && !(t < e && e < s)) {
      setMsg("做空订单需满足：目标位 < 计划入场 < 止损位（当前目标应低于入场、止损高于入场）");
      return;
    }
    setBusy(true);
    try {
      await createSimTrade(detail.session_id, prov, {
        side: tradeSide,
        order_type: tradeOrderType,
        planned_entry_price: e,
        stop_price: s,
        target_price: t,
        setup_notes: tradeNotes,
      });
      setTradeFormOpen(false);
      setTradeNotes("");
      refreshData(detail.session_id, prov, true);
      setMsg("模拟交易订单已下达 🎯");
      setTimeout(() => setMsg(""), 2500);
    } catch (err) {
      setMsg(`下单失败: ${err}`);
    } finally {
      setBusy(false);
    }
  };

  const handleManualExit = async (tradeId: string) => {
    if (!detail) return;
    const prov = curProvider(detail);
    try {
      await manualExitTrade(tradeId, detail.session_id, prov, "手动平仓");
      refreshData(detail.session_id, prov, true);
      setMsg("已平仓离场 ✓");
      setTimeout(() => setMsg(""), 2000);
    } catch (err) {
      setMsg(`平仓失败: ${err}`);
    }
  };

  const onSaveNote = async () => {
    if (!detail || !noteText.trim()) {
      setNoteOpen(false);
      return;
    }
    try {
      await addAnnotation(detail.session_id, curProvider(detail), detail.info.bar_index, "note", null, noteText.trim());
      setNoteText("");
      setNoteOpen(false);
      setMsg("标注已保存 ✓");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg(`标注失败：${e}`);
    }
  };

  const lastBar = useMemo(() => detail?.bars[detail.bars.length - 1] ?? null, [detail]);
  const candidates = detail?.candidates ?? [];
  const unlocked = candidates.length > 0;

  // 模拟持仓可视化：开放仓位在图上画 入场(蓝)/止损(红)/目标(绿) 三条价格线
  const tradeLines = useMemo<TradeLine[]>(() => {
    if (!detail) return [];
    return trades
      .filter((t) => t.status === "open" || t.status === "pending")
      .flatMap((t): TradeLine[] => {
        const entry = t.actual_entry_price ?? t.planned_entry_price;
        const sideTag = t.side === "long" ? "多" : "空";
        return [
          { price: entry, color: "#4da3ff", title: `入场 ${sideTag}` },
          { price: t.stop_price, color: "#ef5350", title: "止损" },
          { price: t.target_price, color: "#26a69a", title: "目标" },
        ];
      });
  }, [detail, trades]);

  // 开放仓位的浮动盈亏（R 倍数）与距止损/目标距离
  const openPositions = useMemo(() => {
    const cur = lastBar?.close ?? null;
    return trades
      .filter((t) => t.status === "open" || t.status === "pending")
      .map((t) => {
        const entry = t.actual_entry_price ?? t.planned_entry_price;
        const risk = t.initial_risk || Math.abs(entry - t.stop_price) || 1;
        const curPrice = cur ?? entry;
        const floatingR =
          t.side === "long" ? (curPrice - entry) / risk : (entry - curPrice) / risk;
        return {
          trade: t,
          entry,
          curPrice,
          floatingR: Math.round(floatingR * 100) / 100,
          distToStop: Math.abs(curPrice - t.stop_price),
          distToTarget: Math.abs(t.target_price - curPrice),
        };
      });
  }, [trades, lastBar]);
  const curCands = useMemo(
    () => candidates.filter((c) => c.bar_index === (detail?.info.bar_index ?? -1)),
    [candidates, detail?.info.bar_index],
  );

  const patternCount = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of candidates) {
      if (c.detector_id === "bar_pattern") m[String(c.result)] = (m[String(c.result)] ?? 0) + 1;
      if (c.detector_id === "inside_bar" && c.result === true) m.inside = (m.inside ?? 0) + 1;
      if (c.detector_id === "outside_bar" && c.result === true) m.outside = (m.outside ?? 0) + 1;
      if (c.detector_id === "hl_counting") m[String(c.result)] = (m[String(c.result)] ?? 0) + 1;
      if (c.detector_id === "wedge") m.wedge = (m.wedge ?? 0) + 1;
      if (c.detector_id === "climax") m.climax = (m.climax ?? 0) + 1;
      if (c.detector_id === "micro_channel") m.micro_channel = (m.micro_channel ?? 0) + 1;
    }
    return m;
  }, [candidates]);

  const cell = (id: string) => fmtCell(curCands.find((c) => c.detector_id === id));

  const chartMarkers = useMemo<ChartMarker[]>(() => {
    if (!detail || !unlocked || !showMarkers) return [];
    const ctxCount = detail.info.context_bar_count || 0;
    return candidates.flatMap((c): ChartMarker[] => {
      // 训练日的 bar_index 加上 context_bar_count 偏移，对齐完整 bars 数组
      const actualIdx = ctxCount + c.bar_index;
      const bar = detail.bars[actualIdx];
      if (!bar) return [];
      if (c.detector_id === "inside_bar" && c.result === true)
        return [{ time: bar.ts_open_utc, kind: "inside" as const }];
      if (c.detector_id === "outside_bar" && c.result === true)
        return [{ time: bar.ts_open_utc, kind: "outside" as const }];
      if (c.detector_id === "bar_pattern" && ["ii", "iii", "ioi"].includes(String(c.result)))
        return [{ time: bar.ts_open_utc, kind: String(c.result) as "ii" | "iii" | "ioi" }];
      if (c.detector_id === "swing" && ["swing_high", "swing_low"].includes(String(c.result))) {
        const j = (c.evidence as { swing_bar_index?: number }).swing_bar_index;
        const targetIdx = ctxCount + (j ?? c.bar_index);
        const sb = detail.bars[targetIdx] ?? bar;
        return [{ time: sb.ts_open_utc, kind: String(c.result) as "swing_high" | "swing_low" }];
      }
      if (c.detector_id === "hl_counting") {
        return [{ time: bar.ts_open_utc, kind: "hl" as const }];
      }
      if (c.detector_id === "wedge") {
        return [{ time: bar.ts_open_utc, kind: "wedge" as const }];
      }
      if (c.detector_id === "climax") {
        return [{ time: bar.ts_open_utc, kind: "climax" as const }];
      }
      if (c.detector_id === "micro_channel") {
        return [{ time: bar.ts_open_utc, kind: "micro_channel" as const }];
      }
      return [];
    });
  }, [detail, candidates, unlocked, showMarkers]);

  if (!detail) {
    return (
      <div className="setup-container">
        <div className="setup-header">
          <h2>🎯 逐根回放训练 · 会话设置</h2>
          <p className="sub">服务端权威游标 · 严格无前视偏差 · 支持加载前N日背景走势 · 模拟交易撮合与 MFE/MAE 追踪</p>
        </div>

        <div className="setup-grid">
          <div className="form-group">
            <label>行情数据源</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
              <option value="synthetic">本地合成演示数据 (Synthetic)</option>
              <option value="hfdl">真实 SPY 行情 (HF Data Library)</option>
            </select>
          </div>

          <div className="form-group">
            <label>训练模式</label>
            <select value={mode} onChange={(e) => setMode(e.target.value as "free" | "hidden_answer" | "exam")}>
              <option value="free">自由训练 (可回退后看)</option>
              <option value="hidden_answer">严格训练 (禁止回看)</option>
              <option value="exam">封存盲测考试 (随机封存集样本)</option>
            </select>
          </div>
          <div className="form-group">
            <label>选择指定交易日</label>
            <select value={day} onChange={(e) => setDay(e.target.value)}>
              <option value="">-- 请选择交易日 --</option>
              {days.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>预热天数 (前N日历史走势背景，0-60)</label>
            <input
              type="number"
              min={0}
              max={60}
              value={contextDays}
              onChange={(e) => {
                const v = Number(e.target.value);
                setContextDays(Number.isFinite(v) ? Math.max(0, Math.min(60, Math.floor(v))) : 0);
              }}
            />
          </div>

          <div className="form-group">
            <label>当日开盘预热 K 线数</label>
            <input
              type="number"
              min={0}
              max={50}
              value={warmup}
              onChange={(e) => setWarmup(Number(e.target.value) || 0)}
            />
          </div>
        </div>

        <div className="setup-actions">
          <button className="primary" disabled={!day || busy} onClick={() => start(day)}>
            🚀 开启逐根训练
          </button>
          <button className="ghost" onClick={startRandom} disabled={busy}>
            🎲 随机抽取交易日
          </button>
        </div>

        {msg && <p className="err" style={{ marginTop: 14 }}>{msg}</p>}

        <SessionsManager
          onResume={async (sid, prov, d) => {
            try {
              const det = await getSession(sid, prov);
              apply(det);
              setDay(d);
              setProvider(prov);
              setMode((det.info as { mode?: string }).mode === "exam" ? "exam" : (det.info as { mode?: string }).mode === "hidden_answer" ? "hidden_answer" : "free");
              refreshData(sid, prov);
              setMsg("已恢复历史训练会话 ✓");
              setTimeout(() => setMsg(""), 3000);
            } catch (e) {
              setMsg(`恢复会话失败：${e}`);
            }
          }}
        />
      </div>
    );
  }

  const kl = detail.key_levels;

  return (
    <div className="workbench">
      <div className="wb-main">
        <div className="toolbar">
          <div className="toolbar-group">
            <button className="primary" onClick={() => setPlaying((p) => !p)} disabled={detail.info.is_completed}>
              {playing ? "⏸ 暂停" : "▶ 播放"}
            </button>
            <button onClick={doAdvance} disabled={detail.info.is_completed}>
              → 下一根
            </button>
            <button className="ghost" onClick={doBack} disabled={mode !== "free"}>
              ← 上一根
            </button>
            <div className="toolbar-divider" />
            <select value={String(speedMs)} onChange={(e) => setSpeedMs(Number(e.target.value))}>
              {SPEEDS.map(([v, t]) => (
                <option key={v} value={v}>{t}</option>
              ))}
            </select>
          </div>

          <div className="toolbar-group">
            <button className="gold" onClick={() => setJudgmentOpen(true)}>
              ⚡ J · 提交判断
            </button>
            <button className="primary" onClick={() => {
              setTradeEntry(String(lastBar?.close ?? ""));
              setTradeStop("");
              setTradeTarget("");
              setTradeFormOpen(true);
            }}>
              🎯 T · 模拟下单
            </button>
            <button className="ghost" onClick={() => setNoteOpen(true)}>
              📝 M · 笔记
            </button>
            <div className="toolbar-divider" />
            <span className={`pill ${detail.info.is_completed ? "bad" : "ok"}`}>
              {detail.info.is_completed ? "COMPLETED" : "RECORDING"}
            </span>
            <button
              className="ghost small"
              onClick={() => {
                setDetail(null);
                setPlaying(false);
                setJudgments([]);
                setTrades([]);
              }}
            >
              ✕ 结束会话
            </button>
            <button
              className="ghost small coach-discard-btn"
              onClick={handleDeleteCurrentSession}
              title="彻底删除本次训练会话（清空其全部判断、持仓与笔记）"
            >
              🗑️ 丢弃会话
            </button>
          </div>
        </div>

        <div className="chart-area">
          <div className="overlay-toolbar">
            <button
              className={`small ghost overlay-toggle-btn ${overlaysOpen ? "active" : ""}`}
              onClick={() => setOverlaysOpen((v) => !v)}
              title="选择图表上显示的指标与图层"
            >
              ⚙️ 指标图层
            </button>
            {overlaysOpen && (
              <div className="overlay-panel">
                <div className="overlay-panel-title">图表图层显示开关</div>
                {(() => {
                  const row = (
                    key: Exclude<keyof ChartOverlays, "levelItems">,
                    label: string,
                    color?: string,
                  ) => (
                    <label key={key} className="overlay-item">
                      <input
                        type="checkbox"
                        checked={overlays[key]}
                        onChange={(e) => setOverlays((prev) => ({ ...prev, [key]: e.target.checked }))}
                      />
                      {color && <span className="overlay-color" style={{ background: color }} />}
                      {label}
                    </label>
                  );
                  return (
                    <>
                      <div className="overlay-group">
                        <div className="overlay-group-title">均线 EMA</div>
                        {row("ema5", "EMA20 · 5 分钟（基准）", "#f0b90b")}
                        {row("ema15", "EMA20 · 15 分钟（Brooks 近似）", "#4da3ff")}
                        {row("ema60", "EMA20 · 60 分钟（Brooks 近似）", "#9a86c9")}
                        {row("emaAxisLabels", "均线右侧数值标签")}
                      </div>
                      <div className="overlay-group">
                        <div className="overlay-group-title">关键价位线</div>
                        {row("keyLevels", "显示关键价位线（总开关）", "#c98a4b")}
                        <div className="overlay-level-grid">
                          {KEY_LEVEL_ITEMS.map((it) => (
                            <label
                              key={it.key}
                              className={`overlay-item ${overlays.keyLevels ? "" : "is-disabled"}`}
                            >
                              <input
                                type="checkbox"
                                disabled={!overlays.keyLevels}
                                checked={overlays.levelItems[it.key] !== false}
                                onChange={(e) =>
                                  setOverlays((prev) => ({
                                    ...prev,
                                    levelItems: { ...prev.levelItems, [it.key]: e.target.checked } as Record<
                                      LevelKey,
                                      boolean
                                    >,
                                  }))
                                }
                              />
                              <span className="overlay-color" style={{ background: it.color }} />
                              {it.label}
                            </label>
                          ))}
                        </div>
                        {row("keyLevelTitles", "价位线文字标题（如 PDH 前日高）")}
                      </div>
                      <div className="overlay-group">
                        <div className="overlay-group-title">交易与辅助</div>
                        {row("positions", "模拟持仓线（入场/止损/目标）", "#26a69a")}
                        <label className="overlay-item">
                          <input
                            type="checkbox"
                            checked={showMarkers}
                            onChange={(e) => setShowMarkers(e.target.checked)}
                          />
                          <span className="overlay-color" style={{ background: "#26a69a" }} />
                          形态识别标记（SH/SL/MC/Wedge…）
                        </label>
                        {row("ohlcLegend", "顶部 OHLC 实时图例")}
                      </div>
                    </>
                  );
                })()}
                <div className="overlay-panel-hint">
                  设置自动保存在本机浏览器，刷新后保持；周期切换与画线工具在图表右上角工具条。画线悬停可拖动、拖端点微调；双击画线可打开设置（精确价位 / 斐波那契水平 / 盈亏比目标 / 颜色）。
                </div>
              </div>
            )}
          </div>
          <CandleChart
            bars={detail.bars}
            ema20={detail.ema20}
            ema15={detail.ema15}
            ema60={detail.ema60}
            keyLevels={kl}
            markers={chartMarkers}
            overlays={overlays}
            tradeLines={tradeLines}
            sessionKey={detail.session_id}
          />
        </div>

        <div className="statusbar">
          <div className="statusbar-left">
            <span>标的：<b>SPY 5m ({detail.info.provider})</b></span>
            <span>日期：<b>{detail.info.day}</b></span>
            {detail.info.context_bar_count > 0 && (
              <span>背景：<b>{detail.info.context_bar_count} 根历史K线</b></span>
            )}
            <span>当日进度：第 <b>{detail.info.bar_index + 1}</b> / 78 根</span>
            <span>市场时间：<b>{fmtET(detail.info.market_time_utc)} ET</b> <span className="hint">({fmtSH(detail.info.market_time_utc)} CST)</span></span>
          </div>
          <div className="hint">
            {detail.info.provider === "hfdl" ? "HFDL 真实数据 · 复权价格 · 仅 RTH" : "本地合成演示数据"}
          </div>
        </div>
      </div>

      <aside className="wb-side">
        <div className="sidebar-card">
          <h4>
            <span>日内关键价位 (Key Levels)</span>
            <span className="hint">已收盘基准</span>
          </h4>
          <table className="kv">
            <tbody>
              <tr><td>前日开盘 (PDO)</td><td>{kl?.prev_day_open?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>前日最高 (PDH)</td><td>{kl?.prev_day_high?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>前日最低 (PDL)</td><td>{kl?.prev_day_low?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>前日收盘 (PDC)</td><td>{kl?.prev_day_close?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>今日开盘 (OPEN)</td><td>{kl?.today_open?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>盘前最高 (PRE-H)</td><td>{kl?.premarket_high?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>盘前最低 (PRE-L)</td><td>{kl?.premarket_low?.toFixed(2) ?? "—"}</td></tr>
              <tr><td>跳空缺口 (GAP)</td><td>{kl?.gap ? `${kl.gap > 0 ? "+" : ""}${kl.gap.toFixed(2)}` : "—"}</td></tr>
            </tbody>
          </table>
        </div>

        {/* 仓位管理 · 模拟持仓卡片 */}
        <div className="sidebar-card">
          <h4>
            <span>仓位管理 · 模拟持仓</span>
            <span className={`pill ${openPositions.length ? "primary" : "ghost"}`}>
              持仓 {openPositions.length} / 历史 {trades.length}
            </span>
          </h4>
          {tradesError && (
            <div className="position-error">
              <span>⚠️ {tradesError}</span>
              {detail && (
                <button
                  className="small ghost"
                  onClick={() => refreshData(detail.session_id, curProvider(detail), true)}
                >
                  立即重试
                </button>
              )}
            </div>
          )}
          {trades.length === 0 && !tradesError ? (
            <p className="hint" style={{ padding: "6px 0" }}>
              按 <b>T</b> 或点击工具栏「🎯 模拟下单」开立头寸。下单后入场/止损/目标会自动画在图表上。
            </p>
          ) : (
            <div className="jlist">
              {openPositions.length === 0 && (
                <p className="hint" style={{ padding: "4px 0" }}>
                  当前无开放仓位。以下为已了结的历史交易：
                </p>
              )}
              {openPositions.map(({ trade: t, entry, curPrice, floatingR, distToStop, distToTarget }) => (
                <div key={t.id} className="jitem position-item">
                  <div className="jitem-header">
                    <span className="jitem-title">
                      {t.side === "long" ? "🟢 多头持仓" : "🔴 空头持仓"} @ {entry}
                    </span>
                    <span className={`pill small ${floatingR >= 0 ? "ok" : "bad"}`}>
                      {floatingR >= 0 ? "+" : ""}
                      {floatingR.toFixed(2)}R
                    </span>
                  </div>
                  <table className="kv position-kv">
                    <tbody>
                      <tr>
                        <td>现价</td>
                        <td><b>{curPrice}</b></td>
                      </tr>
                      <tr>
                        <td className="stop-cell">止损 {t.stop_price}</td>
                        <td>还差 <b>{distToStop.toFixed(2)}</b> 点触发</td>
                      </tr>
                      <tr>
                        <td className="target-cell">目标 {t.target_price}</td>
                        <td>还差 <b>{distToTarget.toFixed(2)}</b> 点到达</td>
                      </tr>
                      <tr>
                        <td>风险基数 R</td>
                        <td>{t.initial_risk}</td>
                      </tr>
                    </tbody>
                  </table>
                  <div className="hint" style={{ marginTop: 2, fontSize: 10.5 }}>
                    MFE +{t.mfe_in_r ?? 0}R / MAE {t.mae_in_r ?? 0}R（随推进自动更新）
                  </div>
                  <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                    <button className="small ghost" onClick={() => handleManualExit(t.id)}>
                      ✋ 市价平仓
                    </button>
                    <span className="hint" style={{ alignSelf: "center" }}>
                      或等待 K 线推进自动触发止损/止盈
                    </span>
                  </div>
                </div>
              ))}
              {trades
                .filter((t) => t.status === "closed")
                .map((t) => (
                  <div key={t.id} className="jitem">
                    <div className="jitem-header">
                      <span className="jitem-title">
                        {t.side === "long" ? "🟢 多" : "🔴 空"} @ {t.actual_entry_price ?? t.planned_entry_price} → {t.exit_price}
                      </span>
                      <span className={`pill small ${t.pnl && t.pnl > 0 ? "ok" : "bad"}`}>
                        {t.exit_reason}: {t.pnl_in_r}R
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

        <div className="sidebar-card">
          <h4>
            <span>价格行为形态识别器 (Level 1-5)</span>
            <span className={`pill ${unlocked ? "ok" : "ghost"}`}>{unlocked ? "已解锁" : "未解锁"}</span>
          </h4>
          {!unlocked ? (
            <p className="hint" style={{ padding: "6px 0" }}>
              💡 按 <b>J</b> 提交当前市场判断后，系统候选识别依据将自动揭晓。
            </p>
          ) : (
            <>
              <table className="kv">
                <tbody>
                  <tr><td>K线类型 (trend_bar)</td><td><b>{cell("trend_bar")}</b></td></tr>
                  <tr><td>十字星 (doji)</td><td>{cell("doji")}</td></tr>
                  <tr><td>内包/外包 (IB/OB)</td><td>{cell("inside_bar")} / {cell("outside_bar")}</td></tr>
                  <tr><td>形态序列 (ii/iii/ioi)</td><td><b>{cell("bar_pattern")}</b></td></tr>
                  <tr><td>摆动高低 (swing)</td><td>{cell("swing")}</td></tr>
                  <tr><td>回调状态 (pullback)</td><td>{cell("pullback_leg")}</td></tr>
                  <tr><td>计数序列 (H/L)</td><td><span className="pill primary">{cell("hl_counting")}</span></td></tr>
                  <tr><td>微型通道 (micro_channel)</td><td><b>{cell("micro_channel")}</b></td></tr>
                  <tr><td>楔形三推 (wedge)</td><td><b>{cell("wedge")}</b></td></tr>
                  <tr><td>高潮反转 (climax)</td><td><b>{cell("climax")}</b></td></tr>
                </tbody>
              </table>
              <div className="hint" style={{ marginTop: 8, fontSize: 11 }}>
                当日统计：内包 {patternCount.inside ?? 0} · 外包 {patternCount.outside ?? 0}
                {patternCount.ii ? ` · ii ${patternCount.ii}` : ""}
                {patternCount.iii ? ` · iii ${patternCount.iii}` : ""}
                {patternCount.ioi ? ` · ioi ${patternCount.ioi}` : ""}
                {patternCount.wedge ? ` · 楔形 ${patternCount.wedge}` : ""}
                {patternCount.climax ? ` · 高潮 ${patternCount.climax}` : ""}
              </div>
              <div className="hint" style={{ marginTop: 6 }}>
                形态标记可通过图表左上角「⚙️ 指标图层」自主显示/隐藏。
              </div>
            </>
          )}
        </div>

        <div className="sidebar-card">
          <h4>
            <span>已锁定判断记录 ({judgments.length})</span>
            <span className="hint">Predict First</span>
          </h4>
          <div className="jlist">
            {judgments.length === 0 ? (
              <p className="hint" style={{ padding: "8px 0" }}>暂无判断记录。按 <b>J</b> 先行提交观点。</p>
            ) : (
              judgments.slice().reverse().map((j) => (
                <div key={j.id} className="jitem">
                  <div className="jitem-header">
                    <span className="jitem-title">#{j.bar_index + 1} 根 · {CONTEXT_ZH[j.payload.context_label] ?? j.payload.context_label}</span>
                    <span className={`pill small ${j.payload.direction === "long" ? "ok" : j.payload.direction === "short" ? "bad" : "ghost"}`}>
                      {j.payload.direction === "long" ? "做多" : j.payload.direction === "short" ? "做空" : "不交易"}
                    </span>
                  </div>
                  {j.payload.reasons.length > 0 && (
                    <div className="jitem-reasons">理由：{j.payload.reasons.join("；")}</div>
                  )}
                  <div className="jitem-footer">
                    <span className="hint">已保留原始判断</span>
                    <div className="jitem-actions">
                      <button
                        className="small coach-button"
                        onClick={() => openCoachReview(j, false)}
                        title={
                          reviewCache[j.id] || (detail && getStoredReview(detail.session_id, j.id))
                            ? "点击查看已保存的 AI 对照复盘"
                            : "调用 AI 生成对照复盘"
                        }
                      >
                        {reviewCache[j.id] || (detail && getStoredReview(detail.session_id, j.id))
                          ? "✦ 查看复盘"
                          : "✦ AI 对照复盘"}
                      </button>
                      {(reviewCache[j.id] || (detail && getStoredReview(detail.session_id, j.id))) && (
                        <button
                          className="small ghost coach-reanalyze-icon-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            openCoachReview(j, true);
                          }}
                          disabled={coachLoading && coachJudgment?.id === j.id}
                          title="重新分析：重新调用 AI 独立诊断"
                        >
                          🔄
                        </button>
                      )}
                      <button
                        className="small ghost coach-delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteJudgment(j.id);
                        }}
                        title="删除该判断记录及对应的 AI 复盘与形态缓存"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* 模拟下单弹窗 */}
      {tradeFormOpen && (
        <div className="modal-mask" onClick={() => setTradeFormOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 520 }}>
            <h3>🎯 建立模拟交易订单 (Sim Trade)</h3>
            
            <div className="setup-grid">
              <div className="form-group">
                <label>交易方向</label>
                <div className="radio-group">
                  <span className={`chip ${tradeSide === "long" ? "on bull" : ""}`} onClick={() => setTradeSide("long")}>做多 (Long)</span>
                  <span className={`chip ${tradeSide === "short" ? "on bear" : ""}`} onClick={() => setTradeSide("short")}>做空 (Short)</span>
                </div>
              </div>
              <div className="form-group">
                <label>订单类型</label>
                <select value={tradeOrderType} onChange={(e) => setTradeOrderType(e.target.value as any)}>
                  <option value="market">市价单 (Market)</option>
                  <option value="limit">限价单 (Limit)</option>
                  <option value="stop">停止突破单 (Stop)</option>
                </select>
              </div>
            </div>

            <div className="setup-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
              <div className="form-group">
                <label>计划价格 (Entry)</label>
                <input type="number" step="0.01" value={tradeEntry} onChange={(e) => setTradeEntry(e.target.value)} />
              </div>
              <div className="form-group">
                <label>止损价 (Stop / 失效点)</label>
                <input type="number" step="0.01" value={tradeStop} onChange={(e) => setTradeStop(e.target.value)} />
              </div>
              <div className="form-group">
                <label>止盈目标价 (Target)</label>
                <input type="number" step="0.01" value={tradeTarget} onChange={(e) => setTradeTarget(e.target.value)} />
              </div>
            </div>

            <div className="form-group">
              <label>入场依据与逻辑笔记 (Setup Thesis)</label>
              <textarea rows={2} value={tradeNotes} onChange={(e) => setTradeNotes(e.target.value)} placeholder="例如：突破 20EMA 后首个 H2 二次买点..." />
            </div>

            <div className="actions">
              <button className="ghost" onClick={() => setTradeFormOpen(false)}>取消</button>
              <button className="primary" onClick={handleCreateTrade} disabled={busy}>确认下单</button>
            </div>
          </div>
        </div>
      )}

      {judgmentOpen && (
        <JudgmentForm
          barIndex={detail.info.bar_index}
          price={lastBar?.close ?? 0}
          onSubmit={onSubmitJudgment}
          onCancel={() => setJudgmentOpen(false)}
        />
      )}

      {coachOpen && coachJudgment && (
        <div className="modal-mask coach-mask" onClick={() => setCoachOpen(false)}>
          <section className="coach-drawer" onClick={(e) => e.stopPropagation()} aria-labelledby="coach-title">
            <div className="coach-header">
              <div>
                <div className="eyebrow">DECISION REVIEW · #{coachJudgment.bar_index + 1}</div>
                <h3 id="coach-title">AI 对照复盘</h3>
                <p className="hint">只对照提交当刻可见信息，不改写、不覆盖你的原始判断。</p>
              </div>
              <div className="coach-header-actions">
                <button
                  className="small secondary coach-reanalyze-button"
                  onClick={() => openCoachReview(coachJudgment, true)}
                  disabled={coachLoading}
                  title="让 AI 重新深度分析此决策点（覆盖已有记忆）"
                >
                  {coachLoading ? "正在重新分析…" : "🔄 重新分析"}
                </button>
                <button className="ghost small" onClick={() => setCoachOpen(false)} aria-label="关闭复盘面板">✕</button>
              </div>
            </div>

            <div className="coach-original">
              <div className="coach-section-label">我的判断 <span className="pill primary">ORIGINAL</span></div>
              <div className="coach-original-grid">
                <span>背景：<b>{CONTEXT_ZH[coachJudgment.payload.context_label] ?? coachJudgment.payload.context_label}</b></span>
                <span>方向：<b>{coachJudgment.payload.direction === "long" ? "做多" : coachJudgment.payload.direction === "short" ? "做空" : "不交易"}</b></span>
                <span>信心：<b>{coachJudgment.payload.confidence || "—"}</b></span>
                <span>概率：<b>{coachJudgment.payload.probability_estimate || "—"}</b></span>
              </div>
              {coachJudgment.payload.structure_note && <p>{coachJudgment.payload.structure_note}</p>}
              {coachJudgment.payload.reasons.length > 0 && <p className="coach-reasons">理由：{coachJudgment.payload.reasons.join("；")}</p>}
            </div>

            {coachLoading ? (
              <div className="coach-loading"><span className="coach-spinner" /> 正在检索来源并生成对照…</div>
            ) : coachError ? (
              <div className="coach-state coach-state-error"><b>复盘暂时不可用</b><span>{coachError}</span></div>
            ) : coachConfig && (!coachConfig.configured || !coachConfig.enabled) ? (
              <div className="coach-state coach-state-muted">
                <div className="coach-state-icon">AI</div>
                <div><b>AI 教练尚未配置</b><p>当前仅保留你的判断，不会伪造 AI 结论或相似走势数据。配置 {coachConfig.provider} API Key 后即可生成三层对照复盘。</p></div>
                <span className="pill ghost">未配置</span>
              </div>
            ) : coachReview ? (
              <>
                <div className="coach-layer-grid">
                  <article className="coach-layer source">
                    <span className="coach-layer-index">01</span>
                    <div>
                      <h4>阿布价格行为学课件原意</h4>
                      {renderLayerBody(coachReview.source_grounded, "source_grounded", "暂无可引用的课件原意。")}
                    </div>
                  </article>
                  <article className="coach-layer mechanical">
                    <span className="coach-layer-index">02</span>
                    <div>
                      <h4>当前行情客观事实</h4>
                      {renderLayerBody(coachReview.mechanical_approx, "mechanical_approx", "暂无行情客观事实说明。")}
                    </div>
                  </article>
                  <article className="coach-layer interpretation">
                    <span className="coach-layer-index">03</span>
                    <div>
                      <h4>教练解释</h4>
                      {renderLayerBody(coachReview.coach_interpretation, "coach_interpretation", "暂无教练解释。")}
                    </div>
                  </article>
                </div>
                <div className="coach-references">
                  <div className="coach-section-label">
                    📖 阿布课件与原书相关形态图示 <span className={`pill ${coachReview.references.length ? "blue" : "ghost"}`}>{coachReview.references.length} 张原型图</span>
                  </div>
                  {coachReview.references.length ? (
                    <div className="reference-list">
                      {coachReview.references.map((ref, i) => (
                        <div className="reference-item" key={`${ref.chunk_id ?? "ref"}-${i}`}>
                          <span className="reference-mark">{String(i + 1).padStart(2, "0")}</span>
                          <div className="reference-content">
                            <div className="reference-header">
                              <b>{ref.book ?? "知识库来源"}</b>
                              <small>
                                {ref.pdf_page ? `PDF p.${ref.pdf_page}` : "页码未标注"}
                                {ref.print_page ? ` · 印刷页 ${ref.print_page}` : ""}
                                {ref.source_file
                                  ? ` · ${ref.source_file.split(/[\\/]/).pop()}`
                                  : ref.source_type
                                  ? ` · ${ref.source_type}`
                                  : ""}
                              </small>
                            </div>
                            {ref.content && <p className="reference-quote">{ref.content}</p>}
                            {ref.image_url && (
                              <div
                                className="reference-preview-box"
                                onClick={() => setLightboxImage(ref.image_url || null)}
                                title="点击放大查看原版课件/原书高清原图"
                              >
                                <img src={ref.image_url} alt={`${ref.book} p.${ref.pdf_page}`} loading="lazy" />
                                <span className="reference-preview-overlay">
                                  🔍 点击全屏放大查看阿布课件原版图示 (第 {ref.pdf_page} 页)
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="hint">暂无可核验来源。请将此结果视为不充分证据。</p>
                  )}
                  {coachReview.insufficient_evidence && (
                    <div className="evidence-warning">
                      依据不足：AI 已明确标记 insufficient_evidence，请勿将本次对照视为确定结论。
                    </div>
                  )}
                </div>
                <div className="coach-extension">
                  <div className="analog-extension-header">
                    <div className="coach-section-label">
                      📊 过往 SPY 历史相似走势走势图 (严格排除当前训练日) <span className="pill blue">TOP {analogMatches.length}</span>
                    </div>
                    <div className="analog-date-filter">
                      <span className="filter-hint">限定过往时间段：</span>
                      <div className="date-range-inputs">
                        <input
                          type="date"
                          value={analogStartDate}
                          onChange={(e) => setAnalogStartDate(e.target.value)}
                          placeholder="起始日期"
                          title="限定历史形态起始日期 (YYYY-MM-DD)"
                        />
                        <span className="range-sep">至</span>
                        <input
                          type="date"
                          value={analogEndDate}
                          onChange={(e) => setAnalogEndDate(e.target.value)}
                          placeholder="结束日期"
                          title="限定历史形态结束日期 (YYYY-MM-DD)"
                        />
                      </div>
                      <button
                        className="small secondary"
                        onClick={() => handleFetchAnalogsByRange(analogStartDate, analogEndDate)}
                        disabled={(!analogStartDate && !analogEndDate) || analogLoading}
                      >
                        {analogLoading ? "检索中…" : "抓取该时间段形态"}
                      </button>
                      {(analogStartDate || analogEndDate) && (
                        <button
                          className="small ghost"
                          onClick={() => {
                            setAnalogStartDate("");
                            setAnalogEndDate("");
                            handleFetchAnalogsByRange("", "");
                          }}
                          disabled={analogLoading}
                          title="重置为全量过往历史检索"
                        >
                          恢复全部历史
                        </button>
                      )}
                    </div>
                  </div>
                  {analogMatches.length ? (
                    <div className="analog-list">
                      {analogMatches.map((match) => (
                        <div className="analog-item" key={`${match.start_time}-${match.distance}`}>
                          <div className="analog-item-header">
                            <span>
                              <b>{match.date} (过往历史 SPY)</b>
                              <small>
                                {new Date(match.start_time).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })} —{" "}
                                {new Date(match.end_time).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })} · {match.pattern_label}
                              </small>
                            </span>
                            <span className="analog-result">
                              <b
                                className={
                                  match.forward_direction === "up"
                                    ? "color-bull"
                                    : match.forward_direction === "down"
                                    ? "color-bear"
                                    : ""
                                }
                              >
                                {match.forward_direction === "up"
                                  ? "▲ 上涨"
                                  : match.forward_direction === "down"
                                  ? "▼ 下跌"
                                  : "— 震荡"}
                                {match.forward_return !== null &&
                                  ` (${(match.forward_return * 100).toFixed(2)}%)`}
                              </b>
                              <small>{(match.similarity * 100).toFixed(1)}% 相似</small>
                            </span>
                          </div>
                          {match.chart_image_url && (
                            <div
                              className="analog-chart-box"
                              onClick={() => setLightboxImage(match.chart_image_url || null)}
                              title="点击全屏查看过往 SPY 高清走势图"
                            >
                              <img src={match.chart_image_url} alt="过往 SPY 真实走势图" loading="lazy" />
                              <span className="reference-preview-overlay">
                                🔍 点击全屏放大查看过往 SPY K 线走势图与后 10 根演化
                              </span>
                            </div>
                          )}
                          {(match.window_bars?.length || match.forward_bars?.length) ? (
                            <MiniCandleChart
                              windowBars={match.window_bars}
                              forwardBars={match.forward_bars}
                            />
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <small>暂无可用历史片段；系统不会展示伪造相似走势。</small>
                  )}
                </div>
              </>
            ) : null}
          </section>
        </div>
      )}

      {lightboxImage && (
        <div className="modal-mask lightbox-mask" onClick={() => setLightboxImage(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <div className="lightbox-header">
              <span>📖 Al Brooks 课件与原书图示原型</span>
              <button className="ghost small" onClick={() => setLightboxImage(null)}>✕ 关闭</button>
            </div>
            <div className="lightbox-body">
              <img src={lightboxImage} alt="课件原图高保真预览" />
            </div>
          </div>
        </div>
      )}

      {noteOpen && (
        <div className="modal-mask" onClick={() => setNoteOpen(false)}>
          <div className="modal note-modal" onClick={(e) => e.stopPropagation()}>
            <div className="note-modal-header">
              <h3>📝 K 线笔记</h3>
              <span className="note-modal-meta">
                第 <b>{detail.info.bar_index + 1}</b> 根 ·{" "}
                {fmtET(detail.info.market_time_utc)} ET · 现价{" "}
                <b>{lastBar?.close ?? "—"}</b>
              </span>
            </div>
            <textarea
              className="note-textarea"
              rows={8}
              autoFocus
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder={"记录当前读图心得，例如：\n· 此处回调至 EMA20 上方出现多头信号棒\n· 但上方前高存在明显阻力，等待二次突破确认\n· 若跌破前低则多头论调失效"}
            />
            <div className="note-modal-footer">
              <span className="hint">{noteText.length} 字 · 保存后可在复盘与错题本中回看</span>
              <div className="actions" style={{ margin: 0 }}>
                <button className="ghost" onClick={() => setNoteOpen(false)}>取消</button>
                <button className="primary" onClick={onSaveNote} disabled={!noteText.trim()}>
                  保存笔记
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {msg && (
        <div className={`msg ${/失败|错误|Error|不可用/.test(msg) ? "msg-error" : ""}`}>
          <span className="msg-text">{msg}</span>
          <button className="msg-close" onClick={() => setMsg("")} aria-label="关闭提示">
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
