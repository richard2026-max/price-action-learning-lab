/**
 * MVP-D Scanner 扫描工作台。
 * 功能：创建扫描任务、任务进度监控、候选多维筛选、一键进入无未来回放复核、4 档人工审核、典型案例收藏、错题本归档。
 */

import { useCallback, useEffect, useState } from "react";
import {
  CandidateRecord,
  Provider,
  RegisteredDetector,
  ReviewCandidatePayload,
  ScanTask,
  createScanTask,
  listCandidates,
  listDays,
  listDetectors,
  listScanTasks,
  reviewCandidate,
} from "../api/client";

interface Props {
  onOpenReplay?: (day: string, provider: Provider, warmupBars: number) => void;
}

const REVIEW_ZH: Record<string, { text: string; cls: string }> = {
  unreviewed: { text: "待审核", cls: "pill ghost" },
  confirmed: { text: "符合 (正例)", cls: "pill ok" },
  rejected: { text: "不符合 (反例)", cls: "pill bad" },
  uncertain: { text: "不确定", cls: "pill" },
  needs_review: { text: "需深入研究", cls: "pill primary" },
};

const REASONS_ZH: Record<string, string> = {
  context_mismatch: "市场背景不符",
  mechanical_flaw: "机械定义缺陷",
  data_quality: "数据异常/脏数据",
  ambiguous_pattern: "形态过于模糊",
  conflicts_with_book: "与原书定义冲突",
  other: "其他原因",
};

export default function ScannerWorkbench({ onOpenReplay }: Props) {
  const [provider, setProvider] = useState<Provider>("hfdl");
  const [days, setDays] = useState<string[]>([]);
  const [startDay, setStartDay] = useState("");
  const [endDay, setEndDay] = useState("");
  const [detectors, setDetectors] = useState<RegisteredDetector[]>([]);
  const [selectedDetectors, setSelectedDetectors] = useState<string[]>([]);
  const [tasks, setTasks] = useState<ScanTask[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string>("");
  const [filterDetector, setFilterDetector] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [onlyFavorites, setOnlyFavorites] = useState(false);
  const [onlyMistakes, setOnlyMistakes] = useState(false);
  const [candidates, setCandidates] = useState<CandidateRecord[]>([]);
  const [selectedCand, setSelectedCand] = useState<CandidateRecord | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [msg, setMsg] = useState("");

  // 加载可用日期与已注册 detector
  useEffect(() => {
    listDays(provider).then((ds) => {
      setDays(ds);
      if (ds.length > 0) {
        setStartDay(ds[0]);
        setEndDay(ds[Math.min(ds.length - 1, 30)]); // 默认 30 天区间
      }
    });
    listDetectors().then((d) => setDetectors(d.detectors)).catch(() => {});
    loadTasks();
  }, [provider]);

  const loadTasks = async () => {
    try {
      const ts = await listScanTasks();
      setTasks(ts);
      if (ts.length > 0 && !currentTaskId) {
        setCurrentTaskId(ts[0].id);
      }
    } catch {
      /* ignore */
    }
  };

  const loadCandidates = useCallback(async () => {
    try {
      const cands = await listCandidates({
        task_id: currentTaskId || undefined,
        detector_id: filterDetector || undefined,
        review_status: filterStatus || undefined,
        only_favorites: onlyFavorites,
        only_mistakes: onlyMistakes,
        limit: 300,
      });
      setCandidates(cands);
    } catch (e) {
      setMsg(`加载候选失败: ${e}`);
    }
  }, [currentTaskId, filterDetector, filterStatus, onlyFavorites, onlyMistakes]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  const handleStartScan = async () => {
    if (!startDay || !endDay) return;
    setIsScanning(true);
    setMsg("正在执行批量扫描...");
    try {
      const task = await createScanTask({
        provider,
        start_day: startDay,
        end_day: endDay,
        detector_ids: selectedDetectors,
      });
      setMsg(`扫描完成：共扫描 ${task.scanned_days} 天，发现 ${task.candidate_count} 个候选`);
      await loadTasks();
      setCurrentTaskId(task.id);
    } catch (e) {
      setMsg(`扫描失败: ${e}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleReview = async (candId: string, payload: ReviewCandidatePayload) => {
    try {
      const updated = await reviewCandidate(candId, payload);
      setCandidates((prev) => prev.map((c) => (c.id === candId ? updated : c)));
      if (selectedCand?.id === candId) setSelectedCand(updated);
      setMsg("审核已保存 ✓");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg(`审核失败: ${e}`);
    }
  };

  return (
    <div className="scanner-wb">
      <section className="scan-config panel">
        <h3>创建历史候选扫描任务</h3>
        <div className="row">
          <label>
            数据源：
            <select value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
              <option value="hfdl">真实 SPY (HF Data Library)</option>
              <option value="synthetic">合成演示数据</option>
            </select>
          </label>
          <label>
            开始日期：
            <select value={startDay} onChange={(e) => setStartDay(e.target.value)}>
              {days.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
          <label>
            结束日期：
            <select value={endDay} onChange={(e) => setEndDay(e.target.value)}>
              {days.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
          <button onClick={handleStartScan} disabled={isScanning || !startDay}>
            {isScanning ? "扫描中..." : "🚀 启动批量扫描"}
          </button>
        </div>
        <div className="det-select">
          <span className="hint">指定 Detector（留空扫描全部 11 类）：</span>
          <div className="row chips">
            {detectors.map((d) => {
              const on = selectedDetectors.includes(d.detector_id);
              return (
                <span
                  key={d.detector_id}
                  className={`chip ${on ? "on" : ""}`}
                  onClick={() => {
                    setSelectedDetectors((prev) =>
                      on ? prev.filter((id) => id !== d.detector_id) : [...prev, d.detector_id]
                    );
                  }}
                >
                  {d.label} ({d.detector_id})
                </span>
              );
            })}
          </div>
        </div>
      </section>

      <div className="scan-body">
        <aside className="scan-sidebar panel">
          <h4>扫描任务历史</h4>
          <div className="task-list">
            {tasks.map((t) => (
              <div
                key={t.id}
                className={`task-card ${t.id === currentTaskId ? "active" : ""}`}
                onClick={() => setCurrentTaskId(t.id)}
              >
                <div className="task-header">
                  <b>{t.provider} · {t.start_day} ~ {t.end_day}</b>
                  <span className={`pill ${t.status === "completed" ? "ok" : "bad"}`}>{t.status}</span>
                </div>
                <div className="task-meta hint">
                  <span>{t.scanned_days} 天 / {t.candidate_count} 候选</span>
                  <span>{new Date(t.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <main className="scan-main panel">
          <div className="filter-bar">
            <select value={filterDetector} onChange={(e) => setFilterDetector(e.target.value)}>
              <option value="">全部 Detector</option>
              {detectors.map((d) => (
                <option key={d.detector_id} value={d.detector_id}>{d.label}</option>
              ))}
            </select>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">全部审核状态</option>
              <option value="unreviewed">待审核</option>
              <option value="confirmed">已确认 (正例)</option>
              <option value="rejected">已拒绝 (反例)</option>
              <option value="uncertain">不确定</option>
              <option value="needs_review">需深入研究</option>
            </select>
            <label className="checkbox-label">
              <input type="checkbox" checked={onlyFavorites} onChange={(e) => setOnlyFavorites(e.target.checked)} />
              ★ 仅收藏
            </label>
            <label className="checkbox-label">
              <input type="checkbox" checked={onlyMistakes} onChange={(e) => setOnlyMistakes(e.target.checked)} />
              📕 错题本
            </label>
            <span className="hint">匹配候选: {candidates.length} 条</span>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>日期 / 序号</th>
                  <th>形态 / 识别器</th>
                  <th>输出结果</th>
                  <th>审核状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {candidates.length === 0 ? (
                  <tr><td colSpan={5} className="empty">暂无匹配的候选记录。</td></tr>
                ) : (
                  candidates.map((c) => {
                    const st = REVIEW_ZH[c.review_status] ?? { text: c.review_status, cls: "pill" };
                    return (
                      <tr
                        key={c.id}
                        className={selectedCand?.id === c.id ? "selected-row" : ""}
                        onClick={() => setSelectedCand(c)}
                      >
                        <td>
                          <b>{c.day}</b> <span className="hint">#{c.bar_index + 1}</span>
                        </td>
                        <td>
                          <b>{c.detector_id}</b>
                          <div className="hint">{c.provenance}</div>
                        </td>
                        <td>
                          <code>{typeof c.result === "object" ? JSON.stringify(c.result) : String(c.result)}</code>
                        </td>
                        <td>
                          <span className={st.cls}>{st.text}</span>
                          {c.is_favorite && " ★"}
                          {c.is_mistake_notebook && " 📕"}
                        </td>
                        <td>
                          <button
                            className="small ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onOpenReplay) onOpenReplay(c.day, c.provider as Provider, Math.max(0, c.bar_index));
                            }}
                          >
                            打开回放 ↗
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {selectedCand && (
            <div className="review-drawer">
              <div className="drawer-header">
                <h4>候选证据与人工审核 · {selectedCand.detector_id} (第 {selectedCand.bar_index + 1} 根)</h4>
                <button className="small ghost" onClick={() => setSelectedCand(null)}>✕ 关闭</button>
              </div>
              <div className="drawer-content">
                <div className="evidence-box">
                  <div className="hint">判定依据 (Evidence):</div>
                  <pre>{JSON.stringify(selectedCand.evidence, null, 2)}</pre>
                </div>

                <div className="review-actions">
                  <div className="btn-group">
                    <button
                      className={selectedCand.review_status === "confirmed" ? "on ok" : "ghost"}
                      onClick={() => handleReview(selectedCand.id, { review_status: "confirmed" })}
                    >
                      ✓ 确认符合 (正例)
                    </button>
                    <button
                      className={selectedCand.review_status === "rejected" ? "on bad" : "ghost"}
                      onClick={() => handleReview(selectedCand.id, { review_status: "rejected", rejection_reason: "context_mismatch" })}
                    >
                      ✗ 拒绝 (反例)
                    </button>
                    <button
                      className={selectedCand.review_status === "uncertain" ? "on" : "ghost"}
                      onClick={() => handleReview(selectedCand.id, { review_status: "uncertain" })}
                    >
                      ? 不确定
                    </button>
                    <button
                      className={selectedCand.review_status === "needs_review" ? "on primary" : "ghost"}
                      onClick={() => handleReview(selectedCand.id, { review_status: "needs_review" })}
                    >
                      🔍 需深入研究
                    </button>
                  </div>

                  {selectedCand.review_status === "rejected" && (
                    <div className="rejection-box">
                      <label>
                        拒绝原因：
                        <select
                          value={selectedCand.rejection_reason ?? "context_mismatch"}
                          onChange={(e) =>
                            handleReview(selectedCand.id, {
                              review_status: "rejected",
                              rejection_reason: e.target.value as any,
                            })
                          }
                        >
                          {Object.entries(REASONS_ZH).map(([k, v]) => (
                            <option key={k} value={k}>{v}</option>
                          ))}
                        </select>
                      </label>
                    </div>
                  )}

                  <div className="tag-actions">
                    <button
                      className={`small ${selectedCand.is_favorite ? "on" : "ghost"}`}
                      onClick={() =>
                        handleReview(selectedCand.id, {
                          review_status: selectedCand.review_status as any,
                          is_favorite: !selectedCand.is_favorite,
                        })
                      }
                    >
                      {selectedCand.is_favorite ? "★ 已收藏" : "☆ 收藏为典型案例"}
                    </button>
                    <button
                      className={`small ${selectedCand.is_mistake_notebook ? "on" : "ghost"}`}
                      onClick={() =>
                        handleReview(selectedCand.id, {
                          review_status: selectedCand.review_status as any,
                          is_mistake_notebook: !selectedCand.is_mistake_notebook,
                        })
                      }
                    >
                      {selectedCand.is_mistake_notebook ? "📕 已在错题本" : "📘 收入错题本"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {msg && <p className="msg">{msg}</p>}
    </div>
  );
}
