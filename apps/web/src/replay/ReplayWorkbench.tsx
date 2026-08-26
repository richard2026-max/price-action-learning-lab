/**
 * MVP-A/Phase 2/Phase 3 回放工作台（整合 Level 1-5 全阶价格行为形态、前N日走势上下文背景与模拟交易）。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CandleChart, { type ChartMarker } from "../chart/CandleChart";
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
  listSessionTrades,
  manualExitTrade,
  randomDay,
  submitJudgment,
  getCoachConfig,
  reviewJudgmentWithCoach,
  searchJudgmentAnalogs,
  type AnalogMatch,
  type Candidate,
  type CoachConfig,
  type CoachReview,
  type Judgment,
  type JudgmentPayload,
  type Provider,
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
  const [analogMatches, setAnalogMatches] = useState<AnalogMatch[]>([]);
  const [coachJudgment, setCoachJudgment] = useState<Judgment | null>(null);
  const [coachError, setCoachError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [showMarkers, setShowMarkers] = useState(true);
  const advLock = useRef(false);

  useEffect(() => {
    listDays(provider).then(setDays).catch((e) => setMsg(`获取日期失败：${e}`));
  }, [provider]);

  const refreshData = useCallback((sid: string, p: Provider) => {
    listJudgments(sid, p).then(setJudgments).catch(() => setJudgments([]));
    listSessionTrades(sid).then(setTrades).catch(() => setTrades([]));
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

  const openCoachReview = async (judgment: Judgment) => {
    if (!detail) return;
    setCoachJudgment(judgment);
    setCoachReview(null);
    setAnalogMatches([]);
    setCoachError("");
    setCoachOpen(true);
    setCoachLoading(true);
    try {
      const config = await getCoachConfig();
      setCoachConfig(config);
      const analogPromise = searchJudgmentAnalogs(detail.session_id, judgment.id)
        .then((result) => setAnalogMatches(result.matches))
        .catch(() => setAnalogMatches([]));
      if (!config.configured || !config.enabled) {
        await analogPromise;
        return;
      }
      const [review] = await Promise.all([
        reviewJudgmentWithCoach(detail.session_id, judgment.id),
        analogPromise,
      ]);
      setCoachReview(review);
    } catch (e) {
      setCoachError(String(e));
    } finally {
      setCoachLoading(false);
    }
  };

  const onSubmitJudgment = async (p: JudgmentPayload) => {
    if (!detail) return;
    const prov = curProvider(detail);
    await submitJudgment(detail.session_id, prov, p);
    setJudgmentOpen(false);
    refreshData(detail.session_id, prov);
    try {
      apply(await getSession(detail.session_id, prov));
    } catch {
      /* ignore */
    }
    setMsg("判断已锁定，系统候选已揭晓 ✓");
    setTimeout(() => setMsg(""), 3000);
  };

  const handleCreateTrade = async () => {
    if (!detail) return;
    const prov = curProvider(detail);
    const e = Number(tradeEntry), s = Number(tradeStop), t = Number(tradeTarget);
    if (!tradeEntry || !tradeStop || !tradeTarget) {
      setMsg("请填写完整的计划价格");
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
      refreshData(detail.session_id, prov);
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
      refreshData(detail.session_id, prov);
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
            <label>预热天数 (前N日历史走势背景)</label>
            <input
              type="number"
              min={0}
              max={10}
              value={contextDays}
              onChange={(e) => setContextDays(Number(e.target.value) || 0)}
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
          </div>
        </div>

        <div className="chart-area">
          <CandleChart bars={detail.bars} ema20={detail.ema20} keyLevels={kl} markers={chartMarkers} />
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

        {/* 模拟交易持仓卡片 */}
        <div className="sidebar-card">
          <h4>
            <span>模拟持仓与出场 (Sim Trades: {trades.length})</span>
            <span className="pill blue">Level 6</span>
          </h4>
          {trades.length === 0 ? (
            <p className="hint" style={{ padding: "6px 0" }}>按 <b>T</b> 或点击工具栏下单按钮开立模拟头寸。</p>
          ) : (
            <div className="jlist">
              {trades.map((t) => (
                <div key={t.id} className="jitem">
                  <div className="jitem-header">
                    <span className="jitem-title">
                      {t.side === "long" ? "🟢 BUY 多" : "🔴 SELL 空"} @ {t.actual_entry_price ?? t.planned_entry_price}
                    </span>
                    <span className={`pill small ${t.status === "closed" ? (t.pnl && t.pnl > 0 ? "ok" : "bad") : "primary"}`}>
                      {t.status === "closed" ? `${t.exit_reason}: ${t.pnl_in_r}R` : t.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="hint" style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
                    S: {t.stop_price} | T: {t.target_price} | R: {t.initial_risk}
                  </div>
                  {t.status === "open" && (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                      <span className="hint">MFE: +{t.mfe_in_r}R / MAE: {t.mae_in_r}R</span>
                      <button className="small ghost" onClick={() => handleManualExit(t.id)}>平仓</button>
                    </div>
                  )}
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
              <label className="hint" style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 6 }}>
                <input type="checkbox" checked={showMarkers} onChange={(e) => setShowMarkers(e.target.checked)} />
                在 K 线图上叠加几何与形态标记
              </label>
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
                    <button className="small coach-button" onClick={() => openCoachReview(j)}>
                      ✦ AI 对照复盘
                    </button>
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
              <button className="ghost small" onClick={() => setCoachOpen(false)} aria-label="关闭复盘面板">✕</button>
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
                  <article className="coach-layer source"><span className="coach-layer-index">01</span><div><h4>原书依据</h4><p>{coachReview.source_grounded || "暂无可引用的原书依据。"}</p></div></article>
                  <article className="coach-layer mechanical"><span className="coach-layer-index">02</span><div><h4>系统机械近似</h4><p>{coachReview.mechanical_approx || "暂无机械近似说明。"}</p></div></article>
                  <article className="coach-layer interpretation"><span className="coach-layer-index">03</span><div><h4>教练解释</h4><p>{coachReview.coach_interpretation || "暂无教练解释。"}</p></div></article>
                </div>
                <div className="coach-references">
                  <div className="coach-section-label">引用页码 / 来源 <span className={`pill ${coachReview.references.length ? "blue" : "ghost"}`}>{coachReview.references.length} 条</span></div>
                  {coachReview.references.length ? <div className="reference-list">{coachReview.references.map((ref, i) => <div className="reference-item" key={`${ref.chunk_id ?? "ref"}-${i}`}><span className="reference-mark">{String(i + 1).padStart(2, "0")}</span><span><b>{ref.book ?? "知识库来源"}</b><small>{ref.pdf_page ? `PDF p.${ref.pdf_page}` : "页码未标注"}{ref.print_page ? ` · 印刷页 ${ref.print_page}` : ""} · {ref.source_file ?? ref.source_type ?? "本地知识库"}</small></span></div>)}</div> : <p className="hint">暂无可核验来源。请将此结果视为不充分证据。</p>}
                  {coachReview.insufficient_evidence && <div className="evidence-warning">依据不足：AI 已明确标记 insufficient_evidence，请勿将本次对照视为确定结论。</div>}
                </div>
                <div className="coach-extension">
                  <div className="coach-section-label">历史相似走势 <span className="pill blue">TOP {analogMatches.length}</span></div>
                  {analogMatches.length ? <div className="analog-list">{analogMatches.map((match) => <div className="analog-item" key={`${match.start_time}-${match.distance}`}><span><b>{match.date}</b><small>{new Date(match.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} — {new Date(match.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · {match.pattern_label}</small></span><span className="analog-result"><b>{match.forward_direction.toUpperCase()}</b><small>{(match.similarity * 100).toFixed(1)}% 相似</small></span></div>)}</div> : <small>暂无可用历史片段；系统不会展示伪造相似走势。</small>}
                </div>
              </>
            ) : null}
          </section>
        </div>
      )}

      {noteOpen && (
        <div className="modal-mask" onClick={() => setNoteOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 640 }}>
            <h3>📝 添加 K 线笔记 (第 {detail.info.bar_index + 1} 根)</h3>
            <textarea
              rows={6}
              autoFocus
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="记录当前读图心得，例如：此处回调至 EMA20 上方出现多头信号棒，但上方前高存在明显阻力..."
            />
            <div className="actions">
              <button className="ghost" onClick={() => setNoteOpen(false)}>取消</button>
              <button className="primary" onClick={onSaveNote}>保存笔记</button>
            </div>
          </div>
        </div>
      )}

      {msg && <div className="msg">{msg}</div>}
    </div>
  );
}
