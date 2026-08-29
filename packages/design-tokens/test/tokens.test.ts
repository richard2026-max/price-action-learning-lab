import { describe, expect, it } from "vitest";
import { darkFinanceCssVariables, darkFinanceTokens } from "../src";

describe("dark finance tokens", () => {
  it("uses distinct bullish, bearish, and chart colors", () => {
    expect(darkFinanceTokens.color.market.bull).not.toBe(darkFinanceTokens.color.market.bear);
    expect(darkFinanceTokens.color.background.canvas).toMatch(/^#[0-9A-F]{6}$/i);
    expect(darkFinanceTokens.color.chart.ema20).toBe(darkFinanceTokens.color.accent.gold);
  });

  it("provides platform-neutral CSS variable values", () => {
    expect(darkFinanceCssVariables["--pa-bg-canvas"]).toBe(darkFinanceTokens.color.background.canvas);
    expect(darkFinanceCssVariables["--pa-market-bull"]).toBe(darkFinanceTokens.color.market.bull);
    expect(Object.keys(darkFinanceCssVariables).length).toBeGreaterThan(10);
  });

  it("shares chart geometry defaults with consumers", () => {
    expect(darkFinanceTokens.chart.candleBodyWidthRatio).toBeGreaterThan(0);
    expect(darkFinanceTokens.chart.pricePaddingRatio).toBeGreaterThan(0);
    expect(darkFinanceTokens.chart.keyLevelDash).toEqual([5, 4]);
  });
});
