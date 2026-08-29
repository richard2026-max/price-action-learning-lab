"""FastAPI 应用工厂。核心领域逻辑不放在路由（编码原则）。"""

from __future__ import annotations

import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import (
    analytics,
    auth,
    coach,
    data,
    day_type,
    detectors,
    health,
    knowledge,
    replay,
    reviews,
    scanner,
    trades,
)
from app.core.config import REPO_ROOT, Settings
from app.core.logging import setup_logging
from app.db.session import init_db, make_engine, make_session_factory
from app.replay.service import ReplayService
from app.repositories.replay_repo import ReplayRepository
from app.repositories.scanner_repo import ScannerRepository
from app.repositories.sim_trade_repo import SimTradeRepository
from app.repositories.user_repo import UserRepository
from app.services.ai_coach_service import AICoachService
from app.services.analog_search_service import AnalogSearchService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService, TokenService, WeChatCode2SessionService
from app.services.calendar import default_calendar
from app.services.decision_review_service import DecisionContextExtractor
from app.services.knowledge_service import KnowledgeService
from app.services.market_data import MarketDataStore
from app.services.scanner_service import ScannerService
from app.services.sim_trade_service import SimTradeService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    setup_logging()

    # 生产守卫：非 debug 环境必须显式配置认证密钥，禁止静默使用随机临时密钥
    # （随机密钥会导致每次重启后所有已发放 token 失效）。
    if not settings.debug and not settings.auth_token_secret:
        raise RuntimeError(
            "PALL_AUTH_TOKEN_SECRET must be set when PALL_DEBUG=false "
            "(生产环境不允许使用随机临时密钥)"
        )

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
    token_secret = settings.auth_token_secret or secrets.token_urlsafe(32)
    app.state.auth_service = AuthService(
        UserRepository(factory), TokenService(token_secret, settings.auth_token_ttl_seconds)
    )
    app.state.wechat_code2session_service = WeChatCode2SessionService(
        app_id=settings.wechat_app_id,
        app_secret=settings.wechat_app_secret,
        base_url=settings.wechat_code2session_url,
    )
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
    app.state.analog_search_service = AnalogSearchService(store=app.state.store)
    app.state.knowledge_service = KnowledgeService(settings)
    app.state.ai_coach_service = AICoachService(app.state.knowledge_service, settings=settings)
    app.state.decision_context_extractor = DecisionContextExtractor(
        replay_service=app.state.replay_service,
        trade_repo=app.state.sim_trade_service._repo,
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(data.router, prefix="/api/v1")
    app.include_router(replay.router, prefix="/api/v1")
    app.include_router(detectors.router, prefix="/api/v1")
    app.include_router(scanner.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(trades.router, prefix="/api/v1")
    app.include_router(knowledge.router, prefix="/api/v1")
    app.include_router(coach.router, prefix="/api/v1")
    app.include_router(day_type.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")

    # 单进程模式：若前端构建产物存在，直接由后端伺服（本地单用户工具，免开 Vite dev）。
    dist = REPO_ROOT / "apps" / "web" / "dist"
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app


app = create_app()
