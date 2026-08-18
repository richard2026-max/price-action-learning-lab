/**
 * Predict First 判断表单（专业金融终端风格弹窗）。
 */

import { useState } from "react";
import type { JudgmentPayload } from "../api/client";

interface Props {
  barIndex: number;
  price: number;
  onSubmit: (p: JudgmentPayload) => Promise<void>;
  onCancel: () => void;
}

const CONTEXT_LABELS = [
  ["trend_up", "多头强趋势 (Trend Up)"],
  ["trend_down", "空头强趋势 (Trend Down)"],
  ["trading_range", "震荡交易区间 (Trading Range)"],
  ["transition", "过渡 / 模糊地带 (Transition)"],
] as const;

const TERNARY = [
  ["unknown", "不确定"],
  ["yes", "是 (确认回调)"],
  ["no", "否 (趋势延伸/横盘)"],
] as const;

const DIRECTIONS = [
  ["none", "保持观望 (No Trade)"],
  ["long", "做多 (Buy / Long)"],
  ["short", "做空 (Sell / Short)"],
] as const;

const GRADES = [
  ["good", "★ Good (概率优势大)"],
  ["okay", "● Okay (可接受胜率)"],
  ["bad", "▼ Bad (边缘/弱胜率)"],
] as const;

export default function JudgmentForm({ barIndex, price, onSubmit, onCancel }: Props) {
  const [contextLabel, setContextLabel] = useState("transition");
  const [structureNote, setStructureNote] = useState("");
  const [pullback, setPullback] = useState("unknown");
  const [barCountingNote, setBarCountingNote] = useState("");
  const [direction, setDirection] = useState("none");
  const [reason1, setReason1] = useState("");
  const [reason2, setReason2] = useState("");
  const [entry, setEntry] = useState("");
  const [stop, setStop] = useState("");
  const [target, setTarget] = useState("");
  const [probability, setProbability] = useState("okay");
  const [confidence, setConfidence] = useState("okay");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const considering = direction !== "none";

  const validate = (): string => {
    if (considering) {
      if (!reason1.trim() || !reason2.trim()) return "必须提供至少两个独立的入场理由（Two Reasons Rule）";
      const e = Number(entry), s = Number(stop), t = Number(target);
      if (!entry || !stop || !target) return "考虑入场交易时，必须明确设定 Entry / Stop / Target";
      if (direction === "long" && !(s < e && e < t)) return "做多交易要求：止损 < 入场 < 目标";
      if (direction === "short" && !(t < e && e < s)) return "做空交易要求：目标 < 入场 < 止损";
    }
    return "";
  };

  const submit = async () => {
    const v = validate();
    if (v) {
      setErr(v);
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await onSubmit({
        context_label: contextLabel,
        structure_note: structureNote,
        pullback_present: pullback,
        bar_counting_note: barCountingNote,
        considering_trade: considering,
        direction,
        reasons: considering ? [reason1.trim(), reason2.trim()] : [],
        entry: considering ? Number(entry) : null,
        stop: considering ? Number(stop) : null,
        target: considering ? Number(target) : null,
        probability_estimate: probability,
        confidence,
      });
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-mask">
      <div className="modal judgment">
        <div className="modal-header">
          <h3>
            <span>⚡ Predict First · 盘中实时判断 (第 {barIndex + 1} 根)</span>
            <span className="pill primary">提交后永久锁定</span>
          </h3>
          <span className="hint">当前基准价：{price.toFixed(2)}</span>
        </div>

        <div className="form-group">
          <label>1. 当前市场处于什么宏观环境？(Market Regime)</label>
          <div className="radio-group">
            {CONTEXT_LABELS.map(([v, t]) => (
              <span
                key={v}
                className={`chip ${contextLabel === v ? "on" : ""}`}
                onClick={() => setContextLabel(v)}
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>2. 几何结构与腿位置 (Swing / Leg / Channel / S&R)</label>
          <textarea
            rows={2}
            value={structureNote}
            onChange={(e) => setStructureNote(e.target.value)}
            placeholder="描述当前价格所处的形态，例如：开盘大阳线突破后第 2 腿回调，测试 EMA20 支撑线..."
          />
        </div>

        <div className="setup-grid">
          <div className="form-group">
            <label>3. 是否存在 Pullback 回调？</label>
            <div className="radio-group">
              {TERNARY.map(([v, t]) => (
                <span
                  key={v}
                  className={`chip ${pullback === v ? "on" : ""}`}
                  onClick={() => setPullback(v)}
                >
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>4. Bar Counting (H1/H2, L1/L2 等计数)</label>
            <input
              value={barCountingNote}
              onChange={(e) => setBarCountingNote(e.target.value)}
              placeholder="例如：H2 确认 / 2nd Entry Long"
            />
          </div>
        </div>

        <div className="form-group">
          <label>5. 交易意图与方向选择 (Trade Decision)</label>
          <div className="radio-group">
            {DIRECTIONS.map(([v, t]) => {
              const cls = direction === v ? (v === "long" ? "on bull" : v === "short" ? "on bear" : "on") : "";
              return (
                <span key={v} className={`chip ${cls}`} onClick={() => setDirection(v)}>
                  {t}
                </span>
              );
            })}
          </div>
        </div>

        {considering && (
          <div className="trade-plan-box">
            <div className="form-group">
              <label>6. 入场理由（至少提供 2 个独立的客观价格行为依据）</label>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <input
                  value={reason1}
                  onChange={(e) => setReason1(e.target.value)}
                  placeholder="依据 1：例如，顺大趋势回调至 20 EMA，收出强多头信号棒"
                />
                <input
                  value={reason2}
                  onChange={(e) => setReason2(e.target.value)}
                  placeholder="依据 2：例如，形成二次入场 (H2 / Second Entry)，前期阻力转化为支撑"
                />
              </div>
            </div>

            <div className="setup-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", marginBottom: 0 }}>
              <div className="form-group">
                <label>计划入场价 (Entry)</label>
                <input
                  type="number"
                  step="0.01"
                  value={entry}
                  onChange={(e) => setEntry(e.target.value)}
                  placeholder={String(price)}
                />
              </div>
              <div className="form-group">
                <label>保护性止损 (Stop / 失效点)</label>
                <input
                  type="number"
                  step="0.01"
                  value={stop}
                  onChange={(e) => setStop(e.target.value)}
                  placeholder="判断证伪点"
                />
              </div>
              <div className="form-group">
                <label>目标止盈价 (Target)</label>
                <input
                  type="number"
                  step="0.01"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  placeholder="磁吸/阻力位"
                />
              </div>
            </div>

            <div className="invalidation-tip">
              📌 <b>Brooks 心法</b>：止损点必须是逻辑上证明“你的假设已经被证伪”的位置，而非凭空假想的市场最差价。
            </div>
          </div>
        )}

        <div className="setup-grid" style={{ marginBottom: 0 }}>
          <div className="form-group">
            <label>7. 主观胜率评估 (Probability Grade)</label>
            <div className="radio-group">
              {GRADES.map(([v, t]) => (
                <span
                  key={v}
                  className={`chip ${probability === v ? "on" : ""}`}
                  onClick={() => setProbability(v)}
                >
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>8. 自身决策置信度 (Confidence)</label>
            <div className="radio-group">
              {GRADES.map(([v, t]) => (
                <span
                  key={v}
                  className={`chip ${confidence === v ? "on" : ""}`}
                  onClick={() => setConfidence(v)}
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>

        {err && <p className="err">{err}</p>}

        <div className="actions">
          <button className="ghost" onClick={onCancel} disabled={busy}>
            取消
          </button>
          <button className="gold" onClick={submit} disabled={busy}>
            {busy ? "正在锁定..." : "🔒 提交判断并解锁后续"}
          </button>
        </div>
      </div>
    </div>
  );
}
