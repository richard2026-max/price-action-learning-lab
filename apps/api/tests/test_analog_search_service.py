from datetime import UTC, datetime, timedelta

from app.domain.bar import Bar, SessionType, Timeframe
from app.services.analog_search_service import AnalogSearchService


def make_bars(values: list[float], start: datetime, *, step: float = 0.0) -> list[Bar]:
    bars = []
    for i, close in enumerate(values):
        ts = start + timedelta(minutes=5 * i)
        open_ = close - step
        high = max(open_, close) + 0.1
        low = min(open_, close) - 0.1
        bars.append(
            Bar(
                instrument_id="SPY",
                timeframe=Timeframe.M5,
                ts_open_utc=ts,
                ts_close_utc=ts + timedelta(minutes=5),
                open=open_, high=high, low=low, close=close, volume=1,
                session=SessionType.RTH, provider="local", feed="test", data_version="test",
            )
        )
    return bars


def test_excludes_query_window_and_overlapping_windows():
    values = [100 + i for i in range(20)] + [120 + i for i in range(20)]
    bars = make_bars(values, datetime(2024, 1, 2, 14, 30, tzinfo=UTC))
    matches = AnalogSearchService(history_bars=bars, window_length=20, top_k=3).search(bars[-20:])

    assert matches
    query_start = bars[-20].ts_open_utc
    query_end = bars[-1].ts_close_utc
    assert all(not (m.start_time < query_end and m.end_time > query_start) for m in matches)
    assert all(m.start_time != query_start for m in matches)


def test_ranks_nearest_shape_first_and_returns_top_three():
    # query shape is [0, 1, ..., 19]. Candidate A is exact up to base price;
    # candidate B has a visibly different path and should rank lower.
    query = make_bars(list(range(100, 120)), datetime(2024, 1, 5, 14, 30, tzinfo=UTC))
    candidate_a = make_bars(list(range(200, 220)), datetime(2024, 1, 2, 14, 30, tzinfo=UTC))
    candidate_b = make_bars([200 + (i % 2) for i in range(20)], datetime(2024, 1, 3, 14, 30, tzinfo=UTC))
    extra = make_bars([300 + i * 0.5 for i in range(30)], datetime(2024, 1, 4, 14, 30, tzinfo=UTC))
    history = candidate_a + candidate_b + extra + query

    matches = AnalogSearchService(history_bars=history, window_length=20, top_k=3).search(query)

    assert len(matches) == 3
    assert matches[0].date == candidate_a[0].ts_open_utc.date()
    assert matches[0].distance < matches[1].distance
    assert matches[0].similarity > matches[1].similarity


def test_reports_ten_bar_forward_direction_and_result():
    candidate = make_bars(list(range(100, 120)), datetime(2024, 1, 2, 14, 30, tzinfo=UTC))
    future = make_bars(list(range(120, 130)), candidate[-1].ts_close_utc)
    query = make_bars(list(range(50, 70)), datetime(2024, 1, 5, 14, 30, tzinfo=UTC))
    history = candidate + future + query

    matches = AnalogSearchService(history_bars=history, window_length=20, forward_bars=10).search(query)

    match = next(m for m in matches if m.date == candidate[0].ts_open_utc.date())
    assert match.forward_direction == "up"
    assert match.forward_result == "up"
    assert match.forward_return is not None and match.forward_return > 0
