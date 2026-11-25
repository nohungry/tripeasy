"""E2E 共用設定：重用 tests/conftest.py 的 fixture 與 helper（以 importlib 載入，避免模組名 conftest 衝突）。"""

import datetime
import importlib.util
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# 已過期 token 的 exp 偏移（login_token(exp_delta=EXPIRED)）
EXPIRED = datetime.timedelta(seconds=-60)


def _load_tests_conftest():
    spec = importlib.util.spec_from_file_location("tests_conftest", ROOT / "tests" / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_tests_conftest = _load_tests_conftest()

# 明確匯出（pytest 以模組屬性收集 fixture）。mock_google_code 由 Task 10 補進。
db = _tests_conftest.db
mock_google_code = _tests_conftest.mock_google_code
make_user = _tests_conftest.make_user
make_tour = _tests_conftest.make_tour
make_order = _tests_conftest.make_order
make_coupon = _tests_conftest.make_coupon
live_promotion = _tests_conftest.live_promotion
purge_leftovers = _tests_conftest.purge_leftovers
delete_user = _tests_conftest.delete_user
auth_header = _tests_conftest.auth_header
login_token = _tests_conftest.login_token
TEST_PASSWORD = _tests_conftest.TEST_PASSWORD
captcha_cookie = _tests_conftest.captcha_cookie
API_BASE = _tests_conftest.API_BASE
FRONTEND_BASE = _tests_conftest.FRONTEND_BASE
MAILPIT_BASE = _tests_conftest.MAILPIT_BASE


@pytest.fixture(scope="session")
def base_url():
    return FRONTEND_BASE


@pytest.fixture
def new_email(db):
    """回傳產生 e2e-<uuid8>@example.com 的函式；teardown 刪除這些 email 對應的會員。"""
    created: list[str] = []

    def _new() -> str:
        email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
        created.append(email)
        return email

    yield _new
    for email in created:
        row = db.execute('SELECT user_id FROM "user" WHERE email = %s', (email,)).fetchone()
        if row:
            delete_user(db, str(row[0]))
