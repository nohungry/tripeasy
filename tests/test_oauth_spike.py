"""Spike：mock-oauth2-server 能不能替代 Google，讓 backend 的 Google 登入流程在本機跑通。"""
import os

import pytest
import requests

from conftest import MOCK_OAUTH_BASE, delete_user, mock_google_code

MOCK_EMAIL = "mock.user@example.com"


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
    claims = {
        "sub": "mock-google-001",
        "email": MOCK_EMAIL,
        "email_verified": False,
        "name": "Mock 使用者",
        "picture": "https://example.com/mock.png",
    }
    code = mock_google_code(claims)
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

    for key, value in claims.items():
        assert info[key] == value, key


def test_backend_google_login_via_mock(api, db, clean_mock_user):
    code = mock_google_code(
        {
            "sub": "mock-google-001",
            "email": MOCK_EMAIL,
            "email_verified": True,
            "name": "Mock 使用者",
            "picture": "https://example.com/mock.png",
        }
    )

    r = api.post("/api/v1/auth/userinfo/login/google", json={"code": code})

    assert r.status_code == 200, r.text
    row = db.execute(
        'SELECT u.name, u.login_method, s.provider_id, s.provider_token FROM "user" u '
        'JOIN "socialLogin" s ON s.user_id = u.user_id WHERE u.email = %s',
        (MOCK_EMAIL,),
    ).fetchone()
    assert row == ("Mock 使用者", 2, "mock-google-001", None)
