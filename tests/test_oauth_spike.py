"""Spike：mock-oauth2-server 能不能替代 Google，讓 backend 的 Google 登入流程在本機跑通。"""
import os
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from conftest import MOCK_OAUTH_BASE, delete_user

MOCK_EMAIL = "mock.user@example.com"


def _get_code():
    r = requests.get(
        f"{MOCK_OAUTH_BASE}/google/authorize",
        params={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
            "response_type": "code",
            "scope": "openid email profile",
            "state": "p0",
        },
        allow_redirects=False,
        timeout=10,
    )
    assert r.status_code == 302, r.text
    return parse_qs(urlparse(r.headers["Location"]).query)["code"][0]


@pytest.fixture
def clean_mock_user(db):
    def _clean():
        row = db.execute('SELECT user_id FROM "user" WHERE email = %s', (MOCK_EMAIL,)).fetchone()
        if row:
            delete_user(db, str(row[0]))

    _clean()
    yield
    _clean()


def test_mock_oauth_issues_google_like_claims():
    code = _get_code()
    token = requests.post(
        f"{MOCK_OAUTH_BASE}/google/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
        },
        timeout=10,
    )
    assert token.status_code == 200, token.text

    info = requests.get(
        f"{MOCK_OAUTH_BASE}/google/userinfo",
        headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        timeout=10,
    ).json()

    assert info["sub"] == "mock-google-001"
    assert info["email"] == MOCK_EMAIL
    assert info["name"] == "Mock 使用者"


@pytest.mark.xfail(strict=True, reason="socialLogin.provider_token 為 VARCHAR(255)，放不下 JWT access token；P2 以 migration 修正")
def test_backend_google_login_via_mock(api, db, clean_mock_user):
    code = _get_code()

    r = api.post("/api/v1/auth/userinfo/login/google", json={"code": code})

    assert r.status_code == 200, r.text
    row = db.execute(
        'SELECT name, login_method FROM "user" WHERE email = %s', (MOCK_EMAIL,)
    ).fetchone()
    assert row == ("Mock 使用者", 2)
