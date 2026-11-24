"""P4 Task 1：購物車與建立訂單的 controller 不可洩漏資料庫連線（pool max 10，迴圈 max + 5 次）。"""
import datetime

from conftest import auth_header

POOL_MAX = 10  # backend/src/config/database.js 未設定 max，採 pg 預設 10
LOOPS = POOL_MAX + 5
CART = "/api/v1/user/trade/cart"
CHECKOUT_ORDER = "/api/v1/user/checkout/order"


def add_to_cart(api, user, tour, people=1, start_date=None, end_date=None):
    """加入購物車；tour 為 make_tour 回傳的 dict（type／item 取自它）。日期預設明天、後天。"""
    today = datetime.date.today()
    start_date = start_date or (today + datetime.timedelta(days=1)).isoformat()
    end_date = end_date or (today + datetime.timedelta(days=2)).isoformat()
    body = {
        "type": tour["type"],
        "item": tour["item"],
        "people": people,
        "options": {"start_date": start_date, "end_date": end_date},
    }
    return api.post(f"{CART}/{tour['tour_id']}", json=body, headers=auth_header(user), timeout=5)


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
