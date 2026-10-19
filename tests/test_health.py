def test_health_ok(api):
    r = api.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
