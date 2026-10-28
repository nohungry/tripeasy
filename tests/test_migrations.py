"""確認 Flyway 已套用 V1、V2，並且 V1 的 25 張表都存在。"""

EXPECTED_TABLES = {
    "user", "socialLogin", "user_level", "coupon", "user_coupon", "point_record",
    "tour", "tour_detail", "restaurant", "restaurant_business", "restaurant_menu",
    "hotel", "hotel_room", "notification", "country", "region",
    "cart", "cart_item", "orders", "order_item", "payment",
    "review", "hidden_play", "auto_setting", "favorite",
}


def test_flyway_applied_v1_and_v2(db):
    rows = db.execute(
        "SELECT version, success FROM flyway_schema_history "
        "WHERE version IS NOT NULL ORDER BY installed_rank"
    ).fetchall()
    assert rows == [("1", True), ("2", True)]


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
