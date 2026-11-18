"""確認 Flyway 已套用 V1、V2、V3 與 R__views_functions，並且 V1 的 25 張表都存在；V3 的表格約束。"""
import psycopg
import pytest

EXPECTED_TABLES = {
    "user", "socialLogin", "user_level", "coupon", "user_coupon", "point_record",
    "tour", "tour_detail", "restaurant", "restaurant_business", "restaurant_menu",
    "hotel", "hotel_room", "notification", "country", "region",
    "cart", "cart_item", "orders", "order_item", "payment",
    "review", "hidden_play", "auto_setting", "favorite",
}


def test_flyway_applied_v1_to_v3(db):
    rows = db.execute(
        "SELECT version, success FROM flyway_schema_history "
        "WHERE version IS NOT NULL ORDER BY installed_rank"
    ).fetchall()
    assert rows == [("1", True), ("2", True), ("3", True)]


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
