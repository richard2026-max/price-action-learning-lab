"""健康检查测试。"""


def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"]["sqlite"] == "ok"
    assert body["checks"]["data_dir"] == "ok"


def test_root(client):
    """单进程模式：/ 由前端构建产物伺服（dist 存在时返回 SPA 首页）。"""
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
