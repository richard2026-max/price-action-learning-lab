import { describe, expect, it } from "vitest";
import type { Bar, KeyLevels } from "@price-action/domain";
import {
  calculateKeyLevelGeometry,
  calculateOhlcGeometry,
  calculatePriceRange,
  indexToX,
  keyLevelPrices,
  priceToY,
  sliceBarWindow,
} from "../src";

const bar = (open: number, high: number, low: number, close: number): Bar => ({
  ts_open_utc: "2024-07-15T13:30:00Z",
  ts_close_utc: "2024-07-15T13:35:00Z",
  open,
  high,
  low,
  close,
  volume: 1000,
  session: "regular",
  is_complete: true,
});

const levels: KeyLevels = {
  prev_day_open: 99,
  prev_day_high: 103,
  prev_day_low: 97,
  prev_day_close: 101,
  today_open: 100,
  premarket_high: null,
  premarket_low: 98,
  gap: 1,
};

describe("chart geometry", () => {
  it("calculates a padded price range from bars and extra prices", () => {
    expect(calculatePriceRange([bar(100, 102, 99, 101)], { paddingRatio: 0, extraPrices: [98] })).toEqual({
      min: 98,
      max: 102,
    });
    expect(calculatePriceRange([], { extraPrices: [] })).toBeNull();
    expect(calculatePriceRange([bar(100, 100, 100, 100)], { paddingRatio: 0, minimumSpan: 2 })).toEqual({
      min: 99,
      max: 101,
    });
  });

  it("slices a cursor-inclusive visible window", () => {
    expect(sliceBarWindow([0, 1, 2, 3, 4], 3, 3)).toEqual([1, 2, 3]);
    expect(sliceBarWindow([0, 1], 99, 5)).toEqual([0, 1]);
    expect(sliceBarWindow([0, 1], -1, 5)).toEqual([]);
  });

  it("maps prices and indices into viewport coordinates", () => {
    expect(priceToY(110, { min: 100, max: 110 }, 20, 200)).toBe(20);
    expect(priceToY(100, { min: 100, max: 110 }, 20, 200)).toBe(220);
    expect(priceToY(120, { min: 100, max: 110 }, 20, 200, true)).toBe(20);
    expect(indexToX(0, 4, 10, 400)).toBe(60);
    expect(indexToX(3, 4, 10, 400)).toBe(360);
  });

  it("produces wick and body geometry for Canvas rendering", () => {
    const geometry = calculateOhlcGeometry(
      bar(100, 104, 98, 102),
      0,
      2,
      { left: 0, top: 0, width: 200, height: 300 },
      { min: 98, max: 104 },
    );
    expect(geometry.direction).toBe("up");
    expect(geometry.centerX).toBe(50);
    expect(geometry.wick.from).toEqual({ x: 50, y: 0 });
    expect(geometry.wick.to).toEqual({ x: 50, y: 300 });
    expect(geometry.body.width).toBe(64);
    expect(geometry.body.height).toBe(100);
  });

  it("creates horizontal geometry only for price-like key levels", () => {
    expect(keyLevelPrices(levels)).toEqual([99, 103, 97, 101, 100, 98]);
    const geometry = calculateKeyLevelGeometry(
      levels,
      { left: 10, top: 20, width: 300, height: 200 },
      { min: 95, max: 105 },
    );
    expect(geometry).toHaveLength(6);
    expect(geometry.find((level) => level.id === "today_open")?.line).toEqual({
      from: { x: 10, y: 120 },
      to: { x: 310, y: 120 },
    });
  });
});
