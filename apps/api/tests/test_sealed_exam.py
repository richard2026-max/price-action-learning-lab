"""封存考试集隔离保护与确定性划分测试。"""

from datetime import date

from app.services.sealed_exam import (
    get_exam_split_summary,
    is_sealed_exam_day,
    partition_days,
)


def test_sealed_exam_deterministic():
    d1 = date(2020, 3, 16)
    r1 = is_sealed_exam_day(d1)
    r2 = is_sealed_exam_day(d1)
    assert r1 == r2, "相同日期多次判定结果必须恒定"


def test_partition_days_split_ratio():
    # 模拟三年 750 个交易日
    from app.services.calendar import default_calendar

    cal = default_calendar()
    days = cal.trading_days(date(2019, 1, 1), date(2021, 12, 31))
    train, sealed = partition_days(days)

    assert len(train) + len(sealed) == len(days)
    ratio = len(sealed) / len(days)
    assert 0.10 <= ratio <= 0.20, f"封存比例应在 10%~20% 之间，实际: {ratio:.4f}"
    # 两个集合互斥
    assert set(train).isdisjoint(set(sealed))


def test_exam_split_summary():
    days = [date(2020, 1, i) for i in range(1, 25)]
    summary = get_exam_split_summary(days)
    assert summary["total_days"] == len(days)
    assert "years" in summary


def test_replay_api_blocks_sealed_day_in_free_mode(seeded_client):
    """验证普通回放创建请求试图加载封存日时，被服务端 403 严格拦截。"""
    from app.services.sealed_exam import is_sealed_exam_day

    # 查出一个封存日
    days_resp = seeded_client.get("/api/v1/replay/days?include_sealed=true").json()["days"]
    sealed_day = next(d for d in days_resp if is_sealed_exam_day(date.fromisoformat(d)))

    # 普通模式试图直接创建 -> 403 拦截
    r_bad = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": sealed_day, "mode": "free"},
    )
    assert r_bad.status_code == 403
    assert "sealed_exam_day_protected" in r_bad.text

    # 考试模式创建 -> 允许通过
    r_ok = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": sealed_day, "mode": "exam"},
    )
    assert r_ok.status_code == 200
