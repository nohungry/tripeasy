import re
import time

import requests
from playwright.sync_api import Page, expect

from e2e.conftest import FRONTEND_BASE, MAILPIT_BASE, TEST_PASSWORD, captcha_cookie


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
    expect(page.get_by_role("heading", name="會員登入")).to_be_visible()


def test_unknown_route_shows_404(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/no-such-page")
    expect(page.get_by_text("找不到頁面", exact=True)).to_be_visible()


def test_logout_stays_in_spa(page: Page, make_user):
    user = make_user()
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    _login_via_ui(page, user["email"], TEST_PASSWORD)
    page.wait_for_url("**/#/admin/userprofile", timeout=10_000)

    page.evaluate("window.__spa_marker = 'alive'")
    # 桌機與手機選單的「嗨！」「登出」同時都是 visible，限定桌機的 .user-dropdown
    desktop_menu = page.locator(".user-dropdown")
    desktop_menu.get_by_text("嗨！").click()
    desktop_menu.get_by_role("link", name="登出", exact=True).click()

    page.wait_for_url("**/#/")
    assert page.evaluate("window.__spa_marker") == "alive"
    assert page.evaluate("localStorage.getItem('authToken')") is None
    # 首頁本身另帶一個 header（既有重複，P3 以後），故有兩個可見的「註冊/登入」，取第一個
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True).first).to_be_visible()


def test_facebook_login_not_offered(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    expect(page.get_by_role("heading", name="會員登入")).to_be_visible()
    expect(page.locator(".fa-facebook-f")).to_have_count(0)


def test_login_lockout_message(page: Page, make_user):
    user = make_user()
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    swal = page.get_by_role("dialog")

    for attempt in range(3):
        _login_via_ui(page, user["email"], "WrongPass123")
        expect(swal).to_be_visible()
        if attempt == 2:
            expect(swal).to_contain_text("帳號已鎖定 30 分鐘")
        page.get_by_role("button", name="OK", exact=True).click()
        expect(swal).to_be_hidden()

    _login_via_ui(page, user["email"], TEST_PASSWORD)
    expect(swal).to_contain_text("帳號鎖定中")


def test_search_page_single_header(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/search", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="購物專區")).to_be_visible()
    expect(page.locator(".header")).to_have_count(1)
    expect(page.get_by_text("找不到頁面")).to_have_count(0)


def test_invalid_token_redirects_and_clears_state(page: Page):
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    page.evaluate("localStorage.setItem('authToken', 'garbage-token')")
    page.reload()  # 讓 userStore 載入時讀到 token，先進入「已登入」狀態
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True)).to_have_count(0)
    page.goto(f"{FRONTEND_BASE}/#/admin/userprofile")
    page.wait_for_url("**/#/admin/login")
    assert page.evaluate("localStorage.getItem('authToken')") is None
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True)).to_be_visible()


def _latest_reset_link(email: str) -> str:
    """有期限地輪詢 Mailpit，取該收件人最新一封信中的重設連結。"""
    deadline = time.time() + 10
    messages = []
    while time.time() < deadline:
        messages = requests.get(
            f"{MAILPIT_BASE}/api/v1/search", params={"query": f"to:{email}"}, timeout=10
        ).json()["messages"]
        if messages:
            break
        time.sleep(0.5)
    assert messages, "沒有收到重設信"
    html = requests.get(f"{MAILPIT_BASE}/api/v1/message/{messages[0]['ID']}", timeout=10).json()["HTML"]
    match = re.search(r'href="([^"]*resetpw\?token=[^"]+)"', html)
    assert match, "信中找不到重設連結"
    return match.group(1)


def test_forgot_password_via_mailpit(page: Page, make_user):
    new_password = "Newpass123"
    user = make_user()

    page.goto(f"{FRONTEND_BASE}/#/admin/forgotpw")
    page.get_by_placeholder("請輸入 Email").fill(user["email"])
    page.get_by_role("button", name="送出", exact=True).click()
    swal = page.get_by_role("dialog")
    expect(swal).to_contain_text("連結寄送成功")
    swal.get_by_role("button", name="OK", exact=True).click()  # 模態對話框開著會讓頁面其餘內容從 a11y 樹消失

    link = _latest_reset_link(user["email"])
    # 頁面載入時會打 GET /captcha，其 Set-Cookie 會蓋掉注入值，故等該回應完成後才注入
    with page.expect_response(re.compile(r"/captcha$")):
        page.goto(link)
    page.context.add_cookies(
        [
            {
                "name": "captcha",
                "value": captcha_cookie("abcde"),
                "domain": "localhost",
                "path": "/",
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ]
    )

    page.get_by_placeholder("請輸入新密碼", exact=True).fill(new_password)
    page.get_by_placeholder("請再次輸入新密碼").fill(new_password)
    page.get_by_placeholder("請輸入驗證碼").fill("abcde")
    page.get_by_role("button", name="送出", exact=True).click()

    page.wait_for_url("**/#/admin/login", timeout=15_000)
    _login_via_ui(page, user["email"], new_password)
    page.wait_for_url("**/#/admin/userprofile", timeout=10_000)
