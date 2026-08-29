import type { JudgmentPayload } from "./types";

export type JudgmentValidationCode =
  | "TRADE_FLAG_DIRECTION_MISMATCH"
  | "TWO_REASONS_REQUIRED"
  | "DUPLICATE_REASONS"
  | "TRADE_PRICES_REQUIRED"
  | "TRADE_PRICES_NOT_FINITE"
  | "INVALID_LONG_PRICE_ORDER"
  | "INVALID_SHORT_PRICE_ORDER"
  | "NO_TRADE_PRICES_PRESENT";

export interface JudgmentValidationError {
  code: JudgmentValidationCode;
  field: "considering_trade" | "direction" | "reasons" | "entry" | "stop" | "target" | "trade_plan";
  message: string;
}

export interface JudgmentValidationResult {
  valid: boolean;
  errors: JudgmentValidationError[];
}

const addError = (
  errors: JudgmentValidationError[],
  code: JudgmentValidationCode,
  field: JudgmentValidationError["field"],
  message: string,
): void => {
  errors.push({ code, field, message });
};

const isFinitePrice = (value: number | null): value is number =>
  typeof value === "number" && Number.isFinite(value);

export function validateJudgment(payload: JudgmentPayload): JudgmentValidationResult {
  const errors: JudgmentValidationError[] = [];
  const isTradeDirection = payload.direction === "long" || payload.direction === "short";

  if (payload.considering_trade !== isTradeDirection) {
    addError(
      errors,
      "TRADE_FLAG_DIRECTION_MISMATCH",
      "considering_trade",
      "considering_trade must be true exactly when direction is long or short.",
    );
  }

  if (!isTradeDirection) {
    if (payload.entry !== null || payload.stop !== null || payload.target !== null) {
      addError(
        errors,
        "NO_TRADE_PRICES_PRESENT",
        "trade_plan",
        "A no-trade judgment must not include entry, stop, or target prices.",
      );
    }
    return { valid: errors.length === 0, errors };
  }

  const reasons = payload.reasons.map((reason) => reason.trim()).filter(Boolean);
  if (reasons.length < 2) {
    addError(errors, "TWO_REASONS_REQUIRED", "reasons", "At least two non-empty reasons are required.");
  } else if (new Set(reasons.map((reason) => reason.toLocaleLowerCase("en-US"))).size < 2) {
    addError(errors, "DUPLICATE_REASONS", "reasons", "The two reasons must be independent and distinct.");
  }

  const { entry, stop, target } = payload;
  if (entry === null || stop === null || target === null) {
    addError(
      errors,
      "TRADE_PRICES_REQUIRED",
      "trade_plan",
      "Entry, stop, and target are all required for a trade judgment.",
    );
    return { valid: false, errors };
  }
  if (!isFinitePrice(entry) || !isFinitePrice(stop) || !isFinitePrice(target)) {
    addError(
      errors,
      "TRADE_PRICES_NOT_FINITE",
      "trade_plan",
      "Entry, stop, and target must be finite numbers.",
    );
    return { valid: false, errors };
  }

  if (payload.direction === "long" && !(stop < entry && entry < target)) {
    addError(
      errors,
      "INVALID_LONG_PRICE_ORDER",
      "trade_plan",
      "A long trade requires stop < entry < target.",
    );
  }
  if (payload.direction === "short" && !(target < entry && entry < stop)) {
    addError(
      errors,
      "INVALID_SHORT_PRICE_ORDER",
      "trade_plan",
      "A short trade requires target < entry < stop.",
    );
  }

  return { valid: errors.length === 0, errors };
}

export function assertValidJudgment(payload: JudgmentPayload): void {
  const result = validateJudgment(payload);
  if (!result.valid) {
    throw new Error(result.errors.map((error) => `${error.code}: ${error.message}`).join("; "));
  }
}

/** 双端统一的中文校验文案；后端 Pydantic 仍是提交时的最终权威。 */
export const judgmentErrorMessages: Record<JudgmentValidationCode, string> = {
  TRADE_FLAG_DIRECTION_MISMATCH: "请选择与交易意图一致的方向",
  TWO_REASONS_REQUIRED: "必须提供至少两个独立的入场理由（Two Reasons Rule）",
  DUPLICATE_REASONS: "两个理由必须彼此独立，不能重复",
  TRADE_PRICES_REQUIRED: "考虑入场交易时，必须明确设定 Entry / Stop / Target",
  TRADE_PRICES_NOT_FINITE: "价格必须是有效数字",
  INVALID_LONG_PRICE_ORDER: "做多交易要求：止损 < 入场 < 目标",
  INVALID_SHORT_PRICE_ORDER: "做空交易要求：目标 < 入场 < 止损",
  NO_TRADE_PRICES_PRESENT: "保持观望时不应保留价格计划",
};

export function firstJudgmentErrorMessage(result: JudgmentValidationResult): string {
  const first = result.errors[0];
  return first ? judgmentErrorMessages[first.code] : "";
}

