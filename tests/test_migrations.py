"""確認 Flyway 已套用 V1–V6 與 R__views_functions，並且 V1 的 25 張表都存在；V3、V4、V5、V6 的表格約束。"""
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


def test_flyway_applied_v1_to_v6(db):
    rows = db.execute(
        "SELECT version FROM flyway_schema_history "
        "WHERE version IS NOT NULL AND success"
    ).fetchall()
    assert {r[0] for r in rows} >= {"1", "2", "3", "4", "5", "6"}


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
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'review' AND indexname = 'review_user_tour_key'"
    ).fetchone()
    assert row is not None, "缺少 review_user_tour_key"
    assert "UNIQUE" in row[0]
    assert "(user_id, tour_id)" in row[0]
    assert "WHERE (tour_id IS NOT NULL)" in row[0]


def test_review_duplicate_user_tour_rejected(tx):
    user = insert(tx, "user")
    tour = insert(tx, "tour")
    insert(tx, "review", user_id=user["user_id"], tour_id=tour["tour_id"], type="travel", rating=5)
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        insert(tx, "review", user_id=user["user_id"], tour_id=tour["tour_id"], type="travel", rating=4)
    assert exc.value.diag.constraint_name == "review_user_tour_key"


def test_web_reviews_not_limited_by_unique_index(tx):
    """對照組：tour_id 為 NULL 的評論不受限；partial 條件由 indexdef 測試驗證。"""
    user = insert(tx, "user")
    insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=5)
    insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=4)
    count = tx.execute(
        "SELECT count(*) FROM review WHERE user_id = %s AND tour_id IS NULL", (user["user_id"],)
    ).fetchone()[0]
    assert count == 2


@pytest.mark.parametrize("rating, ok", [(0, False), (6, False), (1, True), (5, True)])
def test_review_rating_check(tx, rating, ok):
    user = insert(tx, "user")
    if ok:
        insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=rating)
    else:
        with pytest.raises(psycopg.errors.CheckViolation) as exc:
            insert(tx, "review", user_id=user["user_id"], tour_id=None, type="web", rating=rating)
        assert exc.value.diag.constraint_name == "review_rating_range"


def test_payment_merchant_order_no_column(db):
    row = db.execute(
        "SELECT data_type, character_maximum_length, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'payment' AND column_name = 'merchant_order_no'"
    ).fetchone()
    assert row == ("character varying", 30, "YES")


def _payment(tx, user, order, **cols):
    return insert(tx, "payment", user_id=user["user_id"], order_id=order["order_id"], **cols)


def test_payment_merchant_order_no_unique(tx):
    user = insert(tx, "user")
    order = insert(tx, "orders", user_id=user["user_id"], payment_status=0)
    _payment(tx, user, order, payment_status=0, merchant_order_no=None)  # 兩列 NULL 不報錯
    _payment(tx, user, order, payment_status=0, merchant_order_no=None)
    _payment(tx, user, order, payment_status=0, merchant_order_no="TE-UNIQ-1")
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        _payment(tx, user, order, payment_status=0, merchant_order_no="TE-UNIQ-1")
    assert exc.value.diag.constraint_name == "payment_merchant_order_no_key"


def test_payment_one_paid_per_order(tx):
    user = insert(tx, "user")
    order = insert(tx, "orders", user_id=user["user_id"], payment_status=1)
    _payment(tx, user, order, payment_status=0)  # 未付款可並存
    _payment(tx, user, order, payment_status=0)
    _payment(tx, user, order, payment_status=1)
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        _payment(tx, user, order, payment_status=1)
    assert exc.value.diag.constraint_name == "payment_order_paid_key"


def test_seed_payments_have_null_merchant_order_no(db):
    total, non_null = db.execute(
        "SELECT count(*), count(merchant_order_no) FROM payment"
    ).fetchone()
    assert total == 15
    assert non_null == 0


# ---- V6（P5 spec §3）：收藏、購物車、通知設定各一個唯一約束 ----

def _constraint_exists(db, table, name):
    return db.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = %s AND contype = 'u' AND conrelid = %s::regclass",
        (name, f'public."{table}"'),
    ).fetchone() is not None


def test_favorite_user_tour_unique(tx):
    user = insert(tx, "user")
    tour = insert(tx, "tour")
    insert(tx, "favorite", user_id=user["user_id"], tour_id=tour["tour_id"])
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        insert(tx, "favorite", user_id=user["user_id"], tour_id=tour["tour_id"])
    assert exc.value.diag.constraint_name == "favorite_user_tour_key"
    tx.rollback()
    assert _constraint_exists(tx, "favorite", "favorite_user_tour_key")


def test_cart_user_unique(tx):
    user = insert(tx, "user")
    insert(tx, "cart", user_id=user["user_id"])
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        insert(tx, "cart", user_id=user["user_id"])
    assert exc.value.diag.constraint_name == "cart_user_id_key"
    tx.rollback()
    assert _constraint_exists(tx, "cart", "cart_user_id_key")


def test_auto_setting_user_unique(tx):
    user = insert(tx, "user")
    insert(tx, "auto_setting", user_id=user["user_id"])
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        insert(tx, "auto_setting", user_id=user["user_id"])
    assert exc.value.diag.constraint_name == "auto_setting_user_id_key"
    tx.rollback()
    assert _constraint_exists(tx, "auto_setting", "auto_setting_user_id_key")
