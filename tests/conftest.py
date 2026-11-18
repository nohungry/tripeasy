"""共用 fixture：API session、DB 連線、測試使用者、JWT。"""
import datetime
import hashlib
import hmac
import importlib.util
import os
import time
import uuid
from pathlib import Path

import jwt
import psycopg
import pytest
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_BASE = os.getenv("TEST_API_BASE", "http://localhost:3000")
FRONTEND_BASE = os.getenv("TEST_FRONTEND_BASE", "http://localhost:5173")
MAILPIT_BASE = os.getenv("TEST_MAILPIT_BASE", "http://localhost:8025")
MOCK_OAUTH_BASE = os.getenv("TEST_MOCK_OAUTH_BASE", "http://localhost:8090")
DEFAULT_TIMEOUT = 10
BUILD_SCRIPT = ROOT / "db" / "seed-build" / "build_seed.py"


def load_build_seed():
    """seed 產生腳本不在 package 裡，用路徑載入。"""
    spec = importlib.util.spec_from_file_location("build_seed", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Api(requests.Session):
    """路徑以 / 開頭時自動接上 base，並一律帶 timeout（避免卡住的請求讓測試無限等待）。"""

    def __init__(self, base: str):
        super().__init__()
        self.base = base

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        if url.startswith("/"):
            url = self.base + url
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="session")
def api():
    session = Api(API_BASE)
    yield session
    session.close()


def _db_params() -> dict:
    return dict(
        host=os.getenv("TEST_DB_HOST", "localhost"),
        port=int(os.getenv("TEST_DB_PORT", "5432")),
        user=os.environ["POSTGRES_DB_USER"],
        password=os.environ["POSTGRES_DB_PASSWORD"],
        dbname=os.environ["POSTGRES_DB_NAME"],
    )


@pytest.fixture(scope="session")
def db():
    conn = psycopg.connect(**_db_params(), autocommit=True)
    yield conn
    conn.close()


@pytest.fixture
def tx():
    """不自動 commit 的連線。測試結束一律 rollback，不留下任何資料。"""
    conn = psycopg.connect(**_db_params())
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


# 直接參照 "user" 的表（V1 全部），順序即刪除順序（orders、cart 放最後）；test_member_auth 會比對 pg_constraint
USER_FK_TABLES = (
    '"socialLogin"', "user_level", "point_record", "user_coupon", "payment", "review",
    "hidden_play", "auto_setting", "favorite", "orders", "cart",
)  # fmt: skip


def delete_user(db, user_id: str) -> None:
    """依 FK 順序刪除使用者和它的附屬資料（涵蓋 V1 所有參照 "user" 的表，含 orders / cart 底下的間接相依）。"""
    # 先清掉依附在「該會員的 orders / cart」底下的子表
    order_ids = "SELECT order_id FROM orders WHERE user_id = %s"
    cart_ids = "SELECT cart_id FROM cart WHERE user_id = %s"
    db.execute(f"DELETE FROM order_item WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM payment WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM point_record WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM user_coupon WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM cart_item WHERE cart_id IN ({cart_ids})", (user_id,))
    # 再清直接參照 "user" 的表（orders、cart 放最後）
    for table in USER_FK_TABLES:
        db.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
    db.execute('DELETE FROM "user" WHERE user_id = %s', (user_id,))


TEST_PASSWORD = "Tripeasy123"
# TEST_PASSWORD 的 bcrypt（cost 10，用 backend 容器的 bcrypt 產生；測試環境沒有 Python bcrypt 套件）
TEST_PASSWORD_HASH = "$2b$10$Gv8aWHvXWoOcP9b.gyVTl.vEznO/bXW1hLig..ZaTtEgRMmJGuIlG"
_DEFAULT = object()


@pytest.fixture
def make_user(db):
    created: list[str] = []

    def _make(role: str = "User", email: str | None = None, password=_DEFAULT) -> dict:
        """password 預設存 TEST_PASSWORD 的 bcrypt；傳 None 存 NULL。"""
        if password is _DEFAULT:
            password = TEST_PASSWORD_HASH
        email = email or f"p0-{uuid.uuid4().hex[:8]}@example.com"
        (user_id,) = db.execute(
            'INSERT INTO "user" (name, email, role, password, preference1, preference2, preference3) '
            "VALUES (%s, %s, %s, %s, 1, 2, 3) RETURNING user_id",
            ("P0 測試", email, role, password),
        ).fetchone()
        created.append(str(user_id))
        # 同 Email 註冊交易（controllers/userinfo.js）：登入成功路徑會讀 user_level
        db.execute(
            "INSERT INTO user_level (user_id, level, name, badge_url, travel_point) "
            "VALUES (%s, 'Level 1', '初心旅人', 'https://example.com/badges/level1.png', 0)",
            (user_id,),
        )
        return {"user_id": str(user_id), "email": email, "role": role}

    yield _make
    for user_id in created:
        delete_user(db, user_id)


def password_fingerprint(password) -> str:
    """共用約定的 pwv：HMAC-SHA256(key = JWT_SECRET, msg = password ?? '') 的 hex 前 16 字元。"""
    key = os.environ["JWT_SECRET"].encode()
    return hmac.new(key, (password or "").encode(), hashlib.sha256).hexdigest()[:16]


def current_pwv(user: dict) -> str:
    """用新連線查該會員目前的 password 算 pwv（不沿用測試的 db fixture，避免交易可見性問題）。"""
    with psycopg.connect(**_db_params(), autocommit=True) as conn:
        row = conn.execute('SELECT password FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    return password_fingerprint(row[0] if row else None)


def login_token(user: dict, exp_delta: datetime.timedelta | None = None) -> str:
    """登入 token：{id, role, typ: 'login', pwv}；exp_delta 給定時 exp = 現在 + exp_delta（負值即已過期）。"""
    payload = {"id": user["user_id"], "role": user["role"], "typ": "login", "pwv": current_pwv(user)}
    payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + (exp_delta or datetime.timedelta(days=30))
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def reset_token(user: dict) -> str:
    """重設 token：{id, typ: 'reset', pwv}，效期 15 分鐘。"""
    payload = {
        "id": user["user_id"],
        "typ": "reset",
        "pwv": current_pwv(user),
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def auth_header(user: dict) -> dict:
    """跟 backend 登入時簽發的登入 token 一樣（帶 pwv）。"""
    return {"Authorization": f"Bearer {login_token(user)}"}


CAPTCHA_TTL_MS = 5 * 60 * 1000


def captcha_cookie(answer: str = "abcde", issued_at: int | None = None) -> str:
    """合法的驗證碼 cookie 值：'<expiresMs>.<hex64>'。

    issued_at 為簽發時間（epoch 毫秒，預設現在），expiresMs = issued_at + 5 分鐘；
    簽章 = HMAC-SHA256(key = CAPTCHA_SECRET, msg = f"{answer.lower()}.{expiresMs}")。
    金鑰在呼叫時才讀，缺少就 KeyError（不設預設值，避免與後端悄悄不一致）。
    """
    if issued_at is None:
        issued_at = int(time.time() * 1000)
    expires_ms = issued_at + CAPTCHA_TTL_MS
    key = os.environ["CAPTCHA_SECRET"].encode()
    sig = hmac.new(key, f"{answer.lower()}.{expires_ms}".encode(), hashlib.sha256).hexdigest()
    return f"{expires_ms}.{sig}"
