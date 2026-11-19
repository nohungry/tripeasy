"""共用 fixture：API session、DB 連線、測試使用者、JWT。"""
import datetime
import hashlib
import hmac
import importlib.util
import json
import os
import time
import uuid
from pathlib import Path

import jwt
import psycopg
import pytest
import requests
from dotenv import load_dotenv

from dbfactory import insert

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


def _cleanup_all(items, delete) -> None:
    """逐筆清除；單筆失敗不影響其餘，全部試完後才拋出第一個錯誤。"""
    first_error = None
    for item in items:
        try:
            delete(item)
        except Exception as exc:  # noqa: BLE001
            first_error = first_error or exc
    if first_error is not None:
        raise first_error


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
    _cleanup_all(created, lambda user_id: delete_user(db, user_id))


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


def mock_google_code(claims: dict) -> str:
    """向 mock-oauth（interactiveLogin: true）取一個授權碼；該碼換到的 userinfo 等於 claims。

    作法：POST 它的登入表單（欄位 username 與 claims JSON），取 302 Location 的 code。
    注意：mock 對任何 code（含亂填、重複使用）都會簽發 token，驗證 code 是 Google 的責任，這一層測不到。
    """
    from urllib.parse import parse_qs, urlparse

    r = requests.post(
        f"{MOCK_OAUTH_BASE}/google/authorize",
        params={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
            "response_type": "code",
            "scope": "openid email profile",
            "state": "p2",
        },
        data={"username": str(claims["sub"]), "claims": json.dumps(claims)},
        allow_redirects=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert r.status_code == 302, r.text
    return parse_qs(urlparse(r.headers["Location"]).query)["code"][0]


# ------------------------------------------------------------------ P3：測試行程、訂單與殘留清除

# 全小寫；比對用 lower(email)，且 email 必須以 @example.com 結尾
TEST_EMAIL_PREFIXES: tuple[str, ...] = (
    "p0-", "e2e-", "factory-", "a.", "g.", "mixed.", "nobody.", "val.", "race.", "pref.", "lower.", "dup.", "co.", "mock.",
)  # fmt: skip
TEST_TOUR_PREFIX = "p3-"


def delete_tour(db, tour_id: str) -> None:
    """依 FK 順序刪除行程與其附屬資料。"""
    p = (tour_id,)
    for table in ("review", "hidden_play", "favorite", "cart_item", "notification", "order_item", "tour_detail"):
        db.execute(f"DELETE FROM {table} WHERE tour_id = %s", p)
    restaurants = "SELECT restaurant_id FROM restaurant WHERE tour_id = %s"
    db.execute(f"DELETE FROM restaurant_business WHERE restaurant_id IN ({restaurants})", p)
    db.execute(f"DELETE FROM restaurant_menu WHERE restaurant_id IN ({restaurants})", p)
    db.execute("DELETE FROM restaurant WHERE tour_id = %s", p)
    db.execute("DELETE FROM hotel_room WHERE hotel_id IN (SELECT hotel_id FROM hotel WHERE tour_id = %s)", p)
    db.execute("DELETE FROM hotel WHERE tour_id = %s", p)
    db.execute("DELETE FROM tour WHERE tour_id = %s", p)


def purge_leftover_test_data(db) -> dict:
    """刪除前次測試殘留的測試會員與測試行程（先會員後行程）。"""
    user_ids = [
        str(user_id)
        for user_id, email in db.execute('SELECT user_id, lower(email) FROM "user"').fetchall()
        if email.endswith("@example.com") and email.startswith(TEST_EMAIL_PREFIXES)
    ]
    for user_id in user_ids:
        delete_user(db, user_id)
    tour_ids = [
        str(r[0])
        for r in db.execute(
            "SELECT tour_id FROM tour WHERE starts_with(title, %s)", (TEST_TOUR_PREFIX,)
        ).fetchall()
    ]
    for tour_id in tour_ids:
        delete_tour(db, tour_id)
    return {"users": len(user_ids), "tours": len(tour_ids)}


@pytest.fixture(scope="session", autouse=True)
def purge_leftovers(db):
    purge_leftover_test_data(db)


@pytest.fixture
def make_tour(db):
    created: list[str] = []

    def _make(item: str = "travel", status: int = 1, with_detail: bool = True, title: str | None = None) -> dict:
        if with_detail and item not in ("travel", "spot"):
            raise ValueError(f"item={item!r} 不能建立 tour_detail（只允許 travel／spot）")
        title = title or f"{TEST_TOUR_PREFIX}{uuid.uuid4().hex[:8]}"
        assert title.startswith(TEST_TOUR_PREFIX), title
        tour_type = "tourgroup" if item == "travel" else "backpacker"
        # tour_start_date／tour_end_date 刻意不傳（保持 NULL）
        row = insert(db, "tour", type=tour_type, item=item, status=status, title=title)
        tour_id = str(row["tour_id"])
        created.append(tour_id)
        if with_detail:
            insert(db, "tour_detail", tour_id=tour_id)
        return {"tour_id": tour_id, "title": title, "type": tour_type, "item": item, "status": status}

    yield _make
    _cleanup_all(created, lambda tour_id: delete_tour(db, tour_id))


def live_promotion(db, make_tour) -> dict:
    """建立一個上架行程，並寫一筆有效的促銷（now() ± 1 day、discount 10、promo_price 900）；回傳該行程。"""
    t = make_tour()
    db.execute(
        "INSERT INTO notification (tour_id, type, start_date, end_date, discount, promo_price) "
        "VALUES (%s, '促銷', now() - interval '1 day', now() + interval '1 day', 10, 900)",
        (t["tour_id"],),
    )  # notification 由 make_tour teardown 的 delete_tour 清除
    return t


@pytest.fixture
def make_order(db):
    created: list[tuple[str, str]] = []

    def _make(
        user: dict, tour_id: str, payment_status: int = 1, quantity: int = 1, order_payment_status: int | None = None
    ) -> dict:
        """payment_status 是 order_item 的；order_payment_status 是 orders 的（預設與 payment_status 相同）。"""
        total = 1000 * quantity
        order_status = payment_status if order_payment_status is None else order_payment_status
        order = insert(db, "orders", user_id=user["user_id"], payment_status=order_status, total_price=total)
        order_id = str(order["order_id"])
        item = insert(
            db, "order_item", order_id=order_id, tour_id=tour_id, payment_status=payment_status,
            total_price=total, quantity=quantity, start_date=datetime.datetime.now(),
        )  # fmt: skip
        item_id = str(item["order_item_id"])
        created.append((order_id, item_id))
        return {"order_id": order_id, "order_item_id": item_id}

    yield _make

    def _delete(pair):
        order_id, item_id = pair
        db.execute("DELETE FROM order_item WHERE order_item_id = %s", (item_id,))
        db.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))

    _cleanup_all(created, _delete)
