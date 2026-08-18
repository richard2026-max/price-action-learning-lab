"""结构化日志（JSON 行）。禁止把 API 密钥、书籍正文写入日志。"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_REDACT_KEYS = {"alpaca_key_id", "alpaca_secret_key", "api_key", "secret", "token"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra = getattr(record, "ctx", None)
        if isinstance(extra, dict):
            payload["ctx"] = {k: ("***" if k in _REDACT_KEYS else v) for k, v in extra.items()}
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
