"""前端 dev server 可以存取、API base 已經注入、CORS 只允許前端的 origin。"""
import requests

from conftest import FRONTEND_BASE


def test_frontend_dev_server_serves_app():
    r = requests.get(f"{FRONTEND_BASE}/", timeout=10)
    assert r.status_code == 200
    assert 'id="app"' in r.text


def test_frontend_api_base_points_to_backend():
    # Vite dev server 會把 import.meta.env 換成實際的值，直接看轉譯後的 api.js
    r = requests.get(f"{FRONTEND_BASE}/src/utils/api.js", timeout=10)
    assert r.status_code == 200
    assert "http://localhost:3000" in r.text


def test_cors_allows_frontend_origin(api):
    r = api.options(
        "/api/v1/health",
        headers={
            "Origin": FRONTEND_BASE,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert r.status_code == 204
    assert r.headers["Access-Control-Allow-Origin"] == FRONTEND_BASE
    assert r.headers["Access-Control-Allow-Credentials"] == "true"


def test_cors_rejects_unknown_origin(api):
    r = api.get("/api/v1/health", headers={"Origin": "http://evil.example.com"})
    assert "Access-Control-Allow-Origin" not in r.headers
    assert api.get("/api/v1/health").status_code == 200


def test_cors_credentials_still_true(api):
    r = api.get("/api/v1/health", headers={"Origin": FRONTEND_BASE})
    assert r.headers["Access-Control-Allow-Credentials"] == "true"
