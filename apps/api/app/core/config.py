"""应用配置。配置与代码分离；密钥仅从环境变量 / .env 加载，不入 Git、不入日志。"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根目录 = apps/api/app/core/config.py 的上四级
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """全局设置。所有路径与密钥都可被环境变量覆盖（前缀 PALL_）。"""

    model_config = SettingsConfigDict(
        env_prefix="PALL_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Price Action Learning Lab"
    debug: bool = True

    # 本地数据目录（默认仓库 data/）
    data_dir: Path = REPO_ROOT / "data"

    # SQLite 应用数据库（WAL 模式在 db/session.py 中设置）
    sqlite_path: Path = REPO_ROOT / "data" / "app.sqlite"

    # 合成数据生成种子（可复现性：同种子 + 同参数 => 同数据）
    synthetic_seed: int = 20260816

    # ---- 数据源密钥（市场数据密钥；与任何交易权限密钥在设计上无关，本项目不保存交易密钥）----
    alpaca_key_id: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_feed: str = "iex"  # iex（免费层）/ sip；feed 记录进 manifest，不静默混用

    # ---- HF Data Library（免费 SPY 1m 历史数据；CC BY 4.0，需注明出处）----
    hfdl_api_key: str | None = None
    hfdl_base_url: str = "https://api.hfdatalibrary.com/v1"

    # AI 默认禁用（Product 边界：AI 关闭时核心功能正常）
    ai_enabled: bool = False


def get_settings() -> Settings:
    return Settings()
