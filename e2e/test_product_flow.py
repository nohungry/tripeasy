import datetime
import json
import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import FRONTEND_BASE, live_promotion, login_token

EXPIRED = datetime.timedelta(seconds=-60)


def _seed_tour(db, item: str) -> tuple[str, str]:
    """seed 中該 item 第一個上架行程（ORDER BY title）的 (tour_id, title)；只讀。"""
    row = db.execute(
        "SELECT tour_id, title FROM tour WHERE item = %s AND status = 1 AND title NOT LIKE 'p3-%%' "
        "ORDER BY title LIMIT 1", (item,)
    ).fetchone()
    assert row, f"seed 沒有上架的 {item} 行程"
    return str(row[0]), row[1]


def _expire_session(page: Page, user: dict) -> None:
    """在頁面腳本執行前寫入過期 token 與 userName，userStore 一載入就是「已登入」。"""
    token = login_token(user, exp_delta=EXPIRED)
    page.add_init_script(
        f"localStorage.setItem('authToken', {json.dumps(token)}); localStorage.setItem('userName', 'expired-user');"
    )


def _open_detail(page: Page, tour_id: str) -> None:
    page.goto(f"{FRONTEND_BASE}/#/tour/{tour_id}", wait_until="domcontentloaded")


def test_detail_page_shows_travel_tour(page: Page, db):
    tour_id, title = _seed_tour(db, "travel")
    _open_detail(page, tour_id)
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page.get_by_role("heading", name="行程特色", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="行程規劃", exact=True)).to_be_visible()


@pytest.mark.parametrize(
    "item, headings",
    [
        ("hotel", ["房型介紹", "客房服務"]),
        ("food", ["餐廳介紹", "菜單", "營業時間"]),
        ("spot", ["行程特色", "行程規劃"]),
    ],
)
def test_detail_page_item_sections(page: Page, db, item, headings):
    tour_id, title = _seed_tour(db, item)
    _open_detail(page, tour_id)
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    for heading in headings:
        expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()


@pytest.mark.parametrize("path", [str(uuid.uuid4()), "not-a-uuid", "unlisted"], ids=["uuid-not-exist", "not-a-uuid", "unlisted"])
def test_detail_page_unknown_tour(page: Page, make_tour, path):
    if path == "unlisted":
        path = make_tour(status=2)["tour_id"]  # 已下架
    page.goto(f"{FRONTEND_BASE}/#/tour/{path}", wait_until="domcontentloaded")
    expect(page.get_by_text("查無此行程", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="回搜尋頁")).to_have_attribute("href", "#/search")


def test_detail_page_single_header(page: Page, db):
    # 落到 404 頁時也只有一組 header／footer，此測試要到綠燈（真的詳情頁）才有分辨力
    tour_id, title = _seed_tour(db, "travel")
    _open_detail(page, tour_id)
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page.locator(".header")).to_have_count(1)
    expect(page.locator(".footer")).to_have_count(1)


@pytest.mark.parametrize("path", ["#/tour", "#/tourfake", "#/tourfakeUSA"])
def test_fake_tour_routes_removed(page: Page, path):
    page.goto(f"{FRONTEND_BASE}/{path}", wait_until="domcontentloaded")
    expect(page.get_by_text("找不到頁面", exact=True)).to_be_visible()


def test_add_to_cart_coming_soon(page: Page, db):
    tour_id, title = _seed_tour(db, "travel")
    _open_detail(page, tour_id)
    expect(page.get_by_role("button", name="加入購物車（即將開放）")).to_be_disabled()


def test_detail_promo_price_shown(page: Page, db, make_tour):
    tour = make_tour()
    db.execute(
        "INSERT INTO notification (tour_id, type, start_date, end_date, discount, promo_price) "
        "VALUES (%s, '促銷', now() - interval '1 day', now() + interval '1 day', 10, 900)",
        (tour["tour_id"],),
    )  # notification 由 make_tour teardown 的 delete_tour 清除
    _open_detail(page, tour["tour_id"])
    expect(page.get_by_role("heading", name=tour["title"])).to_be_visible()
    expect(page.get_by_text("NT$900", exact=True)).to_be_visible()
    expect(page.locator("del").get_by_text("NT$1,000", exact=True)).to_be_visible()


def test_detail_with_expired_token_still_renders(page: Page, db, make_user):
    user = make_user()
    _expire_session(page, user)
    tour_id, title = _seed_tour(db, "travel")
    detail_auth: list[bool] = []
    page.on(
        "request",
        lambda r: detail_auth.append("authorization" in r.headers)
        if r.url.split("?")[0].endswith(f"/api/v1/user/product/search/{tour_id}")
        else None,
    )
    _open_detail(page, tour_id)
    # 提示只顯示 2 秒（timer），先確認提示，再確認標題
    expect(page.get_by_text("登入已過期", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page).to_have_url(re.compile(rf"#/tour/{tour_id}$"))
    assert detail_auth == [True, False]  # 第一筆帶過期 token，重試不帶
    assert page.evaluate("localStorage.getItem('authToken')") is None
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True)).to_be_visible()


def test_detail_server_error_shows_load_failed(page: Page, db):
    tour_id, _ = _seed_tour(db, "travel")
    page.route(
        "**/api/v1/user/product/search/*",
        lambda route: route.fulfill(
            status=500, content_type="application/json", body='{"status":"failed","message":"伺服器錯誤"}'
        ),
    )
    _open_detail(page, tour_id)
    expect(page.get_by_text("載入失敗，請稍後再試", exact=True)).to_be_visible()
    expect(page.get_by_text("查無此行程", exact=True)).to_have_count(0)


# ---------- 首頁 ----------

HOME_API = "/user/home/search/products"
HOME_CARD_TITLES = "[data-testid=home-product-card] h3"


def _home_titles(page: Page) -> list[str]:
    return page.locator(HOME_CARD_TITLES).all_inner_texts()


def _home_response(item: str, page_no: int | None = None):
    """predicate：首頁商品 API 且 item（與 page）符合。"""

    def _match(r):
        if HOME_API not in r.url or not re.search(rf"[?&]item={item}(&|$)", r.url):
            return False
        return page_no is None or re.search(rf"[?&]page={page_no}(&|$)", r.url) is not None

    return _match


def _api_titles(response) -> list[str]:
    return [row["旅遊名稱"] for row in response.json()["data"]]


def test_home_page_single_header(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    expect(page.locator(".header")).to_have_count(1)
    expect(page.locator(".footer")).to_have_count(1)


def test_home_products_match_api(page: Page, db, make_tour):
    promo_tour = live_promotion(db, make_tour)
    with page.expect_response(_home_response("popular")) as info:
        page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    expected = _api_titles(info.value)
    assert expected, "熱門專區回應不應為空"
    expect(page.locator(HOME_CARD_TITLES)).to_have_text(expected)

    categories = page.get_by_role("tablist", name="商品分類")
    subs = page.get_by_role("tablist", name="子分類")
    with page.expect_response(_home_response("promotion")) as info:
        subs.get_by_role("tab", name="促銷專區").click()
    expected = _api_titles(info.value)
    assert expected, "促銷專區回應不應為空（已自建促銷）"
    assert expected[0] == promo_tour["title"]
    expect(page.locator(HOME_CARD_TITLES)).to_have_text(expected)

    with page.expect_response(_home_response("hotel")) as info:
        categories.get_by_role("tab", name="背包客").click()
    expected = _api_titles(info.value)
    assert expected, "住宿回應不應為空"
    expect(subs.get_by_role("tab")).to_have_text(["住宿", "美食", "景點"])
    expect(page.locator(HOME_CARD_TITLES)).to_have_text(expected)


def test_home_product_pagination(page: Page):
    with page.expect_response(_home_response("popular", 1)) as info:
        page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    data = info.value.json()["data"]
    page_no = 1
    prev_button = page.get_by_role("button", name="上一頁")
    next_button = page.get_by_role("button", name="下一頁")
    expect(prev_button).to_be_disabled()
    while len(data) == 4:
        with page.expect_response(_home_response("popular", page_no + 1)) as info:
            next_button.click()
        page_no += 1
        data = info.value.json()["data"]
        expect(page.locator(HOME_CARD_TITLES)).to_have_text([row["旅遊名稱"] for row in data])
    assert page_no >= 2, "熱門專區至少要有 2 頁才能測分頁"
    expect(next_button).to_be_disabled()
    with page.expect_response(_home_response("popular", page_no - 1)) as info:
        prev_button.click()
    expect(page.locator(HOME_CARD_TITLES)).to_have_text(_api_titles(info.value))


def test_home_product_opens_detail(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    first = page.locator("[data-testid=home-product-card]").first
    expect(first).to_be_visible()
    title = first.locator("h3").inner_text()
    first.click()
    expect(page).to_have_url(re.compile(r"/#/tour/[^/]+$"))
    expect(page.get_by_role("heading", name=title)).to_be_visible()


def test_home_with_expired_token_lists_products(page: Page, make_user):
    _expire_session(page, make_user())
    page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    # 提示只顯示 2 秒（timer），先確認提示，再確認清單
    expect(page.get_by_text("登入已過期", exact=True)).to_be_visible()
    expect(page.locator("[data-testid=home-product-card]").first).to_be_visible()


# ---------- 搜尋頁與 header 搜尋框（Task 11） ----------

SEARCH_CARD = "[data-testid=tour-card]"
SEARCH_TITLES = "[data-testid=tour-card] h5"


def _search_response(**params):
    """predicate：搜尋列表 API（不含詳情），且 query 含指定的參數值。"""

    def _match(r):
        path, _, query = r.url.partition("?")
        if not path.endswith("/user/product/search"):
            return False
        return all(re.search(rf"[?&]{k}={v}(&|$)", "?" + query) for k, v in params.items())

    return _match


def _open_search(page: Page) -> list[str]:
    """開搜尋頁並回傳第一頁 API 的標題序列（斷言非空，PF7）。"""
    with page.expect_response(_search_response()) as info:
        page.goto(f"{FRONTEND_BASE}/#/search", wait_until="domcontentloaded")
    titles = _api_titles(info.value)
    assert titles, "搜尋頁第一頁回應不應為空"
    return titles


def test_search_lists_tours_from_api(page: Page):
    expected = _open_search(page)
    assert len(expected) == 6
    expect(page.locator(SEARCH_TITLES)).to_have_text(expected)


def test_search_pagination_visits_every_listed_tour_once(page: Page, db):
    first = _open_search(page)
    expect(page.locator(SEARCH_TITLES)).to_have_text(first)
    seen = list(first)
    next_button = page.get_by_role("button", name="下一頁")
    page_no = 1
    while next_button.is_enabled():
        page_no += 1
        with page.expect_response(_search_response(page=page_no)) as info:
            next_button.click()
        titles = _api_titles(info.value)
        expect(page.locator(SEARCH_TITLES)).to_have_text(titles)
        expect(page.get_by_text(f"第 {page_no} 頁")).to_be_visible()
        seen.extend(titles)
        assert page_no < 50, "分頁沒有終點"
    assert page_no >= 2, "至少要有 2 頁才能測分頁"
    assert len(seen) == len(set(seen)), f"分頁出現重複行程：{seen}"
    rows = db.execute("SELECT title FROM tour WHERE status = 1").fetchall()
    assert set(seen) == {r[0] for r in rows}


def test_header_keyword_search(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/", wait_until="domcontentloaded")
    box = page.locator(".search_txtbox:visible").first
    box.fill("  北海道 ")
    with page.expect_response(_search_response(keyword="%E5%8C%97%E6%B5%B7%E9%81%93")):
        box.press("Enter")
    expect(page).to_have_url(re.compile(r"#/search\?keyword="))
    expect(page.locator(SEARCH_TITLES)).to_have_text(["北海道雪景 5 日深度遊"])


def test_search_price_filter_and_sort(page: Page):
    _open_search(page)
    page.get_by_placeholder("最小金額").fill("20000")
    page.get_by_placeholder("最大金額").fill("50000")
    page.get_by_label("金額排序").select_option("desc")
    with page.expect_response(_search_response(min_price=20000, max_price=50000, sort_by="price", order="desc")) as info:
        page.get_by_role("button", name="搜尋", exact=True).click()
    rows = info.value.json()["data"]
    assert rows, "價格區間內應有行程"
    prices = [float(r["價錢"]) for r in rows]
    assert all(20000 <= p <= 50000 for p in prices), prices
    assert prices == sorted(prices, reverse=True), prices
    expect(page.locator(SEARCH_TITLES)).to_have_text([r["旅遊名稱"] for r in rows])


def test_search_no_result(page: Page):
    _open_search(page)
    page.get_by_placeholder("請輸入關鍵字（標題或介紹）").fill("p3-不存在-zzzz")
    page.get_by_role("button", name="搜尋", exact=True).click()
    expect(page.get_by_text("查無符合條件的行程")).to_be_visible()
    expect(page.locator(SEARCH_CARD)).to_have_count(0)


def test_search_card_opens_detail(page: Page):
    with page.expect_response(_search_response()) as info:
        page.goto(f"{FRONTEND_BASE}/#/search", wait_until="domcontentloaded")
    rows = info.value.json()["data"]
    assert rows, "搜尋頁第一頁回應不應為空"
    first_row = rows[0]
    card = page.locator(SEARCH_CARD).first
    expect(card.locator("h5")).to_have_text(first_row["旅遊名稱"])
    link = card.get_by_role("link", name="查看詳情")
    expect(link).to_have_attribute("href", f"#/tour/{first_row['旅遊編號']}")
    link.click()
    expect(page).to_have_url(re.compile(r"/#/tour/[^/]+$"))
    expect(page.get_by_role("heading", name=first_row["旅遊名稱"])).to_be_visible()


def test_search_country_region_selects_removed(page: Page):
    _open_search(page)
    expect(page.get_by_text("所在國家")).to_have_count(0)
    expect(page.get_by_text("所在地區")).to_have_count(0)
