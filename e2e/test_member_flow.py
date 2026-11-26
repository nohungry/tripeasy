import json
import re
import uuid
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import (
    API_BASE,
    EXPIRED,
    FRONTEND_BASE,
    MAILPIT_BASE,
    TEST_PASSWORD,
    auth_header,
    captcha_cookie,
    login_token,
)


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
    with page.expect_response("**/login/status"):
        page.reload()  # 讓 userStore 載入時讀到 token；等初始導航的 /login/status 結束，避免後續 hash 跳轉被吞掉
    expect(page.get_by_role("heading", name="會員登入")).to_be_visible()
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True)).to_have_count(0)
    with page.expect_response("**/login/status") as status:
        page.goto(f"{FRONTEND_BASE}/#/admin/userprofile")
    assert status.value.status == 401
    page.wait_for_url("**/#/admin/login")
    assert page.evaluate("localStorage.getItem('authToken')") is None
    expect(page.get_by_role("link", name="註冊/登入", exact=True).filter(visible=True)).to_be_visible()


def _latest_reset_link(email: str) -> str:
    """有期限地輪詢 Mailpit，取該收件人最新一封信中的重設連結。"""
    deadline = time.time() + 10
    messages = []
    while time.time() < deadline:
        search = requests.get(
            f"{MAILPIT_BASE}/api/v1/search", params={"query": f"to:{email}"}, timeout=10
        )
        search.raise_for_status()
        messages = search.json()["messages"]
        if messages:
            break
        time.sleep(0.5)
    assert messages, "沒有收到重設信"
    detail = requests.get(f"{MAILPIT_BASE}/api/v1/message/{messages[0]['ID']}", timeout=10)
    detail.raise_for_status()
    html = detail.json()["HTML"]
    match = re.search(r'href="([^"]*resetpw\?token=[^"]+)"', html)
    assert match, "信中找不到重設連結"
    return match.group(1)


def test_forgot_password_via_mailpit(page: Page, make_user):
    new_password = "Newpass123"
    user = make_user()

    page.goto(f"{FRONTEND_BASE}/#/admin/forgotpw")
    page.get_by_placeholder("請輸入 Email").fill(user["email"])
    page.get_by_role("button", name="送出", exact=True).click()
    expect(page.get_by_role("dialog")).to_contain_text("連結寄送成功")

    link = _latest_reset_link(user["email"])
    # 模擬使用者從信中點連結：新分頁整頁載入（舊分頁的成功 Swal 不會干擾）
    reset_page = page.context.new_page()
    # 頁面載入時會打 GET /captcha，其 Set-Cookie 會蓋掉注入值，故等該回應完成後才注入
    with reset_page.expect_response(re.compile(r"/captcha$")):
        reset_page.goto(link)
    page.context.add_cookies(
        [
            {
                "name": "captcha",
                "value": captcha_cookie("abcde"),
                "domain": urlparse(API_BASE).hostname,
                "path": "/",
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ]
    )

    expect(reset_page.get_by_role("heading", name="修改密碼")).to_be_visible()
    reset_page.get_by_placeholder("請輸入新密碼", exact=True).fill(new_password)
    reset_page.get_by_placeholder("請再次輸入新密碼").fill(new_password)
    reset_page.get_by_placeholder("請輸入驗證碼").fill("abcde")
    reset_page.get_by_role("button", name="送出", exact=True).click()

    reset_page.wait_for_url("**/#/admin/login", timeout=15_000)
    _login_via_ui(reset_page, user["email"], new_password)
    reset_page.wait_for_url("**/#/admin/userprofile", timeout=10_000)
    expect(reset_page.get_by_label("信箱")).to_have_value(user["email"])


# ---- Task 9：會員中心 ----

AVATAR_FIXTURE = Path(__file__).parent / "fixtures" / "avatar.png"


def _login_to_profile(page: Page, user: dict) -> None:
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    _login_via_ui(page, user["email"], TEST_PASSWORD)
    page.wait_for_url("**/#/admin/userprofile", timeout=10_000)
    expect(page.get_by_label("信箱")).to_have_value(user["email"])


# 註：「儲存設定」「更新密碼」按鈕內有 bootstrap-icons 字型圖示，圖示字元會進入 accessible name，
# 無法用 exact=True，改用子字串比對。


def _edit_name(page: Page, new_name: str) -> None:
    # 姓名欄預設 disabled，要先按旁邊的編輯圖示
    page.locator("#userinfo .form-group").filter(has=page.locator("#name")).locator(".edit-icon").click()
    page.get_by_label("姓名").fill(new_name)


def test_profile_edit_name_and_preferences(page: Page, make_user):
    user = make_user()
    _login_to_profile(page, user)

    _edit_name(page, "新名字")
    page.get_by_label("個人偏好", exact=True).select_option("懶人輕鬆")
    with page.expect_response(re.compile(r"/user/userinfo/info$")) as resp:
        page.get_by_role("button", name="儲存設定").click()
    assert resp.value.status == 200

    page.reload()
    expect(page).to_have_url(re.compile(r"#/admin/userprofile$"))
    expect(page.get_by_label("姓名")).to_have_value("新名字")
    expect(page.get_by_label("個人偏好", exact=True)).to_have_value("懶人輕鬆")


def test_avatar_upload(page: Page, make_user, db):
    user = make_user()
    _login_to_profile(page, user)

    sidebar_img = page.locator(".sidebar .headimg")
    old_src = sidebar_img.get_attribute("src")
    with page.expect_response(re.compile(r"/user/userinfo/avatar$")) as resp:
        with page.expect_file_chooser() as chooser:
            sidebar_img.click()
        chooser.value.set_files(str(AVATAR_FIXTURE))
    assert resp.value.status == 200
    new_url = resp.value.json()["data"]["avatar_url"]

    assert new_url != old_src
    expect(sidebar_img).to_have_attribute("src", new_url)
    expect(page.locator(".user-dropdown #userPicture")).to_have_attribute("src", new_url)
    (db_url,) = db.execute('SELECT avatar_url FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    assert db_url == new_url

    page.reload()
    expect(page.locator(".user-dropdown #userPicture")).to_have_attribute("src", new_url)
    assert page.evaluate("localStorage.getItem('userPicture')") == new_url


def test_change_password_redirects_to_login(page: Page, make_user):
    new_password = "Newpass123"
    user = make_user()
    _login_to_profile(page, user)

    old_token = page.evaluate("localStorage.getItem('authToken')")
    page.get_by_placeholder("請輸入舊密碼").fill(TEST_PASSWORD)
    page.locator("#password .pw-edit-icon").nth(0).click()
    page.locator("#password .pw-edit-icon").nth(1).click()
    page.get_by_placeholder("請輸入新密碼").fill(new_password)
    page.get_by_placeholder("再次輸入新密碼").fill(new_password)
    page.get_by_role("button", name="更新密碼").click()

    page.wait_for_url("**/#/admin/login", timeout=10_000)
    assert page.evaluate("localStorage.getItem('authToken')") is None
    stale = requests.get(
        f"{API_BASE}/api/v1/user/userinfo/info",
        headers={"Authorization": f"Bearer {old_token}"},
        timeout=10,
    )
    assert stale.status_code == 401
    _login_via_ui(page, user["email"], new_password)
    page.wait_for_url("**/#/admin/userprofile", timeout=10_000)
    expect(page.get_by_label("信箱")).to_have_value(user["email"])


def test_null_password_user_sees_set_password_hint(page: Page, make_user):
    user = make_user(password=None)
    token = auth_header(user)["Authorization"].removeprefix("Bearer ")
    page.add_init_script(f"localStorage.setItem('authToken', '{token}')")
    page.goto(f"{FRONTEND_BASE}/#/admin/userprofile")
    expect(page.get_by_label("信箱")).to_have_value(user["email"])

    page.get_by_placeholder("請輸入舊密碼").fill("Whatever123")
    page.locator("#password .pw-edit-icon").nth(0).click()
    page.locator("#password .pw-edit-icon").nth(1).click()
    page.get_by_placeholder("請輸入新密碼").fill("Newpass123")
    page.get_by_placeholder("再次輸入新密碼").fill("Newpass123")
    page.get_by_role("button", name="更新密碼").click()

    expect(page.get_by_role("dialog")).to_contain_text("此帳號尚未設定密碼，請透過忘記密碼設定。")


def test_expired_token_redirects_to_login(page: Page, make_user):
    user = make_user()
    _login_to_profile(page, user)

    page.evaluate("t => localStorage.setItem('authToken', t)", login_token(user, exp_delta=EXPIRED))
    _edit_name(page, "過期後改名")
    with page.expect_response(re.compile(r"/user/userinfo/info$")) as resp:
        page.get_by_role("button", name="儲存設定").click()
    assert resp.value.status == 401

    page.wait_for_url("**/#/admin/login", timeout=10_000)
    for key in ["authToken", "userName", "userPicture", "levelName"]:
        assert page.evaluate("k => localStorage.getItem(k)", key) is None, key


def test_profile_save_network_error_shows_message(page: Page, make_user):
    user = make_user()
    page_errors: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))
    _login_to_profile(page, user)

    def handler(route):
        if route.request.method == "PATCH":
            route.abort()
        else:
            route.continue_()

    page.route("**/api/v1/user/userinfo/info", handler)
    _edit_name(page, "斷線改名")
    page.get_by_role("button", name="儲存設定").click()

    expect(page.locator(".swal2-icon-error")).to_be_visible()
    expect(page.get_by_role("dialog")).to_contain_text("無法連線到伺服器")
    assert not [e for e in page_errors if "Cannot read properties of undefined" in e], page_errors


def test_resetpw_page_opens_with_expired_token(page: Page, make_user):
    """既有行為的回歸測試：過期 token 不得讓重設密碼頁被導走（一開始就綠）。

    這個案例只驗過期 token 不會把使用者導走；已登入（token 有效）的使用者能不能開這兩頁，
    也就是 authPages 擋錯頁的保護，由 test_logged_in_user_can_open_forgotpw_and_resetpw 負責。
    """
    user = make_user()
    page.add_init_script(
        f"localStorage.setItem('authToken', '{login_token(user, exp_delta=EXPIRED)}')"
    )
    # resetpw 不在 authPages：守衛不再打 /login/status，直接等頁面內容
    page.goto(f"{FRONTEND_BASE}/#/admin/resetpw?token=x")
    expect(page.get_by_role("heading", name="修改密碼")).to_be_visible()
    assert "#/admin/resetpw" in page.url


@pytest.mark.parametrize(
    "path,heading", [("register", "會員註冊"), ("forgotpw", "忘記密碼")]
)
def test_register_and_forgotpw_pages_open_with_expired_token(page: Page, make_user, path, heading):
    """既有行為的回歸測試（一開始就綠）。

    只驗過期 token 不會把使用者導走；已登入（token 有效）時被導走的保護，
    由 test_logged_in_user_can_open_forgotpw_and_resetpw 負責（該案例涵蓋 forgotpw 與 resetpw）。
    """
    user = make_user()
    page.add_init_script(
        f"localStorage.setItem('authToken', '{login_token(user, exp_delta=EXPIRED)}')"
    )
    if path == "register":  # register 仍在 authPages，守衛會先打 /login/status；forgotpw 不會
        with page.expect_response("**/login/status"):
            page.goto(f"{FRONTEND_BASE}/#/admin/{path}")
    else:
        page.goto(f"{FRONTEND_BASE}/#/admin/{path}")
    expect(page.get_by_role("heading", name=heading)).to_be_visible()
    assert f"#/admin/{path}" in page.url


def test_coming_soon_tabs(page: Page, make_user):
    user = make_user()
    _login_to_profile(page, user)
    for tab in ["個人偏好設定", "會員等級", "個人訂單查看"]:
        page.locator(".sidebar").get_by_text(tab, exact=True).click()
        expect(page.get_by_text("即將開放", exact=True)).to_be_visible()
        expect(page.get_by_label("信箱")).not_to_be_visible()
    page.locator(".sidebar").get_by_text("會員資訊", exact=True).click()
    expect(page.get_by_label("信箱")).to_be_visible()
    expect(page.get_by_text("即將開放", exact=True)).to_have_count(0)


def test_require_auth_network_error_keeps_token(page: Page, make_user):
    user = make_user()
    _login_to_profile(page, user)

    page.route("**/login/status", lambda route: route.abort())
    # 先離開會員中心，確保接下來的 hash 跳轉會重新觸發 requireAuth
    page.goto(f"{FRONTEND_BASE}/#/")
    # 等首頁專屬的標題出現（header 各頁都有，不能用來判斷），確認已離開會員中心
    expect(page.get_by_role("heading", name="矚目功能")).to_be_visible()
    page.goto(f"{FRONTEND_BASE}/#/admin/userprofile")

    page.wait_for_url("**/#/admin/login", timeout=10_000)
    assert page.evaluate("localStorage.getItem('authToken')") is not None

    # 保留下來的 token 仍可用：解除攔截後可進入會員中心
    page.unroute("**/login/status")
    with page.expect_response("**/login/status"):
        page.reload()  # 目前在登入頁且 token 有效：守衛會自動導到會員中心，不需再 goto（同 hash 不會再發請求）
    page.wait_for_url("**/#/admin/userprofile")
    expect(page.get_by_label("信箱")).to_have_value(user["email"])


def test_logged_in_user_can_open_forgotpw_and_resetpw(page: Page, make_user):
    """spec §2.1：Google 會員要靠忘記密碼設定密碼；已登入點信中重設連結也要能開。登入頁仍導向會員中心（§0.2）。"""
    user = make_user()
    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    page.evaluate("t => localStorage.setItem('authToken', t)", login_token(user))
    with page.expect_response("**/login/status"):
        page.reload()  # 讓 userStore 載入時讀到 token；登入頁會被導向會員中心
    page.wait_for_url("**/#/admin/userprofile")

    page.goto(f"{FRONTEND_BASE}/#/admin/forgotpw")
    expect(page.get_by_role("heading", name="忘記密碼")).to_be_visible()
    assert "#/admin/forgotpw" in page.url

    page.goto(f"{FRONTEND_BASE}/#/admin/resetpw?token=x")
    expect(page.get_by_role("heading", name="修改密碼")).to_be_visible()
    assert "#/admin/resetpw" in page.url

    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    page.wait_for_url("**/#/admin/userprofile")


def test_google_login_via_mock(page: Page, new_email, db):
    email = new_email()
    sub = f"g-{email.split('@')[0]}"
    claims = {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": "Google 測試員",
        "picture": "https://example.com/g.png",
    }

    google_posts: list[str] = []
    page.on(
        "request",
        lambda r: google_posts.append(r.url) if r.method == "POST" and r.url.endswith("/login/google") else None,
    )

    page.goto(f"{FRONTEND_BASE}/#/admin/login")
    page.locator(".icon-circle.google").click()

    # 跨站到 mock-oauth 的登入表單（interactive 模式）
    page.wait_for_url("**/google/authorize**", timeout=10_000)
    page.get_by_placeholder("Enter any user/subject").fill(sub)
    page.get_by_placeholder("Optional claims JSON value").fill(json.dumps(claims))
    page.get_by_role("button", name="Sign-in").click()

    # 回跳前端：oauthRedirect.js 把 ?code= 轉進 hash 路由，loginPage 處理後清掉 code，登入成功後進會員中心
    page.wait_for_url(re.compile(r"/#/admin/login$"), timeout=10_000)
    assert "code=" not in page.url
    page.wait_for_url("**/#/admin/userprofile", timeout=15_000)
    assert "code=" not in page.url
    assert len(google_posts) == 1, google_posts
    expect(page.get_by_label("信箱")).to_have_value(email, timeout=10_000)
    assert page.evaluate("localStorage.getItem('authToken')")

    rows = db.execute(
        'SELECT s.provider_method FROM "socialLogin" s JOIN "user" u ON u.user_id = s.user_id WHERE u.email = %s',
        (email,),
    ).fetchall()
    assert [r[0] for r in rows] == ["google"]


# ---- P3 Task 8：提示框改用 timer、401 統一訊息 ----


def test_login_success_ok_closes_and_redirects_immediately(page: Page, make_user):
    user = make_user()
    page.goto(f"{FRONTEND_BASE}/#/admin/login", wait_until="domcontentloaded")
    _login_via_ui(page, user["email"], TEST_PASSWORD)

    page.locator(".swal2-confirm").wait_for(state="visible")
    page.locator(".swal2-confirm").click()
    # 原本要等滿 3 秒才跳轉；改用 timer 後按 OK 應立即跳轉
    page.wait_for_url("**/#/admin/userprofile", timeout=2000)


def test_signup_success_ok_redirects_immediately(page: Page, new_email):
    email = new_email()
    page.goto(f"{FRONTEND_BASE}/#/admin/register", wait_until="domcontentloaded")
    page.get_by_placeholder("請輸入姓名").fill("測試會員")
    page.get_by_placeholder("請輸入 Email").fill(email)
    page.get_by_placeholder("請輸入密碼").fill(TEST_PASSWORD)
    selects = page.get_by_role("combobox")
    for i, label in enumerate(["探索冒險", "放鬆療癒", "文化體驗"]):
        selects.nth(i).select_option(label=label)
    page.get_by_role("button", name="加入會員", exact=True).click()

    page.locator(".swal2-confirm").wait_for(state="visible")
    page.locator(".swal2-confirm").click()
    page.wait_for_url("**/#/admin/login", timeout=2000)


def _trigger_save(page: Page) -> None:
    _edit_name(page, "過期後改名")
    page.get_by_role("button", name="儲存設定").click()


def _trigger_avatar(page: Page) -> None:
    with page.expect_file_chooser() as chooser:
        page.locator(".sidebar .headimg").click()
    chooser.value.set_files(str(AVATAR_FIXTURE))


def _trigger_change_password(page: Page) -> None:
    new_password = "Newpass123"
    page.get_by_placeholder("請輸入舊密碼").fill(TEST_PASSWORD)
    page.locator("#password .pw-edit-icon").nth(0).click()
    page.locator("#password .pw-edit-icon").nth(1).click()
    page.get_by_placeholder("請輸入新密碼").fill(new_password)
    page.get_by_placeholder("再次輸入新密碼").fill(new_password)
    page.get_by_role("button", name="更新密碼").click()


@pytest.mark.parametrize(
    "trigger, pattern",
    [
        (_trigger_save, r"/user/userinfo/info$"),
        (_trigger_avatar, r"/user/userinfo/avatar$"),
        (_trigger_change_password, r"/auth/userinfo/resetprofilepw$"),
    ],
    ids=["save", "avatar", "password"],
)
def test_session_expired_on_member_api_shows_message(page: Page, make_user, trigger, pattern):
    user = make_user()
    _login_to_profile(page, user)

    page.evaluate("t => localStorage.setItem('authToken', t)", login_token(user, exp_delta=EXPIRED))
    # 提示框 2 秒後自動關閉，斷言要在 wait_for_url 之前；觸發動作在 expect_response 內
    with page.expect_response(re.compile(pattern)) as resp:
        trigger(page)
    assert resp.value.status == 401

    expect(page.get_by_text("登入已過期")).to_be_visible()
    expect(page.get_by_text("請重新登入")).to_be_visible()
    expect(page.locator(".swal2-icon-warning")).to_be_visible()
    expect(page.locator(".swal2-confirm")).to_be_hidden()
    expect(page.locator(".swal2-icon-error")).to_have_count(0)
    page.wait_for_url("**/#/admin/login", timeout=10_000)


# ---- P5 Task 2：姓名 2 到 20 字（註冊、會員資料、結帳）----
NAME_LEN_MSG = "「姓名」需為 2 到 20 個字"


def test_register_name_too_long_shows_message(page: Page, new_email):
    posts: list[str] = []
    page.on("request", lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/signup") else None)
    page.goto(f"{FRONTEND_BASE}/#/admin/register", wait_until="domcontentloaded")
    page.get_by_placeholder("請輸入姓名").fill("王" * 21)
    page.get_by_placeholder("請輸入 Email").fill(new_email())
    page.get_by_placeholder("請輸入密碼").fill(TEST_PASSWORD)
    selects = page.get_by_role("combobox")
    for i, label in enumerate(["探索冒險", "放鬆療癒", "文化體驗"]):
        selects.nth(i).select_option(label=label)
    page.get_by_role("button", name="加入會員", exact=True).click()
    expect(page.get_by_text(NAME_LEN_MSG)).to_be_visible()
    assert posts == []


def test_profile_name_too_long_shows_message(page: Page, make_user, db):
    user = make_user()
    _login_to_profile(page, user)
    patches: list[str] = []
    page.on("request", lambda r: patches.append(r.url) if r.method == "PATCH" and r.url.endswith("/user/userinfo/info") else None)
    _edit_name(page, "名" * 21)
    page.get_by_role("button", name="儲存設定").click()
    expect(page.get_by_text(NAME_LEN_MSG)).to_be_visible()
    assert patches == []
    assert db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()[0] == "P0 測試"


def _tour_in_cart(make_tour, user):
    from e2e.test_trade_flow import _api_add, _tour_dates

    start, end = _tour_dates()
    tour = make_tour(price=1000, start_date=start, end_date=end)
    _api_add(user, tour)
    return tour


def test_pay_name_too_long_blocked(page: Page, make_user, make_tour):
    from e2e.test_trade_flow import _go_checkout_from_cart, _login, _open

    user = make_user()
    _tour_in_cart(make_tour, user)
    _login(page, user)
    previews: list[str] = []
    page.on("request", lambda r: previews.append(r.url) if "/checkout/preview" in r.url else None)
    _open(page, "#/cart")
    _go_checkout_from_cart(page)
    expect(page.get_by_label("email")).not_to_have_value("")
    page.get_by_label("全名").fill("王" * 21)
    page.get_by_label("地址").fill("台北市測試路1號")
    page.get_by_label("連絡電話").fill("0912345678")
    page.get_by_role("button", name="確認並前往付款").click()
    expect(page.get_by_text(NAME_LEN_MSG)).to_be_visible()
    assert previews == []


def test_google_long_name_can_checkout(page: Page, db, make_tour):
    from e2e.conftest import delete_user, mock_google_code
    from e2e.test_trade_flow import MOCK_BASE, _go_checkout_from_cart, _open, _tour_dates

    tag = uuid.uuid4().hex[:8]
    claims = {
        "sub": f"g-{tag}",
        "email": f"g.{tag}@example.com",
        "email_verified": True,
        "name": "長" * 25,
        "picture": "https://example.com/g.png",
    }
    r = requests.post(f"{API_BASE}/api/v1/auth/userinfo/login/google", json={"code": mock_google_code(claims)}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    user = {"user_id": data["user"]["id"], "email": claims["email"], "role": "User"}
    try:
        start, end = _tour_dates()
        tour = make_tour(price=1000, start_date=start, end_date=end)
        page.add_init_script(
            f"localStorage.setItem('authToken', {json.dumps(data['token'])}); localStorage.setItem('userName', 'e2e-user');"
        )
        body = {
            "type": tour["type"], "item": tour["item"], "people": 1,
            "options": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        }  # fmt: skip
        res = requests.post(
            f"{API_BASE}/api/v1/user/trade/cart/{tour['tour_id']}",
            json=body, headers={"Authorization": f"Bearer {data['token']}"}, timeout=5,
        )  # fmt: skip
        assert res.status_code in (200, 201), res.text
        _open(page, "#/cart")
        _go_checkout_from_cart(page)
        expect(page.get_by_label("全名")).to_have_value("長" * 20)
        page.get_by_label("地址").fill("台北市測試路1號")
        page.get_by_label("連絡電話").fill("0912345678")
        page.get_by_role("button", name="確認並前往付款").click()
        page.wait_for_url(f"{MOCK_BASE}/**")
    finally:
        delete_user(db, user["user_id"])
