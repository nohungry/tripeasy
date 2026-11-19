"""P3 測試基礎建設：make_tour／make_order fixture、殘留清除、CI 版本鎖定。"""
import re
import uuid

import pytest
from dbfactory import insert

from conftest import ROOT

BASE = "/api/v1"


def test_make_tour_creates_listed_tour(api, make_tour):
    t = make_tour()
    r = api.get(f"{BASE}/user/product/search/{t['tour_id']}", params={"lang": "zh-TW"})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["title"] == t["title"]
    assert data["item"] == "travel"


def test_make_tour_rejects_detail_for_hotel(make_tour):
    with pytest.raises(ValueError):
        make_tour(item="hotel", with_detail=True)


def test_make_order_writes_paid_item(db, make_user, make_tour, make_order):
    user = make_user()
    tour = make_tour()
    ids = make_order(user, tour["tour_id"])
    row = db.execute(
        "SELECT oi.payment_status, o.user_id::text, oi.tour_id::text "
        "FROM order_item oi JOIN orders o ON o.order_id = oi.order_id WHERE oi.order_item_id = %s",
        (ids["order_item_id"],),
    ).fetchone()
    assert row[0] == 1
    assert row[1] == user["user_id"]
    assert row[2] == tour["tour_id"]


def test_purge_removes_only_test_data(db):
    from conftest import delete_user, purge_leftover_test_data

    test_email = f"e2e-purge{uuid.uuid4().hex[:8]}@example.com"
    keep_email = "keep." + uuid.uuid4().hex[:8] + "@example.com"
    tour = insert(db, "tour", title=f"p3-purge{uuid.uuid4().hex[:8]}")
    insert(db, "tour_detail", tour_id=tour["tour_id"])
    user = insert(db, "user", email=test_email)
    insert(db, "user_level", user_id=user["user_id"], level="Level 1", name="初心旅人",
           badge_url="https://example.com/b.png", travel_point=0)  # fmt: skip
    order = insert(db, "orders", user_id=user["user_id"], payment_status=1)
    insert(db, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"], payment_status=1)
    insert(db, "review", user_id=user["user_id"], tour_id=tour["tour_id"])
    gmail_email = f"e2e-{uuid.uuid4().hex[:8]}@gmail.com"
    upper_email = f"E2E-{uuid.uuid4().hex[:8]}@Example.com"
    other_tours = "SELECT count(*) FROM tour WHERE NOT starts_with(title, 'p3-')"
    other_before = db.execute(other_tours).fetchone()[0]
    try:
        insert(db, "user", email=keep_email)
        insert(db, "user", email=gmail_email)
        insert(db, "user", email=upper_email)
        result = purge_leftover_test_data(db)
        assert result["users"] >= 1 and result["tours"] >= 1
        assert db.execute('SELECT 1 FROM "user" WHERE email = %s', (test_email,)).fetchone() is None
        assert db.execute("SELECT 1 FROM tour WHERE tour_id = %s", (tour["tour_id"],)).fetchone() is None
        assert db.execute('SELECT 1 FROM "user" WHERE email = %s', (keep_email,)).fetchone() is not None
        assert other_before > 0
        assert db.execute(other_tours).fetchone()[0] == other_before
        assert db.execute('SELECT 1 FROM "user" WHERE email = %s', (gmail_email,)).fetchone() is not None
        assert db.execute('SELECT 1 FROM "user" WHERE email = %s', (upper_email,)).fetchone() is None
        for seed in ("alice", "bob", "carol"):
            assert db.execute('SELECT 1 FROM "user" WHERE email = %s', (f"{seed}@example.com",)).fetchone()
    finally:
        for email in (keep_email, gmail_email, upper_email):
            for row in db.execute('SELECT user_id FROM "user" WHERE email = %s', (email,)).fetchall():
                delete_user(db, str(row[0]))

def test_purge_prefixes_cover_fixture_emails():
    from conftest import TEST_EMAIL_PREFIXES

    pattern = re.compile(r"f\"([A-Za-z0-9._-]+?)\{[^}]+\}@[Ee]xample\.(?:com|COM)")
    found = set()
    for folder in ("tests", "e2e"):
        for path in (ROOT / folder).rglob("*.py"):
            found.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert found, "regex 沒掃到任何前綴"
    from test_oauth_spike import MOCK_EMAIL

    assert MOCK_EMAIL.lower().startswith(TEST_EMAIL_PREFIXES), MOCK_EMAIL
    for prefix in found:
        assert prefix.lower().startswith(TEST_EMAIL_PREFIXES), prefix


def test_requires_python_has_upper_bound():
    assert 'requires-python = ">=3.10,<3.14"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert re.search(r'requires-python = ">=3\.10, ?<3\.14"', lock)


def test_setup_uv_pins_uv_version():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r'uses: astral-sh/setup-uv@v10\.3\.3\s*\n\s*with:\s*\n\s*version: "0\.13\.9"', ci)


def test_runner_and_python_pinned():
    """既有行為的回歸測試。"""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "runs-on: ubuntu-24.04" in ci
    assert (ROOT / ".python-version").read_text().strip() == "3.13"


@pytest.mark.parametrize("item", ["travel", "restaurant", "hotel"])
def test_delete_tour_removes_all_child_rows(db, make_user, make_tour, item):
    """回歸測試：delete_tour 清乾淨每一張子表。"""
    from conftest import delete_tour

    user = make_user()
    t = make_tour(item=item, with_detail=item == "travel")
    tid = t["tour_id"]
    insert(db, "review", user_id=user["user_id"], tour_id=tid)
    insert(db, "hidden_play", user_id=user["user_id"], tour_id=tid)
    insert(db, "favorite", user_id=user["user_id"], tour_id=tid)
    cart = insert(db, "cart", user_id=user["user_id"])
    insert(db, "cart_item", cart_id=cart["cart_id"], tour_id=tid)
    insert(db, "notification", tour_id=tid)
    order = insert(db, "orders", user_id=user["user_id"], payment_status=1)
    insert(db, "order_item", order_id=order["order_id"], tour_id=tid, payment_status=1)
    tables = ["review", "hidden_play", "favorite", "cart_item", "notification", "order_item"]
    grandchildren: list[tuple[str, str, str]] = []  # (表, 父欄位, 父 id)
    if item == "travel":
        tables.append("tour_detail")
    if item == "restaurant":
        r = insert(db, "restaurant", tour_id=tid)
        insert(db, "restaurant_business", restaurant_id=r["restaurant_id"])
        insert(db, "restaurant_menu", restaurant_id=r["restaurant_id"])
        grandchildren += [("restaurant_business", "restaurant_id", str(r["restaurant_id"])),
                          ("restaurant_menu", "restaurant_id", str(r["restaurant_id"]))]  # fmt: skip
        tables.append("restaurant")
    if item == "hotel":
        h = insert(db, "hotel", tour_id=tid)
        insert(db, "hotel_room", hotel_id=h["hotel_id"])
        grandchildren.append(("hotel_room", "hotel_id", str(h["hotel_id"])))
        tables.append("hotel")
    for table in tables:
        assert db.execute(f"SELECT count(*) FROM {table} WHERE tour_id = %s", (tid,)).fetchone()[0] == 1, table
    for table, col, pid in grandchildren:
        assert db.execute(f"SELECT count(*) FROM {table} WHERE {col} = %s", (pid,)).fetchone()[0] == 1, table
    delete_tour(db, tid)
    for table, col, pid in grandchildren:
        assert db.execute(f"SELECT count(*) FROM {table} WHERE {col} = %s", (pid,)).fetchone()[0] == 0, table
    for table in tables:
        assert db.execute(f"SELECT count(*) FROM {table} WHERE tour_id = %s", (tid,)).fetchone()[0] == 0, table
    assert db.execute("SELECT 1 FROM tour WHERE tour_id = %s", (tid,)).fetchone() is None


def test_cleanup_all_continues_after_failure():
    """回歸測試：單筆刪除失敗時，其餘仍會被呼叫，最後拋出第一個錯誤。"""
    from conftest import _cleanup_all

    called = []
    boom = RuntimeError("boom-2")

    def delete(item):
        called.append(item)
        if item == 2:
            raise boom

    with pytest.raises(RuntimeError) as exc_info:
        _cleanup_all([1, 2, 3], delete)
    assert called == [1, 2, 3]
    assert exc_info.value is boom
