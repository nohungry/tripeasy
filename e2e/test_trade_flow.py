import datetime
import json
import re

import requests
from playwright.sync_api import Page, expect

from e2e.conftest import API_BASE, FRONTEND_BASE, auth_header, login_token

CART_API = f"{API_BASE}/api/v1/user/trade/cart"


def _login(page: Page, user: dict) -> None:
    """在頁面腳本執行前寫入 token 與 userName，userStore 一載入就是「已登入」（同 P3）。"""
    token = login_token(user)
    page.add_init_script(
        f"localStorage.setItem('authToken', {json.dumps(token)}); localStorage.setItem('userName', 'e2e-user');"
    )


def _api_add(user: dict, tour: dict, people: int = 1) -> None:
    today = datetime.date.today()
    body = {
        "type": tour["type"],
        "item": tour["item"],
        "people": people,
        "options": {
            "start_date": (today + datetime.timedelta(days=10)).isoformat(),
            "end_date": (today + datetime.timedelta(days=12)).isoformat(),
        },
    }
    res = requests.post(f"{CART_API}/{tour['tour_id']}", json=body, headers=auth_header(user), timeout=5)
    assert res.status_code in (200, 201), res.text


def _open(page: Page, hash_path: str) -> None:
    page.goto(f"{FRONTEND_BASE}/{hash_path}", wait_until="domcontentloaded")


def _row(page: Page, tour: dict):
    return page.get_by_test_id("cart-item").filter(has_text=tour["title"])


def test_add_to_cart_from_detail(page: Page, db, make_user, make_tour):
    user = make_user()
    today = datetime.date.today()
    tour = make_tour(price=1000, start_date=today + datetime.timedelta(days=10), end_date=today + datetime.timedelta(days=12))
    _login(page, user)
    _open(page, f"#/tour/{tour['tour_id']}")
    page.get_by_label("人數").fill("2")
    page.get_by_role("button", name="加入購物車").click()
    expect(page.get_by_text("已加入購物車")).to_be_visible()
    row = db.execute(
        "SELECT ci.quantity, ci.start_date, ci.end_date FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user["user_id"], tour["tour_id"]),
    ).fetchone()
    assert row and row[0] == 2
    assert row[1] == datetime.datetime.combine(today + datetime.timedelta(days=10), datetime.time())
    assert row[2] == datetime.datetime.combine(today + datetime.timedelta(days=12), datetime.time())


def test_guest_add_to_cart_goes_to_login(page: Page, make_tour):
    today = datetime.date.today()
    tour = make_tour(price=1000, start_date=today + datetime.timedelta(days=10), end_date=today + datetime.timedelta(days=12))
    _open(page, f"#/tour/{tour['tour_id']}")
    page.get_by_role("button", name="加入購物車").click()
    page.wait_for_url("**/#/admin/login")


def _cart_dates(db, user: dict) -> list:
    return db.execute(
        "SELECT ci.tour_id, ci.start_date, ci.end_date FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s ORDER BY ci.tour_id",
        (user["user_id"],),
    ).fetchall()


def test_cart_page_lists_and_updates(page: Page, db, make_user, make_tour):
    user = make_user()
    tour_a = make_tour(price=1000)
    tour_b = make_tour(price=2000)
    _api_add(user, tour_a)
    _api_add(user, tour_b)
    _login(page, user)
    _open(page, "#/cart")
    expect(page.get_by_test_id("cart-item")).to_have_count(2)
    expect(page.get_by_test_id("cart-total")).to_have_text("NT$3,000")
    dates_before = _cart_dates(db, user)
    people = _row(page, tour_a).get_by_label("人數")
    people.fill("2")
    people.blur()  # 人數於 change 事件（離開欄位）時才送出
    expect(page.get_by_test_id("cart-total")).to_have_text("NT$4,000")
    assert _cart_dates(db, user) == dates_before  # 改人數不得移動日期
    _row(page, tour_b).get_by_role("button", name="移除").click()
    expect(page.get_by_test_id("cart-item")).to_have_count(1)
    expect(page.get_by_test_id("cart-total")).to_have_text("NT$2,000")


def test_empty_cart_message(page: Page, make_user):
    user = make_user()
    _login(page, user)
    _open(page, "#/cart")
    expect(page.get_by_text("購物車是空的")).to_be_visible()
    expect(page.get_by_role("button", name="去結帳")).to_have_count(0)


def test_checkout_button_creates_order(page: Page, db, make_user, make_tour):
    user = make_user()
    tour = make_tour(price=1000)
    _api_add(user, tour)
    _login(page, user)
    _open(page, "#/cart")
    page.get_by_role("button", name="去結帳").click()
    page.wait_for_url(re.compile(r".*#/pay\?order=.+"))
    order_id = page.url.split("order=")[1]
    row = db.execute("SELECT payment_status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user["user_id"])).fetchone()
    assert row and row[0] == -1


def _make_hotel_with_rooms(db, make_tour, room_titles: list[str]) -> dict:
    today = datetime.date.today()
    tour = make_tour(
        item="hotel", with_detail=False, price=1000,
        start_date=today + datetime.timedelta(days=10), end_date=today + datetime.timedelta(days=12),
    )
    (hotel_id,) = db.execute("INSERT INTO hotel (tour_id) VALUES (%s) RETURNING hotel_id", (tour["tour_id"],)).fetchone()
    for title in room_titles:
        db.execute(
            "INSERT INTO hotel_room (hotel_id, title, capacity, room_count, image, image_desc) "
            "VALUES (%s, %s, 2, 5, 'https://img.example.com/room.jpg', '房型圖')",
            (hotel_id, title),
        )
    return tour


def test_add_hotel_to_cart_with_room_type(page: Page, db, make_user, make_tour):
    user = make_user()
    rooms = ["p3-room-A", "p3-room-B"]
    tour = _make_hotel_with_rooms(db, make_tour, rooms)
    _login(page, user)
    _open(page, f"#/tour/{tour['tour_id']}")
    page.get_by_label("房型").select_option(label="p3-room-B")
    page.get_by_role("button", name="加入購物車").click()
    expect(page.get_by_text("已加入購物車")).to_be_visible()
    row = db.execute(
        "SELECT ci.room_type FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user["user_id"], tour["tour_id"]),
    ).fetchone()
    assert row and row[0] == "p3-room-B"


def test_hotel_without_rooms_not_orderable(page: Page, db, make_user, make_tour):
    user = make_user()
    tour = _make_hotel_with_rooms(db, make_tour, [])
    _login(page, user)
    _open(page, f"#/tour/{tour['tour_id']}")
    expect(page.get_by_text("此行程暫不開放線上訂購")).to_be_visible()
    expect(page.get_by_role("button", name="加入購物車")).to_be_disabled()


def test_payment_error_shows_backend_message(page: Page, make_user, make_tour, make_order):
    user = make_user()
    tour = make_tour(price=1000)
    order = make_order(user, tour["tour_id"], payment_status=2)  # 已取消的訂單不能付款
    _login(page, user)
    _open(page, "#/cart")
    expect(page.get_by_text("購物車是空的")).to_be_visible()
    # 從頁面內呼叫真正的 api.js::post_payment（responseType: 'text' 的錯誤回應是字串）
    page.evaluate(
        "orderId => import('/src/utils/api.js').then(m => m.post_payment(orderId)).catch(() => null)",
        order["order_id"],
    )
    expect(page.locator(".swal2-html-container")).to_have_text("訂單狀態不允許此操作")
