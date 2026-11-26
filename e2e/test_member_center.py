"""P5 Task 4：會員中心 ?tab= 切換、Header 連結、訂單分頁。"""

import re

import requests
from playwright.sync_api import Page, expect

from e2e.conftest import API_BASE, Api, auth_header, negative_points_via_refund
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
    # 沒有折扣：顯示「無」，不可露出 discount_type 的原始值 none
    expect(page.get_by_test_id("order-discount")).to_have_text("無")
    expect(page.get_by_test_id("order-detail")).not_to_contain_text("none")


def test_order_detail_shows_coupon_discount(page: Page, db, make_user, make_tour, make_order, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    order = make_order(user, make_tour(price=1000)["tour_id"], payment_status=1)
    db.execute(
        "UPDATE user_coupon SET status = 1, order_id = %s WHERE coupon_id = %s", (order["order_id"], coupon["coupon_id"])
    )
    try:
        _login(page, user)
        _open(page, "#/admin/userprofile?tab=orders")
        row = _row(page, order["order_id"])
        row.get_by_role("button", name="明細").click()
        detail = page.get_by_test_id("order-detail")
        expect(detail).to_contain_text("優惠券")
        expect(detail).to_contain_text("-NT$100")
        expect(detail).not_to_contain_text("coupon")
    finally:
        db.execute("UPDATE user_coupon SET order_id = NULL WHERE coupon_id = %s", (coupon["coupon_id"],))


def test_orders_paging_uses_limit_10(page: Page, db, make_user, make_tour, make_order):
    user = make_user()
    tour = make_tour(price=1000)
    orders = [make_order(user, tour["tour_id"], payment_status=1) for _ in range(11)]
    for i, order in enumerate(orders):  # orders[10] 最舊，落在第 2 頁
        db.execute(
            "UPDATE orders SET created_at = now() - make_interval(mins => %s) WHERE order_id = %s",
            (i + 1, order["order_id"]),
        )
    _login(page, user)
    _open(page, "#/admin/userprofile?tab=orders")
    expect(page.get_by_test_id("order-row")).to_have_count(10)
    expect(_row(page, orders[10]["order_id"])).to_have_count(0)
    page.get_by_role("button", name="下一頁").click()
    expect(page.get_by_test_id("order-row")).to_have_count(1)
    expect(_row(page, orders[10]["order_id"])).to_have_count(1)


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
    for bogus in ("constructor", "toString", "__proto__"):
        _open(page, f"#/admin/userprofile?tab={bogus}")
        expect(page.locator(".sidebaritem.active")).to_have_text("會員資訊")
        expect(page.get_by_label("信箱")).to_be_visible()


def test_level_tab_shows_points_and_records(page: Page, db, make_user, make_tour, make_order):
    user = make_user()
    order = make_order(user, make_tour(price=1000)["tour_id"], payment_status=1)
    db.execute("UPDATE user_level SET travel_point = 170 WHERE user_id = %s", (user["user_id"],))
    for type_, point, mins in [("新增", 170, 3), ("減少", -100, 2), ("減少_確認中", -50, 1)]:
        db.execute(
            "INSERT INTO point_record (user_id, order_id, type, point, created_at) "
            "VALUES (%s, %s, %s, %s, now() - make_interval(mins => %s))",
            (user["user_id"], order["order_id"], type_, point, mins),
        )
    _login(page, user)
    _open(page, "#/admin/userprofile?tab=level")
    expect(page.get_by_text("點數餘額 170 點")).to_be_visible()
    expect(page.get_by_text("目前等級 初心旅人")).to_be_visible()
    expect(page.get_by_text("購物回饋比例 10%")).to_be_visible()
    rows = page.get_by_test_id("point-record")
    expect(rows).to_have_count(2)
    expect(rows.nth(1)).to_contain_text("購物回饋")
    expect(rows.nth(1)).to_contain_text("+170")
    expect(rows.nth(1)).to_contain_text(order["order_id"][:8])
    expect(rows.nth(0)).to_contain_text("點數折抵")
    expect(rows.nth(0)).to_contain_text("-100")
    expect(page.get_by_test_id("point-record").filter(has_text="-50")).to_have_count(0)
    expect(page.get_by_text("目前沒有可用的優惠券")).to_be_visible()
    expect(page.get_by_text("點數紀錄為明細，加總不一定等於目前餘額（初始點數沒有對應紀錄）")).to_be_visible()
    expect(page.get_by_text("升級規則尚未開放")).to_be_visible()


def test_level_tab_negative_points_shows_zero(page: Page, db, make_user, make_tour):
    user = negative_points_via_refund(Api(API_BASE), db, make_user, make_tour)
    _login(page, user)
    with page.expect_response(lambda r: "/userinfo/pointslevel" in r.url) as info:
        _open(page, "#/admin/userprofile?tab=level")
    assert info.value.status == 200
    expect(page.get_by_text("目前等級")).to_be_visible()  # 等級卡片在 API 回應後才會出現
    expect(page.get_by_text("點數餘額 0 點")).to_be_visible()
    expect(page.get_by_text("-8 點")).to_have_count(0)


# ---- P5 Task 6：個人偏好設定（通知設定）----
AUTOMATION_API = f"{API_BASE}/api/v1/user/automation"
DELISTED_NOTE = "（目前沒有上架行程）"


def _open_preference_tab(page: Page) -> None:
    """開分頁並等設定與地區清單兩支 API 都回來，才開始斷言。"""
    with (
        page.expect_response(re.compile(r"/user/automation/allnotifi-settings$")) as settings,
        page.expect_response(re.compile(r"/user/automation/regions$")) as regions,
    ):
        _open(page, "#/admin/userprofile?tab=preference")
    assert settings.value.status == 200
    assert regions.value.status == 200


def test_notify_settings_persist_after_reload(page: Page, db, make_user):
    user = make_user()
    _login(page, user)
    _open_preference_tab(page)
    expect(page.get_by_text("目前只儲存設定，尚未寄送通知")).to_be_visible()
    expect(page.get_by_label("國家")).to_have_count(0)  # 開啟價格追蹤才顯示
    page.get_by_label("出發前提醒").check()
    page.get_by_label("價格追蹤").check()
    page.get_by_label("國家").select_option("Japan")
    page.get_by_label("地區").select_option("Tokyo")
    page.get_by_label("預算上限").fill("30000")
    with page.expect_response(re.compile(r"/user/automation/price-tracking$")) as resp:
        page.get_by_role("button", name="儲存設定").click()
    assert resp.value.status == 200
    expect(page.get_by_role("dialog")).to_contain_text("設定已儲存")
    assert db.execute(
        "SELECT early_notify, flexible_notify, country, region, price FROM auto_setting WHERE user_id = %s",
        (user["user_id"],),
    ).fetchall() == [(1, 1, "Japan", "Tokyo", 30000.0)]

    with page.expect_response(re.compile(r"/user/automation/allnotifi-settings$")):
        page.reload()
    expect(page.get_by_label("出發前提醒")).to_be_checked()
    expect(page.get_by_label("價格追蹤")).to_be_checked()
    expect(page.get_by_label("國家")).to_have_value("Japan")
    expect(page.get_by_label("地區")).to_have_value("Tokyo")
    expect(page.get_by_label("預算上限")).to_have_value("30000")


def test_delisted_saved_region_shown_with_note(page: Page, db, make_user, make_tour):
    user = make_user()
    tour = make_tour()
    db.execute("UPDATE tour SET country = 'p5land', region = 'p5city' WHERE tour_id = %s", (tour["tour_id"],))
    saved = requests.patch(
        f"{AUTOMATION_API}/price-tracking",
        json={"price_tracking_enabled": True, "country": "p5land", "region": "p5city", "max_price": 1000},
        headers=auth_header(user),
        timeout=5,
    )
    assert saved.status_code == 200, saved.text
    db.execute("UPDATE tour SET status = 0 WHERE tour_id = %s", (tour["tour_id"],))

    _login(page, user)
    _open_preference_tab(page)
    expect(page.get_by_label("國家")).to_have_value("p5land")
    expect(page.get_by_label("地區")).to_have_value("p5city")
    expect(page.get_by_label("國家").locator("option:checked")).to_have_text(f"p5land{DELISTED_NOTE}")
    expect(page.get_by_label("地區").locator("option:checked")).to_have_text(f"p5city{DELISTED_NOTE}")

    with page.expect_response(re.compile(r"/user/automation/price-tracking$")) as resp:
        page.get_by_role("button", name="儲存設定").click()
    assert resp.value.status == 200
    expect(page.get_by_role("dialog")).to_contain_text("設定已儲存")
