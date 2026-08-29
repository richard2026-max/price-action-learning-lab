import { describe, expect, it } from "vitest";
import {
  assertValidJudgment,
  formatEasternTime,
  formatPrice,
  validateJudgment,
  type JudgmentPayload,
} from "../src";

const trade = (overrides: Partial<JudgmentPayload> = {}): JudgmentPayload => ({
  context_label: "trend_up",
  structure_note: "Second entry after EMA pullback",
  pullback_present: "yes",
  bar_counting_note: "H2",
  considering_trade: true,
  direction: "long",
  reasons: ["EMA support", "H2 signal"],
  entry: 100,
  stop: 99,
  target: 102,
  probability_estimate: "good",
  confidence: "okay",
  ...overrides,
});

describe("validateJudgment", () => {
  it("accepts valid long and short plans", () => {
    expect(validateJudgment(trade()).valid).toBe(true);
    expect(validateJudgment(trade({ direction: "short", entry: 100, stop: 101, target: 98 })).valid).toBe(true);
  });

  it("enforces two distinct non-empty reasons", () => {
    expect(validateJudgment(trade({ reasons: ["EMA support", " "] })).errors[0]?.code).toBe("TWO_REASONS_REQUIRED");
    expect(validateJudgment(trade({ reasons: ["H2", " h2 "] })).errors[0]?.code).toBe("DUPLICATE_REASONS");
  });

  it("enforces entry, stop, and target ordering", () => {
    expect(validateJudgment(trade({ stop: 101 })).errors.some((error) => error.code === "INVALID_LONG_PRICE_ORDER")).toBe(true);
    expect(
      validateJudgment(trade({ direction: "short", stop: 99, target: 98 })).errors.some(
        (error) => error.code === "INVALID_SHORT_PRICE_ORDER",
      ),
    ).toBe(true);
    expect(validateJudgment(trade({ target: null })).errors[0]?.code).toBe("TRADE_PRICES_REQUIRED");
  });

  it("keeps no-trade judgments internally consistent", () => {
    const noTrade = trade({
      considering_trade: false,
      direction: "none",
      reasons: [],
      entry: null,
      stop: null,
      target: null,
    });
    expect(validateJudgment(noTrade).valid).toBe(true);
    expect(validateJudgment({ ...noTrade, entry: 100 }).errors[0]?.code).toBe("NO_TRADE_PRICES_PRESENT");
    expect(() => assertValidJudgment(trade({ reasons: [] }))).toThrow("TWO_REASONS_REQUIRED");
  });
});

describe("formatters", () => {
  it("formats prices deterministically", () => {
    expect(formatPrice(432.1)).toBe("432.10");
    expect(formatPrice(1234.567, { decimals: 1, useGrouping: true })).toBe("1,234.6");
    expect(formatPrice(Number.NaN)).toBe("—");
  });

  it("formats New York time across standard and daylight time", () => {
    expect(formatEasternTime("2024-01-15T14:30:00Z")).toBe("09:30");
    expect(formatEasternTime("2024-07-15T13:30:05Z", { includeDate: true, includeSeconds: true })).toBe(
      "2024-07-15 09:30:05",
    );
    expect(formatEasternTime("not-a-date")).toBe("—");
  });
});
