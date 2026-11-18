from playwright.sync_api import Page, expect

from e2e.conftest import FRONTEND_BASE, TEST_PASSWORD


def test_signup_login_profile_main_flow(page: Page, new_email):
    email = new_email()

    page.goto(f"{FRONTEND_BASE}/#/admin/register")
    page.get_by_placeholder("請輸入姓名").fill("測試會員")
    page.get_by_placeholder("請輸入 Email").fill(email)
    page.get_by_placeholder("請輸入密碼").fill(TEST_PASSWORD)
    selects = page.get_by_role("combobox")
    for i, label in enumerate(["探索冒險", "放鬆療癒", "文化體驗"]):
        selects.nth(i).select_option(label=label)
    page.get_by_role("button", name="加入會員", exact=True).click()

    # 註冊成功後應導向 hash 路由的登入頁（現行 window.location.href='/admin/login' 會落到 /，故紅燈）
    page.wait_for_url("**/#/admin/login", timeout=10_000)

    page.get_by_placeholder("請輸入 Email").fill(email)
    page.get_by_placeholder("請輸入密碼").fill(TEST_PASSWORD)
    page.get_by_role("button", name="登入", exact=True).click()

    page.wait_for_url("**/#/admin/userprofile")
    expect(page.get_by_label("信箱")).to_have_value(email)


def _login_via_ui(page: Page, email: str, password: str) -> None:
    page.get_by_placeholder("請輸入 Email").fill(email)
    page.get_by_placeholder("請輸入密碼").fill(password)
    page.get_by_role("button", name="登入", exact=True).click()


def test_profile_requires_login(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/admin/userprofile")
    page.wait_for_url("**/#/admin/login")


def test_unknown_route_shows_404(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/no-such-page")
    expect(page.get_by_text("找不到頁面", exact=True)).to_be_visible()


def test_logout_stays_in_spa(page: Page, make_user):
    user = make_user()
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    _login_via_ui(page, user["email"], TEST_PASSWORD)
    page.wait_for_url("**/#/admin/userprofile", timeout=10_000)

    page.evaluate("window.__spa_marker = 'alive'")
    page.get_by_text("嗨！", exact=False).first.click()
    page.locator(".custom-dropdown-menu").get_by_role("link", name="登出", exact=True).click()

    page.wait_for_url("**/#/")
    assert page.evaluate("window.__spa_marker") == "alive"


def test_facebook_login_not_offered(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    expect(page.get_by_role("heading", name="會員登入")).to_be_visible()
    assert page.locator(".fa-facebook-f").count() == 0 or page.get_by_text("未開放").count() > 0


def test_login_lockout_message(page: Page, make_user):
    user = make_user()
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    swal = page.locator("#swal2-html-container")

    for attempt in range(3):
        _login_via_ui(page, user["email"], "WrongPass123")
        expect(swal).to_be_visible()
        if attempt == 2:
            expect(swal).to_contain_text("帳號已鎖定 30 分鐘")
        page.get_by_role("button", name="OK", exact=True).click()
        expect(swal).to_be_hidden()

    _login_via_ui(page, user["email"], TEST_PASSWORD)
    expect(swal).to_contain_text("帳號鎖定中")
