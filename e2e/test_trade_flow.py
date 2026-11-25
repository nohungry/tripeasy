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
    quantity = db.execute(
        "SELECT ci.quantity FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user["user_id"], tour["tour_id"]),
    ).fetchone()
    assert quantity and quantity[0] == 2


def test_guest_add_to_cart_goes_to_login(page: Page, make_tour):
    today = datetime.date.today()
    tour = make_tour(price=1000, start_date=today + datetime.timedelta(days=10), end_date=today + datetime.timedelta(days=12))
    _open(page, f"#/tour/{tour['tour_id']}")
    page.get_by_role("button", name="加入購物車").click()
    page.wait_for_url("**/#/admin/login")


def test_cart_page_lists_and_updates(page: Page, make_user, make_tour):
    user = make_user()
    tour_a = make_tour(price=1000)
    tour_b = make_tour(price=2000)
    _api_add(user, tour_a)
    _api_add(user, tour_b)
    _login(page, user)
    _open(page, "#/cart")
    expect(page.get_by_test_id("cart-item")).to_have_count(2)
    expect(page.get_by_test_id("cart-total")).to_have_text("NT$3,000")
    people = _row(page, tour_a).get_by_label("人數")
    people.fill("2")
    people.blur()  # 人數於 change 事件（離開欄位）時才送出
    expect(page.get_by_test_id("cart-total")).to_have_text("NT$4,000")
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
