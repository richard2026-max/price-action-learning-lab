/**
 * MVP-A 回放工作台（专业金融终端风格重构版）。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CandleChart, { type ChartMarker } from "../chart/CandleChart";
import JudgmentForm from "./JudgmentForm";
import {
  addAnnotation,
  advance,
  createSession,
  getSession,
  goBack,
  listDays,
  listJudgments,
  randomDay,
  submitJudgment,
  type Candidate,
  type Judgment,
  type JudgmentPayload,
  type Provider,
  type SessionDetail,
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
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(1000);
  const [judgmentOpen, setJudgmentOpen] = useState(false);
  const [judgments, setJudgments] = useState<Judgment[]>([]);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [showMarkers, setShowMarkers] = useState(true);
  const advLock = useRef(false);

  useEffect(() => {
    listDays(provider).then(setDays).catch((e) => setMsg(`获取日期失败：${e}`));
  }, [provider]);

  const refreshJudgments = useCallback((sid: string, p: Provider) => {
    listJudgments(sid, p).then(setJudgments).catch(() => setJudgments([]));
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
        refreshJudgments(d.session_id, (d.info.provider as Provider) ?? "synthetic");
      })
      .catch(() =>
        getSession(last, "hfdl")
          .then((d) => {
            setDetail(d);
            setDay(d.info.day);
            setProvider("hfdl");
            refreshJudgments(d.session_id, "hfdl");
          })
          .catch(() => localStorage.removeItem(LAST_SESSION_KEY)),
      );
  }, [refreshJudgments]);

  const start = async (d: string) => {
    if (!d) return;
    setBusy(true);
    setPlaying(false);
    try {
      const det = await createSession(d, mode, warmup, provider);
      apply(det);
      setDay(d);
      refreshJudgments(det.session_id, curProvider(det));
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
      apply(await advance(detail.session_id, curProvider(detail), 1));
    } catch (e) {
      setMsg(String(e));
      setPlaying(false);
    } finally {
      advLock.current = false;
    }
  }, [detail, apply]);

  const doBack = useCallback(async () => {
    if (!detail || mode !== "free") return;
    try {
      apply(await goBack(detail.session_id, curProvider(detail)));
    } catch (e) {
      setMsg(String(e));
    }
  }, [detail, apply, mode]);

  useEffect(() => {
    if (!playing || !detail || detail.info.is_completed || judgmentOpen) return;
    const t = setInterval(doAdvance, speedMs);
    return () => clearInterval(t);
  }, [playing, speedMs, detail, doAdvance, judgmentOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || judgmentOpen) return;
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
      } else if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        setNoteOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [detail, doAdvance, doBack, judgmentOpen]);

  const onSubmitJudgment = async (p: JudgmentPayload) => {
    if (!detail) return;
    const prov = curProvider(detail);
    await submitJudgment(detail.session_id, prov, p);
    setJudgmentOpen(false);
    refreshJudgments(detail.session_id, prov);
    try {
      apply(await getSession(detail.session_id, prov));
    } catch {
      /* ignore */
    }
    setMsg("判断已锁定，系统候选已揭晓 ✓");
    setTimeout(() => setMsg(""), 3000);
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
    }
    return m;
  }, [candidates]);

  const cell = (id: string) => fmtCell(curCands.find((c) => c.detector_id === id));

  const chartMarkers = useMemo<ChartMarker[]>(() => {
    if (!detail || !unlocked || !showMarkers) return [];
    return candidates.flatMap((c): ChartMarker[] => {
      const bar = detail.bars[c.bar_index];
      if (!bar) return [];
      if (c.detector_id === "inside_bar" && c.result === true)
        return [{ time: bar.ts_open_utc, kind: "inside" as const }];
      if (c.detector_id === "outside_bar" && c.result === true)
        return [{ time: bar.ts_open_utc, kind: "outside" as const }];
      if (c.detector_id === "bar_pattern" && ["ii", "iii", "ioi"].includes(String(c.result)))
        return [{ time: bar.ts_open_utc, kind: String(c.result) as "ii" | "iii" | "ioi" }];
      if (c.detector_id === "swing" && ["swing_high", "swing_low"].includes(String(c.result))) {
        const j = (c.evidence as { swing_bar_index?: number }).swing_bar_index;
        const sb = detail.bars[j ?? c.bar_index] ?? bar;
        return [{ time: sb.ts_open_utc, kind: String(c.result) as "swing_high" | "swing_low" }];
      }
      if (c.detector_id === "hl_counting") {
        return [{ time: bar.ts_open_utc, kind: "hl" as const }];
      }
      return [];
    });
  }, [detail, candidates, unlocked, showMarkers]);

  if (!detail) {
    return (
      <div className="setup-container">
        <div className="setup-header">
          <h2>🎯 逐根回放训练 · 会话设置</h2>
          <p className="sub">服务端权威游标 · 严格无前视偏差 · 支持历史盲测考试</p>
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
            <label>开盘预热 K 线数</label>
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
              ⚡ J · 提交判断 (Predict First)
            </button>
            <button className="ghost" onClick={() => setNoteOpen(true)}>
              📝 M · 笔记标注
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
            <span>进度：第 <b>{detail.info.bar_index + 1}</b> / 78 根</span>
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

        <div className="sidebar-card">
          <h4>
            <span>系统候选识别器 (MVP-B/C)</span>
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
                </tbody>
              </table>
              <div className="hint" style={{ marginTop: 8, fontSize: 11 }}>
                当日统计：内包 {patternCount.inside ?? 0} · 外包 {patternCount.outside ?? 0}
                {patternCount.ii ? ` · ii ${patternCount.ii}` : ""}
                {patternCount.iii ? ` · iii ${patternCount.iii}` : ""}
                {patternCount.ioi ? ` · ioi ${patternCount.ioi}` : ""}
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
                  {j.payload.considering_trade && (
                    <div className="hint" style={{ fontFamily: "var(--font-mono)" }}>
                      E: {j.payload.entry} | S: {j.payload.stop} | T: {j.payload.target}
                    </div>
                  )}
                  {j.payload.reasons.length > 0 && (
                    <div className="jitem-reasons">理由：{j.payload.reasons.join("；")}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {judgmentOpen && (
        <JudgmentForm
          barIndex={detail.info.bar_index}
          price={lastBar?.close ?? 0}
          onSubmit={onSubmitJudgment}
          onCancel={() => setJudgmentOpen(false)}
        />
      )}

      {noteOpen && (
        <div className="modal-mask" onClick={() => setNoteOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 440 }}>
            <h3>📝 添加 K 线笔记 (第 {detail.info.bar_index + 1} 根)</h3>
            <textarea
              rows={4}
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
