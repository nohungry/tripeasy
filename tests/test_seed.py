"""spec 3.2：fakedata 改寫成 Flyway repeatable migration，可以重複執行。"""
import re
import uuid

import jwt

from conftest import BUILD_SCRIPT, ROOT, load_build_seed

SEED = ROOT / "db" / "seed" / "R__seed.sql"

# fakedata（2025-05）每張表的筆數。測試可能另外新增資料，所以檢查「至少」
SEED_COUNTS = {
    "user": 3, "socialLogin": 3, "user_level": 3, "coupon": 5,
    "tour": 10, "tour_detail": 6, "restaurant": 2, "restaurant_business": 14,
    "restaurant_menu": 6, "hotel": 2, "hotel_room": 4, "notification": 4,
    "country": 37, "region": 87, "cart": 3, "cart_item": 6,
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


def test_seed_file_is_generated_from_source():
    # R__seed.sql 不能手動改：內容必須跟 build_seed.py 從來源檔產生的結果完全相同
    build_seed = load_build_seed()
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


V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
UUID_LITERAL = re.compile(r"'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'")
SEED_EMAILS = list(SEED_USERS)
COUPON_CODES = ["WEL100", "SUM050", "TRV010", "VIP300", "SPR020"]
# 契約 §0.1 第 7 項：被移除的購物車項目（來源檔的 cart_item_id）
REMOVED_CART_ITEMS = {
    "f0e74ade-183f-4648-b9fe-cbb23458b89c", "70cc5744-2a87-4193-b503-1a5c73dc0b0c",
    "4936201b-d691-460b-97d0-000afae599c3", "c4b9e4b5-d0e9-4e5b-8884-7b115b6877de",
}


def _source_inserts():
    build_seed = load_build_seed()
    text = build_seed.SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n")
    inserts = build_seed.parse_inserts(build_seed.drop_delete_block(text))
    return build_seed, {build_seed.bare(i.table): i for i in inserts}


def _source_rows(table):
    build_seed, source = _source_inserts()
    ins = source[table]
    return [
        {c: build_seed.unquote(v) if v.startswith("'") else v for c, v in zip(ins.columns, row)}
        for row in ins.rows
    ]


def test_seed_primary_keys_are_v4(db):
    pk = load_build_seed().PK_COLUMN
    bad = {}
    for table in SEED_COUNTS:
        ids = [r[0] for r in db.execute(f'SELECT {pk[table]}::text FROM "{table}"').fetchall()]
        wrong = [i for i in ids if not V4.match(i)]
        if wrong:
            bad[table] = wrong[:2]
    assert not bad, f"主鍵不是 v4：{bad}"


def test_seed_natural_keys_are_not_duplicated(db):
    titles = [r["title"] for r in _source_rows("tour")]
    countries = [r["name"] for r in _source_rows("country")]
    for column, table, values in (
        ("email", "user", SEED_EMAILS), ("code", "coupon", COUPON_CODES),
        ("title", "tour", titles), ("name", "country", countries),
    ):
        rows = db.execute(
            f'SELECT {column}, count(*) FROM "{table}" WHERE {column} = ANY(%s) GROUP BY {column}',
            (values,),
        ).fetchall()
        assert dict(rows) == {v: 1 for v in values}, f"{table}.{column}：{rows}"


def test_seed_coupon_codes_match_validator(db):
    # discounts_Validatior.js:9–13
    codes = [r[0] for r in db.execute("SELECT code FROM coupon").fetchall()]
    assert set(COUPON_CODES) <= set(codes)
    assert [c for c in codes if not re.fullmatch(r"[A-Z0-9]{6}", c)] == []


def test_seed_one_cart_per_user(db):
    rows = db.execute(
        'SELECT u.email, count(c.cart_id) FROM "user" u LEFT JOIN cart c USING (user_id)'
        " WHERE u.email = ANY(%s) GROUP BY u.email",
        (SEED_EMAILS,),
    ).fetchall()
    assert dict(rows) == {e: 1 for e in SEED_EMAILS}


def test_seed_foreign_keys_follow_column_owner(db):
    # 同一個舊字面值是好幾張表的主鍵；外鍵必須依欄位名稱對到正確的表
    build_seed = load_build_seed()
    old_title = {r["tour_id"]: r["title"] for r in _source_rows("tour")}
    old_email = {r["user_id"]: r["email"] for r in _source_rows("user")}

    for table, pk, skip in (
        ("cart_item", "cart_item_id", REMOVED_CART_ITEMS), ("order_item", "order_item_id", set()),
    ):
        expected = {
            build_seed.seed_id(table, r[pk]): old_title[r["tour_id"]]
            for r in _source_rows(table) if r[pk] not in skip
        }
        actual = dict(db.execute(
            f'SELECT t."{pk}"::text, tour.title FROM "{table}" t JOIN tour USING (tour_id)'
        ).fetchall())
        found = {k: v for k, v in actual.items() if k in expected}
        assert found == expected, f"{table}：{set(expected.items()) ^ set(found.items())}"

    expected = {(old_email[r["user_id"]], old_title[r["tour_id"]]) for r in _source_rows("favorite")}
    actual = set(db.execute(
        'SELECT u.email, tour.title FROM favorite f JOIN tour USING (tour_id) JOIN "user" u USING (user_id)'
    ).fetchall())
    assert expected <= actual


def test_seed_source_ids_are_all_remapped():
    build_seed = load_build_seed()
    source = set(UUID_LITERAL.findall(build_seed.SOURCE.read_text(encoding="utf-8").lower()))
    leaked = {i for i in source if i in SEED.read_text(encoding="utf-8").lower()}
    assert source and not leaked, f"R__seed.sql 還有來源檔的 id：{sorted(leaked)[:3]}"
