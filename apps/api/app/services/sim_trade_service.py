"""模拟交易执行引擎（SimTradeService，Level 6 交易管理训练）。

核心规则（ADR-005、PRD §十二）：
1. 订单类型支持：
   - Market：立即在当前 Bar 收盘价（或下一根开盘）成交；
   - Limit：当价格触及或优于限价时成交；
   - Stop：当价格突破停止价时成交。
2. 歧义结算默认保守（Pessimistic Matching）：
   - 同一根 K 线内 High 触及 Target 且 Low 触及 Stop 时，默认判定为止损先触及（保守结算，不虚夸收益）。
3. 过程统计：
   - 随每根 K 线推进实时更新 MFE（最大有利浮盈）与 MAE（最大不利回撤），并折算为 R 倍数。
"""

from __future__ import annotations

import uuid

from app.domain.bar import Bar
from app.models.orm import SimTradeORM
from app.repositories.sim_trade_repo import SimTradeRepository
from app.schemas.sim_trade import CreateSimTradeIn, ManualExitTradeIn


class SimTradeService:
    def __init__(self, repo: SimTradeRepository) -> None:
        self._repo = repo

    def create_order(
        self,
        session_id: str,
        instrument_id: str,
        provider: str,
        current_bar: Bar,
        bar_index: int,
        req: CreateSimTradeIn,
    ) -> SimTradeORM:
        initial_risk = abs(req.planned_entry_price - req.stop_price)
        if initial_risk <= 0:
            raise ValueError("止损价格不能等于入场价")

        trade = SimTradeORM(
            id=uuid.uuid4().hex,
            session_id=session_id,
            instrument_id=instrument_id,
            provider=provider,
            day=current_bar.ts_open_utc.date(),
            side=req.side.value,
            order_type=req.order_type.value,
            status="pending",
            order_bar_index=bar_index,
            order_time_utc=current_bar.ts_close_utc,
            planned_entry_price=req.planned_entry_price,
            stop_price=req.stop_price,
            target_price=req.target_price,
            initial_risk=round(initial_risk, 4),
            setup_notes=req.setup_notes,
            reasons=req.reasons,
        )

        # 市价单立即在当前 bar 收盘成交
        if req.order_type.value == "market":
            trade.status = "open"
            trade.actual_entry_price = current_bar.close
            trade.entry_bar_index = bar_index
            trade.entry_time_utc = current_bar.ts_close_utc
            trade.mfe_price = current_bar.close
            trade.mfe_in_r = 0.0
            trade.mae_price = current_bar.close
            trade.mae_in_r = 0.0

        return self._repo.create_trade(trade)

    def process_bar_advancement(self, session_id: str, bar: Bar, bar_index: int) -> list[SimTradeORM]:
        """每当回放推进一根 K 线时，撮合挂单并更新持仓的 MFE/MAE 与出场判断。"""
        open_trades = self._repo.list_open_trades(session_id)
        updated: list[SimTradeORM] = []

        for t in open_trades:
            # 1. 撮合 Pending 挂单
            if t.status == "pending":
                filled, fill_price = self._match_entry(t, bar)
                if filled and fill_price is not None:
                    t.status = "open"
                    t.actual_entry_price = fill_price
                    t.entry_bar_index = bar_index
                    t.entry_time_utc = bar.ts_close_utc
                    t.mfe_price = fill_price
                    t.mfe_in_r = 0.0
                    t.mae_price = fill_price
                    t.mae_in_r = 0.0
                    self._repo.update_trade(t)
                    updated.append(t)
                continue

            # 2. 已持仓：更新 MFE / MAE 并检查止盈止损
            if t.status == "open" and t.actual_entry_price is not None:
                self._update_mfe_mae(t, bar)
                exited, exit_price, reason = self._check_exit(t, bar)
                if exited and exit_price is not None:
                    t.status = "closed"
                    t.exit_price = exit_price
                    t.exit_bar_index = bar_index
                    t.exit_time_utc = bar.ts_close_utc
                    t.exit_reason = reason
                    pnl = (
                        (exit_price - t.actual_entry_price)
                        if t.side == "long"
                        else (t.actual_entry_price - exit_price)
                    )
                    t.pnl = round(pnl, 4)
                    t.pnl_in_r = round(pnl / t.initial_risk, 4) if t.initial_risk else 0.0

                self._repo.update_trade(t)
                updated.append(t)

        return updated

    def manual_exit(self, trade_id: str, current_bar: Bar, bar_index: int, req: ManualExitTradeIn) -> SimTradeORM:
        t = self._repo.get_trade(trade_id)
        if not t:
            raise ValueError("Trade not found")
        if t.status != "open" or t.actual_entry_price is None:
            raise ValueError("Only open trades can be manually exited")

        exit_price = req.exit_price if req.exit_price is not None else current_bar.close
        t.status = "closed"
        t.exit_price = exit_price
        t.exit_bar_index = bar_index
        t.exit_time_utc = current_bar.ts_close_utc
        t.exit_reason = "manual"
        if req.notes:
            t.setup_notes = (t.setup_notes or "") + f" [Exit Notes: {req.notes}]"

        pnl = (exit_price - t.actual_entry_price) if t.side == "long" else (t.actual_entry_price - exit_price)
        t.pnl = round(pnl, 4)
        t.pnl_in_r = round(pnl / t.initial_risk, 4) if t.initial_risk else 0.0

        self._repo.update_trade(t)
        return t

    @staticmethod
    def _match_entry(t: SimTradeORM, bar: Bar) -> tuple[bool, float | None]:
        target = t.planned_entry_price
        if t.order_type == "limit":
            if t.side == "long" and bar.low <= target:
                return True, min(bar.open, target)  # 开盘低开则以更优开盘价成交
            if t.side == "short" and bar.high >= target:
                return True, max(bar.open, target)
        elif t.order_type == "stop":
            if t.side == "long" and bar.high >= target:
                return True, max(bar.open, target)
            if t.side == "short" and bar.low <= target:
                return True, min(bar.open, target)
        return False, None

    @staticmethod
    def _update_mfe_mae(t: SimTradeORM, bar: Bar) -> None:
        entry = t.actual_entry_price
        if entry is None:
            return
        risk = t.initial_risk or 1.0

        if t.side == "long":
            # 多头：高点贡献最好浮盈，低点贡献最差浮亏
            best_fav = max(t.mfe_price or entry, bar.high)
            worst_adv = min(t.mae_price or entry, bar.low)
            t.mfe_price = round(best_fav, 4)
            t.mfe_in_r = round((best_fav - entry) / risk, 4)
            t.mae_price = round(worst_adv, 4)
            t.mae_in_r = round((worst_adv - entry) / risk, 4)
        else:
            # 空头：低点贡献最好浮盈，高点贡献最差浮亏
            best_fav = min(t.mfe_price or entry, bar.low)
            worst_adv = max(t.mae_price or entry, bar.high)
            t.mfe_price = round(best_fav, 4)
            t.mfe_in_r = round((entry - best_fav) / risk, 4)
            t.mae_price = round(worst_adv, 4)
            t.mae_in_r = round((entry - worst_adv) / risk, 4)

    @staticmethod
    def _check_exit(t: SimTradeORM, bar: Bar) -> tuple[bool, float | None, str | None]:
        """出场检查。遵循 ADR-005 保守策略（同根 Bar 同时触及止损止盈时，默认止损先发生）。"""
        if t.side == "long":
            hit_stop = bar.low <= t.stop_price
            hit_target = bar.high >= t.target_price
            if hit_stop and hit_target:
                # 歧义判定：保守结算为止损
                return True, t.stop_price, "stop"
            if hit_stop:
                return True, t.stop_price, "stop"
            if hit_target:
                return True, t.target_price, "target"
        else:
            hit_stop = bar.high >= t.stop_price
            hit_target = bar.low <= t.target_price
            if hit_stop and hit_target:
                return True, t.stop_price, "stop"
            if hit_stop:
                return True, t.stop_price, "stop"
            if hit_target:
                return True, t.target_price, "target"

        return False, None, None
