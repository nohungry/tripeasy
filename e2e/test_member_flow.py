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
