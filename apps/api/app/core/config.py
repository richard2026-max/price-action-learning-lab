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

    # 认证：开发模式允许无 token 的旧 Web 自动映射到 legacy local user。
    auth_token_secret: str | None = None
    auth_token_ttl_seconds: int = 7 * 24 * 60 * 60
    legacy_local_user_enabled: bool = True
    wechat_app_id: str | None = None
    wechat_app_secret: str | None = None
    wechat_allowed_openids: str = ""
    wechat_code2session_url: str = "https://api.weixin.qq.com/sns/jscode2session"

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

    # ---- 学习资料目录（原书 + 中文课件，提前解析并本地增量索引）----
    # 原书目录（默认 AlBrooks书）
    books_dir: Path = REPO_ROOT.parent / "AlBrooks书"
    # 中文课件目录（默认 AlBrooks课件）
    courseware_dir: Path = REPO_ROOT.parent / "AlBrooks课件"
    # 知识库增量缓存索引文件
    knowledge_cache_path: Path = REPO_ROOT / "data" / "cache" / "knowledge_index.json"

    # ---- AI 教练（DeepSeek 优先；默认禁用）----
    ai_enabled: bool = False
    ai_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str | None = None
    ai_model: str = "deepseek-chat"
    ai_temperature: float = 0.2


def get_settings() -> Settings:
    return Settings()
