"""共用 fixture：API session、DB 連線、測試使用者、JWT。"""
import importlib.util
import os
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


@pytest.fixture
def make_user(db):
    created: list[str] = []

    def _make(role: str = "User", email: str | None = None) -> dict:
        email = email or f"p0-{uuid.uuid4().hex[:8]}@example.com"
        (user_id,) = db.execute(
            'INSERT INTO "user" (name, email, role, password, preference1, preference2, preference3) '
            "VALUES (%s, %s, %s, %s, 1, 2, 3) RETURNING user_id",
            ("P0 測試", email, role, "not-a-real-hash"),
        ).fetchone()
        created.append(str(user_id))
        return {"user_id": str(user_id), "email": email, "role": role}

    yield _make
    for user_id in created:
        delete_user(db, user_id)


def auth_header(user: dict) -> dict:
    """跟 backend 登入時簽發的 payload 一樣：{id, role}。"""
    token = jwt.encode(
        {"id": user["user_id"], "role": user["role"]},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
