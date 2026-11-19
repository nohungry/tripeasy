import datetime
import json
import uuid

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import FRONTEND_BASE, login_token

EXPIRED = datetime.timedelta(seconds=-60)


def _seed_tour(db, item: str) -> tuple[str, str]:
    """seed 中該 item 第一個上架行程（ORDER BY title）的 (tour_id, title)；只讀。"""
    row = db.execute(
        "SELECT tour_id, title FROM tour WHERE item = %s AND status = 1 ORDER BY title LIMIT 1", (item,)
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


@pytest.mark.parametrize("path", [str(uuid.uuid4()), "not-a-uuid"], ids=["uuid-not-exist", "not-a-uuid"])
def test_detail_page_unknown_tour(page: Page, path):
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
    _open_detail(page, tour_id)
    # 提示只顯示 2 秒（timer），先確認提示，再確認標題
    expect(page.get_by_text("登入已過期", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    assert page.evaluate("localStorage.getItem('authToken')") is None
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True)).to_be_visible()
