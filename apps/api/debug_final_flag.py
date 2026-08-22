"""Debug script for final_flag detection."""
from app.detectors.bar_facts import register_bar_facts, anatomy
from app.detectors.base import all_detectors
from app.detectors.complex import register_complex
from app.detectors.patterns import register_patterns
from app.detectors.structure import HL_STATE, register_structure
from app.detectors.advanced import register_advanced
from app.domain.bar import Bar, SessionType, Timeframe

HL_STATE.reset()
register_bar_facts()
register_patterns()
register_structure()
register_complex()
register_advanced()

from datetime import UTC, datetime, timedelta
_T0 = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
def mk(o, h, lo, c, i=0):
    return Bar(instrument_id="SPY", timeframe=Timeframe.M5,
        ts_open_utc=_T0 + timedelta(minutes=5*i), ts_close_utc=_T0 + timedelta(minutes=5*(i+1)),
        open=o, high=h, low=lo, close=c, volume=1000.0,
        session=SessionType.RTH, provider="synthetic", feed="t", data_version="t")

bars = [mk(100, 100.3, 99.8, 100.1, i) for i in range(20)]
p = 100.1
for j in range(20, 23):
    bars.append(mk(p, p + 2.5, p - 0.5, p + 2.0, j))
    p += 2.0
flag_start = p
for j in range(23, 27):
    if j % 2 == 0:
        bars.append(mk(flag_start - 0.2, flag_start + 0.3, flag_start - 0.5, flag_start + 0.1, j))
    else:
        bars.append(mk(flag_start + 0.1, flag_start + 0.4, flag_start - 0.3, flag_start - 0.1, j))

# Check anatomy of climax bars
for i in [20, 21, 22]:
    f = anatomy(bars, i)
    print(f"bar {i}: dir={f['direction']} br={f['body_ratio']} rr={f['relative_range']}")

# Check climax detection
det_climax = all_detectors()["climax"]
for i in range(len(bars)):
    c_out = det_climax.fn(bars, i)
    if c_out:
        print(f"i={i}: CLIMAX: {c_out.result}")

# Check final_flag at each bar after climax
det_final = all_detectors()["final_flag"]
for i in range(23, len(bars)):
    f_out = det_final.fn(bars, i)
    if f_out:
        print(f"i={i}: FINAL_FLAG: {f_out.result}")
    else:
        # Debug why not detected
        # Check if climax is found in lookback
        found_climax = False
        for back in range(2, 11):
            check_i = i - back
            if check_i < 0:
                break
            cf = anatomy([ctx[check_i]] if False else [bars[check_i]], 0)
            rr = cf["relative_range"]
            br = cf["body_ratio"]
            if rr is not None and rr >= 2.6 and br is not None and br >= 0.7:
                found_climax = True
                break
        if i == len(bars) - 1:
            print(f"i={i}: final_flag=None, found_climax_in_lookback={found_climax}")
