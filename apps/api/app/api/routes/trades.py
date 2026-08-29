"""模拟交易（SimTrade）相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_replay_service, get_sim_trade_service, resolve_instrument
from app.models.orm import UserORM
from app.replay.service import ReplayError, ReplayService
from app.schemas.sim_trade import CreateSimTradeIn, ManualExitTradeIn, SimTradeOut
from app.services.sim_trade_service import SimTradeService

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("/sessions/{session_id}", response_model=SimTradeOut, status_code=201)
def create_sim_trade(
    session_id: str,
    req: CreateSimTradeIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    replay_svc: ReplayService = Depends(get_replay_service),
    trade_svc: SimTradeService = Depends(get_sim_trade_service),
    user: UserORM = Depends(get_current_user),
) -> SimTradeOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        session_detail = replay_svc.get(session_id, instrument, user.id)
    except ReplayError as e:
        raise HTTPException(status_code=e.status, detail=e.message) from e

    bar_index = session_detail.info.bar_index
    current_bar_out = session_detail.bars[bar_index]

    # 构建领域 Bar 对象用于撮合
    from app.domain.bar import Bar, SessionType, Timeframe
    current_bar = Bar(
        instrument_id=instrument.instrument_id,
        timeframe=Timeframe.M5,
        ts_open_utc=current_bar_out.ts_open_utc,
        ts_close_utc=current_bar_out.ts_close_utc,
        open=current_bar_out.open,
        high=current_bar_out.high,
        low=current_bar_out.low,
        close=current_bar_out.close,
        volume=current_bar_out.volume,
        session=SessionType(current_bar_out.session),
        provider=instrument.provider,
        feed=instrument.feed,
        data_version="trade-runtime",
    )

    try:
        orm = trade_svc.create_order(
            session_id=session_id,
            instrument_id=instrument.instrument_id,
            provider=instrument.provider,
            current_bar=current_bar,
            bar_index=bar_index,
            req=req,
        )
        return SimTradeOut.model_validate(orm, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/sessions/{session_id}", response_model=list[SimTradeOut])
def list_session_trades(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    replay_svc: ReplayService = Depends(get_replay_service),
    trade_svc: SimTradeService = Depends(get_sim_trade_service),
    user: UserORM = Depends(get_current_user),
) -> list[SimTradeOut]:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        replay_svc.get(session_id, instrument, user.id)
    except ReplayError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    rows = trade_svc._repo.list_trades_for_session(session_id)
    return [SimTradeOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/{trade_id}/exit", response_model=SimTradeOut)
def manual_exit_trade(
    trade_id: str,
    req: ManualExitTradeIn,
    session_id: str = Query(...),
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    replay_svc: ReplayService = Depends(get_replay_service),
    trade_svc: SimTradeService = Depends(get_sim_trade_service),
    user: UserORM = Depends(get_current_user),
) -> SimTradeOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        session_detail = replay_svc.get(session_id, instrument, user.id)
    except ReplayError as e:
        raise HTTPException(status_code=e.status, detail=e.message) from e

    bar_index = session_detail.info.bar_index
    current_bar_out = session_detail.bars[bar_index]

    from app.domain.bar import Bar, SessionType, Timeframe
    current_bar = Bar(
        instrument_id=instrument.instrument_id,
        timeframe=Timeframe.M5,
        ts_open_utc=current_bar_out.ts_open_utc,
        ts_close_utc=current_bar_out.ts_close_utc,
        open=current_bar_out.open,
        high=current_bar_out.high,
        low=current_bar_out.low,
        close=current_bar_out.close,
        volume=current_bar_out.volume,
        session=SessionType(current_bar_out.session),
        provider=instrument.provider,
        feed=instrument.feed,
        data_version="trade-runtime",
    )

    try:
        updated = trade_svc.manual_exit(trade_id, current_bar, bar_index, req)
        return SimTradeOut.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
