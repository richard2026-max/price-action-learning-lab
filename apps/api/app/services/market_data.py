"""行情存储：Parquet 分区写入/读取 + manifest + 质量检查。

职责（architecture.md）：Parquet 行情（分区）、manifest（每数据集一份）、缺失/重复明确记录。
禁止静默前向填充缺失K线；重复K线去重并计数。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import polars as pl

from app.domain.bar import Bar, SessionType, Timeframe
from app.domain.instrument import Instrument

SCHEMA_VERSION = "1.0.0"


def _iso(v) -> str | None:
    return v.isoformat() if v is not None else None

_SCHEMA = {
    "ts_open_utc": pl.Datetime("us", "UTC"),
    "ts_close_utc": pl.Datetime("us", "UTC"),
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
    "trade_count": pl.Int64,
    "vwap": pl.Float64,
    "is_complete": pl.Boolean,
    "session": pl.String,
    "provider": pl.String,
    "feed": pl.String,
    "data_version": pl.String,
}


def _bars_to_df(bars: list[Bar]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ts_open_utc": [b.ts_open_utc for b in bars],
            "ts_close_utc": [b.ts_close_utc for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
            "trade_count": [b.trade_count for b in bars],
            "vwap": [b.vwap for b in bars],
            "is_complete": [b.is_complete for b in bars],
            "session": [b.session.value for b in bars],
            "provider": [b.provider for b in bars],
            "feed": [b.feed for b in bars],
            "data_version": [b.data_version for b in bars],
        },
        schema=_SCHEMA,  # type: ignore[arg-type]
    )


def _df_to_bars(df: pl.DataFrame, instrument_id: str, timeframe: Timeframe) -> list[Bar]:
    return [
        Bar(
            instrument_id=instrument_id,
            timeframe=timeframe,
            ts_open_utc=row["ts_open_utc"],
            ts_close_utc=row["ts_close_utc"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            session=SessionType(row["session"]),
            provider=row["provider"],
            feed=row["feed"],
            data_version=row["data_version"],
            trade_count=row["trade_count"],
            vwap=row["vwap"],
            is_complete=row["is_complete"],
        )
        for row in df.iter_rows(named=True)
    ]


class MarketDataStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.market_dir = data_dir / "market"
        self.manifest_dir = self.market_dir / "manifests"

    # ---------- 路径 ----------
    def _part_dir(self, instrument: Instrument, timeframe: Timeframe, year: int) -> Path:
        return (
            self.market_dir
            / f"provider={instrument.provider}"
            / f"instrument={instrument.instrument_id}"
            / f"timeframe={timeframe.value}"
            / f"year={year}"
        )

    # ---------- 写入 ----------
    def write_bars(self, bars: list[Bar], instrument: Instrument, timeframe: Timeframe) -> dict:
        if not bars:
            return {"written": 0, "duplicate_count": 0}
        incoming = _bars_to_df(bars)
        years = incoming["ts_open_utc"].dt.year().unique().to_list()

        duplicate_total = 0
        for year in sorted(years):
            part = incoming.filter(pl.col("ts_open_utc").dt.year() == year)
            d = self._part_dir(instrument, timeframe, year)
            d.mkdir(parents=True, exist_ok=True)
            f = d / "part-000.parquet"
            if f.exists():
                existing = pl.read_parquet(f)
                combined = pl.concat([existing, part]).sort("ts_open_utc")
                n_before = combined.height
                combined = combined.unique(subset=["ts_open_utc", "session"], keep="first")
                duplicate_total += n_before - combined.height
                combined.write_parquet(f)
            else:
                part.write_parquet(f)

        manifest = self._build_manifest(instrument, timeframe)
        self._write_manifest(manifest)
        return {**manifest, "written": len(bars), "duplicate_count": duplicate_total}

    def _build_manifest(self, instrument: Instrument, timeframe: Timeframe) -> dict:
        frames = []
        for part_dir in sorted(self._instrument_root(instrument, timeframe).glob("year=*")):
            f = part_dir / "part-000.parquet"
            if f.exists():
                frames.append(pl.read_parquet(f, columns=["ts_open_utc", "close", "session"]))
        if not frames:
            df = pl.DataFrame(
                schema={"ts_open_utc": pl.Datetime("us", "UTC"), "close": pl.Float64, "session": pl.String}
            )
        else:
            df = pl.concat(frames).sort("ts_open_utc")
        h = hashlib.blake2b()
        for row in df.iter_rows(named=True):
            h.update(row["ts_open_utc"].isoformat().encode())
            h.update(str(row["close"]).encode())
        return {
            "provider": instrument.provider,
            "feed": instrument.feed,
            "instrument_id": instrument.instrument_id,
            "timeframe": timeframe.value,
            "start": _iso(df["ts_open_utc"].min()),
            "end": _iso(df["ts_open_utc"].max()),
            "row_count": df.height,
            "duplicate_count": 0,
            "missing_bar_count": self._count_missing_rth(instrument, timeframe, df),
            "checksum": h.hexdigest(),
            "generated_at": datetime.now(UTC).isoformat(),
            "schema_version": SCHEMA_VERSION,
            "aggregation_rules": (
                "1m raw -> 5m: session-aware, anchor premarket 04:00 / rth 09:30 ET, DST via zoneinfo, "
                "no cross-session buckets, no forward-fill"
                if timeframe == Timeframe.M5
                else "raw 1m as ingested"
            ),
            "quote_side": instrument.quote_side,
            "feed_consolidated": instrument.feed_consolidated,
        }

    def _count_missing_rth(self, instrument: Instrument, timeframe: Timeframe, df: pl.DataFrame) -> int:
        """统计 RTH 时段整桶缺失数（交易日内应出现而未出现的桶）。仅对 5m 有意义。"""
        from app.services.calendar import default_calendar

        if df.height == 0:
            return 0
        cal = default_calendar()
        first_day = cast("datetime", df["ts_open_utc"].min()).date()
        last_day = cast("datetime", df["ts_open_utc"].max()).date()
        days = set(cal.trading_days(first_day, last_day))
        present = {
            (row["ts_open_utc"].date(), row["session"])
            for row in df.iter_rows(named=True)
        }
        missing = 0
        expected_per_day = 78  # RTH 390min / 5min；半日市由实际 session 窗口覆盖
        for d in sorted(days):
            if (d, "rth") not in present:
                continue  # 该日完全无数据（未摄取范围），不计缺失
            windows = cal.sessions_for(d)
            rth_minutes = next(
                int((w.end_utc - w.start_utc).total_seconds() // 60)
                for w in windows
                if w.session_type == "rth"
            )
            expected = rth_minutes // (5 if timeframe == Timeframe.M5 else 1)
            actual = df.filter(
                (pl.col("ts_open_utc").dt.date() == d) & (pl.col("session") == "rth")
            ).height
            missing += max(0, (expected or expected_per_day) - actual)
        return missing

    def _instrument_root(self, instrument: Instrument, timeframe: Timeframe) -> Path:
        return (
            self.market_dir
            / f"provider={instrument.provider}"
            / f"instrument={instrument.instrument_id}"
            / f"timeframe={timeframe.value}"
        )

    def _write_manifest(self, manifest: dict) -> None:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        path = self.manifest_dir / (
            f"{manifest['provider']}_{manifest['instrument_id']}_{manifest['timeframe']}.json"
        )
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---------- 读取 ----------
    def read_bars(
        self, instrument: Instrument, timeframe: Timeframe, start: date, end: date
    ) -> list[Bar]:
        root = self._instrument_root(instrument, timeframe)
        if not root.exists():
            return []
        frames = []
        for year_dir in sorted(root.glob("year=*")):
            f = year_dir / "part-000.parquet"
            if not f.exists():
                continue
            df = pl.read_parquet(f)
            df = df.filter(
                (pl.col("ts_open_utc").dt.date() >= start)
                & (pl.col("ts_open_utc").dt.date() <= end)
            )
            if df.height:
                frames.append(df)
        if not frames:
            return []
        merged = pl.concat(frames).sort("ts_open_utc")
        return _df_to_bars(merged, instrument.instrument_id, timeframe)

    def read_day(
        self, instrument: Instrument, timeframe: Timeframe, day: date, session: SessionType | None = None
    ) -> list[Bar]:
        bars = self.read_bars(instrument, timeframe, day, day)
        if session is not None:
            bars = [b for b in bars if b.session == session]
        return bars

    def list_datasets(self) -> list[dict]:
        if not self.manifest_dir.exists():
            return []
        out = []
        for f in sorted(self.manifest_dir.glob("*.json")):
            out.append(json.loads(f.read_text(encoding="utf-8")))
        return out
