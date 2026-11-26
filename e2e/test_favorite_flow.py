"""P5 Task 8：愛心元件、收藏頁、P5 主線 E2E（spec §0、§5）。

寫入一律用 make_user；等 API 一律 expect_response，不用固定秒數等待。
"""

import re
import urllib.parse

import requests
from playwright.sync_api import Page, expect

from e2e.conftest import API_BASE, FRONTEND_BASE, auth_header
from e2e.test_product_flow import HOME_API, _home_response, _search_response
from e2e.test_trade_flow import (
    _fill_contact,
    _go_checkout_from_cart,
    _login,
    _open,
    _pay_and_reach_mock,
    _tour_dates,
)

COLLECTION_API = f"{API_BASE}/api/v1/user/collection/info"


def _is_collection(method: str):
    def _match(r):
        return r.request.method == method and "/user/collection/info/" in r.url

    return _match


def _is_favorites_list(r):
    return r.request.method == "GET" and r.url.split("?")[0].endswith("/user/collection/info/all")


def _open_search_for(page: Page, title: str):
    """以標題關鍵字開搜尋頁，等搜尋 API 回來，回傳該標題的卡片。"""
    with page.expect_response(_search_response(keyword=urllib.parse.quote(title))):
        page.goto(f"{FRONTEND_BASE}/#/search?keyword={urllib.parse.quote(title)}", wait_until="domcontentloaded")
    card = page.get_by_test_id("tour-card").filter(has_text=title)
    expect(card).to_have_count(1)
    return card


def _open_collect(page: Page) -> None:
    with page.expect_response(_is_favorites_list):
        page.goto(f"{FRONTEND_BASE}/#/admin/collect", wait_until="domcontentloaded")


def _db_favorites(db, user: dict) -> int:
    return db.execute("SELECT count(*) FROM favorite WHERE user_id = %s", (user["user_id"],)).fetchone()[0]


def _api_favorite(user: dict, tour: dict) -> str:
    res = requests.post(f"{COLLECTION_API}/{tour['tour_id']}", headers=auth_header(user), timeout=5)
    assert res.status_code in (200, 201), res.text
    return res.json()["data"]["favorite_id"]


def test_p5_main_flow(page: Page, db, make_user, make_tour):
    user = make_user()
    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    _login(page, user)

    card = _open_search_for(page, tour["title"])
    heart = card.get_by_test_id("favorite-heart")
    expect(heart).to_have_attribute("aria-pressed", "false")
    with page.expect_response(_is_collection("POST")):
        heart.click()
    expect(heart).to_have_attribute("aria-pressed", "true")
    assert _db_favorites(db, user) == 1

    _open_collect(page)
    fav = page.get_by_test_id("favorite-card").filter(has_text=tour["title"])
    expect(fav).to_have_count(1)
    fav.click()
    page.wait_for_url(f"**/#/tour/{tour['tour_id']}")

    page.get_by_label("人數").fill("1")
    page.get_by_role("button", name="加入購物車").click()
    expect(page.get_by_text("已加入購物車")).to_be_visible()
    _open(page, "#/cart")
    order_id = _go_checkout_from_cart(page)
    _fill_contact(page)
    _pay_and_reach_mock(page)
    page.get_by_role("button", name="付款成功").click()
    page.wait_for_url("**/#/pay/result?order=*")
    expect(page.get_by_text("付款成功")).to_be_visible(timeout=15000)

    with page.expect_response(lambda r: "/user/orders" in r.url and r.request.method == "GET"):
        page.goto(f"{FRONTEND_BASE}/#/admin/userprofile?tab=orders", wait_until="domcontentloaded")
    row = page.get_by_test_id("order-row").filter(has_text=order_id[:8])
    expect(row).to_have_count(1)
    expect(row).to_contain_text("已付款")
    row.get_by_role("button", name="明細").click()
    expect(page.get_by_test_id("order-detail")).to_contain_text(tour["title"])

    with page.expect_response(lambda r: "/user/points/records" in r.url and r.request.method == "GET"):
        page.goto(f"{FRONTEND_BASE}/#/admin/userprofile?tab=level", wait_until="domcontentloaded")
    record = page.get_by_test_id("point-record")
    expect(record).to_have_count(1)
    expect(record).to_contain_text("購物回饋")
    expect(record).to_contain_text("+100")

    _open_collect(page)
    expect(page.get_by_test_id("favorite-card").filter(has_text=tour["title"])).to_have_count(1)
    with page.expect_response(_is_collection("DELETE")):
        page.get_by_role("button", name="取消收藏").click()
    expect(page.get_by_text("還沒有收藏的行程")).to_be_visible()
    assert _db_favorites(db, user) == 0


def test_tour_page_heart_toggles(page: Page, db, make_user, make_tour):
    user = make_user()
    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    _login(page, user)
    _open(page, f"#/tour/{tour['tour_id']}")
    heart = page.get_by_test_id("favorite-heart")
    expect(heart).to_have_attribute("aria-pressed", "false")
    with page.expect_response(_is_collection("POST")):
        heart.click()
    expect(heart).to_have_attribute("aria-pressed", "true")
    assert _db_favorites(db, user) == 1
    with page.expect_response(_is_collection("DELETE")):
        heart.click()
    expect(heart).to_have_attribute("aria-pressed", "false")
    assert _db_favorites(db, user) == 0


def test_guest_heart_goes_to_login(page: Page, make_tour):
    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    card = _open_search_for(page, tour["title"])
    card.get_by_test_id("favorite-heart").click()
    page.wait_for_url("**/#/admin/login")


def test_home_heart_does_not_open_tour(page: Page, make_user):
    user = make_user()
    _login(page, user)
    with page.expect_response(lambda r: HOME_API in r.url and r.status == 200):
        page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    card = page.get_by_test_id("home-product-card").first
    expect(card).to_be_visible()
    heart = card.get_by_test_id("favorite-heart")
    with page.expect_response(_is_collection("POST")):
        heart.click()
    expect(heart).to_have_attribute("aria-pressed", "true")
    expect(page).to_have_url(re.compile(r"#/$"))


def test_heart_reverts_on_failure(page: Page, db, make_user, make_tour):
    user = make_user()
    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    _login(page, user)
    card = _open_search_for(page, tour["title"])
    page.route(
        "**/user/collection/info/*",
        lambda r: r.fulfill(status=500, body='{"status":"error","message":"伺服器錯誤"}'),
    )
    heart = card.get_by_test_id("favorite-heart")
    heart.click()
    expect(page.locator(".swal2-popup")).to_be_visible()
    expect(heart).to_have_attribute("aria-pressed", "false")
    assert _db_favorites(db, user) == 0


def test_unlisted_favorite_is_marked_and_removable(page: Page, db, make_user, make_tour):
    user = make_user()
    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    _api_favorite(user, tour)
    db.execute("UPDATE tour SET status = 0 WHERE tour_id = %s", (tour["tour_id"],))
    _login(page, user)
    _open_collect(page)
    fav = page.get_by_test_id("favorite-card").filter(has_text=tour["title"])
    expect(fav).to_have_count(1)
    expect(fav.get_by_text("已下架")).to_be_visible()
    url = page.url
    fav.click()
    expect(page).to_have_url(url)
    with page.expect_response(_is_collection("DELETE")):
        fav.get_by_role("button", name="取消收藏").click()
    expect(fav).to_have_count(0)
    assert _db_favorites(db, user) == 0


def test_collect_page_empty(page: Page, make_user):
    user = make_user()
    _login(page, user)
    _open_collect(page)
    expect(page.get_by_text("還沒有收藏的行程")).to_be_visible()
    page.get_by_role("link", name="去逛逛").click()
    page.wait_for_url("**/#/search")
