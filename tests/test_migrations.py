"""確認 Flyway 已套用 V1–V4 與 R__views_functions，並且 V1 的 25 張表都存在；V3、V4 的表格約束。"""
import psycopg
import pytest

from dbfactory import insert

EXPECTED_TABLES = {
    "user", "socialLogin", "user_level", "coupon", "user_coupon", "point_record",
    "tour", "tour_detail", "restaurant", "restaurant_business", "restaurant_menu",
    "hotel", "hotel_room", "notification", "country", "region",
    "cart", "cart_item", "orders", "order_item", "payment",
    "review", "hidden_play", "auto_setting", "favorite",
}


def test_flyway_applied_v1_to_v4(db):
    rows = db.execute(
        "SELECT version, success FROM flyway_schema_history "
        "WHERE version IS NOT NULL ORDER BY installed_rank"
    ).fetchall()
    assert rows == [("1", True), ("2", True), ("3", True), ("4", True)]


def test_all_v1_tables_exist(db):
    names = {
        r[0]
        for r in db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    }
    missing = EXPECTED_TABLES - names
    assert not missing, f"缺少資料表：{sorted(missing)}"


def test_flyway_applied_views_functions(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history "
        "WHERE script = 'R__views_functions.sql' ORDER BY installed_rank DESC LIMIT 1"
    ).fetchone()
    assert row == (True,)


def test_v3_applied(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history WHERE version = '3'"
    ).fetchone()
    assert row == (True,)


def test_user_password_is_nullable(db):
    row = db.execute(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'user' AND column_name = 'password'"
    ).fetchone()
    assert row == ("YES",)


def test_user_email_lower_unique_index(db):
    row = db.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'user_email_lower_key'"
    ).fetchone()
    assert row is not None, "缺少 user_email_lower_key"
    assert "UNIQUE" in row[0]
    assert "lower((email)::text)" in row[0]


def test_email_case_duplicate_rejected(tx):
    sql = (
        'INSERT INTO "user" (name, email, role, password, preference1, preference2, preference3) '
        "VALUES ('P2 測試', %s, 'User', NULL, 1, 2, 3)"
    )
    tx.execute(sql, ("Case@Example.com",))
    with pytest.raises(psycopg.errors.UniqueViolation):
        tx.execute(sql, ("case@example.com",))


def test_v4_applied(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history WHERE version = '4'"
    ).fetchone()
    assert row == (True,)


def test_review_user_tour_unique_index(db):
    row = db.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'review_user_tour_key'"
    ).fetchone()
    assert row is not None, "缺少 review_user_tour_key"
    assert "UNIQUE" in row[0]
    assert "(user_id, tour_id)" in row[0]
    assert "WHERE (tour_id IS NOT NULL)" in row[0]


def test_review_duplicate_user_tour_rejected(tx):
    user = insert(tx, "user")
    tour = insert(tx, "tour")
    insert(tx, "review", user_id=user["user_id"], tour_id=tour["tour_id"], type="travel", rating=5)
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert(tx, "review", user_id=user["user_id"], tour_id=tour["tour_id"], type="travel", rating=4)


def test_web_reviews_not_limited_by_unique_index(tx):
    user = insert(tx, "user")
    insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=5)
    insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=4)


@pytest.mark.parametrize("rating, ok", [(0, False), (6, False), (1, True), (5, True)])
def test_review_rating_check(tx, rating, ok):
    user = insert(tx, "user")
    if ok:
        insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=rating)
    else:
        with pytest.raises(psycopg.errors.CheckViolation):
            insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=rating)
