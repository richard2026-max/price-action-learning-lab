"""本地历史行情中的类比形态检索（阶段 3）。

服务只操作调用方传入的 :class:`Bar` 或本地 ``MarketDataStore`` 数据，
不发起网络请求。查询形态由最后 ``window_length`` 根可见 K 线构成，
候选窗口使用同样长度，并以 close 路径、每根波幅和可选 EMA 关系计算欧氏距离。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.domain.bar import Bar, Timeframe
from app.domain.instrument import Instrument
from app.services.market_data import MarketDataStore


@dataclass(frozen=True, slots=True)
class AnalogMatch:
    """一个历史类比窗口及其窗口后的已知结果。"""

    date: date
    start_time: datetime
    end_time: datetime
    similarity: float
    distance: float
    pattern_label: str
    forward_direction: str
    forward_result: str
    forward_return: float | None
    window_bars: list[dict[str, Any]] = field(default_factory=list)
    forward_bars: list[dict[str, Any]] = field(default_factory=list)
    chart_image_url: str | None = None

    @property
    def start(self) -> datetime:
        return self.start_time

    @property
    def end(self) -> datetime:
        return self.end_time

    @property
    def result(self) -> str:
        return self.forward_result


class AnalogSearchService:
    """在本地 SPY 5m 历史数据上检索 Top-K 类比窗口。

    ``history_bars`` 是可选的依赖注入点，适合单测和离线运行；未传入时，
    ``search`` 会通过 ``store`` 按查询日期范围读取数据。也可直接调用
    ``find_analogs(query_bars, history_bars=...)``，完全不依赖存储层。
    """

    def __init__(
        self,
        store: MarketDataStore | None = None,
        history_bars: Sequence[Bar] | None = None,
        window_length: int = 20,
        forward_bars: int = 10,
        top_k: int = 3,
        include_ema: bool = False,
        ema_period: int = 20,
    ) -> None:
        if window_length <= 0 or forward_bars < 0 or top_k <= 0 or ema_period <= 0:
            raise ValueError("window_length/top_k/ema_period 必须为正，forward_bars 不得为负")
        self.store = store
        self.history_bars = list(history_bars) if history_bars is not None else None
        self.window_length = window_length
        self.forward_bars = forward_bars
        self.top_k = top_k
        self.include_ema = include_ema
        self.ema_period = ema_period

    def search(
        self,
        query_bars: Sequence[Bar],
        *,
        instrument: Instrument | None = None,
        history_bars: Sequence[Bar] | None = None,
        window_length: int | None = None,
        forward_bars: int | None = None,
        top_k: int | None = None,
        include_ema: bool | None = None,
        target_date: date | str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> list[AnalogMatch]:
        """检索查询序列最后一个窗口；候选必须有完整的后续结果 K 线。支持指定日期或日期范围。"""
        n = window_length if window_length is not None else self.window_length
        horizon = forward_bars if forward_bars is not None else self.forward_bars
        limit = top_k if top_k is not None else self.top_k
        use_ema = include_ema if include_ema is not None else self.include_ema
        if n <= 0 or horizon < 0 or limit <= 0:
            raise ValueError("window_length/top_k 必须为正，forward_bars 不得为负")

        query = self._clean(query_bars)
        if len(query) < n:
            return []
        query_window = query[-n:]

        candidates = history_bars if history_bars is not None else self.history_bars
        if candidates is None:
            if self.store is None or instrument is None:
                raise ValueError("未提供 history_bars 时必须提供 store 和 instrument")
            candidates = self._read_all_local_history(instrument, query)
        history = [
            b for b in self._clean(candidates)
            if b.instrument_id == query_window[0].instrument_id and b.timeframe == query_window[0].timeframe
        ]
        if not history:
            return []

        q_features = self._features(query_window, use_ema)
        q_start, q_end = query_window[0].ts_open_utc, query_window[-1].ts_close_utc
        query_date = query_window[0].ts_open_utc.date()
        has_other_days = any(b.ts_open_utc.date() != query_date for b in history)

        t_date = date.fromisoformat(target_date) if isinstance(target_date, str) else target_date
        s_date = date.fromisoformat(start_date) if isinstance(start_date, str) else start_date
        e_date = date.fromisoformat(end_date) if isinstance(end_date, str) else end_date

        matches: list[AnalogMatch] = []
        for i in range(0, len(history) - n - horizon + 1):
            window = history[i : i + n]
            w_start, w_end = window[0].ts_open_utc, window[-1].ts_close_utc
            w_date = w_start.date()

            # 支持指定特定历史交易日或日期区间进行精准比对
            if t_date and w_date != t_date:
                continue
            if s_date and w_date < s_date:
                continue
            if e_date and w_date > e_date:
                continue

            # 严格排除当前训练日：当存在多日历史数据时，排除属于当前训练日的任何候选（仅找过往真实 SPY 历史）
            if has_other_days and w_date == query_date:
                continue
            if w_start < q_end and w_end > q_start:
                continue  # 排除查询窗口本身及任何重叠窗口；边界相接不算重叠
            # 只接受连续时间序列的窗口，避免跨缺失桶造成伪形态。
            if not self._contiguous(window):
                continue
            future = history[i + n : i + n + horizon]
            candidate_features = self._features(window, use_ema)
            distance = sum(
                (a - b) ** 2 for a, b in zip(q_features, candidate_features, strict=True)
            ) ** 0.5
            end_close = window[-1].close
            future_close = future[-1].close if future else end_close
            change = (future_close - end_close) / end_close if end_close else None
            direction = self._direction(change)
            matches.append(
                AnalogMatch(
                    date=w_start.date(),
                    start_time=w_start,
                    end_time=w_end,
                    similarity=1.0 / (1.0 + distance),
                    distance=distance,
                    pattern_label=self._pattern_label(window),
                    forward_direction=direction,
                    forward_result=self._forward_result(direction, change),
                    forward_return=round(change, 6) if change is not None else None,
                    window_bars=[
                        {
                            "open": round(b.open, 2),
                            "high": round(b.high, 2),
                            "low": round(b.low, 2),
                            "close": round(b.close, 2),
                            "time": b.ts_open_utc.isoformat(),
                        }
                        for b in window
                    ],
                    forward_bars=[
                        {
                            "open": round(b.open, 2),
                            "high": round(b.high, 2),
                            "low": round(b.low, 2),
                            "close": round(b.close, 2),
                            "time": b.ts_open_utc.isoformat(),
                        }
                        for b in future
                    ],
                )
            )
        matches.sort(key=lambda m: (m.distance, m.start_time))
        top_matches = matches[:limit]

        final_matches: list[AnalogMatch] = []
        for m in top_matches:
            chart_url = self._ensure_chart_image(m)
            final_matches.append(
                AnalogMatch(
                    date=m.date,
                    start_time=m.start_time,
                    end_time=m.end_time,
                    similarity=m.similarity,
                    distance=m.distance,
                    pattern_label=m.pattern_label,
                    forward_direction=m.forward_direction,
                    forward_result=m.forward_result,
                    forward_return=m.forward_return,
                    window_bars=m.window_bars,
                    forward_bars=m.forward_bars,
                    chart_image_url=chart_url,
                )
            )
        return final_matches

    def find_analogs(self, query_bars: Sequence[Bar], **kwargs) -> list[AnalogMatch]:
        """search 的语义别名，便于服务层调用方使用更明确的名称。"""
        return self.search(query_bars, **kwargs)

    def _read_all_local_history(self, instrument: Instrument, query: Sequence[Bar]) -> list[Bar]:
        """按 manifest 读取该 instrument 的全部本地 5m 数据，避免只检索查询日。"""
        manifests = [
            m
            for m in self.store.list_datasets()  # type: ignore[union-attr]
            if m.get("provider") == instrument.provider
            and m.get("instrument_id") == instrument.instrument_id
            and m.get("timeframe") == Timeframe.M5.value
            and m.get("start")
            and m.get("end")
        ]
        if not manifests:
            first_day = min(b.ts_open_utc.date() for b in query)
            last_day = max(b.ts_open_utc.date() for b in query)
            return self.store.read_bars(instrument, Timeframe.M5, first_day, last_day)  # type: ignore[union-attr]
        start = min(date.fromisoformat(m["start"][:10]) for m in manifests)
        end = max(date.fromisoformat(m["end"][:10]) for m in manifests)
        return self.store.read_bars(instrument, Timeframe.M5, start, end)  # type: ignore[union-attr]

    @staticmethod
    def _clean(bars: Sequence[Bar]) -> list[Bar]:
        return sorted((b for b in bars if b.is_complete), key=lambda b: b.ts_open_utc)

    @staticmethod
    def _contiguous(bars: Sequence[Bar]) -> bool:
        if len(bars) < 2:
            return True
        expected = bars[0].ts_close_utc - bars[0].ts_open_utc
        return all(b.ts_open_utc - a.ts_open_utc == expected for a, b in zip(bars, bars[1:], strict=False))

    def _features(self, bars: Sequence[Bar], include_ema: bool) -> list[float]:
        base = bars[0].close or 1.0
        closes = [(b.close - base) / base for b in bars]
        ranges = [(b.high - b.low) / base for b in bars]
        features = closes + ranges
        if include_ema:
            ema_values = self._ema([b.close for b in bars])
            features.extend((b.close - ema) / base for b, ema in zip(bars, ema_values, strict=True))
        return features

    def _ema(self, values: Sequence[float]) -> list[float]:
        alpha = 2.0 / (self.ema_period + 1.0)
        ema = values[0]
        result = [ema]
        for value in values[1:]:
            ema = alpha * value + (1.0 - alpha) * ema
            result.append(ema)
        return result

    @staticmethod
    def _direction(change: float | None) -> str:
        if change is None or abs(change) < 1e-9:
            return "flat"
        return "up" if change > 0 else "down"

    @staticmethod
    def _forward_result(direction: str, change: float | None) -> str:
        if change is None:
            return "insufficient_data"
        return direction

    @staticmethod
    def _pattern_label(bars: Sequence[Bar]) -> str:
        net = bars[-1].close - bars[0].close
        span = max(b.high for b in bars) - min(b.low for b in bars)
        ratio = abs(net) / span if span else 0.0
        if ratio >= 0.6:
            return "trend_up" if net > 0 else "trend_down"
        return "range"

    def _ensure_chart_image(self, match: AnalogMatch) -> str | None:
        try:
            cache_name = (
                f"analog_{match.date.isoformat()}_{match.start_time.strftime('%H%M%S')}_"
                f"{int(match.similarity * 1000)}.png"
            )
            if self.store and hasattr(self.store, "data_dir"):
                cache_dir = Path(self.store.data_dir) / "cache" / "analog_charts"
            else:
                from app.core.config import Settings

                cache_dir = Settings().data_dir / "cache" / "analog_charts"
            cache_path = cache_dir / cache_name

            if match.forward_direction == "up":
                dir_label = "上涨 ▲"
            elif match.forward_direction == "down":
                dir_label = "下跌 ▼"
            else:
                dir_label = "震荡 —"
            ret_str = f" ({match.forward_return * 100:.2f}%)" if match.forward_return is not None else ""
            title = (
                f"SPY 5m 过往历史相似走势 · {match.date.isoformat()} "
                f"({match.start_time.strftime('%H:%M')} - {match.end_time.strftime('%H:%M')}) · "
                f"相似度 {match.similarity * 100:.1f}% · 走向: [{dir_label}{ret_str}]"
            )
            render_analog_candlestick_chart(match.window_bars, match.forward_bars, title, cache_path)
            return f"/api/v1/coach/analogs/chart-image?file={cache_name}"
        except Exception:
            return None


def render_analog_candlestick_chart(
    bars_pattern: list[dict[str, Any]],
    bars_forward: list[dict[str, Any]],
    title_text: str,
    output_path: Path,
) -> Path:
    """使用 matplotlib 绘制深色专业 K 线形态对比图（包含 20 根匹配形态与 10 根后续演化）。"""
    if output_path.is_file() and output_path.stat().st_size > 0:
        return output_path

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as patches
        import matplotlib.pyplot as plt

        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(8.5, 3.0), dpi=100)
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        all_bars = bars_pattern + bars_forward
        n = len(all_bars)
        if n == 0:
            plt.close(fig)
            return output_path

        highs = [b["high"] for b in all_bars]
        lows = [b["low"] for b in all_bars]
        max_h, min_l = max(highs), min(lows)
        span = max_h - min_l or 1.0

        for i, b in enumerate(all_bars):
            is_bull = b["close"] >= b["open"]
            color = "#26a69a" if is_bull else "#ef5350"
            ax.plot([i, i], [b["low"], b["high"]], color=color, linewidth=1.1, zorder=2)
            y = min(b["open"], b["close"])
            h = max(0.04, abs(b["close"] - b["open"]))
            rect = patches.Rectangle(
                (i - 0.32, y), 0.64, h, facecolor=color, edgecolor=color, linewidth=0.5, zorder=3
            )
            ax.add_patch(rect)

        split_i = len(bars_pattern) - 0.5
        ax.axvline(split_i, color="#f0b90b", linestyle="--", linewidth=1.4, alpha=0.9, zorder=4)
        if bars_forward:
            ax.axvspan(split_i, n - 0.5, color="#2979ff", alpha=0.08, zorder=1)

        ax.text(
            len(bars_pattern) / 2 - 0.5,
            max_h + span * 0.04,
            "过往历史形态 (20 根)",
            color="#8b949e",
            fontsize=8.5,
            ha="center",
            weight="bold",
        )
        if bars_forward:
            ax.text(
                len(bars_pattern) + len(bars_forward) / 2 - 0.5,
                max_h + span * 0.04,
                "随后 10 根真实走向",
                color="#2979ff",
                fontsize=8.5,
                ha="center",
                weight="bold",
            )

        ax.set_title(title_text, color="#f0b90b", fontsize=9.5, pad=8, weight="bold")
        ax.set_xlim(-0.8, n - 0.2)
        ax.set_ylim(min_l - span * 0.08, max_h + span * 0.16)
        ax.tick_params(colors="#8b949e", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#30363d")
        ax.grid(True, linestyle=":", color="#21262d", alpha=0.5)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
    except Exception:
        pass
    return output_path
