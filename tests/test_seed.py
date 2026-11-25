"""spec 3.2：fakedata 改寫成 Flyway repeatable migration，可以重複執行。"""
import json
import math
import re
import uuid
from collections import Counter, defaultdict
from typing import NamedTuple

import jwt

from conftest import BUILD_SCRIPT, ROOT, load_build_seed

SEED = ROOT / "db" / "seed" / "R__seed.sql"

# 每張表的確切筆數（契約 §0.1 seed 目標值第 1 項；契約沒列的子表筆數由 extra_seed.sql 決定）。
# 重複的 volume 或殘留的舊列都會讓筆數不符，所以用 exact count
SEED_COUNTS = {
    "user": 3, "socialLogin": 3, "user_level": 3, "coupon": 5,
    "tour": 23, "tour_detail": 19, "restaurant": 5, "restaurant_business": 35,
    "restaurant_menu": 12, "hotel": 6, "hotel_room": 12, "notification": 9,
    "country": 37, "region": 87, "cart": 3, "cart_item": 6,
    "orders": 20, "order_item": 20, "payment": 15, "review": 13, "hidden_play": 6,
    "auto_setting": 4, "favorite": 9, "point_record": 18, "user_coupon": 4,
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
    wrong = {t: (counts[t], n) for t, n in SEED_COUNTS.items() if counts[t] != n}
    assert not wrong, f"（實際, 預期）：{wrong}"


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
    expected = build_seed.build(
        build_seed.SOURCE.read_text(encoding="utf-8"), build_seed.EXTRA.read_text(encoding="utf-8")
    )
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
    # 契約 §0.1 第 2 項：確切偏移，不只是「不早於載入日」
    rows = db.execute("SELECT code, expire_date::date - %s FROM coupon", (load_day,)).fetchall()
    assert dict(rows) == COUPON_EXPIRE_DAYS
    (earliest,) = db.execute("SELECT min(expire_date)::date - %s FROM coupon", (load_day,)).fetchone()
    assert earliest == min(COUPON_EXPIRE_DAYS.values())


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
# 契約 §0.1 第 2 項：expire_date 相對載入日的天數
COUPON_EXPIRE_DAYS = {"SPR020": 11, "SUM050": 103, "TRV010": 133, "WEL100": 225, "VIP300": 225}
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

    # order_item 已改成重建（契約 §0.1 第 9 項的 20 張訂單），期望值取自契約的訂單表
    for table, pk, expected in (
        ("cart_item", "cart_item_id", {
            build_seed.seed_id("cart_item", r["cart_item_id"]): old_title[r["tour_id"]]
            for r in _source_rows("cart_item") if r["cart_item_id"] not in REMOVED_CART_ITEMS
        }),
        ("order_item", "order_item_id", {
            build_seed.seed_id("order_item", f"{EMAIL[o.user]}:{o.title}"): o.title for o in ORDERS
        }),
    ):
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


# ---- 資料目標（契約 §0.1「seed 目標值（定案）」第 3–11 項）----
EMAIL = {"alice": "alice@example.com", "bob": "bob@example.com", "carol": "carol@example.com"}
HOKKAIDO, MALDIVES, ITALY, NZ = "北海道雪景 5 日深度遊", "馬爾地夫蜜月天堂 6 日", "義大利深度文化之旅", "紐西蘭壯麗景觀自駕遊"
OSAKA, KAOHSIUNG, PARIS, SEOUL = "大阪美食自由行", "高雄夜市美食攻略", "巴黎歷史建築巡禮", "首爾咖啡文青小旅行"
BANGKOK, OKINAWA, CHIANG_MAI = "曼谷設計旅店探索", "沖繩海景度假旅店", "清邁自然旅宿體驗"
ICELAND, SWISS, SPAIN = "冰島極光 8 日探索", "瑞士鐵道山岳 7 日", "西班牙陽光巡禮 9 日"
TAINAN, KYOTO = "台南小吃巡禮", "京都古寺散步"

# 第 3 項：(type, item) → status = 1 的行程
TOURS_BY_GROUP = {
    ("tourgroup", "travel"): {HOKKAIDO, MALDIVES, ITALY, NZ, ICELAND, SWISS, SPAIN},
    ("backpacker", "food"): {OSAKA, KAOHSIUNG, TAINAN, "東京拉麵地圖", "曼谷街頭美食"},
    ("backpacker", "spot"): {PARIS, SEOUL, KYOTO, "倫敦博物館漫遊", "新加坡花園城市導覽"},
    ("backpacker", "hotel"): {BANGKOK, OKINAWA, "峇里島別墅旅宿", "河內古城精品旅店", "釜山海岸旅店"},
}


class Order(NamedTuple):
    n: int
    user: str
    title: str
    status: int
    quantity: int
    total: int
    item_discount: int | None
    payment_type: str | None
    discount_type: str | None
    discount: int | None  # orders.discount_price

    @property
    def days_ago(self) -> int:  # 第 9 項「訂單時間」
        return {1: 9, 2: 8, 3: 7, 4: 4, 5: 3}.get(self.n, 36 - self.n)


# 第 9 項的 20 張訂單
ORDERS = [Order(*row) for row in (
    (1, "alice", HOKKAIDO, 1, 1, 45000, 40500, "credit_card", "none", None),
    (2, "bob", HOKKAIDO, 1, 1, 45000, 40500, "credit_card", "coupon", 40490),
    (3, "carol", HOKKAIDO, 1, 1, 45000, 40500, "credit_card", "none", None),
    (4, "alice", MALDIVES, 1, 1, 98000, 83300, "credit_card", "coupon", 83000),
    (5, "carol", MALDIVES, 1, 1, 98000, 83300, "atm", "none", None),
    (6, "bob", NZ, 1, 1, 85000, None, "credit_card", "coupon", 84700),
    (7, "alice", KAOHSIUNG, 1, 2, 8400, None, "credit_card", "point", 8200),
    (8, "bob", KAOHSIUNG, 1, 3, 12600, None, "cvs", "none", None),
    (9, "carol", OSAKA, 1, 2, 30000, None, "credit_card", "point", 29680),
    (10, "alice", SEOUL, 1, 2, 19000, None, "credit_card", "none", None),
    (11, "carol", SEOUL, 1, 1, 9500, None, "credit_card", "none", None),
    (12, "bob", PARIS, 1, 1, 22000, None, "credit_card", "none", None),
    (13, "bob", BANGKOK, 1, 2, 18000, None, "credit_card", "point", 17600),
    (14, "carol", BANGKOK, 1, 1, 9000, None, "credit_card", "none", None),
    (15, "alice", OKINAWA, 1, 2, 17600, None, "credit_card", "none", None),
    (16, "alice", ITALY, -1, 1, 72000, None, None, None, None),
    (17, "bob", OSAKA, 0, 1, 15000, None, "atm", "none", None),
    (18, "carol", NZ, 2, 1, 85000, None, "credit_card", "none", None),
    (19, "carol", PARIS, 3, 1, 22000, None, "credit_card", "none", None),
    (20, "alice", NZ, 4, 1, 85000, None, "cvs", "none", None),
)]
ADDRESS_PHONE = {
    "alice": ("台北市中山區南京東路3段123號", "0987654321"),
    "bob": ("高雄市鼓山區美術館路45號", "0912345678"),
    "carol": ("台中市西區公益路321巷9號", "0987654321"),
}
# 第 5 項：購買數（order_item.payment_status = 1 的列數）與收藏數；沒列出的行程都是 0
PURCHASES = {
    HOKKAIDO: 3, MALDIVES: 2, NZ: 1, KAOHSIUNG: 2, OSAKA: 1, SEOUL: 2, PARIS: 1, BANGKOK: 2, OKINAWA: 1,
}
FAVORITE_COUNTS = {MALDIVES: 3, HOKKAIDO: 2, NZ: 1, OSAKA: 1, PARIS: 1, BANGKOK: 1}
# 第 8 項：(使用者, 行程, created_at 減幾天)
FAVORITES = {
    ("alice", NZ, 10), ("alice", MALDIVES, 7), ("alice", OSAKA, 3), ("alice", HOKKAIDO, 1),
    ("bob", HOKKAIDO, 9), ("bob", PARIS, 5), ("bob", MALDIVES, 2),
    ("carol", MALDIVES, 8), ("carol", BANGKOK, 4),
}
# 第 6 項：(開始, 結束) 相對載入日的天數
PROMOS = {
    HOKKAIDO: (-10, 20), MALDIVES: (-5, 25), ICELAND: (-7, 14), SWISS: (-3, 30), SPAIN: (-1, 7),
    TAINAN: (10, 40), KYOTO: (-40, -10),
}
# 第 6 項最後一點：tourgroup/travel 的開始日與天數
TRAVEL_STARTS = {
    HOKKAIDO: (195, 5), MALDIVES: (174, 6), NZ: (169, 11), ITALY: (148, 8),
    ICELAND: (220, 8), SWISS: (100, 7), SPAIN: (60, 9),
}
# 第 7 項：保留的購物車項目 (使用者, 行程) → (start_date, end_date) 相對載入日的天數
CART_ITEMS = {
    ("alice", OSAKA): (30, None), ("bob", KAOHSIUNG): (14, None), ("bob", ITALY): (148, 155),
    ("bob", NZ): (169, 179), ("carol", MALDIVES): (174, 179), ("carol", PARIS): (20, 21),
}
# 第 11 項：web 評論 (使用者, created_at 減幾天)
WEB_REVIEWS = {("alice", 5), ("bob", 4), ("carol", 3), ("alice", 2), ("bob", 1)}

LOAD_TS = (
    "(SELECT min(installed_on) FROM flyway_schema_history WHERE script = 'R__seed.sql' AND success)"
)


def _load_day(db):
    return db.execute(f"SELECT {LOAD_TS}::date").fetchone()[0]


def _days_ago(column: str) -> str:
    """載入時間減 column 的天數（四捨五入到整天；載入時間取 Flyway 記錄的 installed_on）。

    已知限制：installed_on 是 migrate 結束後記錄、不含時區的時間，seed 的 CURRENT_TIMESTAMP 是交易開始時間；
    migrate 跨過午夜，或 Flyway 與測試連線的時區不同，日期類斷言會差一天。遇到差一天的失敗先看這裡。
    """
    return f"round(extract(epoch FROM ({LOAD_TS} - {column}::timestamp)) / 86400)::int"


def test_seed_home_sections_have_two_pages(db):
    # 第 3 項：limit=4 時每個首頁區塊都要有第 2 頁（至少 5 列）
    rows = db.execute(
        "SELECT type, item, count(*) FROM tour WHERE status = 1 GROUP BY type, item"
    ).fetchall()
    assert {(t, i): n for t, i, n in rows} == {k: len(v) for k, v in TOURS_BY_GROUP.items()}
    assert all(len(v) >= 5 for v in TOURS_BY_GROUP.values())
    rows = db.execute("SELECT type, item, title FROM tour WHERE status = 1").fetchall()
    found = defaultdict(set)
    for t, i, title in rows:
        found[(t, i)].add(title)
    assert dict(found) == TOURS_BY_GROUP
    # 促銷區塊：tourgroup/travel、通知類型 促銷、載入日在期間內 → 5 列（4＋1）
    (n,) = db.execute(
        "SELECT count(*) FROM tour t JOIN notification n USING (tour_id)"
        " WHERE t.type = 'tourgroup' AND t.item = 'travel' AND t.status = 1 AND n.type = '促銷'"
        " AND n.start_date::date <= %s AND n.end_date::date >= %s",
        (_load_day(db), _load_day(db)),
    ).fetchone()
    assert n == 5


def test_seed_search_list_has_two_pages(db):
    # 第 4 項：status = 1 共 22 個（limit 10 → 3 頁），status = 2 共 1 個
    rows = db.execute("SELECT status, count(*) FROM tour GROUP BY status").fetchall()
    assert dict(rows) == {1: 22, 2: 1}
    (title,) = db.execute("SELECT title FROM tour WHERE status = 2").fetchone()
    assert title == CHIANG_MAI


def test_seed_rankings_are_distinct(db):
    # 第 5 項：購買數、收藏數的確切值，且每組都有 3 個以上不同的購買數
    purchases = dict(db.execute(
        "SELECT t.title, count(*) FROM order_item oi JOIN tour t USING (tour_id)"
        " WHERE oi.payment_status = 1 GROUP BY t.title"
    ).fetchall())
    assert purchases == PURCHASES
    favorites = dict(db.execute(
        "SELECT t.title, count(*) FROM favorite f JOIN tour t USING (tour_id) GROUP BY t.title"
    ).fetchall())
    assert favorites == FAVORITE_COUNTS
    for group, titles in TOURS_BY_GROUP.items():
        assert len({PURCHASES.get(t, 0) for t in titles}) >= 3, group
    travel = TOURS_BY_GROUP[("tourgroup", "travel")]
    assert sorted({FAVORITE_COUNTS.get(t, 0) for t in travel}) == [0, 1, 2, 3]


def test_seed_promotions_cover_in_and_out_of_period(db):
    load_day = _load_day(db)
    rows = db.execute(
        "SELECT t.title, n.start_date::date - %s, n.end_date::date - %s, n.end_date::time::text,"
        " n.discount, n.promo_price, t.price"
        " FROM notification n JOIN tour t USING (tour_id) WHERE n.type = '促銷'",
        (load_day, load_day),
    ).fetchall()
    assert {r[0]: (r[1], r[2]) for r in rows} == PROMOS
    assert {r[3] for r in rows} == {"23:59:59"}
    for title, _, _, _, discount, promo_price, price in rows:
        assert abs(promo_price - price * (1 - discount / 100)) < 0.01, title
    in_period = [t for t, (s, e) in PROMOS.items() if s <= 0 <= e]
    assert len(in_period) == 5
    assert any(s > 0 for s, _ in PROMOS.values()) and any(e < 0 for _, e in PROMOS.values())
    # 異動通知保留：義大利、紐西蘭，日期與折扣皆 NULL
    rows = db.execute(
        "SELECT t.title, n.start_date, n.end_date, n.discount, n.promo_price"
        " FROM notification n JOIN tour t USING (tour_id) WHERE n.type = '異動'"
    ).fetchall()
    assert {r[0] for r in rows} == {ITALY, NZ}
    assert all(r[1:] == (None, None, None, None) for r in rows)


def test_seed_travel_tours_have_distinct_start_dates(db):
    load_day = _load_day(db)
    rows = db.execute(
        "SELECT title, tour_start_date::date - %s, tour_end_date::date - tour_start_date::date + 1, days"
        " FROM tour WHERE type = 'tourgroup' AND item = 'travel'",
        (load_day,),
    ).fetchall()
    assert {r[0]: (r[1], r[2]) for r in rows} == TRAVEL_STARTS
    assert all(r[2] == r[3] for r in rows)
    (n,) = db.execute(
        "SELECT count(*) FROM tour WHERE type = 'backpacker' AND"
        " (tour_start_date IS NOT NULL OR tour_end_date IS NOT NULL OR days <> 0)"
    ).fetchone()
    assert n == 0


def test_seed_cart_items_start_in_future(db):
    load_day = _load_day(db)
    rows = db.execute(
        'SELECT u.email, t.title, ci.start_date::date - %s, ci.end_date::date - %s'
        ' FROM cart_item ci JOIN cart USING (cart_id) JOIN "user" u USING (user_id)'
        " JOIN tour t USING (tour_id)",
        (load_day, load_day),
    ).fetchall()
    assert {(r[0], r[1]): (r[2], r[3]) for r in rows} == {
        (EMAIL[u], t): v for (u, t), v in CART_ITEMS.items()
    }
    assert min(r[2] for r in rows) >= 14


def test_seed_favorite_times_are_distinct(db):
    rows = db.execute(
        f'SELECT u.email, t.title, {_days_ago("f.created_at")}, f.created_at = f.updated_at'
        ' FROM favorite f JOIN "user" u USING (user_id) JOIN tour t USING (tour_id)'
    ).fetchall()
    assert {(r[0], r[1], r[2]) for r in rows} == {(EMAIL[u], t, d) for u, t, d in FAVORITES}
    assert all(r[3] for r in rows)
    assert len({(r[0], r[2]) for r in rows}) == len(rows)  # 同一使用者兩兩不同


def test_seed_orders_match_contract(db):
    rows = db.execute(
        f'SELECT u.email, t.title, o.payment_status, oi.payment_status, oi.quantity, o.total_price,'
        f' oi.total_price, oi.discount_price, o.payment_type, o.discount_type, o.discount_price,'
        f' o.address, o.phone, {_days_ago("o.created_at")}, {_days_ago("oi.created_at")}'
        ' FROM orders o JOIN "user" u USING (user_id) JOIN order_item oi USING (order_id)'
        " JOIN tour t USING (tour_id)"
    ).fetchall()
    assert len(rows) == 20
    got = {(r[0], r[1]): r for r in rows}
    assert len(got) == 20
    for o in ORDERS:
        r = got[(EMAIL[o.user], o.title)]
        address_phone = ADDRESS_PHONE[o.user] if o.status != -1 else (None, None)
        want = (o.status, o.status, o.quantity, o.total, o.total, o.item_discount, o.payment_type,
                o.discount_type, o.discount, *address_phone, o.days_ago, o.days_ago)
        assert r[2:] == want, f"#{o.n}：{r[2:]} != {want}"
    assert len({o.days_ago for o in ORDERS}) == 20


def test_seed_promo_orders_fall_inside_promo_window(db):
    # 帶促銷價的訂單是下單當時有效的價格（契約 §0.1 第 9 項）：訂單時間在該行程的促銷期間內，
    # 且 order_item.discount_price = promo_price × quantity。用關聯檢查，不靠兩邊的字面值剛好一致
    rows = db.execute(
        "SELECT t.title, oi.created_at BETWEEN n.start_date AND n.end_date, o.created_at BETWEEN n.start_date AND n.end_date,"
        " oi.discount_price, n.promo_price * oi.quantity"
        " FROM order_item oi JOIN orders o USING (order_id) JOIN tour t ON t.tour_id = oi.tour_id"
        " JOIN notification n ON n.tour_id = oi.tour_id AND n.type = '促銷'"
        " WHERE oi.discount_price IS NOT NULL"
    ).fetchall()
    assert len(rows) == 5
    assert all(r[1] and r[2] for r in rows), rows
    assert all(abs(r[3] - r[4]) < 0.01 for r in rows), rows
    (n,) = db.execute(
        "SELECT count(*) FROM order_item oi LEFT JOIN notification n ON n.tour_id = oi.tour_id AND n.type = '促銷'"
        " WHERE oi.discount_price IS NOT NULL AND n.notification_id IS NULL"
    ).fetchone()
    assert n == 0


def test_seed_alice_paid_orders_newest_first(db):
    rows = db.execute(
        "SELECT t.title FROM orders o JOIN \"user\" u USING (user_id) JOIN order_item oi USING (order_id)"
        " JOIN tour t ON t.tour_id = oi.tour_id WHERE u.email = %s AND o.payment_status = 1"
        " ORDER BY o.created_at DESC",
        (EMAIL["alice"],),
    ).fetchall()
    want = [next(o.title for o in ORDERS if o.n == n) for n in (4, 1, 15, 10, 7)]  # 契約 §0.1 第 9 項
    assert [r[0] for r in rows] == want


def test_seed_payment_status_coverage(db):
    rows = db.execute("SELECT payment_status, count(*) FROM orders GROUP BY payment_status").fetchall()
    assert dict(rows) == {1: 15, -1: 1, 0: 1, 2: 1, 3: 1, 4: 1}
    # 每個已付款訂單恰好 1 筆 payment，其他訂單沒有
    rows = db.execute(
        "SELECT o.payment_status, count(p.payment_id) FROM orders o"
        " LEFT JOIN payment p USING (order_id) GROUP BY o.order_id, o.payment_status"
    ).fetchall()
    assert sorted(rows) == sorted([(1, 1)] * 15 + [(s, 0) for s in (-1, 0, 2, 3, 4)])
    # payment 欄位照契約 §0.1 第 9 項
    rows = db.execute(
        'SELECT o.order_id::text, o.user_id, o.address, o.phone, o.payment_type, o.discount_price,'
        " p.user_id, p.address, p.phone, p.payment_method, p.payment_status, p.discount_price,"
        " p.return_data, p.result_info, p.return_time IS NOT NULL, p.result_time IS NOT NULL"
        " FROM payment p JOIN orders o USING (order_id)"
    ).fetchall()
    assert len(rows) == 15
    for r in rows:
        order_id, *order, user_id, address, phone, method, status, discount, data, info, rt, rs = r
        assert (user_id, address, phone, method, discount) == (order[0], order[1], order[2], order[3], order[4])
        assert status == 1 and info == "付款成功" and rt and rs
        assert json.loads(data) == {
            "Status": "SUCCESS",
            "Result": {"MerchantOrderNo": order_id, "PaymentType": method, "Message": "付款成功"},
        }


def test_seed_points_follow_rules(db):
    rows = db.execute(
        "SELECT o.discount_price, o.discount_type, pr.type, pr.point, pr.user_id = o.user_id,"
        " (SELECT sum(COALESCE(NULLIF(oi.discount_price, 0), oi.total_price)) FROM order_item oi"
        "  WHERE oi.order_id = o.order_id) AS promo_subtotal"
        " FROM point_record pr JOIN orders o USING (order_id)"
    ).fetchall()
    assert Counter(r[2] for r in rows) == {"新增": 15, "減少": 3}
    assert all(r[4] for r in rows), "point_record.user_id 必須是訂單的使用者"
    # 每張已付款訂單恰好 1 筆新增
    per_order = db.execute(
        "SELECT o.payment_status, count(pr.point_id) FROM orders o"
        " LEFT JOIN point_record pr ON pr.order_id = o.order_id AND pr.type = '新增' GROUP BY o.order_id, o.payment_status"
    ).fetchall()
    assert sorted(per_order) == sorted([(1, 1)] * 15 + [(s, 0) for s in (-1, 0, 2, 3, 4)])
    for discount, discount_type, kind, point, _, promo_subtotal in rows:
        if kind == "新增":
            paid = discount if discount is not None else promo_subtotal  # 實付
            assert point == math.floor(paid * 0.1)
        else:
            assert discount_type == "point" and point < 0
            assert abs(-point * 0.8 - (promo_subtotal - discount)) < 0.01
    # 每張已付款訂單 1 筆新增；未付款等狀態沒有點數
    rows = db.execute(
        "SELECT o.payment_status, pr.type, count(*) FROM point_record pr JOIN orders o USING (order_id)"
        " GROUP BY o.payment_status, pr.type"
    ).fetchall()
    assert {(s, t) for s, t, _ in rows} == {(1, "新增"), (1, "減少")}
    assert dict(db.execute(
        "SELECT u.email, sum(pr.point) FILTER (WHERE pr.type = '減少') FROM point_record pr"
        ' JOIN "user" u USING (user_id) GROUP BY u.email'
    ).fetchall()) == {EMAIL["alice"]: -250, EMAIL["bob"]: -500, EMAIL["carol"]: -400}
    # 餘額取 user_level.travel_point，不加總 point_record（#2 定案 A），維持不變
    assert dict(db.execute(
        'SELECT u.email, ul.travel_point FROM user_level ul JOIN "user" u USING (user_id)'
    ).fetchall()) == {EMAIL["alice"]: 1500, EMAIL["bob"]: 3000, EMAIL["carol"]: 800}


def _paid_by_order(db):
    """{(email, 行程 title): 實付}；實付 = orders.discount_price，NULL 時取 Σ COALESCE(NULLIF(item.discount_price, 0), item.total_price)。"""
    rows = db.execute(
        'SELECT u.email, t.title, COALESCE(o.discount_price, sum(COALESCE(NULLIF(oi.discount_price, 0), oi.total_price))),'
        " o.discount_price, p.discount_price"
        ' FROM orders o JOIN "user" u USING (user_id) JOIN order_item oi USING (order_id)'
        " JOIN tour t ON t.tour_id = oi.tour_id LEFT JOIN payment p ON p.order_id = o.order_id"
        " WHERE o.payment_status = 1 GROUP BY o.order_id, u.email, t.title, o.discount_price, p.discount_price"
    ).fetchall()
    return rows


def test_seed_reward_points_by_paid_amount(db):
    expected = {
        (1, "alice", HOKKAIDO): 4050, (2, "bob", HOKKAIDO): 4049, (3, "carol", HOKKAIDO): 4050,
        (4, "alice", MALDIVES): 8300, (5, "carol", MALDIVES): 8330, (6, "bob", NZ): 8470,
        (7, "alice", KAOHSIUNG): 820, (8, "bob", KAOHSIUNG): 1260, (9, "carol", OSAKA): 2968,
        (10, "alice", SEOUL): 1900, (11, "carol", SEOUL): 950, (12, "bob", PARIS): 2200,
        (13, "bob", BANGKOK): 1760, (14, "carol", BANGKOK): 900, (15, "alice", OKINAWA): 1760,
    }
    actual = {
        (email, title): point for email, title, point in db.execute(
            'SELECT u.email, t.title, pr.point FROM point_record pr JOIN "user" u USING (user_id)'
            " JOIN orders o USING (order_id) JOIN order_item oi USING (order_id)"
            " JOIN tour t ON t.tour_id = oi.tour_id WHERE pr.type = '新增'"
        ).fetchall()
    }
    assert actual == {(EMAIL[user], title): point for (_, user, title), point in expected.items()}


def test_seed_payment_amount_matches_paid(db):
    rows = _paid_by_order(db)
    assert len(rows) == 15
    for email, title, paid, order_discount, payment_discount in rows:
        # payment.discount_price 與 orders.discount_price 同值（NULL 就 NULL）；有值時就是實付
        assert payment_discount == order_discount, (email, title)
        if payment_discount is not None:
            assert payment_discount == paid
    assert {(e, t): d for e, t, _, _, d in rows if d is not None} == {
        (EMAIL["bob"], HOKKAIDO): 40490, (EMAIL["alice"], MALDIVES): 83000,
        (EMAIL["bob"], NZ): 84700, (EMAIL["alice"], KAOHSIUNG): 8200,
        (EMAIL["carol"], OSAKA): 29680, (EMAIL["bob"], BANGKOK): 17600,
    }


def test_seed_user_coupons_point_to_rebuilt_orders(db):
    rows = db.execute(
        'SELECT u.email, c.code, uc.status, o.order_id IS NOT NULL, t.title, o.total_price'
        ' FROM user_coupon uc JOIN "user" u USING (user_id) JOIN coupon c USING (coupon_id)'
        " LEFT JOIN orders o USING (order_id) LEFT JOIN order_item oi USING (order_id)"
        " LEFT JOIN tour t ON t.tour_id = oi.tour_id"
    ).fetchall()
    assert sorted(rows, key=str) == sorted([
        (EMAIL["bob"], "TRV010", 1, True, HOKKAIDO, 45000),   # 訂單 #2
        (EMAIL["bob"], "VIP300", 1, True, NZ, 85000),          # 訂單 #6
        (EMAIL["alice"], "VIP300", 1, True, MALDIVES, 98000),  # 訂單 #4
        (EMAIL["carol"], "TRV010", 0, False, None, None),
    ], key=str)
    # 優惠卷折抵：orders.discount_price = 促銷後金額 - coupon.discount
    rows = db.execute(
        "SELECT (SELECT sum(COALESCE(NULLIF(oi.discount_price, 0), oi.total_price)) FROM order_item oi"
        " WHERE oi.order_id = o.order_id) - c.discount, o.discount_price, o.discount_type"
        " FROM user_coupon uc JOIN orders o USING (order_id) JOIN coupon c USING (coupon_id)"
    ).fetchall()
    assert all(a == b and kind == "coupon" for a, b, kind in rows) and len(rows) == 3


def test_seed_web_reviews_for_home(db):
    rows = db.execute(
        f'SELECT u.email, {_days_ago("r.created_at")}, r.rating FROM review r'
        ' JOIN "user" u USING (user_id) WHERE r.type = %s',
        ("web",),
    ).fetchall()
    assert len(rows) >= 5
    assert {(r[0], r[1]) for r in rows} == {(EMAIL[u], d) for u, d in WEB_REVIEWS}
    assert len({r[1] for r in rows}) == 5  # created_at 兩兩不同（首頁以評論時間排序）
    assert all(1 <= r[2] <= 5 for r in rows)
    (n,) = db.execute("SELECT count(*) FROM review WHERE type <> 'web'").fetchone()
    assert n == 8
