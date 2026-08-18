"""FastAPI 应用工厂。核心领域逻辑不放在路由（编码原则）。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import analytics, data, detectors, health, replay, scanner, trades
from app.core.config import REPO_ROOT, Settings
from app.core.logging import setup_logging
from app.db.session import init_db, make_engine, make_session_factory
from app.replay.service import ReplayService
from app.repositories.replay_repo import ReplayRepository
from app.repositories.scanner_repo import ScannerRepository
from app.repositories.sim_trade_repo import SimTradeRepository
from app.services.analytics_service import AnalyticsService
from app.services.calendar import default_calendar
from app.services.market_data import MarketDataStore
from app.services.scanner_service import ScannerService
from app.services.sim_trade_service import SimTradeService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = make_engine(settings.sqlite_path)
    init_db(engine)
    factory = make_session_factory(engine)

    sim_trade_svc = SimTradeService(repo=SimTradeRepository(factory))

    app.state.settings = settings
    app.state.session_factory = factory
    app.state.store = MarketDataStore(settings.data_dir)
    app.state.synth_seed = settings.synthetic_seed
    app.state.sim_trade_service = sim_trade_svc
    app.state.replay_service = ReplayService(
        store=app.state.store,
        calendar=default_calendar(),
        repo=ReplayRepository(factory),
        trade_service=sim_trade_svc,
    )
    app.state.scanner_service = ScannerService(
        store=app.state.store, calendar=default_calendar(), repo=ScannerRepository(factory)
    )
    app.state.analytics_service = AnalyticsService(factory=factory)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(data.router, prefix="/api/v1")
    app.include_router(replay.router, prefix="/api/v1")
    app.include_router(detectors.router, prefix="/api/v1")
    app.include_router(scanner.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(trades.router, prefix="/api/v1")

    # 单进程模式：若前端构建产物存在，直接由后端伺服（本地单用户工具，免开 Vite dev）。
    dist = REPO_ROOT / "apps" / "web" / "dist"
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app


app = create_app()
