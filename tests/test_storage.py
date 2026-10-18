"""本機 storage adapter：頭像上傳後存在 volume，經由 /uploads 提供存取。"""
from urllib.parse import unquote, urlparse

import requests

from conftest import API_BASE, auth_header

PNG = b"\x89PNG\r\n\x1a\n" + b"tripeasy-p0-avatar"


def _upload_avatar(api, user, filename, content=PNG, mimetype="image/png"):
    return api.patch(
        "/api/v1/user/userinfo/avatar",
        headers=auth_header(user),
        files={"image": (filename, content, mimetype)},
    )


def test_avatar_upload_stored_locally(api, db, make_user):
    user = make_user()

    r = _upload_avatar(api, user, "avatar.png")

    assert r.status_code == 200, r.text
    url = r.json()["data"]["avatar_url"]
    assert url.startswith(f"{API_BASE}/uploads/userProfile/")
    got = requests.get(url, timeout=10)
    assert got.status_code == 200
    assert got.content == PNG
    (db_url,) = db.execute(
        'SELECT avatar_url FROM "user" WHERE user_id = %s', (user["user_id"],)
    ).fetchone()
    assert db_url == url


def test_upload_filename_cannot_escape_upload_dir(api, make_user):
    user = make_user()

    r = _upload_avatar(api, user, "../../../evil 圖.png")

    assert r.status_code == 200, r.text
    url = r.json()["data"]["avatar_url"]
    path = unquote(urlparse(url).path)
    assert path.startswith("/uploads/userProfile/")
    assert ".." not in path.split("/")
    assert requests.get(url, timeout=10).content == PNG


def test_uploaded_file_cannot_run_as_page(api, make_user):
    user = make_user()

    r = _upload_avatar(api, user, "x.html", b"<script>alert(1)</script>", "image/png")

    assert r.status_code == 200, r.text
    got = requests.get(r.json()["data"]["avatar_url"], timeout=10)
    assert got.headers["X-Content-Type-Options"] == "nosniff"
    csp = got.headers["Content-Security-Policy"]
    assert "sandbox" in csp and "default-src 'none'" in csp
