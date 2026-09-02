/**
 * Lightweight Charts 封装（v4.2）。
 *
 * 防前视说明：本组件只渲染服务端返回的 bars（已裁剪到 cursor）；
 * 大周期（15m/60m/日线）由前端对已加载的 5m bars 就地聚合——聚合输入
 * 同样只有 cursor 内数据，不引入任何未来信息（见 chart/aggregate.ts）。
 * 20EMA 与关键价位来自服务端（EMA 以前日已收盘数据预热）；
 * 大周期视图下的 EMA20 为客户端对聚合收盘价的等价重算。
 *
 * 时间轴：十字线时间标签按用户要求统一显示北京时间（周几 + 日期 + 时间）。
 * 图例（OKX 风格）：悬停显示对应 K 线 开/高/低/收/涨跌幅 与 EMA 值，
 * 未悬停时显示最新一根——用于直接读出止损/止盈参考价位。
 *
 * 画线工具：水平线/趋势线/射线/矩形/斐波那契回撤（含 1.618~4.236 扩展位）、
 * 点选删除与清空；锚点以「5m 逻辑索引 + 价格」存储（与周期无关），
 * 切换周期时按聚合几何插值换算像素坐标，画线始终粘在原来的 K 线上；
 * 画线按会话持久化到 localStorage（pall.drawings.<session_id>）。
 * 已完成的画线支持编辑：悬停高亮后整体拖动移动，拖端点圆圈微调（水平线可上下拖）；
 * 画布仅在悬停画线或绘制工具激活时接管指针，其余情况透传给图表平移/缩放。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  Coordinate,
  IChartApi,
  ISeriesApi,
  Logical,
  SeriesMarker,
  Time,
  UTCTimestamp,
  createChart,
} from "lightweight-charts";
import type { Bar, KeyLevels } from "../api/client";
import { TIMEFRAMES, aggregateBars, type Timeframe } from "./aggregate";

export interface ChartMarker {
  time: string; // bar ts_open_utc
  kind:
    | "inside"
    | "outside"
    | "ii"
    | "iii"
    | "ioi"
    | "swing_high"
    | "swing_low"
    | "h1"
    | "h2"
    | "h3"
    | "h4"
    | "l1"
    | "l2"
    | "l3"
    | "l4"
    | "hl"
    | "wedge"
    | "climax"
    | "micro_channel"
    | "bull_trend"
    | "bear_trend"
    | "bull_signal"
    | "bear_signal";
  text?: string;
}

export type LevelKey =
  | "prev_day_open"
  | "prev_day_high"
  | "prev_day_low"
  | "prev_day_close"
  | "today_open"
  | "premarket_high"
  | "premarket_low";

/** 图表层开关（用户可自主勾选显示/隐藏；由父组件持久化到 localStorage）。 */
export interface ChartOverlays {
  ema5: boolean; // 5m 20 bar EMA（主图基准均线）
  ema15: boolean; // 15m 20 bar EMA（Brooks 近似投影）
  ema60: boolean; // 60m 20 bar EMA（Brooks 近似投影）
  emaAxisLabels: boolean; // 均线在右侧价格轴的数值标签与名称
  keyLevels: boolean; // 关键价位线总开关
  keyLevelTitles: boolean; // 价位线端文字标题（PDH 前日高 等）
  levelItems: Partial<Record<LevelKey, boolean>>; // 每条关键价位线单独开关
  positions: boolean; // 模拟持仓线（入场/止损/目标）
  ohlcLegend: boolean; // 顶部 OHLC 实时图例
  // ---- 阶段三：价格行为形态与结构识别图层 ----
  patterns: boolean; // 基础形态（inside, outside, ii, iii, ioi）
  swings: boolean; // 波段高低点（Swing High / Swing Low）
  hlCounts: boolean; // Brooks 回调计数与二次入场（H1/H2/L1/L2）
  complexPatterns: boolean; // 复合形态（楔形 Wedge / 高潮 Climax / 微通道 Micro Channel）
  signalBars: boolean; // 强趋势 K 线与关键信号 K 线
}

export const DEFAULT_OVERLAYS: ChartOverlays = {
  ema5: true,
  ema15: true,
  ema60: true,
  emaAxisLabels: true,
  keyLevels: true,
  keyLevelTitles: true,
  levelItems: {},
  positions: true,
  ohlcLegend: true,
  patterns: true,
  swings: true,
  hlCounts: true,
  complexPatterns: true,
  signalBars: true,
};

/** 兼容旧版本 localStorage 结构：缺省字段回填默认值。 */
export function normalizeOverlays(raw: unknown): ChartOverlays {
  const o = (typeof raw === "object" && raw !== null ? raw : {}) as Partial<ChartOverlays>;
  const levelItems: Partial<Record<LevelKey, boolean>> =
    typeof o.levelItems === "object" && o.levelItems !== null ? { ...o.levelItems } : {};
  return {
    ema5: o.ema5 ?? true,
    ema15: o.ema15 ?? true,
    ema60: o.ema60 ?? true,
    emaAxisLabels: o.emaAxisLabels ?? true,
    keyLevels: o.keyLevels ?? true,
    keyLevelTitles: o.keyLevelTitles ?? true,
    levelItems,
    positions: o.positions ?? true,
    ohlcLegend: o.ohlcLegend ?? true,
    patterns: o.patterns ?? true,
    swings: o.swings ?? true,
    hlCounts: o.hlCounts ?? true,
    complexPatterns: o.complexPatterns ?? true,
    signalBars: o.signalBars ?? true,
  };
}

export const KEY_LEVEL_ITEMS: Array<{ key: LevelKey; label: string; color: string }> = [
  { key: "prev_day_open", label: "PDO 前日开", color: "#c98a4b" },
  { key: "prev_day_high", label: "PDH 前日高", color: "#c98a4b" },
  { key: "prev_day_low", label: "PDL 前日低", color: "#c98a4b" },
  { key: "prev_day_close", label: "PDC 前日收", color: "#9a86c9" },
  { key: "today_open", label: "OPEN 今日开", color: "#4da3ff" },
  { key: "premarket_high", label: "PRE-H 盘前高", color: "#5d8a5f" },
  { key: "premarket_low", label: "PRE-L 盘前低", color: "#5d8a5f" },
];

const isLevelVisible = (ov: ChartOverlays, key: LevelKey): boolean =>
  ov.keyLevels && ov.levelItems[key] !== false;

/** 模拟持仓的价格标线（入场/止损/目标）。 */
export interface TradeLine {
  price: number;
  color: string;
  title: string;
}

// ---------------------------------------------------------------------------
// 画线：类型与样式（参考 TradingView）
// ---------------------------------------------------------------------------

export type DrawTool = "none" | "hline" | "trend" | "ray" | "rect" | "fib" | "pos" | "measure" | "text" | "erase";

/** 画线锚点：5m 逻辑索引 + 价格（与显示周期无关，切周期后仍粘在原 K 线） */
interface DrawPt {
  l: number;
  p: number;
}

/** 斐波那契水平（每条画线可自定义：比例 + 启用） */
interface FibLevel {
  r: number;
  on: boolean;
}

type Drawing =
  | { id: string; type: "hline"; price: number; color?: string; locked?: boolean }
  | { id: string; type: "trend" | "ray" | "rect" | "measure"; a: DrawPt; b: DrawPt; color?: string; locked?: boolean }
  | { id: string; type: "text"; l: number; p: number; text: string; color?: string; locked?: boolean }
  | { id: string; type: "fib"; a: DrawPt; b: DrawPt; color?: string; levels?: FibLevel[]; locked?: boolean }
  | { id: string; type: "pos"; a: DrawPt; b: DrawPt; color?: string; targets?: number[]; locked?: boolean };

/** 悬停命中部位：a/b = 端点手柄，body = 线条/内部（整体拖动） */
type HoverPart = "a" | "b" | "body";

export type { DrawPt, FibLevel, Drawing };
interface HoverHit {
  id: string;
  part: HoverPart;
}

const DRAW_COLORS: Record<Drawing["type"], string> = {
  hline: "#4da3ff",
  trend: "#4da3ff",
  ray: "#4da3ff",
  rect: "#c05fd8",
  measure: "#e8a33d",
  text: "#e6edf3",
  fib: "#e8a33d",
  pos: "#26a69a",
};

const LEVEL_PALETTE = ["#ef5350", "#f0b90b", "#26a69a", "#4da3ff", "#9a86c9", "#e8a33d", "#7ee2a8", "#c05fd8"];

const DEFAULT_FIB_RATIOS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.618, 2.618, 3.618, 4.236];
const DEFAULT_FIB_LEVELS: FibLevel[] = DEFAULT_FIB_RATIOS.map((r) => ({ r, on: true }));
const DEFAULT_POS_TARGETS = [1, 2, 3];

/** 设置面板草稿（确认后才写回画线对象） */
interface SettingsDraft {
  color?: string;
  price?: number;
  levels?: FibLevel[];
  targets?: number[];
  locked?: boolean;
}

const levelsOf = (d: Drawing): FibLevel[] => (d.type === "fib" ? d.levels ?? DEFAULT_FIB_LEVELS : []);
const targetsOf = (d: Drawing): number[] => (d.type === "pos" ? d.targets ?? DEFAULT_POS_TARGETS : []);
const colorOf = (d: Drawing): string => d.color ?? DRAW_COLORS[d.type];

/** 离屏 2D 上下文：命中测试里量文字宽度（与渲染同字体） */
const measureCtx = document.createElement("canvas").getContext("2d");

/** 斐波那契回撤位（含 TradingView 常用扩展位，用于止盈/盈亏比推演） */
const DRAW_TOOLS: Array<{ key: DrawTool; icon: string; name: string; title: string }> = [
  { key: "hline", icon: "─", name: "水平线", title: "水平线（点击放置；悬停可上下拖动，双击可精确输入价位/改颜色）· 快捷键 1" },
  { key: "trend", icon: "╱", name: "趋势线", title: "趋势线（两点线段；悬停可整体拖动，拖端点圆圈微调，双击改颜色）· 快捷键 2" },
  { key: "ray", icon: "→", name: "射线", title: "射线（起点向右无限延伸；悬停可整体拖动，拖端点圆圈微调，双击改颜色）· 快捷键 3" },
  { key: "rect", icon: "□", name: "矩形", title: "矩形（框选震荡区间；悬停可整体拖动，拖角上圆圈改大小，双击改颜色）· 快捷键 4" },
  { key: "fib", icon: "ƒ", name: "斐波那契", title: "斐波那契回撤（0~1 回撤位 + 扩展位；双击可自定义水平与价位）· 快捷键 5" },
  { key: "pos", icon: "±", name: "盈亏比仓位", title: "盈亏比仓位（第 1 点=入场价，第 2 点=止损价；自动识别多空，标出各 R 盈亏比目标位；双击可自定义目标 R）· 快捷键 6" },
  { key: "measure", icon: "📐", name: "测量", title: "测量（第 1 点定起点，第 2 点定终点：价差 / 涨跌幅 / K 线根数 / 时长）· 快捷键 7" },
  { key: "text", icon: "🅣", name: "文字标注", title: "文字标注（点击放置，输入文字；常用于标记 H1/H2、楔形、想法）· 快捷键 8" },
  { key: "erase", icon: "⌫", name: "删除画线", title: "删除画线（点击要删除的画线）" },
];

/** 数字键 1-8 直达工具（顺序与工具栏一致；再按同键取消回 none） */
const HOTKEY_TOOLS: DrawTool[] = ["hline", "trend", "ray", "rect", "fib", "pos", "measure", "text"];

/** 左侧工具栏的抽屉式分组（TradingView 风格）：同族工具折叠进一个槽位，点击展开选择；新工具加进对应组即可 */
const TOOL_GROUPS: Array<{ id: string; label: string; fallbackIcon: string; tools: DrawTool[] }> = [
  { id: "lines", label: "线条", fallbackIcon: "╱", tools: ["hline", "trend", "ray"] },
  { id: "shapes", label: "形状与文字", fallbackIcon: "□", tools: ["rect", "text"] },
  { id: "measure", label: "测算与仓位", fallbackIcon: "📐", tools: ["fib", "pos", "measure"] },
];
const TOOL_BY_KEY: Record<string, { icon: string; name: string; title: string }> = Object.fromEntries(
  DRAW_TOOLS.map((t) => [t.key, { icon: t.icon, name: t.name, title: t.title }]),
);
const hotkeyOf = (tk: DrawTool): string | null => {
  const idx = HOTKEY_TOOLS.indexOf(tk);
  return idx >= 0 ? String(idx + 1) : null;
};

const TOOL_HINTS: Record<DrawTool, string> = {
  none: "",
  hline: "水平线：点击图上位置放置 · Esc 退出",
  trend: "趋势线：点第 1 下定起点，再点 1 下定终点 · Esc 取消",
  ray: "射线：点第 1 下定起点，再点 1 下定延伸方向 · Esc 取消",
  rect: "矩形：点第 1 个对角，再点对角完成 · Esc 取消",
  fib: "斐波那契：点第 1 下（如波段低点），再点终点（如高点），0 位于终点 · Esc 取消",
  pos: "盈亏比仓位：点第 1 下定入场价，再点 1 下定止损价（止损低于入场=做多，反之做空）· Esc 取消",
  measure: "测量：点第 1 下定起点，再点 1 下定终点，显示价差 / 涨跌幅 / K 线根数 / 时长 · Esc 取消",
  text: "文字标注：点击图上位置，输入文字（Esc 取消）",
  erase: "删除画线：点击要删除的线条",
};

const numOrNull = (v: unknown): number | null => (v == null ? null : Number(v));

const hexToRgba = (hex: string, alpha: number): string => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
};

const distToSegment = (px: number, py: number, ax: number, ay: number, bx: number, by: number): number => {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * dx + (py - ay) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
};

const distToRay = (px: number, py: number, ax: number, ay: number, bx: number, by: number): number => {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * dx + (py - ay) * dy) / len2;
  if (t < 0) t = 0;
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
};

const roundRectPath = (ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) => {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
};

// 十字线时间标签：统一北京时间（周几 + 日期 + 时间）
const BJ_TZ = "Asia/Shanghai";
const bjWeekday = new Intl.DateTimeFormat("zh-CN", { timeZone: BJ_TZ, weekday: "short" });
const bjDate = new Intl.DateTimeFormat("en-CA", {
  timeZone: BJ_TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const bjHm = new Intl.DateTimeFormat("en-GB", { timeZone: BJ_TZ, hour: "2-digit", minute: "2-digit", hour12: false });
const fmtBeijingFull = (sec: number): string => {
  const d = new Date(sec * 1000);
  return `${bjWeekday.format(d)} ${bjDate.format(d)} ${bjHm.format(d)}`;
};

interface LegendData {
  open: number;
  high: number;
  low: number;
  close: number;
  chg: number;
  pct: number;
  up: boolean;
  e5: number | null;
  e15: number | null;
  e60: number | null;
}

interface Props {
  bars: Bar[];
  ema20: (number | null)[];
  ema15?: (number | null)[];
  ema60?: (number | null)[];
  keyLevels: KeyLevels | null;
  markers?: ChartMarker[];
  overlays?: ChartOverlays;
  tradeLines?: TradeLine[];
  /** 画线持久化命名空间（一般传 session_id）；缺省则不持久化 */
  sessionKey?: string;
  /** 复盘叠加：判断提交时刻的画线快照（与当前画线并存展示） */
  snapshotDrawings?: Drawing[];
  /** 父层注册回调：随时取当前画线快照（判断提交时随 payload 存档） */
  onRegisterSnapshotGetter?: (fn: (() => Drawing[]) | null) => void;
  /** 父层注册回调：导出图表截图 PNG（含画线/图例） */
  onRegisterExport?: (fn: (() => void) | null) => void;
}

const TF_STORAGE_KEY = "pall.chartTimeframe";
const DRAWING_KEY_PREFIX = "pall.drawings.";
const newId = (): string => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export default function CandleChart({
  bars,
  ema20,
  ema15,
  ema60,
  keyLevels,
  markers,
  overlays,
  tradeLines,
  sessionKey,
  snapshotDrawings,
  onRegisterSnapshotGetter,
  onRegisterExport,
}: Props) {
  const ov = overlays ?? DEFAULT_OVERLAYS;

  const boxRef = useRef<HTMLDivElement>(null);
  const chartDivRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ema15Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ema60Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const priceLinesRef = useRef<ReturnType<ISeriesApi<"Candlestick">["createPriceLine"]>[]>([]);

  // 周期视图（5m 原始 / 15m / 60m / 日线聚合），本地持久化
  const [tf, setTfState] = useState<Timeframe>(() => {
    try {
      const v = localStorage.getItem(TF_STORAGE_KEY) as Timeframe | null;
      return v && TIMEFRAMES.some((t) => t.key === v) ? v : "5m";
    } catch {
      return "5m";
    }
  });
  const agg = useMemo(() => aggregateBars(bars, tf), [bars, tf]);

  const [tool, setToolState] = useState<DrawTool>("none");
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [legend, setLegend] = useState<LegendData | null>(null);
  // 画线悬停与拖拽（tool=none 时：悬停高亮，可整体拖动，拖端点圆圈微调）
  const [hover, setHover] = useState<HoverHit | null>(null);
  const [eraseHoverId, setEraseHoverId] = useState<string | null>(null);
  const [drag, setDrag] = useState<HoverHit | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // 磁吸（锚点吸附 K 线 OHLC）与连续画图（画完不退出工具）：未设置过时默认开
  const [magnet, setMagnet] = useState<boolean>(() => localStorage.getItem("pa_magnet") !== "0");
  const [stayMode, setStayMode] = useState<boolean>(() => localStorage.getItem("pa_stay") !== "0");
  // 撤销/重做：drawings 快照栈（栈本体在 ref；长度进 state 驱动按钮态）
  const [histLen, setHistLen] = useState({ undo: 0, redo: 0 });
  // 隐藏全部画线（裸图对比）；文字标注编辑器（新建/修改共用）
  const [hideDrawings, setHideDrawings] = useState(false);
  const [textEditor, setTextEditor] = useState<{ id: string | null; l: number; p: number; value: string } | null>(null);
  // 画线设置面板（双击打开；草稿确认后生效）
  const [settingsId, setSettingsId] = useState<string | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<SettingsDraft | null>(null);

  // 最新值 refs（供订阅回调 / canvas 渲染读取，避免闭包过期）
  const barsRef = useRef(bars);
  const aggRef = useRef(agg);
  const tfRef = useRef(tf);
  const ovRef = useRef(ov);
  const ema20Ref = useRef(ema20);
  const ema15RefArr = useRef(ema15);
  const ema60RefArr = useRef(ema60);
  const drawingsRef = useRef(drawings);
  const toolRef = useRef(tool);
  const hoverRef = useRef<HoverHit | null>(hover);
  const eraseHoverRef = useRef<string | null>(eraseHoverId);
  const selectedRef = useRef<string | null>(selectedId);
  const hideRef = useRef(hideDrawings);
  const textEditorRef = useRef(textEditor);
  const snapshotRef = useRef<Drawing[]>(snapshotDrawings ?? []);
  snapshotRef.current = snapshotDrawings ?? [];
  const magnetRef = useRef(magnet);
  const stayRef = useRef(stayMode);
  const undoRef = useRef<Drawing[][]>([]);
  const redoRef = useRef<Drawing[][]>([]);
  const preDragRef = useRef<Drawing[] | null>(null);
  const dragMovedRef = useRef(false);
  const dragRef = useRef<{ id: string; part: HoverPart; startPt: DrawPt; orig: Drawing } | null>(null);
  const draftRef = useRef<{ type: "trend" | "ray" | "rect" | "fib" | "pos" | "measure"; a: DrawPt } | null>(null);
  const mousePxRef = useRef<{ x: number; y: number } | null>(null);
  const mouseDrawRef = useRef<DrawPt | null>(null);
  const hoveredIdxRef = useRef<number | null>(null);
  const rafRef = useRef(0);

  barsRef.current = bars;
  aggRef.current = agg;
  tfRef.current = tf;
  ovRef.current = ov;
  ema20Ref.current = ema20;
  ema15RefArr.current = ema15;
  ema60RefArr.current = ema60;
  drawingsRef.current = drawings;
  toolRef.current = tool;
  hoverRef.current = hover;
  eraseHoverRef.current = eraseHoverId;
  selectedRef.current = selectedId;
  hideRef.current = hideDrawings;
  textEditorRef.current = textEditor;
  magnetRef.current = magnet;
  stayRef.current = stayMode;

  // ---- 坐标换算：5m 逻辑索引 ↔ 像素（大周期视图下按聚合几何插值） ----
  const xOf5m = useCallback((l5: number): number | null => {
    const chart = chartRef.current;
    if (!chart) return null;
    const ts = chart.timeScale();
    if (tfRef.current === "5m" || aggRef.current.geom.groups.length === 0) {
      return numOrNull(ts.logicalToCoordinate(l5 as Logical));
    }
    const geom = aggRef.current.geom;
    const n5 = geom.indexOf5m.length;
    if (n5 === 0) return null;
    const xOfAgg = (gi: number) => numOrNull(ts.logicalToCoordinate(gi as Logical));
    const slotOf = (gi: number): number => {
      const x = xOfAgg(gi);
      if (x == null) return ts.options().barSpacing ?? 8;
      const xn = xOfAgg(gi + 1);
      if (xn != null) return xn - x;
      const xp = gi > 0 ? xOfAgg(gi - 1) : null;
      if (xp != null) return x - xp;
      return ts.options().barSpacing ?? 8;
    };
    if (l5 < 0) {
      const cnt = geom.groups[0].count;
      const x0 = xOfAgg(0);
      if (x0 == null) return null;
      const i0 = 0;
      const xFirst = x0 + (i0 - (cnt - 1) / 2) * (slotOf(0) / cnt);
      return xFirst + l5 * (slotOf(0) / cnt);
    }
    if (l5 >= n5) {
      const last = geom.groups.length - 1;
      const cnt = geom.groups[last].count;
      const s5 = slotOf(last) / cnt;
      const xLastCenter = xOfAgg(last);
      if (xLastCenter == null) return null;
      const xLast5 = xLastCenter + ((cnt - 1) / 2) * s5;
      return xLast5 + (l5 - (n5 - 1)) * s5;
    }
    const gi = geom.indexOf5m[l5];
    const gr = geom.groups[gi];
    const xg = xOfAgg(gi);
    if (xg == null) return null;
    const i = l5 - gr.start;
    return xg + (i - (gr.count - 1) / 2) * (slotOf(gi) / gr.count);
  }, []);

  const logical5mFromX = useCallback((x: number): number | null => {
    const chart = chartRef.current;
    if (!chart) return null;
    const ts = chart.timeScale();
    if (tfRef.current === "5m" || aggRef.current.geom.groups.length === 0) {
      return numOrNull(ts.coordinateToLogical(x as Coordinate));
    }
    const geom = aggRef.current.geom;
    const lg = numOrNull(ts.coordinateToLogical(x as Coordinate));
    if (lg == null) return null;
    const gi = Math.max(0, Math.min(geom.groups.length - 1, Math.round(lg)));
    const gr = geom.groups[gi];
    const xg = numOrNull(ts.logicalToCoordinate(gi as Logical));
    if (xg == null) return null;
    const xn = numOrNull(ts.logicalToCoordinate((gi + 1) as Logical));
    const xp = gi > 0 ? numOrNull(ts.logicalToCoordinate((gi - 1) as Logical)) : null;
    const slot = xn != null ? xn - xg : xp != null ? xg - xp : ts.options().barSpacing ?? 8;
    if (gr.count <= 0 || slot <= 0) return gr.start;
    const s5 = slot / gr.count;
    const i = Math.round((x - xg) / s5 + (gr.count - 1) / 2);
    return gr.start + Math.max(0, Math.min(gr.count - 1, i));
  }, []);

  const priceFromY = useCallback((y: number): number | null => {
    return numOrNull(candleRef.current?.coordinateToPrice(y as Coordinate));
  }, []);

  // 画线工具/悬停画线时覆盖画布接管指针，图表收不到鼠标事件；
  // 把光标位置转发给图表十字线，保持价格/时间轴标签可见（便于精确定价）
  const forwardCrosshair = useCallback((pos: { x: number; y: number }) => {
    const chart = chartRef.current;
    const series = candleRef.current;
    if (!chart || !series) return;
    const lg = numOrNull(chart.timeScale().coordinateToLogical(pos.x as Coordinate));
    const bars = aggRef.current.bars;
    if (lg == null || bars.length === 0) return;
    const bar = bars[Math.max(0, Math.min(bars.length - 1, Math.round(lg)))];
    const price = numOrNull(series.coordinateToPrice(pos.y as Coordinate));
    if (price == null) return;
    chart.setCrosshairPosition(price, bar.time as Time, series);
  }, []);

  // 磁吸：锚点吸附到光标下 K 线的开/高/低/收（12px 内取最近），按住 Ctrl 临时关闭
  const snapPt = useCallback((pos: { x: number; y: number }, pt: DrawPt, ctrl: boolean): DrawPt => {
    if (!magnetRef.current || ctrl) return pt;
    const chart = chartRef.current;
    const series = candleRef.current;
    if (!chart || !series) return pt;
    const lg = numOrNull(chart.timeScale().coordinateToLogical(pos.x as Coordinate));
    const bars = aggRef.current.bars;
    if (lg == null || bars.length === 0) return pt;
    const gi = Math.max(0, Math.min(bars.length - 1, Math.round(lg)));
    const b = bars[gi];
    let best: number | null = null;
    let bestD = Number.POSITIVE_INFINITY;
    for (const p of [b.open, b.high, b.low, b.close]) {
      const y = numOrNull(series.priceToCoordinate(p));
      if (y == null) continue;
      const d = Math.abs(y - pos.y);
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    }
    if (best == null || bestD > 12) return pt;
    let l = gi;
    const geom = aggRef.current.geom;
    if (tfRef.current !== "5m" && geom.groups.length > 0 && geom.groups[gi]) {
      const gr = geom.groups[gi];
      l = gr.start + (gr.count - 1) / 2;
    }
    return { l, p: best };
  }, []);

  // ---- 撤销/重做（drawings 快照栈；拖拽在手势结束时入栈） ----
  const syncHist = () => setHistLen({ undo: undoRef.current.length, redo: redoRef.current.length });
  const pushUndo = () => {
    undoRef.current.push(drawingsRef.current);
    if (undoRef.current.length > 100) undoRef.current.shift();
    redoRef.current = [];
    syncHist();
  };
  const undo = () => {
    const prev = undoRef.current.pop();
    if (!prev) return;
    redoRef.current.push(drawingsRef.current);
    setDrawings(prev);
    setEraseHoverId(null);
    setSelectedId(null);
    syncHist();
    requestRedraw();
  };
  const redo = () => {
    const next = redoRef.current.pop();
    if (!next) return;
    undoRef.current.push(drawingsRef.current);
    setDrawings(next);
    setSelectedId(null);
    syncHist();
    requestRedraw();
  };

  const yOfPrice = useCallback((p: number): number | null => {
    return numOrNull(candleRef.current?.priceToCoordinate(p));
  }, []);

  // ---- 画布交互：部位级命中测试（先查端点手柄，再查线体/内部） ----
  const hitTestEx = useCallback(
    (pos: { x: number; y: number }): HoverHit | null => {
      const ds = hideRef.current ? [] : drawingsRef.current;
      for (let i = ds.length - 1; i >= 0; i--) {
        const d = ds[i];
        if (d.locked) continue; // 锁定的画线不可拖动/悬停（右键菜单可解锁）
        if (d.type === "text") {
          const x = xOf5m(d.l);
          const y = yOfPrice(d.p);
          if (x != null && y != null && measureCtx) {
            measureCtx.font = "600 11px system-ui, sans-serif";
            const tw = measureCtx.measureText(d.text).width;
            if (pos.x >= x - 4 && pos.x <= x + tw + 4 && Math.abs(pos.y - y) <= 10) {
              return { id: d.id, part: "body" };
            }
          }
          continue;
        }
        if (d.type === "hline") {
          const y = yOfPrice(d.price);
          if (y != null && Math.abs(pos.y - y) <= 6) return { id: d.id, part: "body" };
          continue;
        }
        const ax = xOf5m(d.a.l);
        const ay = yOfPrice(d.a.p);
        const bx = xOf5m(d.b.l);
        const by = yOfPrice(d.b.p);
        if (ax == null || ay == null || bx == null || by == null) continue;
        if (Math.hypot(pos.x - ax, pos.y - ay) <= 7) return { id: d.id, part: "a" };
        if (Math.hypot(pos.x - bx, pos.y - by) <= 7) return { id: d.id, part: "b" };
        if (d.type === "trend") {
          if (distToSegment(pos.x, pos.y, ax, ay, bx, by) <= 7) return { id: d.id, part: "body" };
        } else if (d.type === "ray") {
          if (distToRay(pos.x, pos.y, ax, ay, bx, by) <= 7) return { id: d.id, part: "body" };
        } else if (d.type === "rect") {
          const x0 = Math.min(ax, bx);
          const x1 = Math.max(ax, bx);
          const y0 = Math.min(ay, by);
          const y1 = Math.max(ay, by);
          if (pos.x >= x0 && pos.x <= x1 && pos.y >= y0 && pos.y <= y1) return { id: d.id, part: "body" };
        } else if (d.type === "measure") {
          const x0 = Math.min(ax, bx);
          const x1 = Math.max(ax, bx);
          const y0 = Math.min(ay, by);
          const y1 = Math.max(ay, by);
          if (pos.x >= x0 && pos.x <= x1 && pos.y >= y0 && pos.y <= y1) return { id: d.id, part: "body" };
        } else if (d.type === "fib") {
          const xl = Math.min(ax, bx) - 6;
          const xr = Math.max(ax, bx) + 6;
          if (pos.x < xl || pos.x > xr) continue;
          const onLevel = levelsOf(d)
            .filter((lv) => lv.on)
            .some((lv) => {
              const y = yOfPrice(d.b.p + (d.a.p - d.b.p) * lv.r);
              return y != null && Math.abs(pos.y - y) <= 5;
            });
          if (onLevel) return { id: d.id, part: "body" };
        } else if (d.type === "pos") {
          const x0 = Math.min(ax, bx) - 4;
          const x1 = Math.max(ax, bx) + 4;
          if (pos.x < x0 || pos.x > x1) continue;
          const nearLine = (price: number, tol: number) => {
            const y = yOfPrice(price);
            return y != null && Math.abs(pos.y - y) <= tol;
          };
          // 入场/止损线或任一 R 目标线 → 整体拖动
          if (
            nearLine(d.a.p, 6) ||
            nearLine(d.b.p, 6) ||
            targetsOf(d).some((r) => nearLine(d.a.p + (d.b.p < d.a.p ? 1 : -1) * Math.abs(d.a.p - d.b.p) * r, 5))
          ) {
            return { id: d.id, part: "body" };
          }
          // 入场~止损之间的风险区内部 → 整体拖动
          const y0 = Math.min(ay, by);
          const y1 = Math.max(ay, by);
          if (pos.y >= y0 && pos.y <= y1) return { id: d.id, part: "body" };
        }
      }
      return null;
    },
    [xOf5m, yOfPrice],
  );

  /** 悬停检测（tool=none 时生效；命中后画布接管指针以便拖动） */
  const updateHover = useCallback(
    (pos: { x: number; y: number } | null) => {
      if (toolRef.current !== "none" || dragRef.current) return;
      const hit = pos ? hitTestEx(pos) : null;
      setHover((prev) => (prev?.id === hit?.id && prev?.part === hit?.part ? prev : hit));
    },
    [hitTestEx],
  );

  // ---- 图例（悬停 K 线的 OHLC / 涨跌幅 / EMA；未悬停显示最新一根） ----
  const updateLegend = useCallback(() => {
    const a = aggRef.current.bars;
    if (a.length === 0) {
      setLegend(null);
      return;
    }
    let idx = hoveredIdxRef.current ?? a.length - 1;
    idx = Math.max(0, Math.min(a.length - 1, idx));
    const b = a[idx];
    const prev = idx > 0 ? a[idx - 1].close : b.open;
    const chg = b.close - prev;
    const pct = prev !== 0 ? (chg / prev) * 100 : 0;
    const arrVal = (arr: (number | null)[] | undefined, i: number): number | null => {
      const v = arr?.[i];
      return v == null ? null : v;
    };
    let e5: number | null = null;
    let e15: number | null = null;
    let e60: number | null = null;
    if (tfRef.current === "5m") {
      e5 = arrVal(ema20Ref.current, idx);
      e15 = arrVal(ema15RefArr.current, idx);
      e60 = arrVal(ema60RefArr.current, idx);
    } else {
      e5 = arrVal(aggRef.current.ema20, idx);
    }
    setLegend({ open: b.open, high: b.high, low: b.low, close: b.close, chg, pct, up: chg >= 0, e5, e15, e60 });
  }, []);

  const idxOfAggTime = useCallback((t: number): number | null => {
    const a = aggRef.current.bars;
    let lo = 0;
    let hi = a.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (a[mid].time === t) return mid;
      if (a[mid].time < t) lo = mid + 1;
      else hi = mid - 1;
    }
    return null;
  }, []);

  // ---- 画布渲染 ----
  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    const box = boxRef.current;
    const chart = chartRef.current;
    const series = candleRef.current;
    if (!canvas || !box || !chart || !series) return;
    const w = box.clientWidth;
    const h = box.clientHeight;
    if (w <= 0 || h <= 0) return;
    const dpr = window.devicePixelRatio || 1;
    const cw = Math.max(1, Math.round(w * dpr));
    const ch = Math.max(1, Math.round(h * dpr));
    if (canvas.width !== cw || canvas.height !== ch) {
      canvas.width = cw;
      canvas.height = ch;
    }
    // 显式 CSS 尺寸：绝对定位的 canvas 在非整数 dpr 下会按缓冲区固有尺寸放大显示，
    // 导致画线相对鼠标出现成比例偏移
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const drawAnchor = (x: number, y: number, color: string) => {
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#10141a";
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.4;
      ctx.stroke();
    };

    const drawOne = (d: Drawing, glow: "erase" | "move" | "sel" | null, isDraft: boolean) => {
      const color = colorOf(d);
      ctx.save();
      if (isDraft) ctx.setLineDash([5, 4]);
      const glowStroke = (trace: () => void, width: number) => {
        if (glow) {
          ctx.save();
          ctx.strokeStyle =
            glow === "erase" ? "rgba(255,82,82,0.4)" : glow === "sel" ? "rgba(130,180,255,0.3)" : "rgba(130,180,255,0.45)";
          ctx.lineWidth = width + 5;
          trace();
          ctx.stroke();
          ctx.restore();
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        trace();
        ctx.stroke();
      };
      const twoPts = (d: Extract<Drawing, { a: DrawPt; b: DrawPt }>) => {
        const ax = xOf5m(d.a.l);
        const ay = yOfPrice(d.a.p);
        const bx = xOf5m(d.b.l);
        const by = yOfPrice(d.b.p);
        return ax == null || ay == null || bx == null || by == null ? null : { ax, ay, bx, by };
      };

      if (d.type === "text") {
        const x = xOf5m(d.l);
        const y = yOfPrice(d.p);
        if (x == null || y == null) {
          ctx.restore();
          return;
        }
        // 正在编辑的这条不画（HTML 输入框替代显示）
        if (textEditorRef.current?.id === d.id) {
          ctx.restore();
          return;
        }
        const tColor = glow === "sel" ? "#4da3ff" : color;
        if (glow) {
          ctx.save();
          ctx.strokeStyle = glow === "erase" ? "rgba(255,82,82,0.45)" : "rgba(130,180,255,0.5)";
          ctx.lineWidth = 4;
          ctx.strokeRect(x - 3, y - 11, ctx.measureText(d.text).width + 6, 22);
          ctx.restore();
        }
        ctx.font = "600 11px system-ui, sans-serif";
        ctx.textBaseline = "middle";
        ctx.fillStyle = hexToRgba(tColor, isDraft ? 0.5 : 0.95);
        ctx.fillText(d.text, x, y);
      } else if (d.type === "hline") {
        const y = yOfPrice(d.price);
        if (y == null) {
          ctx.restore();
          return;
        }
        glowStroke(() => {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
        }, 1.5);
        if (!isDraft) {
          const label = d.price.toFixed(2);
          ctx.font = "600 10px system-ui, sans-serif";
          const tw = ctx.measureText(label).width + 10;
          ctx.fillStyle = color;
          roundRectPath(ctx, w - tw - 2, y - 8, tw, 16, 3);
          ctx.fill();
          ctx.fillStyle = "#10141a";
          ctx.textBaseline = "middle";
          ctx.fillText(label, w - tw + 3, y + 0.5);
        }
      } else if (d.type === "rect") {
        const pts = twoPts(d);
        if (!pts) {
          ctx.restore();
          return;
        }
        const x0 = Math.min(pts.ax, pts.bx);
        const x1 = Math.max(pts.ax, pts.bx);
        const y0 = Math.min(pts.ay, pts.by);
        const y1 = Math.max(pts.ay, pts.by);
        ctx.fillStyle = hexToRgba(color, 0.08);
        ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
        glowStroke(() => {
          ctx.beginPath();
          ctx.rect(x0, y0, x1 - x0, y1 - y0);
        }, 1.4);
        if (!isDraft) {
          drawAnchor(pts.ax, pts.ay, color);
          drawAnchor(pts.bx, pts.by, color);
        }
      } else if (d.type === "fib") {
        const pts = twoPts(d);
        if (!pts) {
          ctx.restore();
          return;
        }
        const priceAt = (r: number) => d.b.p + (d.a.p - d.b.p) * r;
        const xl = Math.min(pts.ax, pts.bx);
        const xr = Math.max(pts.ax, pts.bx);
        const levels = levelsOf(d).filter((lv) => lv.on);
        // 0~1 之间交替浅色带（ TradingView 风格）
        const inRange = levels.map((lv) => lv.r).filter((r) => r >= 0 && r <= 1).sort((a, b) => a - b);
        for (let i = 0; i < inRange.length - 1; i++) {
          const ya = yOfPrice(priceAt(inRange[i]));
          const yb = yOfPrice(priceAt(inRange[i + 1]));
          if (ya == null || yb == null) continue;
          ctx.fillStyle = i % 2 === 0 ? hexToRgba(color, 0.05) : hexToRgba(color, 0.02);
          ctx.fillRect(xl, Math.min(ya, yb), xr - xl, Math.abs(yb - ya));
        }
        for (const lv of levels) {
          const price = priceAt(lv.r);
          const y = yOfPrice(price);
          if (y == null) continue;
          const edge = lv.r === 0 || lv.r === 1;
          const ext = lv.r < 0 || lv.r > 1;
          const lvColor = LEVEL_PALETTE[Math.abs(Math.round(lv.r * 1000)) % LEVEL_PALETTE.length];
          ctx.setLineDash(ext ? [4, 3] : isDraft ? [5, 4] : []);
          ctx.strokeStyle = hexToRgba(lvColor, ext ? 0.5 : edge ? 0.9 : 0.65);
          ctx.lineWidth = edge ? 1.4 : 1;
          ctx.beginPath();
          ctx.moveTo(xl, y);
          ctx.lineTo(xr, y);
          ctx.stroke();
          ctx.setLineDash(isDraft ? [5, 4] : []);
          ctx.font = "600 10px system-ui, sans-serif";
          ctx.fillStyle = lvColor;
          ctx.textBaseline = "bottom";
          ctx.fillText(`${lv.r}  ${price.toFixed(2)}`, xl + 4, y - 2);
        }
        // 两锚点间的虚线（趋势方向提示）
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = hexToRgba(color, 0.5);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pts.ax, pts.ay);
        ctx.lineTo(pts.bx, pts.by);
        ctx.stroke();
        ctx.setLineDash([]);
        if (!isDraft) {
          drawAnchor(pts.ax, pts.ay, color);
          drawAnchor(pts.bx, pts.by, color);
        }
      } else if (d.type === "pos") {
        // 盈亏比仓位：入场（a.p）+ 止损（b.p）→ 1R 距离，标出各 R 目标位
        const pts = twoPts(d);
        if (!pts) {
          ctx.restore();
          return;
        }
        const entryY = pts.ay;
        const stopY = pts.by;
        const x0 = Math.min(pts.ax, pts.bx);
        const x1 = Math.max(pts.ax, pts.bx);
        const long = d.b.p < d.a.p;
        const risk = Math.abs(d.a.p - d.b.p);
        const dirLabel = long ? "多" : "空";
        // 风险区（入场~止损之间红色浅填充）
        ctx.fillStyle = hexToRgba("#ef5350", 0.1);
        ctx.fillRect(x0, Math.min(entryY, stopY), x1 - x0, Math.abs(stopY - entryY));
        // 止损线
        glowStroke(() => {
          ctx.beginPath();
          ctx.moveTo(x0, stopY);
          ctx.lineTo(x1, stopY);
        }, 1.2);
        // 入场线
        ctx.strokeStyle = hexToRgba("#e6edf3", 0.85);
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(x0, entryY);
        ctx.lineTo(x1, entryY);
        ctx.stroke();
        // 各 R 目标线（盈亏比）
        const lineLabel = (text: string, y: number, bg: string, fg: string) => {
          ctx.font = "600 10px system-ui, sans-serif";
          const tw = ctx.measureText(text).width + 8;
          ctx.fillStyle = bg;
          roundRectPath(ctx, x0 + 2, y - 8, tw, 14, 3);
          ctx.fill();
          ctx.fillStyle = fg;
          ctx.textBaseline = "middle";
          ctx.fillText(text, x0 + 6, y - 0.5);
        };
        lineLabel(`入场 ${dirLabel} ${d.a.p.toFixed(2)}`, entryY, "#2d3642", "#e6edf3");
        lineLabel(`止损 ${d.b.p.toFixed(2)}`, stopY, hexToRgba("#ef5350", 0.85), "#ffffff");
        for (const r of targetsOf(d)) {
          const price = d.a.p + (long ? 1 : -1) * risk * r;
          const y = yOfPrice(price);
          if (y == null) continue;
          ctx.setLineDash(isDraft ? [5, 4] : []);
          ctx.strokeStyle = hexToRgba("#26a69a", 0.8);
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(x0, y);
          ctx.lineTo(x1, y);
          ctx.stroke();
          lineLabel(`${r}R（盈亏比 ${r}） ${price.toFixed(2)}`, y, hexToRgba("#26a69a", 0.9), "#ffffff");
        }
        if (!isDraft) {
          drawAnchor(pts.ax, pts.ay, color);
          drawAnchor(pts.bx, pts.by, color);
        }
      } else if (d.type === "measure") {
        const pts = twoPts(d);
        if (!pts) {
          ctx.restore();
          return;
        }
        const up = d.b.p >= d.a.p;
        const mColor = up ? "#26a69a" : "#ef5350";
        const x0 = Math.min(pts.ax, pts.bx);
        const x1 = Math.max(pts.ax, pts.bx);
        const y0 = Math.min(pts.ay, pts.by);
        const y1 = Math.max(pts.ay, pts.by);
        ctx.fillStyle = hexToRgba(mColor, 0.1);
        ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
        if (glow) {
          ctx.save();
          ctx.strokeStyle = glow === "erase" ? "rgba(255,82,82,0.4)" : "rgba(130,180,255,0.45)";
          ctx.lineWidth = 6.2;
          ctx.beginPath();
          ctx.rect(x0, y0, x1 - x0, y1 - y0);
          ctx.stroke();
          ctx.restore();
        }
        ctx.setLineDash(isDraft ? [5, 4] : [4, 3]);
        ctx.strokeStyle = mColor;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.rect(x0, y0, x1 - x0, y1 - y0);
        ctx.stroke();
        ctx.setLineDash([]);
        // 信息标签：价差 / 涨跌幅 / 5m 根数 / 时长
        const dp = d.b.p - d.a.p;
        const pct = d.a.p !== 0 ? (dp / d.a.p) * 100 : 0;
        const nBars = Math.max(0, Math.round(Math.abs(d.b.l - d.a.l)));
        const mins = nBars * 5;
        const durTxt = mins >= 60 ? `${Math.floor(mins / 60)}小时${mins % 60 ? `${mins % 60}分` : ""}` : `${mins}分`;
        const l1 = `${dp >= 0 ? "+" : ""}${dp.toFixed(2)}（${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%）`;
        const l2 = `${nBars} 根 · ${durTxt}`;
        ctx.font = "600 10px system-ui, sans-serif";
        const tw = Math.max(ctx.measureText(l1).width, ctx.measureText(l2).width) + 14;
        const cx = (x0 + x1) / 2;
        const cy = (y0 + y1) / 2;
        const bx = Math.max(2, Math.min(w - tw - 2, cx - tw / 2));
        const by = Math.max(2, Math.min(h - 34, cy - 15));
        ctx.fillStyle = "#10141a";
        roundRectPath(ctx, bx, by, tw, 30, 4);
        ctx.fill();
        ctx.strokeStyle = hexToRgba(mColor, 0.8);
        ctx.lineWidth = 1;
        roundRectPath(ctx, bx, by, tw, 30, 4);
        ctx.stroke();
        ctx.textBaseline = "middle";
        ctx.fillStyle = mColor;
        ctx.fillText(l1, bx + 7, by + 9.5);
        ctx.fillStyle = "#e6edf3";
        ctx.fillText(l2, bx + 7, by + 21);
        if (!isDraft) {
          drawAnchor(pts.ax, pts.ay, mColor);
          drawAnchor(pts.bx, pts.by, mColor);
        }
      } else {
        // trend | ray
        const pts = twoPts(d);
        if (!pts) {
          ctx.restore();
          return;
        }
        let ex = pts.bx;
        let ey = pts.by;
        if (d.type === "ray") {
          const dx = pts.bx - pts.ax;
          const dy = pts.by - pts.ay;
          const len = Math.hypot(dx, dy) || 1;
          const k = 4000 / len;
          ex = pts.ax + dx * k;
          ey = pts.ay + dy * k;
        }
        glowStroke(() => {
          ctx.beginPath();
          ctx.moveTo(pts.ax, pts.ay);
          ctx.lineTo(ex, ey);
        }, 1.6);
        if (!isDraft) {
          drawAnchor(pts.ax, pts.ay, color);
          drawAnchor(pts.bx, pts.by, color);
        }
      }
      ctx.restore();
    };

    const draft = draftRef.current;
    const preview: Drawing | null =
      draft && mouseDrawRef.current ? { id: "__draft", type: draft.type, a: draft.a, b: mouseDrawRef.current } : null;
    const eraseId = dragRef.current ? null : eraseHoverRef.current;
    const moveId = dragRef.current?.id ?? hoverRef.current?.id ?? null;
    const selId = dragRef.current ? null : selectedRef.current;
    // 裸图模式：隐藏全部已存画线（预览/草稿仍显示，避免「工具失灵」的错觉）
    if (!hideRef.current) {
      for (const d of drawingsRef.current) {
        drawOne(d, eraseId === d.id ? "erase" : moveId === d.id ? "move" : selId === d.id ? "sel" : null, false);
      }
    }
    // 判断提交时刻的画线快照：暗色半透明叠加（复盘对照，不参与交互）
    ctx.save();
    ctx.globalAlpha = 0.55;
    for (const d of snapshotRef.current) {
      drawOne(d, null, true);
    }
    ctx.restore();
    if (preview) drawOne(preview, null, true);
  }, [xOf5m, yOfPrice]);

  const redrawRef = useRef<() => void>(() => {});
  redrawRef.current = redraw;

  const requestRedraw = useCallback(() => {
    if (rafRef.current) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0;
      redrawRef.current();
    });
  }, []);

  // ---- 图表初始化（仅一次） ----
  useEffect(() => {
    const el = chartDivRef.current;
    if (!el) return;
    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "#10141a" },
        textColor: "#8b949e",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1c222b" },
        horzLines: { color: "#1c222b" },
      },
      localization: {
        // 十字线时间标签：完整北京时间（周几 + 日期 + 时间）
        timeFormatter: (time: Time) => fmtBeijingFull(typeof time === "number" ? time : 0),
      },
      width: el.clientWidth,
      height: el.clientHeight,
      timeScale: { timeVisible: true, secondsVisible: false, rightOffset: 3 },
      rightPriceScale: { borderColor: "#28303c" },
      crosshair: { mode: 0 },
      autoSize: true,
    });
    candleRef.current = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
      borderVisible: false,
    });
    emaRef.current = chart.addLineSeries({
      color: "#f0b90b",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "EMA20",
    });
    ema15Ref.current = chart.addLineSeries({
      color: "#4da3ff",
      lineWidth: 1,
      lineStyle: 0, // 实线：15m 20 bar EMA
      priceLineVisible: false,
      lastValueVisible: true,
      title: "15m EMA20",
    });
    ema60Ref.current = chart.addLineSeries({
      color: "#9a86c9",
      lineWidth: 2,
      lineStyle: 2, // 虚线：60m 20 bar EMA（对照 Brooks 课件中的虚线高周期均线）
      priceLineVisible: false,
      lastValueVisible: true,
      title: "60m EMA20",
    });

    const onCrosshair = (param: { time?: unknown; point?: { x: number; y: number } | null }) => {
      if (param.time != null && param.point != null) {
        hoveredIdxRef.current = idxOfAggTime(Number(param.time));
      } else {
        hoveredIdxRef.current = null;
      }
      updateLegend();
      // tool=none 时画布对鼠标透明，悬停检测借道图表十字线事件
      if (toolRef.current === "none" && !dragRef.current) {
        updateHover(param.point ?? null);
      }
      requestRedraw();
    };
    chart.subscribeCrosshairMove(onCrosshair);
    chart.timeScale().subscribeVisibleLogicalRangeChange(() => requestRedraw());

    const ro = new ResizeObserver(() => requestRedraw());
    ro.observe(el);
    chartRef.current = chart;

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      emaRef.current = null;
      ema15Ref.current = null;
      ema60Ref.current = null;
      priceLinesRef.current = [];
    };
  }, [idxOfAggTime, updateLegend, updateHover, requestRedraw]);

  // ---- 数据更新（每次全量 setData；5m ≤ 数千根，开销可忽略） ----
  useEffect(() => {
    const series = candleRef.current;
    if (!series) return;
    const times = agg.bars.map((b) => b.time);
    series.setData(
      agg.bars.map((b) => ({
        time: b.time as UTCTimestamp,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );
    const toPoints = (values: (number | null)[]) =>
      values
        .map((v, i) => ({ time: times[i] as UTCTimestamp, value: v }))
        .filter((p): p is { time: UTCTimestamp; value: number } => p.value != null);

    // 主图 EMA：5m 视图用服务端预热值；大周期视图用聚合序列客户端重算
    const mainEma = tf === "5m" ? ema20 : agg.ema20;
    emaRef.current?.setData(ov.ema5 ? toPoints(mainEma) : []);
    ema15Ref.current?.setData(tf === "5m" && ov.ema15 ? toPoints(ema15 ?? []) : []);
    ema60Ref.current?.setData(tf === "5m" && ov.ema60 ? toPoints(ema60 ?? []) : []);

    // 关键价位：先清旧线再画（支持逐条开关与标题开关）
    const chart = chartRef.current;
    if (chart) {
      for (const pl of priceLinesRef.current) series.removePriceLine(pl);
      priceLinesRef.current = [];
      if (keyLevels) {
        for (const s of KEY_LEVEL_ITEMS) {
          if (!isLevelVisible(ov, s.key)) continue;
          const v = keyLevels[s.key];
          if (typeof v === "number") {
            priceLinesRef.current.push(
              series.createPriceLine({
                price: v,
                color: s.color,
                lineWidth: 1,
                lineStyle: 2,
                axisLabelVisible: true,
                title: ov.keyLevelTitles ? s.label : "",
              }),
            );
          }
        }
      }
      // 模拟持仓线：入场/止损/目标（仓位管理可视化）
      if (ov.positions) {
        for (const tl of tradeLines ?? []) {
          priceLinesRef.current.push(
            series.createPriceLine({
              price: tl.price,
              color: tl.color,
              lineWidth: 1,
              lineStyle: 0,
              axisLabelVisible: true,
              title: tl.title,
            }),
          );
        }
      }
    }
    updateLegend();
    requestRedraw();
  }, [agg, tf, ema20, ema15, ema60, keyLevels, ov, tradeLines, updateLegend, requestRedraw]);

  // ---- 均线右轴标签开关 ----
  useEffect(() => {
    const opt = (title: string) => ({
      lastValueVisible: ov.emaAxisLabels,
      title: ov.emaAxisLabels ? title : "",
    });
    emaRef.current?.applyOptions(opt("EMA20"));
    ema15Ref.current?.applyOptions(opt("15m EMA20"));
    ema60Ref.current?.applyOptions(opt("60m EMA20"));
  }, [ov]);

  // ---- 候选标记（克制样式；仅在 Predict First 解锁后由父组件传入） ----
  useEffect(() => {
    const series = candleRef.current;
    if (!series) return;
    const style: Record<ChartMarker["kind"], Pick<SeriesMarker<Time>, "position" | "shape" | "color" | "text">> = {
      inside: { position: "belowBar", shape: "circle", color: "#5a6b7d", text: "i" },
      outside: { position: "aboveBar", shape: "circle", color: "#c98a4b", text: "o" },
      ii: { position: "aboveBar", shape: "square", color: "#e8c66a", text: "ii" },
      iii: { position: "aboveBar", shape: "square", color: "#e8c66a", text: "iii" },
      ioi: { position: "aboveBar", shape: "square", color: "#e8c66a", text: "ioi" },
      swing_high: { position: "aboveBar", shape: "arrowDown", color: "#4da3ff", text: "SH" },
      swing_low: { position: "belowBar", shape: "arrowUp", color: "#4da3ff", text: "SL" },
      h1: { position: "belowBar", shape: "arrowUp", color: "#26a69a", text: "H1" },
      h2: { position: "belowBar", shape: "arrowUp", color: "#00e676", text: "H2 ★" },
      h3: { position: "belowBar", shape: "arrowUp", color: "#26a69a", text: "H3" },
      h4: { position: "belowBar", shape: "arrowUp", color: "#26a69a", text: "H4" },
      l1: { position: "aboveBar", shape: "arrowDown", color: "#ef5350", text: "L1" },
      l2: { position: "aboveBar", shape: "arrowDown", color: "#ff1744", text: "L2 ★" },
      l3: { position: "aboveBar", shape: "arrowDown", color: "#ef5350", text: "L3" },
      l4: { position: "aboveBar", shape: "arrowDown", color: "#ef5350", text: "L4" },
      hl: { position: "belowBar", shape: "square", color: "#7ee2a8", text: "" },
      wedge: { position: "aboveBar", shape: "square", color: "#9c27b0", text: "Wedge" },
      climax: { position: "aboveBar", shape: "arrowDown", color: "#ef5350", text: "Climax" },
      micro_channel: { position: "belowBar", shape: "circle", color: "#26a69a", text: "MC" },
      bull_trend: { position: "belowBar", shape: "circle", color: "#26a69a", text: "▲" },
      bear_trend: { position: "aboveBar", shape: "circle", color: "#ef5350", text: "▼" },
      bull_signal: { position: "belowBar", shape: "arrowUp", color: "#00e676", text: "Buy Sig" },
      bear_signal: { position: "aboveBar", shape: "arrowDown", color: "#ff1744", text: "Sell Sig" },
    };
    // 大周期视图下把 5m 标记吸附到所属聚合 K 线
    series.setMarkers(
      (markers ?? [])
        .map((m) => {
          const s = style[m.kind];
          return {
            time: agg.snapTime(Math.round(Date.parse(m.time) / 1000)) as Time,
            ...s,
            ...(m.text ? { text: m.text } : {}),
          };
        })
        .sort((a, b) => (a.time as number) - (b.time as number)),
    );
  }, [markers, agg]);

  // 每次渲染后同步重绘画布（数据/图层/画线变化兜底）
  useEffect(() => {
    requestRedraw();
  });

  // ---- 周期切换 ----
  const changeTf = (next: Timeframe) => {
    if (next === tf) return;
    draftRef.current = null;
    try {
      localStorage.setItem(TF_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    setTfState(next);
  };

  // 切换周期后重置可视范围（逻辑索引含义随周期变化，沿用旧范围会显示空白）
  const prevTfRef = useRef(tf);
  useEffect(() => {
    if (prevTfRef.current === tf) return;
    prevTfRef.current = tf;
    const chart = chartRef.current;
    const count = aggRef.current.bars.length;
    if (!chart || count === 0) return;
    const visible = tf === "5m" ? 90 : 48;
    if (count <= visible) {
      // 大周期 K 线很少时铺满整个图表，避免缩在中间留大片空白
      chart.timeScale().fitContent();
    } else {
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, count - visible),
        to: count + 3,
      });
    }
  }, [tf]);

  // ---- 画线持久化（按会话） ----
  useEffect(() => {
    draftRef.current = null;
    dragRef.current = null;
    setDrag(null);
    setHover(null);
    setEraseHoverId(null);
    if (!sessionKey) {
      setDrawings([]);
      return;
    }
    let cancelled = false;
    try {
      const raw = localStorage.getItem(DRAWING_KEY_PREFIX + sessionKey);
      const parsed = raw ? JSON.parse(raw) : [];
      if (!cancelled) setDrawings(Array.isArray(parsed) ? parsed : []);
    } catch {
      if (!cancelled) setDrawings([]);
    }
    return () => {
      cancelled = true;
    };
  }, [sessionKey]);

  useEffect(() => {
    if (!sessionKey) return;
    try {
      localStorage.setItem(DRAWING_KEY_PREFIX + sessionKey, JSON.stringify(drawings));
    } catch {
      /* ignore */
    }
  }, [drawings, sessionKey]);

  const setTool = (t: DrawTool) => {
    draftRef.current = null;
    dragRef.current = null;
    setDrag(null);
    setHover(null);
    setEraseHoverId(null);
    setSelectedId(null);
    setToolState(t);
    requestRedraw();
  };

  const clearDrawings = () => {
    if (drawings.length === 0) return;
    if (window.confirm(`确定清空当前会话的全部 ${drawings.length} 条画线吗？`)) {
      pushUndo();
      setDrawings([]);
      setEraseHoverId(null);
      setHover(null);
      setSelectedId(null);
    }
  };

  // Esc 取消进行中的绘制 / 退出工具 / 关闭画线设置 / 取消选中；Del 删除选中画线
  useEffect(() => {
    if (tool === "none" && !settingsId && !selectedId) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target != null && target.isContentEditable);
      if (typing) return; // 焦点在输入框（含文字标注编辑器）：Del/Backspace/Enter 归输入框处理
      if (e.key === "Escape") {
        if (settingsId) closeSettings();
        else if (tool !== "none") setTool("none");
        else if (selectedId) setSelectedId(null);
        return;
      }
      if ((e.key === "Delete" || e.key === "Backspace") && selectedId && !settingsId && !typing) {
        const target = drawingsRef.current.find((d) => d.id === selectedId);
        if (target?.locked) return; // 锁定的画线不响应 Del（先解锁）
        e.preventDefault();
        const id = selectedId;
        pushUndo();
        setSelectedId(null);
        setDrawings((prev) => prev.filter((d) => d.id !== id));
        requestRedraw();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tool, settingsId, selectedId]);

  // 磁吸/连续画图偏好持久化
  useEffect(() => {
    localStorage.setItem("pa_magnet", magnet ? "1" : "0");
  }, [magnet]);
  useEffect(() => {
    localStorage.setItem("pa_stay", stayMode ? "1" : "0");
  }, [stayMode]);

  // 工具快捷键：1-7 切换工具（同键再按取消）、G 磁吸、Ctrl+Z/Ctrl+Y 撤销重做；输入框内不劫持
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target != null && target.isContentEditable);
      if (typing || settingsId || textEditorRef.current) return;
      if ((e.ctrlKey || e.metaKey) && !e.altKey) {
        const k = e.key.toLowerCase();
        if (k === "z") {
          e.preventDefault();
          if (e.shiftKey) redo();
          else undo();
        } else if (k === "y") {
          e.preventDefault();
          redo();
        }
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === "g" || e.key === "G") {
        setMagnet((m) => !m);
        return;
      }
      if (e.key === "s" || e.key === "S") {
        setStayMode((s) => !s);
        return;
      }
      if (e.key === "h" || e.key === "H") {
        if (drawingsRef.current.length === 0) return;
        setHideDrawings((v) => !v);
        return;
      }
      const n = Number(e.key);
      if (Number.isInteger(n) && n >= 1 && n <= HOTKEY_TOOLS.length) {
        const t = HOTKEY_TOOLS[n - 1];
        setTool(toolRef.current === t ? "none" : t);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settingsId]);

  // 选中状态变化时重绘（选中画线显示持续高亮）
  useEffect(() => {
    requestRedraw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  // 裸图模式切换时重绘
  useEffect(() => {
    requestRedraw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hideDrawings]);

  // 文字编辑器打开/关闭时重绘（编辑中的文字由输入框替代渲染）
  useEffect(() => {
    requestRedraw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textEditor]);

  // 快照层变化时重绘
  useEffect(() => {
    requestRedraw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshotDrawings]);

  // 向父层注册：取当前画线快照（判断提交时存档）
  useEffect(() => {
    onRegisterSnapshotGetter?.(() => JSON.parse(JSON.stringify(drawingsRef.current)) as Drawing[]);
    return () => onRegisterSnapshotGetter?.(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onRegisterSnapshotGetter]);

  // 向父层注册：导出图表 PNG（lightweight-charts takeScreenshot + 画线画布合成）
  const exportPng = useCallback(() => {
    const chart = chartRef.current;
    const overlay = canvasRef.current;
    const box = boxRef.current;
    if (!chart || !overlay || !box) return;
    // 1) 图表本体截图（K线/EMA/价位线/图例都是 DOM/canvas 混合，lightweight-charts 官方 API）
    const chartShot = chart.takeScreenshot();
    // 2) 合成到离屏画布：宽高取图表容器实际尺寸
    const w = Math.round(chartShot.width / (window.devicePixelRatio || 1));
    const h = Math.round(chartShot.height / (window.devicePixelRatio || 1));
    const out = document.createElement("canvas");
    out.width = w;
    out.height = h;
    const ctx = out.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#10141a";
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(chartShot, 0, 0, w, h);
    // 3) 叠加画线画布（overlay canvas 与图表同尺寸同位置）
    ctx.drawImage(overlay, 0, 0, w, h);
    const url = out.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = url;
    a.download = `chart-${sessionKey ?? "export"}-${new Date().toISOString().slice(0, 10)}.png`;
    a.click();
  }, [sessionKey]);
  useEffect(() => {
    onRegisterExport?.(exportPng);
    return () => onRegisterExport?.(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onRegisterExport, exportPng]);

  // ---- 画布交互 ----
  // mouseup 常驻监听：快速按下-抬起时 mouseup 可能先于 effect 挂载到达，
  // 条件挂载会导致 dragRef 永久卡死（悬停/点击全部失效）
  useEffect(() => {
    const end = () => {
      if (!dragRef.current) return;
      // 拖拽手势实际移动过才记一步撤销
      if (dragMovedRef.current && preDragRef.current) {
        undoRef.current.push(preDragRef.current);
        if (undoRef.current.length > 100) undoRef.current.shift();
        redoRef.current = [];
        setHistLen({ undo: undoRef.current.length, redo: 0 });
      }
      preDragRef.current = null;
      dragMovedRef.current = false;
      dragRef.current = null;
      setDrag(null);
    };
    window.addEventListener("mouseup", end);
    return () => window.removeEventListener("mouseup", end);
  }, []);

  const pointFromEvent = (e: React.MouseEvent<HTMLCanvasElement>): { pos: { x: number; y: number }; pt: DrawPt | null } | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const r = canvas.getBoundingClientRect();
    const pos = { x: e.clientX - r.left, y: e.clientY - r.top };
    const l = logical5mFromX(pos.x);
    const p = priceFromY(pos.y);
    return { pos, pt: l != null && p != null ? { l, p } : null };
  };

  /** 拖拽应用：端点拖动只动一端，body 拖动整体平移（水平线只随 Y 变价） */
  const applyDrag = (pt: DrawPt) => {
    const dg = dragRef.current;
    if (!dg) return;
    dragMovedRef.current = true;
    const dL = pt.l - dg.startPt.l;
    const dP = pt.p - dg.startPt.p;
    setDrawings((prev) =>
      prev.map((d): Drawing => {
        if (d.id !== dg.id) return d;
        if (d.type === "hline") {
          const origPrice = (dg.orig as { price: number }).price;
          return { ...d, price: origPrice + dP };
        }
        if (d.type === "text") {
          const o = dg.orig as { l: number; p: number };
          return { ...d, l: o.l + dL, p: o.p + dP };
        }
        const o = dg.orig as Extract<Drawing, { a: DrawPt; b: DrawPt }>;
        if (dg.part === "a") return { ...d, a: { l: o.a.l + dL, p: o.a.p + dP } };
        if (dg.part === "b") return { ...d, b: { l: o.b.l + dL, p: o.b.p + dP } };
        return {
          ...d,
          a: { l: o.a.l + dL, p: o.a.p + dP },
          b: { l: o.b.l + dL, p: o.b.p + dP },
        };
      }),
    );
  };

  // ---- 画线设置面板 ----
  const closeSettings = () => {
    setSettingsId(null);
    setSettingsDraft(null);
  };

  const openSettings = (id: string) => {
    const d = drawingsRef.current.find((x) => x.id === id);
    if (!d) return;
    if (d.type === "text") {
      // 文字类型的「设置」就是编辑文字本身
      setTextEditor({ id: d.id, l: d.l, p: d.p, value: d.text });
      return;
    }
    setSettingsId(id);
    setSettingsDraft({
      color: d.color,
      price: d.type === "hline" ? d.price : undefined,
      levels: d.type === "fib" ? levelsOf(d).map((lv) => ({ ...lv })) : undefined,
      targets: d.type === "pos" ? [...targetsOf(d)] : undefined,
      locked: d.locked,
    });
  };

  const applySettings = () => {
    const dr = settingsDraft;
    if (!settingsId || !dr) {
      closeSettings();
      return;
    }
    pushUndo();
    setDrawings((prev) =>
      prev.map((d): Drawing => {
        if (d.id !== settingsId) return d;
        let next: Drawing = { ...d, color: dr.color, locked: dr.locked };
        if (next.type === "hline" && typeof dr.price === "number" && Number.isFinite(dr.price)) {
          next = { ...next, price: dr.price };
        }
        if (next.type === "fib") {
          next = {
            ...next,
            levels: (dr.levels ?? [])
              .map((lv) => ({ r: Number(lv.r), on: lv.on }))
              .filter((lv) => Number.isFinite(lv.r)),
          };
        }
        if (next.type === "pos") {
          next = {
            ...next,
            targets: (dr.targets ?? []).map((v) => Number(v)).filter((v) => Number.isFinite(v) && v > 0),
          };
        }
        return next;
      }),
    );
    closeSettings();
  };

  // ---- 文字标注编辑器（新建与修改共用；空文本=取消） ----
  const commitTextEditor = () => {
    const ed = textEditorRef.current;
    if (!ed) return;
    if (ed.value.trim()) {
      pushUndo();
      if (ed.id == null) {
        setDrawings((prev) => [...prev, { id: newId(), type: "text", l: ed.l, p: ed.p, text: ed.value.trim() }]);
      } else {
        setDrawings((prev) => prev.map((d) => (d.id === ed.id && d.type === "text" ? { ...d, text: ed.value.trim() } : d)));
      }
    }
    setTextEditor(null);
    requestRedraw();
  };
  const cancelTextEditor = () => {
    setTextEditor(null);
    requestRedraw();
  };

  // ---- 右键菜单：设置 / 克隆 / 锁定 / 删除 ----
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; id: string } | null>(null);
  // 抽屉式工具分组当前展开的组 id（null = 全部收起）
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  // 点击工具栏外部或按 Esc 时收起展开的抽屉
  useEffect(() => {
    if (!openGroup) return;
    const close = () => setOpenGroup(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenGroup(null);
    };
    window.addEventListener("mousedown", close);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [openGroup]);
  const ctxDrawing = ctxMenu ? drawings.find((d) => d.id === ctxMenu.id) : null;
  const cloneDrawing = (id: string) => {
    const d = drawingsRef.current.find((x) => x.id === id);
    if (!d) return;
    // 各类型独立构造（偏移 5 根 K 线），避免联合类型收窄问题
    const copy: Drawing =
      d.type === "text"
        ? { ...d, id: newId(), l: d.l + 5 }
        : d.type === "hline"
        ? { ...d, id: newId() } // 水平线克隆保持原价（同名线用颜色区分）
        : d.type === "fib"
        ? { ...d, id: newId(), a: { ...d.a, l: d.a.l + 5 }, b: { ...d.b, l: d.b.l + 5 } }
        : d.type === "pos"
        ? { ...d, id: newId(), a: { ...d.a, l: d.a.l + 5 }, b: { ...d.b, l: d.b.l + 5 } }
        : { ...d, id: newId(), a: { ...d.a, l: d.a.l + 5 }, b: { ...d.b, l: d.b.l + 5 } };
    pushUndo();
    setDrawings((prev) => [...prev, copy]);
    requestRedraw();
  };
  const toggleLockDrawing = (id: string) => {
    pushUndo();
    setDrawings((prev) => prev.map((d) => (d.id === id ? { ...d, locked: !d.locked } : d)));
    if (selectedRef.current === id) setSelectedId(null);
    requestRedraw();
  };
  const deleteDrawingById = (id: string) => {
    pushUndo();
    setDrawings((prev) => prev.filter((d) => d.id !== id));
    if (selectedRef.current === id) setSelectedId(null);
    requestRedraw();
  };
  const onCanvasContextMenu = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (toolRef.current !== "none") return;
    const res = pointFromEvent(e);
    const hit = res ? hitTestEx(res.pos) : null;
    if (!hit) return; // 空白处右键交给浏览器/图表默认菜单
    e.preventDefault();
    e.stopPropagation();
    const r = canvasRef.current?.getBoundingClientRect();
    setCtxMenu({ x: e.clientX - (r?.left ?? 0), y: e.clientY - (r?.top ?? 0), id: hit.id });
  };
  // 右键菜单关闭：点击菜单外 / Esc（锁定线仍可右键操作，锁只挡拖拽与删除工具）
  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCtxMenu(null);
    };
    window.addEventListener("mousedown", close);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [ctxMenu]);

  const onCanvasDoubleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (toolRef.current !== "none") return;
    const res = pointFromEvent(e);
    if (!res?.pt) return;
    const hit = hitTestEx(res.pos);
    if (!hit) return;
    const d = drawingsRef.current.find((x) => x.id === hit.id);
    if (d?.type === "text") {
      // 双击文字进入编辑（沿用在设置面板的弹层风格）
      if (d.locked) return;
      setTextEditor({ id: d.id, l: d.l, p: d.p, value: d.text });
      return;
    }
    openSettings(hit.id);
  };

  const onCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (toolRef.current !== "none") return;
    const res = pointFromEvent(e);
    if (!res?.pt) return;
    const hit = hitTestEx(res.pos);
    if (!hit) {
      if (selectedRef.current != null) setSelectedId(null);
      return;
    }
    const orig = drawingsRef.current.find((d) => d.id === hit.id);
    if (!orig) return;
    e.preventDefault();
    // 端点拖拽走磁吸；整体拖动不吸附（否则整个图形会跳变）
    const startPt = hit.part === "a" || hit.part === "b" ? snapPt(res.pos, res.pt, e.ctrlKey || e.metaKey) : res.pt;
    if (selectedRef.current !== hit.id) setSelectedId(hit.id);
    preDragRef.current = drawingsRef.current;
    dragMovedRef.current = false;
    dragRef.current = { id: hit.id, part: hit.part, startPt, orig: JSON.parse(JSON.stringify(orig)) as Drawing };
    setDrag(hit);
  };

  const onCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const res = pointFromEvent(e);
    if (!res) return;
    forwardCrosshair(res.pos);
    mousePxRef.current = res.pos;
    mouseDrawRef.current = res.pt;
    if (dragRef.current) {
      if (res.pt) applyDrag(res.pt);
      return;
    }
    if (toolRef.current === "erase") {
      const id = res.pt ? hitTestEx(res.pos)?.id ?? null : null;
      setEraseHoverId((prev) => (prev === id ? prev : id));
    } else if (toolRef.current === "none") {
      updateHover(res.pos);
    }
    requestRedraw();
  };

  const onCanvasMouseLeave = () => {
    mousePxRef.current = null;
    mouseDrawRef.current = null;
    chartRef.current?.clearCrosshairPosition();
    if (dragRef.current) return; // 拖拽中不移出（window mouseup 负责结束）
    setHover(null);
    setEraseHoverId(null);
    requestRedraw();
  };

  const onCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const t = toolRef.current;
    if (t === "none" || dragRef.current) return;
    // 不依赖前置 mousemove：直接用点击坐标换算锚点（触摸/合成点击也可靠）
    const res = pointFromEvent(e);
    if (!res || !res.pt) return;
    const pt = snapPt(res.pos, res.pt, e.ctrlKey || e.metaKey);
    mousePxRef.current = res.pos;
    mouseDrawRef.current = pt;
    if (t === "erase") {
      const id = hitTestEx(res.pos)?.id ?? null;
      if (id) {
        const target = drawingsRef.current.find((d) => d.id === id);
        if (target?.locked) return; // 锁定的画线不被删除工具擦除（先解锁）
        pushUndo();
        setDrawings((prev) => prev.filter((d) => d.id !== id));
        setEraseHoverId(null);
        setSelectedId((prev) => (prev === id ? null : prev));
        requestRedraw();
      }
      return;
    }
    if (t === "hline") {
      pushUndo();
      setDrawings((prev) => [...prev, { id: newId(), type: "hline", price: pt.p }]);
      if (!stayRef.current) setTool("none");
      return;
    }
    if (t === "text") {
      setTextEditor({ id: null, l: pt.l, p: pt.p, value: "" });
      if (!stayRef.current) setTool("none");
      return;
    }
    const draft = draftRef.current;
    if (!draft) {
      draftRef.current = { type: t, a: pt };
      requestRedraw();
      return;
    }
    pushUndo();
    setDrawings((prev) => [...prev, { id: newId(), type: draft.type, a: draft.a, b: pt }]);
    draftRef.current = null;
    if (!stayRef.current) setTool("none");
    requestRedraw();
  };

  const tfLabel = TIMEFRAMES.find((t) => t.key === tf)?.label ?? tf;
  // 指针策略：绘制/删除工具激活或悬停/拖拽画线时画布接管指针，其余情况放行给图表（平移/缩放/十字线）
  const pointerActive = tool !== "none" || hover != null || drag != null;
  const cursor =
    drag != null
      ? "grabbing"
      : hover != null
      ? "move"
      : tool === "erase"
      ? eraseHoverId != null
        ? "pointer"
        : "crosshair"
      : tool !== "none"
      ? "crosshair"
      : "default";

  return (
    <div ref={boxRef} className="chart-box">
      <div ref={chartDivRef} className="chart-inner" />
      <canvas
        ref={canvasRef}
        className="chart-canvas"
        style={{ pointerEvents: pointerActive ? "auto" : "none", cursor }}
        onMouseMove={onCanvasMouseMove}
        onMouseDown={onCanvasMouseDown}
        onMouseLeave={onCanvasMouseLeave}
        onClick={onCanvasClick}
        onDoubleClick={onCanvasDoubleClick}
        onContextMenu={onCanvasContextMenu}
      />

      {ov.ohlcLegend && legend && (
        <div className="chart-legend" aria-hidden>
          <div className="legend-row">
            <span className="lg-name">SPY 5m{tf !== "5m" ? ` · ${tfLabel}` : ""}</span>
            <span className="lg-item">
              <i>开</i>
              <b className={legend.up ? "cl-up" : "cl-down"}>{legend.open.toFixed(2)}</b>
            </span>
            <span className="lg-item">
              <i>高</i>
              <b className={legend.up ? "cl-up" : "cl-down"}>{legend.high.toFixed(2)}</b>
            </span>
            <span className="lg-item">
              <i>低</i>
              <b className={legend.up ? "cl-up" : "cl-down"}>{legend.low.toFixed(2)}</b>
            </span>
            <span className="lg-item">
              <i>收</i>
              <b className={legend.up ? "cl-up" : "cl-down"}>{legend.close.toFixed(2)}</b>
            </span>
            <b className={legend.up ? "cl-up" : "cl-down"}>
              {legend.chg >= 0 ? "+" : ""}
              {legend.chg.toFixed(2)}（{legend.pct >= 0 ? "+" : ""}
              {legend.pct.toFixed(2)}%）
            </b>
          </div>
          <div className="legend-row lg-emas">
            {ov.ema5 && legend.e5 != null && (
              <span className="lg-ema" style={{ color: "#f0b90b" }}>
                EMA20 <b>{legend.e5.toFixed(2)}</b>
              </span>
            )}
            {tf === "5m" && ov.ema15 && legend.e15 != null && (
              <span className="lg-ema" style={{ color: "#4da3ff" }}>
                15m EMA20 <b>{legend.e15.toFixed(2)}</b>
              </span>
            )}
            {tf === "5m" && ov.ema60 && legend.e60 != null && (
              <span className="lg-ema" style={{ color: "#9a86c9" }}>
                60m EMA20 <b>{legend.e60.toFixed(2)}</b>
              </span>
            )}
            {tf !== "5m" && (
              <span className="lg-note">
                {tfLabel} 共 {agg.bars.length} 根 · 大周期历史长度由会话「预热天数」决定（会话设置里最多 60 天）
              </span>
            )}
          </div>
        </div>
      )}

      {/* 周期切换：左上角独立小条（显示控制，与画线工具分离） */}
      <div className="tf-switch">
        {TIMEFRAMES.map((t) => (
          <button
            key={t.key}
            className={`tf-btn ${tf === t.key ? "active" : ""}`}
            onClick={() => changeTf(t.key)}
            title={
              ({
                "5m": "5 分钟（回放主周期）",
                "15m": "15 分钟（Brooks 常用高周期）",
                "60m": "60 分钟（找支撑阻力 / 相似形态）",
                "4h": "4 小时（大周期支撑阻力，09:30 开盘对齐）",
                "1d": "日线（大级别支撑阻力）",
                "1w": "周线（最大级别趋势与形态）",
              } as Record<string, string>)[t.key] ?? t.label
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 左侧竖排工具栏（TradingView 式分组；新增工具 = 新增一组或往组里加按钮） */}
      <div className="chart-toolbar">
        <div className="ct-group" data-label="模式">
          <button
            className={`draw-btn ${magnet ? "active" : ""}`}
            onClick={() => setMagnet((m) => !m)}
            title="磁吸模式：锚点自动吸附 K 线开/高/低/收（按住 Ctrl 临时关闭）· 快捷键 G"
          >
            🧲
          </button>
          <button
            className={`draw-btn ${stayMode ? "active" : ""}`}
            onClick={() => setStayMode((s) => !s)}
            title="连续画图：画完一条后保持工具激活，可连续绘制多条（快捷键 S）"
          >
            ✏️
          </button>
          <button
            className={`draw-btn ${hideDrawings ? "active" : ""}`}
            onClick={() => setHideDrawings((v) => !v)}
            disabled={drawings.length === 0}
            title={`裸图模式：一键隐藏全部画线（快捷键 H）· 当前 ${drawings.length} 条`}
          >
            👁
          </button>
        </div>
        <div className="ct-group" data-label="画线">
          {TOOL_GROUPS.map((g) => {
            const activeTool = g.tools.includes(tool) ? tool : null;
            const meta = activeTool ? TOOL_BY_KEY[activeTool] : null;
            return (
              <div className="ct-slot" key={g.id}>
                <button
                  className={`draw-btn ${activeTool ? "active" : ""}`}
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={() => setOpenGroup(openGroup === g.id ? null : g.id)}
                  title={meta ? `${g.label} · 当前：${meta.name}` : `${g.label}（点击展开同族工具）`}
                >
                  {meta ? meta.icon : g.fallbackIcon}
                  <span className="flyout-caret" />
                </button>
                {openGroup === g.id && (
                  <div className="ct-flyout" onMouseDown={(e) => e.stopPropagation()}>
                    {g.tools.map((tk) => (
                      <button
                        key={tk}
                        className={`ct-flyout-item ${tool === tk ? "active" : ""}`}
                        title={TOOL_BY_KEY[tk].title}
                        onClick={() => {
                          setTool(tool === tk ? "none" : tk);
                          setOpenGroup(null);
                        }}
                      >
                        <span className="ct-flyout-icon">{TOOL_BY_KEY[tk].icon}</span>
                        <span className="ct-flyout-name">{TOOL_BY_KEY[tk].name}</span>
                        {hotkeyOf(tk) && <span className="ct-flyout-key">{hotkeyOf(tk)}</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <div className="ct-group" data-label="编辑">
          <button className="draw-btn" onClick={undo} disabled={histLen.undo === 0} title={`撤销（Ctrl+Z）· ${histLen.undo} 步`}>
            ↩
          </button>
          <button className="draw-btn" onClick={redo} disabled={histLen.redo === 0} title={`重做（Ctrl+Y）· ${histLen.redo} 步`}>
            ↪
          </button>
          <button className={`draw-btn ${tool === "erase" ? "active" : ""}`} onClick={() => setTool(tool === "erase" ? "none" : "erase")} title="删除画线工具：点击要删除的线条">
            ⌫
          </button>
          <button className="draw-btn danger" onClick={clearDrawings} title="清空当前会话全部画线">
            🗑️
          </button>
        </div>
      </div>
      {tool !== "none" && (
        <div className="draw-hint">
          {TOOL_HINTS[tool]}
          {tool !== "erase" && tool !== "text" && (
            <>
              {" · "}
              {magnet ? "🧲磁吸开（按住Ctrl临时关）" : "🧲磁吸关"}
              {" · "}
              {stayMode ? "✏️连续开（画完不退出，S键关）" : "✏️连续关（画完退出，S键开）"}
              {" · G/S 切换"}
            </>
          )}
        </div>
      )}
      {tool === "none" && !settingsId && drawings.length > 0 && (
        <div className="draw-hint">快捷键 1-8 切换工具；单击选中（Del 删除），双击设置；右键画线：设置 / 克隆 / 锁定 / 删除；H 裸图对比</div>
      )}

      {textEditor && (
        <div className="chart-box text-editor-layer">
          <input
            className="text-editor"
            autoFocus
            value={textEditor.value}
            placeholder="输入标注文字（回车确认，Esc 取消，空=取消）"
            style={{ left: xOf5m(textEditor.l) ?? 0, top: yOfPrice(textEditor.p) ?? 0 }}
            onChange={(e) => setTextEditor((p) => (p ? { ...p, value: e.target.value } : p))}
            onBlur={commitTextEditor}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commitTextEditor();
              } else if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
                cancelTextEditor();
              }
            }}
          />
        </div>
      )}

      {ctxMenu && ctxDrawing && (
        <div
          className="ctx-menu"
          style={{ left: ctxMenu.x, top: ctxMenu.y }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {ctxDrawing.type !== "text" && (
            <button onClick={() => { openSettings(ctxMenu.id); setCtxMenu(null); }}>⚙ 设置…</button>
          )}
          {ctxDrawing.type === "text" && (
            <button
              disabled={ctxDrawing.locked}
              onClick={() => {
                setTextEditor({ id: ctxDrawing.id, l: ctxDrawing.l, p: ctxDrawing.p, value: ctxDrawing.text });
                setCtxMenu(null);
              }}
            >
              ✎ 编辑文字…
            </button>
          )}
          <button onClick={() => { cloneDrawing(ctxMenu.id); setCtxMenu(null); }}>⧉ 克隆</button>
          <button onClick={() => { toggleLockDrawing(ctxMenu.id); setCtxMenu(null); }}>
            {ctxDrawing.locked ? "🔓 解锁" : "🔒 锁定"}
          </button>
          <button
            className="danger"
            onClick={() => { deleteDrawingById(ctxMenu.id); setCtxMenu(null); }}
          >
            🗑 删除
          </button>
        </div>
      )}

      {settingsId &&
        settingsDraft &&
        (() => {
          const d = drawings.find((x) => x.id === settingsId);
          if (!d) return null;
          const patch = (fn: (p: SettingsDraft) => SettingsDraft) => setSettingsDraft((p) => (p ? fn(p) : p));
          const title =
            d.type === "fib"
              ? "斐波那契回撤 · 设置"
              : d.type === "pos"
              ? "盈亏比仓位 · 设置"
              : d.type === "hline"
              ? "水平线 · 设置"
              : "画线 · 设置";
          return (
            <div className="draw-settings">
              <div className="draw-settings-head">
                <span>{title}</span>
                <button className="ds-close" onClick={closeSettings} aria-label="关闭">
                  ✕
                </button>
              </div>
              <div className="draw-settings-body">
                <div className="ds-row">
                  <span className="ds-label">颜色</span>
                  <span
                    className={`ds-swatch ${!settingsDraft.color ? "on" : ""}`}
                    style={{ background: DRAW_COLORS[d.type] }}
                    onClick={() => patch((p) => ({ ...p, color: undefined }))}
                    title="默认色"
                  />
                  {LEVEL_PALETTE.map((c) => (
                    <span
                      key={c}
                      className={`ds-swatch ${settingsDraft.color === c ? "on" : ""}`}
                      style={{ background: c }}
                      onClick={() => patch((p) => ({ ...p, color: c }))}
                    />
                  ))}
                </div>
                <div className="ds-row">
                  <span className="ds-label">锁定</span>
                  <input
                    type="checkbox"
                    checked={!!settingsDraft.locked}
                    onChange={(e) => patch((p) => ({ ...p, locked: e.target.checked }))}
                  />
                  <span className="ds-hint">锁定后不可拖动/擦除，防误碰</span>
                </div>

                {d.type === "hline" && (
                  <div className="ds-row">
                    <span className="ds-label">价位</span>
                    <input
                      type="number"
                      step="0.01"
                      value={settingsDraft.price ?? 0}
                      onChange={(e) => patch((p) => ({ ...p, price: Number(e.target.value) }))}
                    />
                  </div>
                )}

                {d.type === "fib" && settingsDraft.levels && (
                  <>
                    <div className="ds-row ds-head-row">
                      <span>显示</span>
                      <span>比例</span>
                      <span>价位</span>
                      <span />
                    </div>
                    <div className="ds-levels">
                      {settingsDraft.levels.map((lv, i) => {
                        const price = d.b.p + (d.a.p - d.b.p) * lv.r;
                        return (
                          <div className="ds-level-row" key={i}>
                            <input
                              type="checkbox"
                              checked={lv.on}
                              onChange={(e) =>
                                patch((p) => ({
                                  ...p,
                                  levels: (p.levels ?? []).map((x, j) => (j === i ? { ...x, on: e.target.checked } : x)),
                                }))
                              }
                            />
                            <input
                              type="number"
                              step="0.001"
                              value={lv.r}
                              onChange={(e) =>
                                patch((p) => ({
                                  ...p,
                                  levels: (p.levels ?? []).map((x, j) => (j === i ? { ...x, r: Number(e.target.value) } : x)),
                                }))
                              }
                            />
                            <span className="ds-price">{Number.isFinite(price) ? price.toFixed(2) : "—"}</span>
                            <button
                              className="ds-remove"
                              title="删除该水平"
                              onClick={() => patch((p) => ({ ...p, levels: (p.levels ?? []).filter((_, j) => j !== i) }))}
                            >
                              ✕
                            </button>
                          </div>
                        );
                      })}
                    </div>
                    <div className="ds-inline-actions">
                      <button
                        className="small ghost"
                        onClick={() => patch((p) => ({ ...p, levels: [...(p.levels ?? []), { r: 0, on: true }] }))}
                      >
                        + 添加水平
                      </button>
                      <button
                        className="small ghost"
                        onClick={() => patch((p) => ({ ...p, levels: DEFAULT_FIB_LEVELS.map((lv) => ({ ...lv })) }))}
                      >
                        恢复默认
                      </button>
                    </div>
                  </>
                )}

                {d.type === "pos" && settingsDraft.targets && (
                  <>
                    <div className="ds-row">
                      <span className="ds-label">方向</span>
                      <b>{d.b.p < d.a.p ? "做多" : "做空"}</b>
                      <span className="ds-hint">1R = {Math.abs(d.a.p - d.b.p).toFixed(2)}</span>
                    </div>
                    <div className="ds-row ds-head-row">
                      <span>目标 R（盈亏比）</span>
                      <span>价位</span>
                      <span />
                    </div>
                    <div className="ds-levels">
                      {settingsDraft.targets.map((r, i) => {
                        const price = d.a.p + (d.b.p < d.a.p ? 1 : -1) * Math.abs(d.a.p - d.b.p) * r;
                        return (
                          <div className="ds-level-row pos" key={i}>
                            <input
                              type="number"
                              step="0.1"
                              value={r}
                              onChange={(e) =>
                                patch((p) => ({
                                  ...p,
                                  targets: (p.targets ?? []).map((x, j) => (j === i ? Number(e.target.value) : x)),
                                }))
                              }
                            />
                            <span className="ds-price">{Number.isFinite(price) ? price.toFixed(2) : "—"}</span>
                            <button
                              className="ds-remove"
                              title="删除该目标"
                              onClick={() => patch((p) => ({ ...p, targets: (p.targets ?? []).filter((_, j) => j !== i) }))}
                            >
                              ✕
                            </button>
                          </div>
                        );
                      })}
                    </div>
                    <div className="ds-inline-actions">
                      <button
                        className="small ghost"
                        onClick={() =>
                          patch((p) => {
                            const ts = p.targets ?? [];
                            const next = ts.length ? Math.max(...ts) + 1 : 1;
                            return { ...p, targets: [...ts, next] };
                          })
                        }
                      >
                        + 添加目标 R
                      </button>
                      <button className="small ghost" onClick={() => patch((p) => ({ ...p, targets: [...DEFAULT_POS_TARGETS] }))}>
                        恢复默认
                      </button>
                    </div>
                  </>
                )}
              </div>
              <div className="ds-footer">
                <button className="ghost small" onClick={closeSettings}>
                  取消
                </button>
                <button className="primary small" onClick={applySettings}>
                  确认
                </button>
              </div>
            </div>
          );
        })()}
    </div>
  );
}
