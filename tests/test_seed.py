"""spec 3.2：fakedata 改寫成 Flyway repeatable migration，可以重複執行。"""
import importlib.util
import re
import uuid

import jwt

from conftest import ROOT

SEED = ROOT / "db" / "seed" / "R__seed.sql"

# fakedata（2025-05）每張表的筆數。測試可能另外新增資料，所以檢查「至少」
SEED_COUNTS = {
    "user": 3, "socialLogin": 3, "user_level": 3, "coupon": 5,
    "tour": 10, "tour_detail": 6, "restaurant": 2, "restaurant_business": 14,
    "restaurant_menu": 6, "hotel": 2, "hotel_room": 4, "notification": 4,
    "country": 37, "region": 87, "cart": 6, "cart_item": 10,
    "orders": 5, "order_item": 10, "review": 10, "hidden_play": 6,
    "auto_setting": 4, "favorite": 7, "point_record": 2, "user_coupon": 4,
}


def _counts(conn) -> dict:
    return {
        t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in SEED_COUNTS
    }


def test_flyway_applied_seed(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history "
        "WHERE script = 'R__seed.sql' ORDER BY installed_rank DESC LIMIT 1"
    ).fetchone()
    assert row == (True,)


def test_seed_loaded_every_table(db):
    counts = _counts(db)
    short = {t: (counts[t], n) for t, n in SEED_COUNTS.items() if counts[t] < n}
    assert not short, f"（實際, 預期至少）：{short}"


def test_seed_is_rerunnable(tx):
    # 模擬「volume 還在、seed 內容改過」：Flyway 會把整份 seed 再跑一次
    before = _counts(tx)
    tx.execute(SEED.read_text(encoding="utf-8"))
    assert _counts(tx) == before


SEED_PASSWORD = "Tripeasy123"  # 跟 .env.example 的註解一致
SEED_USERS = {"alice@example.com": "User", "bob@example.com": "admin", "carol@example.com": "User"}
IMAGE_NAMES = ("tour", "feature", "hidden", "badge", "avatar")
BUILD_SCRIPT = ROOT / "db" / "seed-build" / "build_seed.py"


def test_seed_file_is_generated_from_source():
    # R__seed.sql 不能手動改：內容必須跟 build_seed.py 從來源檔產生的結果完全相同
    spec = importlib.util.spec_from_file_location("build_seed", BUILD_SCRIPT)
    build_seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_seed)
    expected = build_seed.build(build_seed.SOURCE.read_text(encoding="utf-8"))
    assert SEED.read_text(encoding="utf-8") == expected


def _login(api, email):
    return api.post(
        "/api/v1/auth/userinfo/login/email", json={"email": email, "password": SEED_PASSWORD}
    )


def test_seed_user_can_login(api):
    r = _login(api, "alice@example.com")
    assert r.status_code == 200, r.text


def test_seed_roles_match_authorize_roles(db):
    rows = db.execute(
        'SELECT email, role FROM "user" WHERE email = ANY(%s)', (list(SEED_USERS),)
    ).fetchall()
    assert dict(rows) == SEED_USERS


def test_seed_admin_passes_authorize_roles(api):
    r = _login(api, "bob@example.com")
    assert r.status_code == 200, r.text
    token = r.json()["data"]["token"]  # resStatus 把 dbdata 放在 data 底下
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["role"] == "admin"

    r = api.patch(
        "/api/v1/admin/product/status",
        headers={"Authorization": f"Bearer {token}"},
        # UUIDField 只接受 v4 / v5，不能用全 0 的 UUID
        json={"tour_ids": [str(uuid.uuid4())], "tour_status": "1"},
    )
    assert r.status_code == 404, r.text  # 過了 authRole('admin')，走到「查無此項目」


def test_seed_dates_are_relative_to_load_day(db):
    # 日期在 seed 載入那天平移一次；之後 ON CONFLICT DO NOTHING 不會再更新，
    # 所以基準是「載入那天」，不是「今天」。保留 volume 太久，資料自然會過期
    (load_day,) = db.execute(
        "SELECT min(installed_on)::date FROM flyway_schema_history"
        " WHERE script = 'R__seed.sql' AND success"
    ).fetchone()
    assert load_day is not None, "Flyway 沒有載入過 seed"
    (past_tours,) = db.execute(
        "SELECT count(*) FROM tour WHERE tour_start_date < %s", (load_day,)
    ).fetchone()
    (expired_coupons,) = db.execute(
        "SELECT count(*) FROM coupon WHERE expire_date < %s", (load_day,)
    ).fetchone()
    assert (past_tours, expired_coupons) == (0, 0)


def test_seed_uses_local_placeholder_images(api):
    text = SEED.read_text(encoding="utf-8")
    assert not re.search(r"https://example\.com/(images|avatar|badges|feature|hidden)/", text)
    for name in IMAGE_NAMES:
        r = api.get(f"/uploads/seed/{name}.svg")
        assert r.status_code == 200, name
        assert r.headers["Content-Type"].startswith("image/svg+xml")
