export interface PriceFormatOptions {
  decimals?: number;
  useGrouping?: boolean;
  fallback?: string;
}

export function formatPrice(value: number | null | undefined, options: PriceFormatOptions = {}): string {
  const { decimals = 2, useGrouping = false, fallback = "—" } = options;
  if (value === null || value === undefined || !Number.isFinite(value)) return fallback;
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 20) {
    throw new RangeError("decimals must be an integer between 0 and 20");
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    useGrouping,
  }).format(value);
}

export interface EasternTimeFormatOptions {
  includeDate?: boolean;
  includeSeconds?: boolean;
  hour12?: boolean;
  fallback?: string;
}

const part = (parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes): string =>
  parts.find((candidate) => candidate.type === type)?.value ?? "";

export function formatEasternTime(
  value: string | number | Date | null | undefined,
  options: EasternTimeFormatOptions = {},
): string {
  const { includeDate = false, includeSeconds = false, hour12 = false, fallback = "—" } = options;
  if (value === null || value === undefined) return fallback;
  const date = value instanceof Date ? value : new Date(value);
  if (!Number.isFinite(date.getTime())) return fallback;

  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: includeDate ? "numeric" : undefined,
    month: includeDate ? "2-digit" : undefined,
    day: includeDate ? "2-digit" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    second: includeSeconds ? "2-digit" : undefined,
    hour12,
    hourCycle: hour12 ? undefined : "h23",
  }).formatToParts(date);

  const time = `${part(parts, "hour")}:${part(parts, "minute")}${includeSeconds ? `:${part(parts, "second")}` : ""}${hour12 ? ` ${part(parts, "dayPeriod")}` : ""}`;
  if (!includeDate) return time;
  return `${part(parts, "year")}-${part(parts, "month")}-${part(parts, "day")} ${time}`;
}
