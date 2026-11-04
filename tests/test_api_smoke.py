"""P1b Task 7：seed 資料走得通 21 個物件中所有「讀取」API 的冒煙測試。

只做 GET，不寫入資料。每個測試：HTTP 200、資料非空、契約列出的欄位名稱出現在第一筆資料裡
（`SELECT *` 原樣輸出的 API 直接對 tests/db_contract.py；controller 轉成英文 key 的 API 對 controller 的 key）。
寫入購物車才會呼叫的 hotel_booking／restaurant_booking／restaurant_isclosed／restaurant_business_parsed
由 test_views_b.py 的行為測試負責，這裡不涵蓋。

已知 controller bug（契約 §4.2「不需決定」）不納入：首頁沒帶 type 的 500、
GET /collection/info/all 送兩次回應（第一次回應完整，requests 只看到第一次，所以仍可驗證 view）、
結帳 GET /summary 對沒有項目的訂單 500 等。
"""
import pytest
from conftest import auth_header
from db_contract import OBJECTS
from test_seed import SEED_USERS

BASE = "/api/v1"
LANG = "zh-TW"
PAGING = {"page": 1, "limit": 20, "lang": LANG}


# ---------------------------------------------------------------- 共用


def contract_cols(name: str, *, replace_preference: bool = False) -> list[str]:
    """契約欄位名稱。controller 會把偏好分類 1/2/3 換成「偏好分類」時 replace_preference=True。"""
    cols = [c for c, _ in OBJECTS[name]["columns"]]
    if replace_preference:
        cols = [c for c in cols if c not in ("偏好分類1", "偏好分類2", "偏好分類3")] + ["偏好分類"]
    return cols


def assert_has_keys(row: dict, expected: list[str]) -> None:
    missing = [k for k in expected if k not in row]
    assert not missing, f"缺少欄位 {missing}；實際欄位 {sorted(row)}"


def data_rows(r) -> list[dict]:
    """取出資料列：data 可能是 list，也可能是 {"data": list}。"""
    assert r.status_code == 200, r.text
    body = r.json()
    data = body.get("data")
    assert data, f"data 為空：{r.text[:300]}"
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    assert isinstance(data, list) and data, f"沒有資料列：{r.text[:300]}"
    return data


@pytest.fixture(scope="module")
def users(db):
    rows = db.execute(
        'SELECT email, user_id, role FROM "user" WHERE email = ANY(%s)', (list(SEED_USERS),)
    ).fetchall()
    return {email: {"user_id": str(uid), "role": role} for email, uid, role in rows}


@pytest.fixture(scope="module")
def alice(users):
    return users["alice@example.com"]


@pytest.fixture(scope="module")
def alice_h(alice):
    return auth_header(alice)


@pytest.fixture(scope="module")
def bob_h(users):
    return auth_header(users["bob@example.com"])


def seed_tour_id(db, type_: str, item: str, *, with_table: str | None = None) -> str:
    """查出一個上架的 seed 行程。with_table：要求該行程在某張資料表有資料（評論、隱藏玩法）。"""
    if with_table:
        sql = (
            f'SELECT t.tour_id FROM tour t WHERE t.type = %s AND t.item = %s AND t.status = 1 '
            f'AND EXISTS (SELECT 1 FROM "{with_table}" x WHERE x.tour_id = t.tour_id) '
            "ORDER BY t.title LIMIT 1"
        )
    else:
        sql = "SELECT tour_id FROM tour WHERE type = %s AND item = %s AND status = 1 ORDER BY title LIMIT 1"
    row = db.execute(sql, (type_, item)).fetchone()
    assert row, f"seed 沒有 {type_}/{item} 的上架行程"
    return str(row[0])


# ------------------------------------------------- 首頁 products：A 組 tour_base／tour_travel／popular／most_favorited

HOME_GROUPS = [
    ("tourgroup", "popular", "tour_travel_popular"),
    ("tourgroup", "promotion", None),
    ("tourgroup", "most_favorited", "tour_travel_most_favorited"),
    ("backpacker", "hotel", "tour_travel_popular"),
    ("backpacker", "food", "tour_travel_popular"),
    ("backpacker", "spot", "tour_travel_popular"),
]


def _home_expected(base: str, ranking: str | None) -> list[str]:
    cols = contract_cols(base, replace_preference=True)
    if ranking:
        cols += contract_cols(ranking)  # tour_id + 購買排行／收藏排行
    return cols


@pytest.mark.parametrize("type_,item,ranking", HOME_GROUPS, ids=lambda v: str(v))
def test_home_products_guest(api, type_, item, ranking):
    # 未登入 → tour_base（join popular／most_favorited）
    r = api.get(f"{BASE}/user/home/search/products", params={"type": type_, "item": item, **PAGING})
    rows = data_rows(r)
    assert_has_keys(rows[0], _home_expected("tour_base", ranking))
    assert {row["小分類"] for row in rows} == {item if type_ == "backpacker" else "travel"}
    assert "收藏狀態" not in rows[0]  # 未登入走 tour_base，沒有收藏狀態


@pytest.mark.parametrize("type_,item,ranking", HOME_GROUPS, ids=lambda v: str(v))
def test_home_products_logged_in(api, alice_h, type_, item, ranking):
    # 已登入 → tour_travel(使用者編號)，多一個收藏狀態
    r = api.get(
        f"{BASE}/user/home/search/products",
        headers=alice_h,
        params={"type": type_, "item": item, **PAGING},
    )
    rows = data_rows(r)
    assert_has_keys(rows[0], _home_expected("tour_travel", ranking))
    assert {row["小分類"] for row in rows} == {item if type_ == "backpacker" else "travel"}


def test_home_promotion_rows_are_promotions(api):
    r = api.get(
        f"{BASE}/user/home/search/products",
        params={"type": "tourgroup", "item": "promotion", **PAGING},
    )
    assert {row["通知狀態"] for row in data_rows(r)} == {"促銷"}


# ----------------------------------------------------------------- 首頁好評：user_level_review_forHome


def test_home_reviews(api):
    r = api.get(f"{BASE}/user/home/search/reviews", params=PAGING)
    assert_has_keys(data_rows(r)[0], contract_cols("user_level_review_forHome"))


# ------------------------------------------------------------------ 公開商品清單：tour_travel


def test_public_product_list_guest(api):
    r = api.get(
        f"{BASE}/user/product/search",
        params={"page": 1, "limit": 20, "sort_by": "date", "order": "asc", "lang": LANG},
    )
    rows = data_rows(r)
    # 偏好分類 1/2/3 由 controller 換成 tags
    expected = [c for c in contract_cols("tour_travel") if not c.startswith("偏好分類")] + ["tags"]
    assert_has_keys(rows[0], expected)


# ------------------------------------------- 公開詳情頁：tour_tour_detail／tour_hotel／tour_restaurant（v4 驗證器）

DETAIL_COMMON = [
    "tour_id", "title", "title_slogan", "type", "item", "image_url", "image_spot", "price",
    "date_start", "date_end", "feature", "location", "description", "tags", "is_favorited",
    "emergency_notice", "promotion",
]  # fmt: skip


def _get_detail(api, tour_id, headers=None):
    r = api.get(f"{BASE}/user/product/search/{tour_id}", headers=headers, params={"lang": LANG})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data, r.text
    assert data["tour_id"] == tour_id
    assert_has_keys(data, DETAIL_COMMON)
    assert len(data["image_spot"]) == 6
    for spot in data["image_spot"]:
        assert set(spot) == {"description", "image_url"}
    assert data["image_spot"][0]["image_url"]  # 來自 旅遊圖1 Url，不是 controller 常數
    assert_has_keys(data["location"], ["country", "region", "address", "google_map"])
    assert_has_keys(data["promotion"], ["is_promoted", "promo_price", "tag", "start_at", "end_at"])
    return data


def test_detail_travel_tour_tour_detail(api, db):
    # tourgroup/travel → tour_tour_detail
    data = _get_detail(api, seed_tour_id(db, "tourgroup", "travel"))
    assert data["type"] == "tourgroup" and data["item"] == "travel"
    assert data["is_favorited"] is False  # 未登入：使用者編號 NULL
    assert data["itinerary"]
    assert len(data["feature"]) == 3 and all(f["description"] for f in data["feature"])


def test_detail_spot_tour_tour_detail(api, db):
    # backpacker/spot 也走 tour_tour_detail
    data = _get_detail(api, seed_tour_id(db, "backpacker", "spot"))
    assert data["item"] == "spot"
    assert data["itinerary"]


def test_detail_hotel_tour_hotel(api, db):
    data = _get_detail(api, seed_tour_id(db, "backpacker", "hotel"))
    assert data["item"] == "hotel"
    rooms = data["feature"]["room"]
    assert rooms and all(room["name"] for room in rooms)
    assert data["feature"]["service"][0]["item"]  # 來自 基本設施與服務 欄位


def test_detail_food_tour_restaurant(api, db):
    data = _get_detail(api, seed_tour_id(db, "backpacker", "food"))
    assert data["item"] == "food"
    feature = data["feature"]
    assert_has_keys(feature, ["about", "menu", "opening"])
    # 菜單列與營業時間列是分開的列（menu XOR opening），所以各自找有值的列
    assert any(m["name"] for m in feature["menu"])
    assert any(o["week"] for o in feature["opening"])


def test_detail_logged_in_has_favorite_flag(api, db, alice_h):
    # 帶使用者編號呼叫 function：alice 有收藏的行程 is_favorited 為 True
    row = db.execute(
        "SELECT f.tour_id FROM favorite f JOIN tour t USING (tour_id) "
        'JOIN "user" u ON u.user_id = f.user_id WHERE u.email = %s AND t.status = 1 '
        "AND t.type = 'tourgroup' AND t.item = 'travel' LIMIT 1",
        ("alice@example.com",),
    ).fetchone()
    assert row, "seed 裡 alice 沒有收藏的 tourgroup/travel 行程"
    assert _get_detail(api, str(row[0]), headers=alice_h)["is_favorited"] is True


# --------------------------------------------- 評論與隱藏玩法：user_user_level（JOIN review／hidden_play）


def test_tour_reviews_use_user_level(api, db):
    tour_id = seed_tour_id(db, "tourgroup", "travel", with_table="review")
    r = api.get(
        f"{BASE}/user/product/search/{tour_id}/reviews", params={"page": 1, "limit": 10, "lang": LANG}
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["reviews"], r.text
    review = data["reviews"][0]
    assert_has_keys(review, ["review_id", "name", "avatar", "level", "rating", "content", "create_date"])
    assert review["name"] and review["level"]["name"] and review["level"]["badge_icon"]


def test_tour_hidden_shares_use_user_level(api, db):
    tour_id = seed_tour_id(db, "backpacker", "food", with_table="hidden_play")
    r = api.get(
        f"{BASE}/user/product/search/{tour_id}/hidden-shares",
        params={"page": 1, "limit": 10, "lang": LANG},
    )
    assert r.status_code == 200, r.text
    rows = r.json()["data"]
    assert rows, r.text
    assert_has_keys(rows[0], ["shares_id", "name", "avatar", "level", "content", "url", "create_date"])
    # controller 的 title 讀 row.type，hidden_play 沒有這欄（undefined → JSON 省略），不是 view 的問題，這裡不斷言
    assert rows[0]["name"] and rows[0]["level"]["name"] and rows[0]["level"]["badge_icon"]


# ------------------------------------------------------- 會員等級與點數：user_level_point_coupon


POINTS_KEYS = [
    "name", "email", "role", "avatar_url", "preference1", "preference2", "preference3",
    "level", "level_name", "badge_url", "travel_point", "coupon",
]  # fmt: skip
COUPON_KEYS = ["coupon_id", "code", "discount", "description", "expire_date"]


def test_points_level_alice_has_null_coupon_placeholder(api, alice_h, alice):
    r = api.get(f"{BASE}/user/userinfo/pointslevel", headers=alice_h)
    me = data_rows(r)[0]
    assert me["user_id"] == alice["user_id"]
    assert_has_keys(me, POINTS_KEYS)
    assert me["level"] and me["travel_point"] > 0
    # alice 唯一的優惠卷 VIP300 已使用（status = 1），不符合 #39（只列 status = 0 且未過期）。
    # 契約 #40（docs/db-contract.md:1303–1306）：LEFT JOIN → 仍有 1 列，優惠卷欄位全 NULL，
    # controller 會 push 一個全 null 的物件。
    assert me["coupon"] == [dict.fromkeys(COUPON_KEYS)]


def test_points_level_carol_has_usable_coupon(api, users):
    # carol 的 TRV010 是 status = 0。注意：TRV010 的 expire_date 由 db/seed-build/build_seed.py 以載入日為錨點
    # （+133 天），到期後 view 的 expire_date >= now() 會把它濾掉，這支測試就要重載 seed（seed 日期維護點）。
    carol = users["carol@example.com"]
    r = api.get(f"{BASE}/user/userinfo/pointslevel", headers=auth_header(carol))
    me = data_rows(r)[0]
    assert me["user_id"] == carol["user_id"]
    assert_has_keys(me, POINTS_KEYS)
    assert_has_keys(me["coupon"][0], COUPON_KEYS)
    assert me["coupon"][0]["code"] == "TRV010"
    assert me["coupon"][0]["expire_date"] is not None


# ------------------------------------------------------------------------- 購物車：user_cartList


def test_cart_list(api, alice_h):
    r = api.get(f"{BASE}/user/trade/cart/list", headers=alice_h, params=PAGING)
    item = data_rows(r)[0]
    assert_has_keys(
        item,
        ["cart_id", "tour_id", "type", "item", "title", "image_url", "price", "promo_price",
         "options", "total_price"],
    )  # fmt: skip
    assert_has_keys(item["options"], ["people", "start_date", "end_date", "room_type"])
    assert item["title"] and item["total_price"] > 0


# ------------------------------------------------------- 優惠卷清單：user_couponList（管理者查 alice）


def test_admin_user_coupon_list(api, bob_h, alice):
    r = api.get(f"{BASE}/admin/members/{alice['user_id']}/coupons", headers=bob_h)
    rows = data_rows(r)
    assert_has_keys(rows[0], contract_cols("user_couponList"))
    assert {row["user_id"] for row in rows} == {alice["user_id"]}


# ------------------------------------------------------------- 結帳摘要：user_orderList（alice 未付款訂單）


def test_checkout_summary_unpaid_order(api, db, alice, alice_h):
    row = db.execute(
        "SELECT o.order_id FROM orders o WHERE o.user_id = %s AND o.payment_status = -1 "
        "AND EXISTS (SELECT 1 FROM order_item oi WHERE oi.order_id = o.order_id) LIMIT 1",
        (alice["user_id"],),
    ).fetchone()
    assert row, "seed 裡 alice 沒有未付款且有項目的訂單"
    order_id = str(row[0])
    r = api.get(f"{BASE}/user/checkout/summary/{order_id}", headers=alice_h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert_has_keys(data, ["user", "payment_method", "discount", "orders", "summary"])
    assert data["orders"], r.text
    order = data["orders"][0]
    assert_has_keys(
        order,
        ["order_id", "tour_id", "type", "item", "title", "cover_image", "price", "discount_price",
         "options", "total_price"],
    )  # fmt: skip
    assert order["order_id"] == order_id and order["title"]
    assert data["summary"]["total_items"] >= 1


# ------------------------------------------------------------------------- 收藏：user_favorite


def test_favorite_list(api, alice_h, alice):
    # 這支 API 會送兩次回應（契約 §4.2 已記錄）；第一次回應是完整資料，足以驗證 view
    r = api.get(f"{BASE}/user/collection/info/all", headers=alice_h, params=PAGING)
    rows = data_rows(r)
    assert_has_keys(rows[0], contract_cols("user_favorite", replace_preference=True))
    assert {row["收藏人員編號"] for row in rows} == {alice["user_id"]}


# ------------------------------------------------------------- 已購買：user_orders／user_order_item


def test_purchases_list(api, alice_h, alice):
    r = api.get(f"{BASE}/user/purchases/info", headers=alice_h)
    rows = data_rows(r)
    assert_has_keys(rows[0], contract_cols("user_orders", replace_preference=True))
    assert {row["使用者編號"] for row in rows} == {alice["user_id"]}


def test_purchases_item_detail(api, alice_h):
    first = data_rows(api.get(f"{BASE}/user/purchases/info", headers=alice_h))[0]
    r = api.get(
        f"{BASE}/user/purchases/info/{first['order_item_id']}", headers=alice_h, params={"lang": LANG}
    )
    row = data_rows(r)[0]
    # controller 把 preference1/2/3 換成 preference
    expected = [c for c in contract_cols("user_order_item") if not c.startswith("preference")]
    assert_has_keys(row, expected + ["preference"])
    assert row["order_item_id"] == first["order_item_id"]


# ------------------------------------------------------------- 管理者：user_adminList、tour_base


def test_admin_member_detail(api, bob_h, alice):
    r = api.get(f"{BASE}/admin/members/{alice['user_id']}", headers=bob_h, params={"lang": LANG})
    row = data_rows(r)[0]
    assert_has_keys(row, contract_cols("user_adminList"))
    assert row["使用者編號"] == alice["user_id"]


def test_admin_promotions(api, bob_h):
    r = api.get(f"{BASE}/admin/promotions", headers=bob_h, params=PAGING)
    rows = data_rows(r)
    assert_has_keys(rows[0], contract_cols("tour_base", replace_preference=True))
    assert {row["通知狀態"] for row in rows} == {"促銷"}


def test_admin_change_info(api, bob_h):
    r = api.get(f"{BASE}/admin/change-info", headers=bob_h, params=PAGING)
    rows = data_rows(r)
    # controllers/admin.js:get_Changeinfo 只 SELECT 這幾欄
    assert_has_keys(
        rows[0],
        ["旅遊編號", "上下架狀態", "通知狀態", "旅遊名稱", "旅遊描述", "所屬國家", "所屬地區", "建立時間",
         "價錢", "旅遊代表圖 Url"],
    )  # fmt: skip


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="契約 §4.2：GET /admin/product 一律 500，兩個獨立 bug 都要修——"
    "middlewares/product/index.js:296 讀 req.user.tour_ids，JWT 只有 {id, role} 所以是 undefined；"
    "index.js:312–315 對 map 回傳的 Promise 陣列讀 .rows。controller 不在 P1 範圍，P2 處理",
)
def test_admin_product_list(api, bob_h):
    r = api.get(f"{BASE}/admin/product", headers=bob_h, params={"page": 1, "limit": 20})
    assert r.status_code == 200, r.text  # 目前是 500 → AssertionError → xfail
    rows = data_rows(r)
    assert_has_keys(
        rows[0],
        ["旅遊編號", "上下架狀態", "旅遊名稱", "旅遊描述", "所屬國家", "所屬地區", "建立時間", "價錢",
         "旅遊代表圖 Url"],
    )  # fmt: skip


# ------------------------------------------------------------------ 篩選：v4 驗證器（seed 國家）


def test_filter_region_for_seed_country(api, db):
    country_id, name = db.execute(
        "SELECT c.country_id, c.name FROM country c "
        "WHERE EXISTS (SELECT 1 FROM region r WHERE r.country_id = c.country_id) ORDER BY c.name LIMIT 1"
    ).fetchone()
    r = api.get(f"{BASE}/web/filter/{country_id}/region")
    rows = data_rows(r)
    assert_has_keys(rows[0], ["region_id", "name"])
    expected = db.execute("SELECT count(*) FROM region WHERE country_id = %s", (country_id,)).fetchone()[0]
    assert len(rows) == expected, name
