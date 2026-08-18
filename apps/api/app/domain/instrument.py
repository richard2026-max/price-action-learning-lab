"""Instrument Metadata（数据合同 §1.2）。以 "one tick" 为依据的 detector 必须依赖此元数据。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: str
    symbol: str
    provider: str
    feed: str
    tick_size: float
    price_precision: int
    tick_value: float
    contract_multiplier: float
    quote_currency: str
    calendar_id: str
    session_definition: str
    quote_side: str
    feed_consolidated: bool


# 第一阶段唯一正式训练品种（Product Design 决策，见 content-provenance-policy §八）
SPY_SYNTH = Instrument(
    instrument_id="SPY",
    symbol="SPY",
    provider="synthetic",
    feed="synthetic-v1",
    tick_size=0.01,
    price_precision=2,
    tick_value=0.01,
    contract_multiplier=1.0,
    quote_currency="USD",
    calendar_id="XNYS",
    session_definition="premarket 04:00-09:30 / rth 09:30-16:00 ET (13:00 early close)",
    quote_side="last",
    feed_consolidated=False,
)

SPY_ALPACA = Instrument(
    instrument_id="SPY",
    symbol="SPY",
    provider="alpaca",
    feed="iex",  # 免费层默认；feed 记录进 manifest，不与 sip 静默混用（OQ-01 待验证一跳精度）
    tick_size=0.01,
    price_precision=2,
    tick_value=0.01,
    contract_multiplier=1.0,
    quote_currency="USD",
    calendar_id="XNYS",
    session_definition="premarket 04:00-09:30 / rth 09:30-16:00 ET (13:00 early close)",
    quote_side="last",
    feed_consolidated=False,
)

# HF Data Library 来源的 SPY（免费历史 1m；仅 RTH；复权价格；无盘前）
# 时段精度说明：2002~2022-03 为合并磁带（CTA/UTP，全市场），之后为 IEX 单所（OQ-01 待验证）
SPY_HFDL = Instrument(
    instrument_id="SPY",
    symbol="SPY",
    provider="hfdl",
    feed="pitrading-cta-utp_to_iex_splice",
    tick_size=0.0001,  # 复权价格不在 0.01 网格上
    price_precision=4,
    tick_value=0.0001,
    contract_multiplier=1.0,
    quote_currency="USD",
    calendar_id="XNYS",
    session_definition="rth 09:30-16:00 ET only (no premarket in this source)",
    quote_side="last",
    feed_consolidated=True,  # 2022-03 前为合并磁带；之后 IEX（splice 边界见 manifest data_version）
)

REGISTRY: dict[tuple[str, str], Instrument] = {
    (SPY_SYNTH.instrument_id, SPY_SYNTH.provider): SPY_SYNTH,
    (SPY_ALPACA.instrument_id, SPY_ALPACA.provider): SPY_ALPACA,
    (SPY_HFDL.instrument_id, SPY_HFDL.provider): SPY_HFDL,
}


def get_instrument(instrument_id: str, provider: str) -> Instrument:
    key = (instrument_id, provider)
    if key not in REGISTRY:
        raise KeyError(f"unknown instrument/provider: {key}")
    return REGISTRY[key]
