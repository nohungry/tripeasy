"""P2 會員：權限與資料清理。後續 Task 的會員測試加在這裡。"""
from conftest import USER_FK_TABLES, auth_header, delete_user
from dbfactory import insert

ROLES = "/api/v1/admin/members/roles"


def _role_of(db, user_id: str) -> str:
    return db.execute('SELECT role FROM "user" WHERE user_id = %s', (user_id,)).fetchone()[0]


def test_change_role_requires_admin(api, db, make_user):
    a = make_user()
    b = make_user()
    r = api.patch(ROLES, headers=auth_header(a), json={"user_ids": [b["user_id"]], "role": "admin"})
    assert r.status_code == 403, r.text
    assert _role_of(db, b["user_id"]) == "User"


def test_change_role_by_admin(api, db, make_user):
    admin = make_user(role="admin")
    b = make_user()
    r = api.patch(ROLES, headers=auth_header(admin), json={"user_ids": [b["user_id"]], "role": "admin"})
    assert r.status_code == 200, r.text
    assert _role_of(db, b["user_id"]) == "admin"


def test_user_fk_tables_list_is_complete(db):
    """Task 2 之後若有 migration 新增參照 "user" 的表，這裡會抓到 delete_user 漏掉的表。"""
    rows = db.execute(
        "SELECT DISTINCT conrelid::regclass::text FROM pg_constraint "
        "WHERE contype = 'f' AND confrelid = '\"user\"'::regclass"
    ).fetchall()
    actual = {r[0].strip('"') for r in rows}
    assert actual == {t.strip('"') for t in USER_FK_TABLES}


def test_delete_user_clears_all_fk_tables(make_user, tx):
    # 參數順序：tx 要先於 make_user 結束（rollback），make_user teardown 刪 user 才不會卡 row lock。
    # 所有 insert 都在 tx 內，失敗也由 rollback 保證不留資料。
    user = make_user()
    uid = user["user_id"]
    tour = insert(tx, "tour")
    coupon = insert(tx, "coupon")
    insert(tx, "socialLogin", user_id=uid)
    insert(tx, "user_level", user_id=uid)
    cart = insert(tx, "cart", user_id=uid)
    insert(tx, "cart_item", cart_id=cart["cart_id"], tour_id=tour["tour_id"])
    insert(tx, "favorite", user_id=uid, tour_id=tour["tour_id"])
    order = insert(tx, "orders", user_id=uid)
    insert(tx, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"])
    insert(tx, "payment", user_id=uid, order_id=order["order_id"])
    insert(tx, "point_record", user_id=uid)
    insert(tx, "point_record", user_id=uid, order_id=order["order_id"])
    insert(tx, "user_coupon", user_id=uid, coupon_id=coupon["coupon_id"], order_id=order["order_id"])
    insert(tx, "review", user_id=uid, tour_id=tour["tour_id"])
    insert(tx, "hidden_play", user_id=uid, tour_id=tour["tour_id"])
    insert(tx, "auto_setting", user_id=uid)

    delete_user(tx, uid)  # 不得丟 FK 錯誤

    for table in USER_FK_TABLES:
        (n,) = tx.execute(f"SELECT count(*) FROM {table} WHERE user_id = %s", (uid,)).fetchone()
        assert n == 0, table
    (n,) = tx.execute('SELECT count(*) FROM "user" WHERE user_id = %s', (uid,)).fetchone()
    assert n == 0
