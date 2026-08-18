/**
 * Analytics 学习分析与错题复盘工作台。
 * 提供：
 * 1. 核心训练行为指标大屏（训练会话/已审核正反例/错题数/收藏数）；
 * 2. 宏观市场环境判断与胜率置信分布；
 * 3. 错题本（Mistake Notebook）复盘列表；
 * 4. 盲测复评（Blind Recheck）去标签测试卡片（一致性对比）。
 */

import { useEffect, useState } from "react";
import {
  AnalyticsOverview,
  BlindRecheckItem,
  RecheckCompareResult,
  getAnalyticsOverview,
  getRecheckQueue,
  submitRecheck,
} from "../api/client";

const REASONS_ZH: Record<string, string> = {
  context_mismatch: "市场背景不符",
  mechanical_flaw: "机械定义缺陷",
  data_quality: "数据异常/脏数据",
  ambiguous_pattern: "形态过于模糊",
  conflicts_with_book: "与原书定义冲突",
  other: "其他原因",
};

export default function AnalyticsWorkbench() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [recheckQueue, setRecheckQueue] = useState<BlindRecheckItem[]>([]);
  const [currentRecheckIndex, setCurrentRecheckIndex] = useState(0);
  const [recheckNotes, setRecheckNotes] = useState("");
  const [lastCompare, setLastCompare] = useState<RecheckCompareResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [ov, q] = await Promise.all([getAnalyticsOverview(), getRecheckQueue(15)]);
      setData(ov);
      setRecheckQueue(q);
      setCurrentRecheckIndex(0);
      setLastCompare(null);
    } catch (e) {
      setMsg(`加载统计数据失败: ${e}`);
    }
  };

  const handleRecheckSubmit = async (status: string) => {
    const cur = recheckQueue[currentRecheckIndex];
    if (!cur) return;
    setBusy(true);
    try {
      const res = await submitRecheck(cur.candidate_id, status, recheckNotes);
      setLastCompare(res);
      setRecheckNotes("");
      // 延时进入下一题
      setTimeout(() => {
        if (currentRecheckIndex < recheckQueue.length - 1) {
          setCurrentRecheckIndex((i) => i + 1);
          setLastCompare(null);
        }
      }, 3500);
    } catch (e) {
      setMsg(`提交复评失败: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  if (!data) {
    return <div className="panel empty">正在加载学习分析大屏...</div>;
  }

  const b = data.behavior;
  const curRecheck = recheckQueue[currentRecheckIndex];

  return (
    <div className="analytics-wb">
      {/* 顶部指标统计 KPI 卡片 */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">已完成训练会话</span>
          <span className="kpi-value">{b.completed_sessions} <small>/ {b.total_sessions}</small></span>
          <span className="hint">已提交判断: {b.total_judgments} 次</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">人工复核候选总数</span>
          <span className="kpi-value">{b.total_reviewed_candidates}</span>
          <span className="hint">
            正例 <b style={{ color: "var(--bull)" }}>{b.total_confirmed_positives}</b> · 反例 <b style={{ color: "var(--bear)" }}>{b.total_rejected_negatives}</b>
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">★ 典型案例收藏</span>
          <span className="kpi-value" style={{ color: "var(--accent-gold)" }}>{b.total_favorites}</span>
          <span className="hint">标杆价格行为案例库</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">📕 错题本待复盘</span>
          <span className="kpi-value" style={{ color: "var(--bear)" }}>{b.total_mistakes}</span>
          <span className="hint">误判与背景不符归档</span>
        </div>
      </div>

      <div className="analytics-grid">
        {/* 左侧：认知判断分布与拒绝原因分析 */}
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <h3>🧠 个人读图与认知习惯画像</h3>

          <div>
            <div className="hint" style={{ marginBottom: 6 }}>宏观市场环境判断倾向 (Context Labels):</div>
            <table className="kv">
              <tbody>
                <tr><td>多头趋势 (Trend Up)</td><td>{data.judgment.context_breakdown.trend_up ?? 0} 次</td></tr>
                <tr><td>空头趋势 (Trend Down)</td><td>{data.judgment.context_breakdown.trend_down ?? 0} 次</td></tr>
                <tr><td>交易区间 (Trading Range)</td><td>{data.judgment.context_breakdown.trading_range ?? 0} 次</td></tr>
                <tr><td>过渡/模糊地带 (Transition)</td><td>{data.judgment.context_breakdown.transition ?? 0} 次</td></tr>
              </tbody>
            </table>
          </div>

          <div>
            <div className="hint" style={{ marginBottom: 6 }}>反例拒绝原因归纳 (Rejection Drivers):</div>
            {Object.keys(data.rejections.reason_counts).length === 0 ? (
              <p className="hint">暂无拒绝记录。在扫描器中审核反例时可归纳具体原因。</p>
            ) : (
              <table className="kv">
                <tbody>
                  {Object.entries(data.rejections.reason_counts).map(([k, v]) => (
                    <tr key={k}>
                      <td>{REASONS_ZH[k] ?? k}</td>
                      <td><b>{v} 次</b></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* 右侧：盲测复评 (Blind Recheck) 卡片 */}
        <div className="panel recheck-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>🎲 盲测复评与一致性自测 (Blind Recheck)</h3>
            <span className="hint">脱敏历史标签 · 检验认知稳定性</span>
          </div>

          {!curRecheck ? (
            <div className="empty">
              <p>当前无待复评样本（需在扫描器中先审核确认至少 1 条正例或反例候选）。</p>
            </div>
          ) : (
            <div className="recheck-body">
              <div className="recheck-meta">
                <span>样本 #{currentRecheckIndex + 1} / {recheckQueue.length}</span>
                <span><b>{curRecheck.day}</b> (第 {curRecheck.bar_index + 1} 根)</span>
                <span className="pill primary">{curRecheck.detector_id}</span>
              </div>

              <div className="evidence-box">
                <div className="hint">客观判定依据 (Evidence 脱敏)：</div>
                <pre>{JSON.stringify(curRecheck.evidence, null, 2)}</pre>
              </div>

              <div className="form-group" style={{ marginTop: 8 }}>
                <label>重新给出你的独立判断（不显示历史结论）：</label>
                <div className="btn-group">
                  <button className="primary" onClick={() => handleRecheckSubmit("confirmed")} disabled={busy}>
                    ✓ 确认为正例
                  </button>
                  <button className="ghost" onClick={() => handleRecheckSubmit("rejected")} disabled={busy}>
                    ✗ 判定为反例
                  </button>
                  <button className="ghost" onClick={() => handleRecheckSubmit("uncertain")} disabled={busy}>
                    ? 不确定
                  </button>
                </div>
              </div>

              {lastCompare && (
                <div className={`recheck-result-box ${lastCompare.is_consistent ? "ok" : "mismatch"}`}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>
                    {lastCompare.is_consistent ? "🎉 认知高度一致！(Consistent)" : "⚠️ 出现认知漂移 (Shift / Conflict)"}
                  </div>
                  <div className="hint" style={{ marginTop: 4 }}>
                    历史结论：<b>{lastCompare.original_status}</b> · 本次复评：<b>{lastCompare.recheck_status}</b>
                  </div>
                  {lastCompare.original_notes && (
                    <div className="hint" style={{ marginTop: 2 }}>当时笔记：{lastCompare.original_notes}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 底部：错题本列表 */}
      <section className="panel">
        <h3>📕 错题本精选归档 (Recent Mistakes)</h3>
        {data.recent_mistakes.length === 0 ? (
          <p className="hint" style={{ padding: "12px 0" }}>暂无错题记录。在扫描器中标记反例或勾选错题本可在此集中归档。</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>交易日 / 序号</th>
                <th>形态类型</th>
                <th>拒绝主因</th>
                <th>复盘笔记</th>
                <th>归档时间</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_mistakes.map((m) => (
                <tr key={m.id}>
                  <td><b>{m.day}</b> <span className="hint">#{m.bar_index + 1}</span></td>
                  <td><span className="pill bad">{m.detector_id}</span></td>
                  <td><b>{REASONS_ZH[m.rejection_reason ?? ""] ?? m.rejection_reason ?? "—"}</b></td>
                  <td>{m.notes ?? "—"}</td>
                  <td className="hint">{m.reviewed_at ? new Date(m.reviewed_at).toLocaleDateString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {msg && <div className="msg">{msg}</div>}
    </div>
  );
}
