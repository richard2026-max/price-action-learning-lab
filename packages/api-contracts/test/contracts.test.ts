import { describe, expect, expectTypeOf, it } from "vitest";
import type {
  Bar,
  JudgmentPayload,
  Provider,
  SessionDetail,
  SubmitJudgmentRequest,
} from "../src";

describe("replay contracts", () => {
  it("keeps judgment request aligned with the domain payload", () => {
    expectTypeOf<SubmitJudgmentRequest>().toEqualTypeOf<JudgmentPayload>();
    expectTypeOf<SessionDetail["bars"]>().toEqualTypeOf<Bar[]>();
    expectTypeOf<SessionDetail["info"]["provider"]>().toEqualTypeOf<Provider>();
  });

  it("represents a replay session without framework dependencies", () => {
    const detail: SessionDetail = {
      session_id: "session-1",
      bars: [],
      ema20: [],
      key_levels: {
        prev_day_open: null,
        prev_day_high: null,
        prev_day_low: null,
        prev_day_close: null,
        today_open: 500,
        premarket_high: null,
        premarket_low: null,
        gap: null,
      },
      info: {
        day: "2024-07-15",
        provider: "synthetic",
        session_name: "regular",
        bar_index: 0,
        context_bar_count: 0,
        market_time_utc: "2024-07-15T13:30:00Z",
        session_close_utc: null,
        is_completed: false,
        mode: "free",
        sampling_mode: "sequential",
      },
    };
    expect(detail.info.provider).toBe("synthetic");
  });
});
