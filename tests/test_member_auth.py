"""P2 會員：權限與資料清理。後續 Task 的會員測試加在這裡。"""
from conftest import auth_header, delete_user
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


# 直接參照 "user" 的表（V1 全部）；orders / cart 底下的 order_item、payment、cart_item 另外塞
USER_FK_TABLES = [
    '"socialLogin"', "user_level", "cart", "orders", "payment", "review",
    "hidden_play", "auto_setting", "favorite", "point_record", "user_coupon",
]  # fmt: skip


def test_delete_user_clears_all_fk_tables(db, make_user):
    user = make_user()
    uid = user["user_id"]
    tour = insert(db, "tour")
    coupon = insert(db, "coupon")
    try:
        insert(db, "socialLogin", user_id=uid)
        insert(db, "user_level", user_id=uid)
        cart = insert(db, "cart", user_id=uid)
        insert(db, "cart_item", cart_id=cart["cart_id"], tour_id=tour["tour_id"])
        insert(db, "favorite", user_id=uid, tour_id=tour["tour_id"])
        order = insert(db, "orders", user_id=uid)
        insert(db, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"])
        insert(db, "payment", user_id=uid, order_id=order["order_id"])
        insert(db, "point_record", user_id=uid)
        insert(db, "point_record", user_id=uid, order_id=order["order_id"])
        insert(db, "user_coupon", user_id=uid, coupon_id=coupon["coupon_id"], order_id=order["order_id"])
        insert(db, "review", user_id=uid, tour_id=tour["tour_id"])
        insert(db, "hidden_play", user_id=uid, tour_id=tour["tour_id"])
        insert(db, "auto_setting", user_id=uid)

        delete_user(db, uid)  # 不得丟 FK 錯誤

        for table in USER_FK_TABLES:
            (n,) = db.execute(f"SELECT count(*) FROM {table} WHERE user_id = %s", (uid,)).fetchone()
            assert n == 0, table
        (n,) = db.execute('SELECT count(*) FROM "user" WHERE user_id = %s', (uid,)).fetchone()
        assert n == 0
    finally:
        delete_user(db, uid)
        db.execute("DELETE FROM coupon WHERE coupon_id = %s", (coupon["coupon_id"],))
        db.execute("DELETE FROM tour WHERE tour_id = %s", (tour["tour_id"],))
