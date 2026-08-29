import type { Bar, KeyLevels } from "@price-action/domain";

export interface PriceRange {
  min: number;
  max: number;
}

export interface ChartViewport {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface PriceRangeOptions {
  paddingRatio?: number;
  minimumSpan?: number;
  extraPrices?: readonly (number | null | undefined)[];
}

export interface Point {
  x: number;
  y: number;
}

export interface Rect extends Point {
  width: number;
  height: number;
}

export interface LineSegment {
  from: Point;
  to: Point;
}

export type CandleDirection = "up" | "down" | "doji";

export interface OhlcGeometry {
  direction: CandleDirection;
  centerX: number;
  wick: LineSegment;
  body: Rect;
  openY: number;
  closeY: number;
  highY: number;
  lowY: number;
}

export type KeyLevelId = Exclude<keyof KeyLevels, "gap">;

export interface KeyLevelGeometry {
  id: KeyLevelId;
  label: string;
  price: number;
  y: number;
  line: LineSegment;
}

const LEVEL_LABELS: Readonly<Record<KeyLevelId, string>> = {
  prev_day_open: "PDO",
  prev_day_high: "PDH",
  prev_day_low: "PDL",
  prev_day_close: "PDC",
  today_open: "OPEN",
  premarket_high: "PRE-H",
  premarket_low: "PRE-L",
};

const assertPositive = (value: number, name: string): void => {
  if (!Number.isFinite(value) || value <= 0) throw new RangeError(`${name} must be a positive finite number`);
};

export function calculatePriceRange(
  bars: readonly Bar[],
  options: PriceRangeOptions = {},
): PriceRange | null {
  const { paddingRatio = 0.05, minimumSpan = 0.01, extraPrices = [] } = options;
  if (!Number.isFinite(paddingRatio) || paddingRatio < 0) {
    throw new RangeError("paddingRatio must be a non-negative finite number");
  }
  assertPositive(minimumSpan, "minimumSpan");

  const prices: number[] = [];
  for (const bar of bars) {
    if (Number.isFinite(bar.low)) prices.push(bar.low);
    if (Number.isFinite(bar.high)) prices.push(bar.high);
  }
  for (const price of extraPrices) {
    if (typeof price === "number" && Number.isFinite(price)) prices.push(price);
  }
  if (prices.length === 0) return null;

  const rawMin = Math.min(...prices);
  const rawMax = Math.max(...prices);
  const center = (rawMin + rawMax) / 2;
  const span = Math.max(rawMax - rawMin, minimumSpan);
  const paddedSpan = span * (1 + paddingRatio * 2);
  return { min: center - paddedSpan / 2, max: center + paddedSpan / 2 };
}

export function sliceBarWindow<T>(bars: readonly T[], endIndex: number, windowSize: number): T[] {
  if (!Number.isInteger(endIndex)) throw new RangeError("endIndex must be an integer");
  if (!Number.isInteger(windowSize) || windowSize < 0) {
    throw new RangeError("windowSize must be a non-negative integer");
  }
  if (bars.length === 0 || windowSize === 0 || endIndex < 0) return [];
  const endExclusive = Math.min(endIndex + 1, bars.length);
  const start = Math.max(0, endExclusive - windowSize);
  return bars.slice(start, endExclusive);
}

export function priceToY(
  price: number,
  range: PriceRange,
  top: number,
  height: number,
  clamp = false,
): number {
  assertPositive(height, "height");
  if (!Number.isFinite(price)) throw new RangeError("price must be finite");
  if (!Number.isFinite(range.min) || !Number.isFinite(range.max) || range.max <= range.min) {
    throw new RangeError("range.max must be greater than range.min");
  }
  const ratio = (range.max - price) / (range.max - range.min);
  const normalized = clamp ? Math.min(1, Math.max(0, ratio)) : ratio;
  return top + normalized * height;
}

export function indexToX(index: number, count: number, left: number, width: number): number {
  if (!Number.isInteger(index) || index < 0 || index >= count) {
    throw new RangeError("index must identify a visible bar");
  }
  if (!Number.isInteger(count) || count <= 0) throw new RangeError("count must be a positive integer");
  assertPositive(width, "width");
  return left + ((index + 0.5) / count) * width;
}

export function calculateOhlcGeometry(
  bar: Pick<Bar, "open" | "high" | "low" | "close">,
  index: number,
  count: number,
  viewport: ChartViewport,
  range: PriceRange,
  bodyWidthRatio = 0.64,
  minimumBodyHeight = 1,
): OhlcGeometry {
  if (!(bar.low <= Math.min(bar.open, bar.close) && Math.max(bar.open, bar.close) <= bar.high)) {
    throw new RangeError("bar must satisfy low <= open/close <= high");
  }
  if (!Number.isFinite(bodyWidthRatio) || bodyWidthRatio <= 0 || bodyWidthRatio > 1) {
    throw new RangeError("bodyWidthRatio must be in (0, 1]");
  }
  if (!Number.isFinite(minimumBodyHeight) || minimumBodyHeight < 0) {
    throw new RangeError("minimumBodyHeight must be non-negative");
  }

  const centerX = indexToX(index, count, viewport.left, viewport.width);
  const slotWidth = viewport.width / count;
  const bodyWidth = slotWidth * bodyWidthRatio;
  const openY = priceToY(bar.open, range, viewport.top, viewport.height);
  const closeY = priceToY(bar.close, range, viewport.top, viewport.height);
  const highY = priceToY(bar.high, range, viewport.top, viewport.height);
  const lowY = priceToY(bar.low, range, viewport.top, viewport.height);
  const naturalHeight = Math.abs(closeY - openY);
  const bodyHeight = Math.max(naturalHeight, minimumBodyHeight);
  const bodyCenterY = (openY + closeY) / 2;

  return {
    direction: bar.close > bar.open ? "up" : bar.close < bar.open ? "down" : "doji",
    centerX,
    wick: { from: { x: centerX, y: highY }, to: { x: centerX, y: lowY } },
    body: {
      x: centerX - bodyWidth / 2,
      y: bodyCenterY - bodyHeight / 2,
      width: bodyWidth,
      height: bodyHeight,
    },
    openY,
    closeY,
    highY,
    lowY,
  };
}

export function keyLevelPrices(levels: KeyLevels | null | undefined): number[] {
  if (!levels) return [];
  return (Object.keys(LEVEL_LABELS) as KeyLevelId[])
    .map((id) => levels[id])
    .filter((price): price is number => typeof price === "number" && Number.isFinite(price));
}

export function calculateKeyLevelGeometry(
  levels: KeyLevels | null | undefined,
  viewport: ChartViewport,
  range: PriceRange,
  clamp = false,
): KeyLevelGeometry[] {
  if (!levels) return [];
  return (Object.keys(LEVEL_LABELS) as KeyLevelId[]).flatMap((id) => {
    const price = levels[id];
    if (typeof price !== "number" || !Number.isFinite(price)) return [];
    const y = priceToY(price, range, viewport.top, viewport.height, clamp);
    return [{
      id,
      label: LEVEL_LABELS[id],
      price,
      y,
      line: {
        from: { x: viewport.left, y },
        to: { x: viewport.left + viewport.width, y },
      },
    }];
  });
}
