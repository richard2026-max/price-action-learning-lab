import { useCallback, useEffect, useState } from "react";
import ReplayWorkbench from "./replay/ReplayWorkbench";
import ScannerWorkbench from "./scanner/ScannerWorkbench";
import { Dataset, Provider, getDatasets, getHealth, listDays, seedDemo } from "./api/client";

const DEMO_START = "2024-01-02";
const DEMO_END = "2024-03-28";

type Tab = "replay" | "scanner" | "data";

export default function App() {
  const [tab, setTab] = useState<Tab>("replay");
  const [health, setHealth] = useState<string>("…");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [days, setDays] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [h, ds] = await Promise.all([getHealth(), getDatasets()]);
      setHealth(h.status);
      setDatasets(ds);
      setDays(await listDays());
    } catch (e) {
      setHealth("error");
      setMsg(String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onSeed = async () => {
    setBusy(true);
    setMsg("生成合成数据中…");
    try {
      const out = await seedDemo(DEMO_START, DEMO_END);
      setMsg(`完成：${out.days} 个交易日，5m ${out.bars_5m} 根`);
      await refresh();
    } catch (e) {
      setMsg(`失败：${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleOpenReplayFromScanner = (targetDay: string, _targetProvider: Provider, _targetWarmup: number) => {
    setTab("replay");
    setMsg(`已切换至回放：${targetDay}`);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">PA</div>
          <div className="brand-title">
            <h1>Price Action Learning Lab</h1>
            <p>Al Brooks 价格行为学习与训练系统 · SPY 5m 单图 · 结构化刻意训练</p>
          </div>
        </div>

        <div className="header-meta">
          <span className={`pill ${health === "ok" ? "ok" : "bad"}`}>
            API {health === "ok" ? "CONNECTED" : "OFFLINE"}
          </span>
        </div>
      </header>

      <nav className="app-tabs">
        <button className={tab === "replay" ? "on" : ""} onClick={() => setTab("replay")}>
          🎯 逐根回放训练 (Replay)
        </button>
        <button className={tab === "scanner" ? "on" : ""} onClick={() => setTab("scanner")}>
          🔍 价格行为扫描器 (Scanner)
        </button>
        <button className={tab === "data" ? "on" : ""} onClick={() => setTab("data")}>
          💾 数据与环境管理 (Data)
        </button>
      </nav>

      {tab === "replay" && <ReplayWorkbench />}

      {tab === "scanner" && <ScannerWorkbench onOpenReplay={handleOpenReplayFromScanner} />}

      {tab === "data" && (
        <section className="panel">
          <h3>数据集与存储元数据</h3>
          {datasets.length === 0 ? (
            <div className="empty">
              <p>暂无数据。生成合成演示数据（零密钥、确定性可复现）。</p>
              <button className="primary" onClick={onSeed} disabled={busy}>
                {busy ? "生成中…" : `生成 ${DEMO_START} ~ ${DEMO_END} 合成数据`}
              </button>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Instrument</th>
                  <th>Timeframe</th>
                  <th>Date Range</th>
                  <th>Total Bars</th>
                  <th>Missing Bars</th>
                  <th>Duplicates</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={`${d.provider}-${d.instrument_id}-${d.timeframe}`}>
                    <td><b>{d.provider}</b></td>
                    <td>{d.instrument_id}</td>
                    <td><span className="pill">{d.timeframe}</span></td>
                    <td>{d.start?.slice(0, 10)} ~ {d.end?.slice(0, 10)}</td>
                    <td><b>{d.row_count.toLocaleString()}</b></td>
                    <td>{d.missing_bar_count}</td>
                    <td>{d.duplicate_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {days.length > 0 && (
            <p className="hint" style={{ marginTop: 12 }}>
              当前可用交易日：{days.length} 天（{days[0]} ~ {days[days.length - 1]}）
            </p>
          )}
        </section>
      )}

      {msg && <div className="msg">{msg}</div>}
    </div>
  );
}
