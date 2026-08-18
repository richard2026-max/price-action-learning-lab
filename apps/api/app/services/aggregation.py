"""1m → 5m session-aware 聚合（数据合同 §〇）。

关键规则：
- 聚合锚点对齐各 session 开市时间（premarket 04:00 ET / RTH 09:30 ET），**禁止按 UTC 整点切桶**；
- DST 由 zoneinfo 正确处理（ET 墙钟分桶，UTC 时间戳按当日实际偏移换算）；
- 桶不跨 session；
- 缺失分钟：桶仍输出（≥1 根即成桶），is_complete=False；完全无数据的桶缺失并在 manifest 记 missing；
- 禁止静默前向填充。
"""

from __future__ import annotations

from datetime import timedelta

from app.domain.bar import Bar, SessionType, Timeframe
from app.services.calendar import XNYSCalendar

BUCKET_MINUTES = 5


def aggregate_day_1m_to_5m(bars_1m: list[Bar], day, calendar: XNYSCalendar) -> list[Bar]:
    """把某交易日的 1m K线聚合为 5m（按 premarket / RTH 两个 session 分别锚定）。"""
    windows = calendar.sessions_for(day)
    by_session: dict[str, list[Bar]] = {"premarket": [], "rth": []}
    for b in bars_1m:
        for w in windows:
            if w.start_utc <= b.ts_open_utc < w.end_utc:
                by_session[w.session_type].append(b)
                break

    out: list[Bar] = []
    for w in windows:
        session_bars = sorted(by_session[w.session_type], key=lambda b: b.ts_open_utc)
        buckets: dict[int, list[Bar]] = {}
        for b in session_bars:
            minutes_since_open = (b.ts_open_utc - w.start_utc).total_seconds() / 60
            idx = int(minutes_since_open // BUCKET_MINUTES)
            buckets.setdefault(idx, []).append(b)

        expected_minutes = int((w.end_utc - w.start_utc).total_seconds() // 60)
        for idx in sorted(buckets):
            group = buckets[idx]
            anchor = w.start_utc + timedelta(minutes=idx * BUCKET_MINUTES)
            # 桶的期望分钟数（session 末桶可能不足 5 分钟；当前 session 长度均为 5 的倍数，仍保守计算）
            remaining = expected_minutes - idx * BUCKET_MINUTES
            expected_in_bucket = min(BUCKET_MINUTES, remaining)
            first, last = group[0], group[-1]
            out.append(
                Bar(
                    instrument_id=first.instrument_id,
                    timeframe=Timeframe.M5,
                    ts_open_utc=anchor,
                    ts_close_utc=anchor + timedelta(minutes=expected_in_bucket),
                    open=first.open,
                    high=max(b.high for b in group),
                    low=min(b.low for b in group),
                    close=last.close,
                    volume=round(sum(b.volume for b in group), 2),
                    session=SessionType(w.session_type),
                    provider=first.provider,
                    feed=first.feed,
                    data_version=first.data_version,
                    trade_count=sum(b.trade_count or 0 for b in group) or None,
                    is_complete=len(group) == expected_in_bucket,
                )
            )
    return out
