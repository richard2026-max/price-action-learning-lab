/**
 * Lightweight Charts 封装（v4）。
 *
 * 防前视说明：本组件只渲染服务端返回的 bars（已裁剪到 cursor），
 * autoscale 由图表按已渲染数据自适应——不存在读取未来价格的通道。
 * 20EMA 与关键价位同样来自服务端（EMA 以前日已收盘数据预热）。
 *
 * Issue #1 修复：localization.timeFormatter 显式转为 America/New_York (美东时区)，
 * 保证底部时间轴刻度与状态栏、Brooks 美股日内开盘 09:30 严格对齐。
 */

import { useEffect, useRef } from "react";
import {
  ColorType,
  IChartApi,
  ISeriesApi,
  SeriesMarker,
  Time,
  createChart,
} from "lightweight-charts";
import type { Bar, KeyLevels } from "../api/client";

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
    | "hl"
    | "wedge"
    | "climax"
    | "micro_channel";
}

/** 图表层开关（用户可自主勾选显示/隐藏；由父组件持久化到 localStorage）。 */
export interface ChartOverlays {
  ema5: boolean; // 5m 20 bar EMA（主图基准均线）
  ema15: boolean; // 15m 20 bar EMA（Brooks 近似投影）
  ema60: boolean; // 60m 20 bar EMA（Brooks 近似投影）
  keyLevels: boolean; // PDO/PDH/PDL/PDC/OPEN/PRE-H/PRE-L 关键价位线
  positions: boolean; // 模拟持仓线（入场/止损/目标）
}

/** 模拟持仓的价格标线（入场/止损/目标）。 */
export interface TradeLine {
  price: number;
  color: string;
  title: string;
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
}

const LEVEL_STYLES: Array<{ key: keyof KeyLevels; title: string; color: string }> = [
  { key: "prev_day_open", title: "PDO 前日开", color: "#c98a4b" },
  { key: "prev_day_high", title: "PDH 前日高", color: "#c98a4b" },
  { key: "prev_day_low", title: "PDL 前日低", color: "#c98a4b" },
  { key: "prev_day_close", title: "PDC 前日收", color: "#9a86c9" },
  { key: "today_open", title: "OPEN 开盘", color: "#4da3ff" },
  { key: "premarket_high", title: "PRE-H 盘前高", color: "#5d8a5f" },
  { key: "premarket_low", title: "PRE-L 盘前低", color: "#5d8a5f" },
];

export default function CandleChart({
  bars,
  ema20,
  ema15,
  ema60,
  keyLevels,
  markers,
  overlays,
  tradeLines,
}: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ema15Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ema60Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const priceLinesRef = useRef<ReturnType<ISeriesApi<"Candlestick">["createPriceLine"]>[]>([]);

  useEffect(() => {
    if (!boxRef.current) return;
    const chart = createChart(boxRef.current, {
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
        timeFormatter: (time: Time) =>
          new Intl.DateTimeFormat("en-US", {
            timeZone: "America/New_York",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          }).format(new Date((typeof time === "number" ? time : 0) * 1000)),
      },
      width: boxRef.current.clientWidth,
      height: boxRef.current.clientHeight,
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
      lastValueVisible: false,
      title: "EMA20",
    });
    ema15Ref.current = chart.addLineSeries({
      color: "#4da3ff",
      lineWidth: 1,
      lineStyle: 0, // 实线：15m 20 bar EMA
      priceLineVisible: false,
      lastValueVisible: false,
      title: "15m EMA20",
    });
    ema60Ref.current = chart.addLineSeries({
      color: "#9a86c9",
      lineWidth: 2,
      lineStyle: 2, // 虚线：60m 20 bar EMA（对照 Brooks 课件中的虚线高周期均线）
      priceLineVisible: false,
      lastValueVisible: false,
      title: "60m EMA20",
    });
    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // 数据更新（每次全量 setData；单日 ≤78 根，开销可忽略）
  useEffect(() => {
    const series = candleRef.current;
    if (!series) return;
    const ov = overlays ?? { ema5: true, ema15: true, ema60: true, keyLevels: true, positions: true };
    series.setData(
      bars.map((b) => ({
        time: (Date.parse(b.ts_open_utc) / 1000) as Time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );
    const toPoints = (values: (number | null)[] | undefined) =>
      (values ?? [])
        .map((v, i) => ({
          time: (Date.parse(bars[i].ts_open_utc) / 1000) as Time,
          value: v,
        }))
        .filter((p): p is { time: Time; value: number } => p.value !== null && p.value !== undefined);

    emaRef.current?.setData(ov.ema5 ? toPoints(ema20) : []);
    ema15Ref.current?.setData(ov.ema15 ? toPoints(ema15) : []);
    ema60Ref.current?.setData(ov.ema60 ? toPoints(ema60) : []);
    // 关键价位：先清旧线再画
    const chart = chartRef.current;
    if (chart) {
      for (const pl of priceLinesRef.current) series.removePriceLine(pl);
      priceLinesRef.current = [];
      if (keyLevels && ov.keyLevels) {
        for (const s of LEVEL_STYLES) {
          const v = keyLevels[s.key];
          if (typeof v === "number") {
            priceLinesRef.current.push(
              series.createPriceLine({
                price: v,
                color: s.color,
                lineWidth: 1,
                lineStyle: 2,
                axisLabelVisible: true,
                title: s.title,
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
  }, [bars, ema20, ema15, ema60, keyLevels, overlays, tradeLines]);

  // 候选标记（克制样式；仅在 Predict First 解锁后由父组件传入）
  useEffect(() => {
    const series = candleRef.current;
    if (!series) return;
    const style: Record<ChartMarker["kind"], Pick<SeriesMarker<Time>, "position" | "shape" | "color" | "text">> = {
      inside: { position: "belowBar", shape: "circle", color: "#5a6b7d", text: "" },
      outside: { position: "aboveBar", shape: "circle", color: "#c98a4b", text: "" },
      ii: { position: "aboveBar", shape: "square", color: "#e8c66a", text: "ii" },
      iii: { position: "aboveBar", shape: "square", color: "#e8c66a", text: "iii" },
      ioi: { position: "aboveBar", shape: "square", color: "#e8c66a", text: "ioi" },
      swing_high: { position: "aboveBar", shape: "arrowDown", color: "#4da3ff", text: "SH" },
      swing_low: { position: "belowBar", shape: "arrowUp", color: "#4da3ff", text: "SL" },
      hl: { position: "belowBar", shape: "square", color: "#7ee2a8", text: "" },
      wedge: { position: "aboveBar", shape: "square", color: "#9c27b0", text: "Wedge" },
      climax: { position: "aboveBar", shape: "arrowDown", color: "#ef5350", text: "Climax" },
      micro_channel: { position: "belowBar", shape: "circle", color: "#26a69a", text: "MC" },
    };
    series.setMarkers(
      (markers ?? [])
        .map((m) => ({
          time: (Date.parse(m.time) / 1000) as Time,
          ...style[m.kind],
        }))
        .sort((a, b) => (a.time as number) - (b.time as number)),
    );
  }, [markers]);

  return <div ref={boxRef} className="chart-box" />;
}
