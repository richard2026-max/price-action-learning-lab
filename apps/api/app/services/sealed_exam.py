"""封存考试集（Sealed Exam Set）管理服务（Product / Learning Design, Early）。

原则（PRD §七.3、data-contracts §1.6）：
1. 确定性稳定划分（deterministic stable split）：Blake2b 哈希 + 分层抽样，不硬编码单一年份；
2. 隔离保护：普通 replay（GET /replay/days）、Scanner、普通查询一律默认排除封存日；
3. 考试模式专属：只有明确带 exam 授权（mode="exam"）的受管请求方可读取封存日；
4. 访问审计：任何封存日被访问或完成考试均在 SQLite 中持久化审计日志。
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from datetime import date

# 默认抽样比例：每个年份约 15% 的交易日作为盲测/封存考试集
DEFAULT_EXAM_RATIO = 0.15
SALT = "pall_sealed_exam_v1"


def is_sealed_exam_day(d: date, ratio: float = DEFAULT_EXAM_RATIO) -> bool:
    """根据确定性哈希判定某个日期是否为封存考试集。

    对同一日期与算法，结果永远保持恒定（跨版本稳定）。
    """
    key = f"{SALT}:{d.isoformat()}".encode()
    digest = hashlib.blake2b(key, digest_size=8).digest()
    val = int.from_bytes(digest, "big") / (1 << 64)
    return val < ratio


def partition_days(days: Sequence[date | str], ratio: float = DEFAULT_EXAM_RATIO) -> tuple[list[str], list[str]]:
    """将日期列表划分为 (普通训练日列表, 封存考试日列表)（均按升序排序）。"""
    training: list[str] = []
    sealed: list[str] = []
    for item in sorted(days):
        d = date.fromisoformat(item) if isinstance(item, str) else item
        iso = d.isoformat()
        if is_sealed_exam_day(d, ratio):
            sealed.append(iso)
        else:
            training.append(iso)
    return training, sealed


def get_exam_split_summary(days: Sequence[date | str]) -> dict[str, object]:
    """生成分年份的划分统计（用于数据质量与审计报告）。"""
    by_year: dict[int, list[str]] = defaultdict(list)
    for item in sorted(days):
        d = date.fromisoformat(item) if isinstance(item, str) else item
        by_year[d.year].append(d.isoformat())

    years_summary = []
    total_train = 0
    total_sealed = 0
    for y in sorted(by_year.keys()):
        train, sealed = partition_days(by_year[y])
        total_train += len(train)
        total_sealed += len(sealed)
        years_summary.append({
            "year": y,
            "total_days": len(by_year[y]),
            "training_days": len(train),
            "sealed_exam_days": len(sealed),
            "sealed_ratio": round(len(sealed) / len(by_year[y]), 4) if by_year[y] else 0.0,
        })

    return {
        "total_days": len(days),
        "total_training_days": total_train,
        "total_sealed_exam_days": total_sealed,
        "overall_sealed_ratio": round(total_sealed / len(days), 4) if days else 0.0,
        "years": years_summary,
    }
