/**
 * 大周期聚合（纯前端、无前视）。
 *
 * 输入是服务端已裁剪到 cursor 的 5m bars（组件契约：永不出现 cursor 后数据），
 * 聚合只是对可见数据做分组压缩，不引入任何未来窗口。
 * 分组边界按美东时间（RTH 数据 09:30 开盘）：
 *   15m → 09:30/09:45/10:00…；60m → 09/10/11… 点位；1d → 美东日期。
 *
 * EMA20 在大周期视图下由客户端对聚合收盘价等价重算（输入仍只有 cursor 内数据）。
 */

import type { Bar } from "../api/client";

export type Timeframe = "5m" | "15m" | "60m" | "4h" | "1d" | "1w";

export const TIMEFRAMES: Array<{ key: Timeframe; label: string }> = [
  { key: "5m", label: "5分" },
  { key: "15m", label: "15分" },
  { key: "60m", label: "60分" },
  { key: "4h", label: "4小时" },
  { key: "1d", label: "日线" },
  { key: "1w", label: "周线" },
];

export interface AggBar {
  /** 聚合 bar 首根 5m bar 的 ts_open_utc（秒）——作为 lightweight-charts 的时间键 */
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

/** 5m 逻辑索引 → 聚合组的映射（画线锚点换算用） */
export interface AggGeometry {
  /** 每个聚合组的 5m 起始索引与包含根数 */
  groups: Array<{ start: number; count: number }>;
  /** 5m 索引 → 聚合组索引 */
  indexOf5m: number[];
}

export interface AggregatedSeries {
  tf: Timeframe;
  bars: AggBar[];
  ema20: (number | null)[];
  geom: AggGeometry;
  /** 5m bar 时间（秒）→ 所属聚合 bar 时间（秒）；5m 视图下原样返回 */
  snapTime: (t5m: number) => number;
}

const ET_TZ = "America/New_York";
const dateFmt = new Intl.DateTimeFormat("en-CA", {
  timeZone: ET_TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const hourFmt = new Intl.DateTimeFormat("en-GB", { timeZone: ET_TZ, hour: "2-digit", hour12: false });
const minuteFmt = new Intl.DateTimeFormat("en-GB", { timeZone: ET_TZ, minute: "2-digit" });

/** 标准 EMA（SMA 种子）：与主流行情软件一致；前 period-1 根为 null */
export function computeEma(closes: number[], period = 20): (number | null)[] {
  const n = closes.length;
  const out: (number | null)[] = new Array(n).fill(null);
  if (n === 0) return out;
  const k = 2 / (period + 1);
  let seed = 0;
  for (let i = 0; i < n; i++) {
    if (i < period - 1) {
      seed += closes[i];
      continue;
    }
    if (i === period - 1) {
      seed = (seed + closes[i]) / period;
      out[i] = seed;
      continue;
    }
    seed = closes[i] * k + seed * (1 - k);
    out[i] = seed;
  }
  return out;
}

export function aggregateBars(bars: Bar[], tf: Timeframe): AggregatedSeries {
  const raw = bars.map((b) => ({
    time: Math.round(Date.parse(b.ts_open_utc) / 1000),
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
  }));

  if (tf === "5m") {
    return {
      tf,
      bars: raw,
      ema20: computeEma(raw.map((b) => b.close)),
      geom: {
        groups: raw.map((_, i) => ({ start: i, count: 1 })),
        indexOf5m: raw.map((_, i) => i),
      },
      snapTime: (t) => t,
    };
  }

  const keyOf = (sec: number): string => {
    const d = new Date(sec * 1000);
    const day = dateFmt.format(d);
    if (tf === "1d") return day;
    if (tf === "1w") {
      // ET 日历周（周一开始）：由 ET 日期反推所在周的周一
      const [y, m, dd] = day.split("-").map(Number);
      const t = Date.UTC(y, m - 1, dd);
      const dow = new Date(t).getUTCDay(); // 0=周日
      const monday = new Date(t - ((dow + 6) % 7) * 86400000);
      return `W${monday.getUTCFullYear()}-${String(monday.getUTCMonth() + 1).padStart(2, "0")}-${String(
        monday.getUTCDate(),
      ).padStart(2, "0")}`;
    }
    if (tf === "4h") {
      // 4 小时桶从 09:30 (ET) 开盘对齐：09:30-13:30 / 13:30-16:00
      const mins = Number(hourFmt.format(d)) * 60 + Number(minuteFmt.format(d));
      return `${day}#${Math.floor((mins - 570) / 240)}`;
    }
    const h = hourFmt.format(d);
    if (tf === "60m") return `${day} ${h}`;
    const m = Math.floor(Number(minuteFmt.format(d)) / 15);
    return `${day} ${h}·${m}`;
  };

  const aggBars: AggBar[] = [];
  const groups: Array<{ start: number; count: number }> = [];
  const indexOf5m: number[] = [];
  const keyToIdx = new Map<string, number>();

  raw.forEach((b, i) => {
    const k = keyOf(b.time);
    let gi = keyToIdx.get(k);
    if (gi === undefined) {
      gi = aggBars.length;
      keyToIdx.set(k, gi);
      aggBars.push({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
      groups.push({ start: i, count: 1 });
    } else {
      const a = aggBars[gi];
      a.high = Math.max(a.high, b.high);
      a.low = Math.min(a.low, b.low);
      a.close = b.close;
      groups[gi].count += 1;
    }
    indexOf5m.push(gi);
  });

  // 5m 时间 → 聚合 bar 时间（二分；聚合时间升序且唯一）
  const times = aggBars.map((b) => b.time);
  const snapTime = (t5m: number): number => {
    if (times.length === 0) return t5m;
    let lo = 0;
    let hi = times.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (times[mid] === t5m) return times[mid];
      if (times[mid] < t5m) lo = mid + 1;
      else hi = mid - 1;
    }
    return times[Math.max(0, Math.min(times.length - 1, hi))];
  };

  return { tf, bars: aggBars, ema20: computeEma(aggBars.map((b) => b.close)), geom: { groups, indexOf5m }, snapTime };
}
