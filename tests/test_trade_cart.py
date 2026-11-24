"""P4 Task 1：購物車與建立訂單的 controller 不可洩漏資料庫連線（pool max 10，迴圈 max + 5 次）。"""
import datetime
import re
from zoneinfo import ZoneInfo

from conftest import CART_API, add_to_cart, auth_header, live_promotion

POOL_MAX = 10  # backend/src/config/database.js 未設定 max，採 pg 預設 10
LOOPS = POOL_MAX + 5
CART = CART_API
CHECKOUT_ORDER = "/api/v1/user/checkout/order"


def _cart_item_id(db, user_id, tour_id) -> str:
    row = db.execute(
        "SELECT ci.cart_item_id FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user_id, tour_id),
    ).fetchone()
    return str(row[0])


def _cart_id(db, user_id) -> str:
    return str(db.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,)).fetchone()[0])


def test_cart_add_does_not_leak_connections(api, make_user, make_tour):
    user = make_user()
    for i in range(LOOPS):
        r = add_to_cart(api, user, make_tour())  # 同會員每次加新行程（重複行程會被 middleware 擋）
        assert r.status_code == 201, (i, r.text)
    assert api.get("/api/v1/health", timeout=5).status_code == 200


def test_cart_patch_and_delete_do_not_leak_connections(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour()
    assert add_to_cart(api, user, tour).status_code == 201
    item_id = _cart_item_id(db, user["user_id"], tour["tour_id"])
    today = datetime.date.today()
    patch_body = {
        "type": tour["type"],
        "item": tour["item"],
        "people": 2,
        "options": {
            "start_date": (today + datetime.timedelta(days=1)).isoformat(),
            "end_date": (today + datetime.timedelta(days=2)).isoformat(),
        },
    }
    for i in range(LOOPS):
        r = api.patch(f"{CART}/{item_id}", json=patch_body, headers=auth_header(user), timeout=5)
        assert r.status_code == 200, (i, r.text)
    for i in range(LOOPS):
        r = api.delete(f"{CART}/{item_id}", headers=auth_header(user), timeout=5)
        assert r.status_code == 200, (i, r.text)
        assert add_to_cart(api, user, tour).status_code == 201
        item_id = _cart_item_id(db, user["user_id"], tour["tour_id"])


def test_create_order_does_not_leak_connections(api, db, make_user, make_tour):
    user = make_user()
    for i in range(LOOPS):
        assert add_to_cart(api, user, make_tour()).status_code == 201
        cart_id = _cart_id(db, user["user_id"])
        r = api.post(f"{CHECKOUT_ORDER}/{cart_id}", headers=auth_header(user), timeout=5)
        assert r.status_code == 200, (i, r.text)


def _taipei_today() -> datetime.date:
    return datetime.datetime.now(ZoneInfo("Asia/Taipei")).date()


def _cart_list(api, user, page=1, limit=10):
    params = {"page": page, "limit": limit}
    r = api.get(f"{CART}/list", params=params, headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    return r.json()


def test_cart_list_returns_cart_item_id(api, make_user, make_tour):
    user = make_user()
    assert add_to_cart(api, user, make_tour()).status_code == 201
    items = _cart_list(api, user)["data"]["data"]
    assert len(items) == 1
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", items[0]["cart_item_id"])


def test_cart_summary_counts_all_pages(api, make_user, make_tour):
    user = make_user()
    for _ in range(3):
        assert add_to_cart(api, user, make_tour(price=1000)).status_code == 201
    body = _cart_list(api, user, limit=2)["data"]
    assert len(body["data"]) == 2
    assert body["summary"]["total_items"] == 3
    assert body["summary"]["total_price"] == 3000


def test_cart_add_same_item_merges_quantity(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour()
    assert add_to_cart(api, user, tour, people=1).status_code == 201
    assert add_to_cart(api, user, tour, people=2).status_code == 201
    rows = db.execute(
        "SELECT ci.quantity FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user["user_id"], tour["tour_id"]),
    ).fetchall()
    assert [r[0] for r in rows] == [3]


def test_cart_add_unlisted_tour_is_404(api, make_user, make_tour):
    r = add_to_cart(api, make_user(), make_tour(status=2))
    assert r.status_code == 404, r.text
    assert "查無此旅遊項目" in r.json()["message"]


def test_cart_add_past_date_is_400(api, make_user, make_tour):
    yesterday = (_taipei_today() - datetime.timedelta(days=1)).isoformat()
    r = add_to_cart(api, make_user(), make_tour(), start_date=yesterday, end_date=yesterday)
    assert r.status_code == 400, r.text
    assert "出發日期不能早於今天" in r.json()["message"]


def test_cart_add_impossible_date_is_400(api, make_user, make_tour):
    r = add_to_cart(api, make_user(), make_tour(), start_date="2027-02-30", end_date="2027-03-01")
    assert r.status_code == 400, r.text
    message = r.json()["message"]
    assert "出發日期" in message
    assert "start_date" not in message


def test_cart_add_offset_datetime_is_400(api, make_user, make_tour):
    r = add_to_cart(
        api, make_user(), make_tour(), start_date="2027-01-10T00:00:00+08:00", end_date="2027-01-11"
    )
    assert r.status_code == 400, r.text


def _patch_body(tour, people=5):
    tomorrow = _taipei_today() + datetime.timedelta(days=1)
    return {
        "type": tour["type"],
        "item": tour["item"],
        "people": people,
        "options": {
            "start_date": tomorrow.isoformat(),
            "end_date": (tomorrow + datetime.timedelta(days=1)).isoformat(),
        },
    }


def _quantity(db, item_id) -> int:
    return db.execute("SELECT quantity FROM cart_item WHERE cart_item_id = %s", (item_id,)).fetchone()[0]


def test_cart_patch_other_users_item_is_404(api, db, make_user, make_tour):
    owner, other = make_user(), make_user()
    tour = make_tour()
    assert add_to_cart(api, owner, tour, people=2).status_code == 201
    item_id = _cart_item_id(db, owner["user_id"], tour["tour_id"])
    r = api.patch(f"{CART}/{item_id}", json=_patch_body(tour), headers=auth_header(other), timeout=5)
    assert r.status_code == 404, r.text
    assert "查無此購物車項目" in r.json()["message"]
    assert _quantity(db, item_id) == 2


def test_cart_delete_other_users_item_is_404(api, db, make_user, make_tour):
    owner, other = make_user(), make_user()
    tour = make_tour()
    assert add_to_cart(api, owner, tour, people=2).status_code == 201
    item_id = _cart_item_id(db, owner["user_id"], tour["tour_id"])
    r = api.delete(f"{CART}/{item_id}", headers=auth_header(other), timeout=5)
    assert r.status_code == 404, r.text
    assert "查無此購物車項目" in r.json()["message"]
    assert _quantity(db, item_id) == 2


def test_cart_list_uses_live_promo_price(api, db, make_user, make_tour):
    user = make_user()
    tour = live_promotion(db, make_tour)
    assert add_to_cart(api, user, tour, people=2).status_code == 201
    items = _cart_list(api, user)["data"]["data"]
    assert [i["total_price"] for i in items] == [1800]
