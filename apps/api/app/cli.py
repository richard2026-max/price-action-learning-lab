"""本地 CLI（Typer）。示例：

    python -m app.cli data seed --start 2024-01-02 --end 2024-01-31
    python -m app.cli data ingest-hfdl --start 2019-01-02 --end 2021-12-31
    python -m app.cli data datasets
    python -m app.cli api dev
"""

from __future__ import annotations

from datetime import date

import typer

from app.core.config import Settings

app_cli = typer.Typer(help="Price Action Learning Lab 本地工具", no_args_is_help=True)
data_app = typer.Typer(help="数据管理", no_args_is_help=True)
app_cli.add_typer(data_app, name="data")


@data_app.command("seed")
def seed(
    start: str = typer.Option(..., help="YYYY-MM-DD"),
    end: str = typer.Option(..., help="YYYY-MM-DD"),
    seed_value: int | None = typer.Option(None, "--seed", help="覆盖默认种子"),
) -> None:
    """生成合成 SPY 1m 数据并聚合为 5m（幂等）。"""
    from app.api.routes.data import seed as seed_ep  # 复用同一服务逻辑
    from app.schemas.data import SeedIn

    settings = Settings()
    s = seed_ep(
        SeedIn(start=start, end=end, seed=seed_value),
        store=_store(settings),
        synth_seed=settings.synthetic_seed,
    )
    typer.echo(
        f"交易日 {s.days} 天 | 1m {s.bars_1m} 根 (重复剔除 {s.duplicate_count_1m}) | "
        f"5m {s.bars_5m} 根 (重复剔除 {s.duplicate_count_5m})"
    )
    typer.echo(f"5m manifest: {s.manifest_5m}")


@data_app.command("ingest-hfdl")
def ingest_hfdl(
    start: str = typer.Option(..., help="YYYY-MM-DD（含）"),
    end: str = typer.Option(..., help="YYYY-MM-DD（含）"),
    redownload: bool = typer.Option(False, help="忽略缓存重新下载全历史 Parquet"),
) -> None:
    """从 HF Data Library 下载真实 SPY 1m 并聚合 5m 入库（幂等）。

    首次运行会下载约 50MB 全历史文件到 data/imports/，之后复用缓存。
    建议训练语料优先用 2022-03 之前的日期（合并磁带时期，精度最佳）。
    """
    import json as _json

    from app.core.config import REPO_ROOT
    from app.data_providers.hfdl_provider import HFDLError, HFDLProvider, verify_splice_boundary
    from app.domain.instrument import SPY_HFDL
    from app.services.ingest import ingest_bars
    from app.services.market_data import MarketDataStore

    settings = Settings()
    try:
        provider = HFDLProvider(
            api_key=settings.hfdl_api_key,
            base_url=settings.hfdl_base_url,
            cache_dir=REPO_ROOT / "data" / "imports",
        )
    except HFDLError as e:
        typer.echo(f"错误: {e}")
        raise typer.Exit(1) from None

    s, e_ = date.fromisoformat(start), date.fromisoformat(end)
    if redownload:
        cache = REPO_ROOT / "data" / "imports" / "hfdl_SPY_clean.parquet"
        cache.unlink(missing_ok=True)

    try:
        bars_1m = provider.fetch_1m_bars(SPY_HFDL, s, e_)
    except HFDLError as exc:
        typer.echo(f"下载/解析失败: {exc}")
        typer.echo("提示：若提示 complete your profile，请先登录 hfdatalibrary.com 补全资料。")
        raise typer.Exit(1) from None

    store = MarketDataStore(settings.data_dir)
    result = ingest_bars(store, SPY_HFDL, bars_1m, s, e_)
    diag = verify_splice_boundary(bars_1m)
    typer.echo(
        f"交易日 {result['days']} 天 | 1m {result['bars_1m']} 根 | 5m {result['bars_5m']} 根 | "
        f"去重 1m/5m: {result['duplicate_1m']}/{result['duplicate_5m']}"
    )
    typer.echo(f"精度诊断(splice 边界): {_json.dumps(diag, ensure_ascii=False)}")
    m5 = next(
        (m for m in store.list_datasets() if m["provider"] == "hfdl" and m["timeframe"] == "5m"),
        None,
    )
    typer.echo(f"5m manifest: {_json.dumps(m5, ensure_ascii=False)}")
    typer.echo("数据来源: HF Data Library (hfdatalibrary.com), CC BY 4.0")


@data_app.command("datasets")
def datasets() -> None:
    import json

    for m in _store(Settings()).list_datasets():
        typer.echo(json.dumps(m, ensure_ascii=False, indent=2))


@data_app.command("calendar")
def calendar(
    start: str = typer.Option(...), end: str = typer.Option(...), early: bool = typer.Option(False)
) -> None:
    from app.services.calendar import XNYSCalendar

    cal = XNYSCalendar()
    days = cal.trading_days(date.fromisoformat(start), date.fromisoformat(end))
    typer.echo(f"交易日 {len(days)} 天")
    if early:
        for d in days:
            mark = "  (early close 13:00)" if cal.is_early_close(d) else ""
            typer.echo(f"  {d}{mark}")
    else:
        typer.echo("  " + ", ".join(d.isoformat() for d in days))


@app_cli.command("api")
def api_dev(host: str = "127.0.0.1", port: int = 8000, reload: bool = True) -> None:
    """启动开发服务器。"""
    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


def _store(settings: Settings):
    from app.services.market_data import MarketDataStore

    return MarketDataStore(settings.data_dir)


def main() -> None:
    app_cli()


if __name__ == "__main__":
    main()
