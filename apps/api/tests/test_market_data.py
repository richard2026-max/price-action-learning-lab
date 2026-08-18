"""存储层测试：Parquet 读写、去重、manifest。"""

from datetime import date

from app.domain.bar import SessionType, Timeframe
from app.domain.instrument import SPY_SYNTH
from app.services.market_data import MarketDataStore

SEED_START = date(2024, 1, 2)
SEED_END = date(2024, 1, 12)


def test_write_read_roundtrip_and_manifest(tmp_path, raw_bars):
    bars_1m, bars_5m, _ = raw_bars
    store = MarketDataStore(tmp_path / "data")
    r = store.write_bars(bars_5m, SPY_SYNTH, Timeframe.M5)
    assert r["written"] == len(bars_5m)

    read_back = store.read_bars(SPY_SYNTH, Timeframe.M5, SEED_START, SEED_END)
    assert read_back == bars_5m  # 值对象逐根相等

    datasets = store.list_datasets()
    assert len(datasets) == 1
    m = datasets[0]
    assert m["provider"] == "synthetic" and m["instrument_id"] == "SPY" and m["timeframe"] == "5m"
    assert m["row_count"] == len(bars_5m)
    assert m["duplicate_count"] == 0
    assert m["missing_bar_count"] == 0  # 合成数据不缺桶
    assert "aggregation_rules" in m and "anchor" in m["aggregation_rules"]
    assert m["checksum"]


def test_duplicate_dedup_counted(tmp_path, raw_bars):
    _, bars_5m, _ = raw_bars
    store = MarketDataStore(tmp_path / "data")
    store.write_bars(bars_5m, SPY_SYNTH, Timeframe.M5)
    r2 = store.write_bars(bars_5m, SPY_SYNTH, Timeframe.M5)  # 全量重写 => 全部判重
    assert r2["duplicate_count"] == len(bars_5m)
    read_back = store.read_bars(SPY_SYNTH, Timeframe.M5, SEED_START, SEED_END)
    assert len(read_back) == len(bars_5m)  # 去重后不变


def test_read_day_session_filter(tmp_path, raw_bars):
    _, bars_5m, _ = raw_bars
    store = MarketDataStore(tmp_path / "data")
    store.write_bars(bars_5m, SPY_SYNTH, Timeframe.M5)
    day = date(2024, 1, 4)
    rth = store.read_day(SPY_SYNTH, Timeframe.M5, day, SessionType.RTH)
    pre = store.read_day(SPY_SYNTH, Timeframe.M5, day, SessionType.PREMARKET)
    assert len(rth) == 78
    assert len(pre) == 66
    assert all(b.session == SessionType.RTH for b in rth)
