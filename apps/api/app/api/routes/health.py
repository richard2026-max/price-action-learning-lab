"""健康检查。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    settings = request.app.state.settings
    checks = {"sqlite": "ok", "data_dir": "ok"}
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        (settings.data_dir / ".write_test").write_text("ok", encoding="utf-8")
        (settings.data_dir / ".write_test").unlink()
    except OSError:
        checks["data_dir"] = "error"
    from sqlalchemy import text

    try:
        with request.app.state.session_factory() as s:
            s.execute(text("SELECT 1"))
    except Exception:
        checks["sqlite"] = "error"
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "version": __version__, "checks": checks}
