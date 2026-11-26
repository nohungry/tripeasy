"""P5 Task 4：會員中心 ?tab= 切換、Header 連結、訂單分頁。"""

import re

import requests
from playwright.sync_api import Page, expect

from e2e.conftest import API_BASE, auth_header
from e2e.test_trade_flow import MOCK_BASE, _api_add, _fill_contact, _login, _open, _tour_dates

CHECKOUT_API = f"{API_BASE}/api/v1/user/checkout"


def _api_pending_order(db, user: dict, tour: dict) -> str:
    """用 API 建單（payment_status = -1），回傳 order_id。"""
    _api_add(user, tour)
    (cart_id,) = db.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user["user_id"],)).fetchone()
    res = requests.post(f"{CHECKOUT_API}/order/{cart_id}", headers=auth_header(user), timeout=5)
    assert res.status_code == 200, res.text
    return res.json()["data"]["order_id"]


def _open_user_menu(page: Page) -> None:
    menu = page.locator(".user-dropdown .custom-dropdown-menu")
    if "active" not in (menu.get_attribute("class") or ""):
        page.locator(".user-dropdown .user-toggle").click()
    expect(menu).to_have_class(re.compile(r"\bactive\b"))


def _row(page: Page, order_id: str):
    return page.get_by_test_id("order-row").filter(has_text=order_id[:8])


def test_header_links_open_tabs(page: Page, make_user):
    user = make_user()
    _login(page, user)
    _open(page, "#/admin/userprofile")
    for label, tab in [("會員等級", "level"), ("個人偏好設定", "preference"), ("個人訂單查看", "orders")]:
        _open_user_menu(page)
        page.locator(".user-dropdown").get_by_role("link", name=label, exact=True).click()
        expect(page).to_have_url(re.compile(rf"#/admin/userprofile\?tab={tab}$"))
        expect(page.locator(".sidebaritem.active")).to_have_text(label)
    _open_user_menu(page)
    page.locator(".user-dropdown").get_by_role("link", name="收藏", exact=True).click()
    page.wait_for_url("**/#/admin/collect")


def test_orders_tab_lists_paid_order_with_detail(page: Page, db, make_user, make_tour, make_order):
    user = make_user()
    tour = make_tour(price=1000)
    order = make_order(user, tour["tour_id"], payment_status=1)
    _login(page, user)
    _open(page, "#/admin/userprofile?tab=orders")
    rows = page.get_by_test_id("order-row")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("已付款")
    expect(rows.first).to_contain_text("NT$1,000")
    expect(rows.first).to_contain_text(order["order_id"][:8])
    expect(rows.first.get_by_role("button", name="繼續付款")).to_have_count(0)
    rows.first.get_by_role("button", name="明細").click()
    expect(page.get_by_test_id("order-detail")).to_contain_text(tour["title"])


def test_continue_payment_goes_to_pay_page(page: Page, db, make_user, make_tour):
    user = make_user()
    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    order_id = _api_pending_order(db, user, tour)
    _login(page, user)
    _open(page, "#/admin/userprofile?tab=orders")
    row = _row(page, order_id)
    expect(row).to_contain_text("待付款")
    row.get_by_role("button", name="繼續付款").click()
    page.wait_for_url(f"**/#/pay?order={order_id}")
    _fill_contact(page)
    page.get_by_role("button", name="確認並前往付款").click()
    page.wait_for_url(f"{MOCK_BASE}/**")
    expect(page.get_by_role("button", name="付款成功")).to_be_visible()


def test_overdue_pending_order_has_no_continue_button(page: Page, db, make_user, make_tour, make_order):
    user = make_user()
    overdue = make_order(user, make_tour(price=1000)["tour_id"], payment_status=-1)
    in_progress = make_order(user, make_tour(price=1000)["tour_id"], payment_status=0)
    for order in (overdue, in_progress):
        db.execute(
            "UPDATE orders SET created_at = now() - interval '61 minutes' WHERE order_id = %s",
            (order["order_id"],),
        )
    db.execute(
        "INSERT INTO payment (user_id, order_id, payment_method, payment_status) VALUES (%s, %s, 'credit_card', 0)",
        (user["user_id"], in_progress["order_id"]),
    )
    try:
        _login(page, user)
        _open(page, "#/admin/userprofile?tab=orders")
        expect(page.get_by_test_id("order-row")).to_have_count(2)
        overdue_row = _row(page, overdue["order_id"])
        expect(overdue_row).to_contain_text("已逾時")
        expect(overdue_row.get_by_role("button", name="繼續付款")).to_have_count(0)
        busy_row = _row(page, in_progress["order_id"])
        expect(busy_row).to_contain_text("付款處理中")
        expect(busy_row.get_by_role("button", name="繼續付款")).to_have_count(0)
        # 讀取不會把逾時的待付款訂單轉成 4
        status = db.execute(
            "SELECT payment_status FROM orders WHERE order_id = %s", (overdue["order_id"],)
        ).fetchone()[0]
        assert status == -1
    finally:
        db.execute("DELETE FROM payment WHERE order_id = %s", (in_progress["order_id"],))


def test_orders_tab_empty(page: Page, make_user):
    user = make_user()
    _login(page, user)
    _open(page, "#/admin/userprofile?tab=orders")
    expect(page.get_by_text("目前沒有訂單")).to_be_visible()
    expect(page.get_by_test_id("order-row")).to_have_count(0)


def test_admin_automatic_redirects_to_preference_tab(page: Page, make_user):
    user = make_user()
    _login(page, user)
    _open(page, "#/admin/manage/automatic")
    page.wait_for_url(re.compile(r".*#/admin/userprofile\?.*tab=preference"))


def test_profile_tab_from_query(page: Page, make_user):
    user = make_user()
    _login(page, user)
    _open(page, "#/admin/userprofile?tab=orders")
    expect(page.locator(".sidebaritem.active")).to_have_text("個人訂單查看")
    expect(page.get_by_text("目前沒有訂單")).to_be_visible()
    _open(page, "#/admin/userprofile?tab=xxx")
    expect(page.locator(".sidebaritem.active")).to_have_text("會員資訊")
    expect(page.get_by_label("信箱")).to_be_visible()
