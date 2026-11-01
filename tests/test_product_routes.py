"""spec 3.0：product router 同時掛在 user 和 admin 兩個前綴，造成兩個路由順序 bug。

- admin 的 GET / 和 GET /:tour_id 宣告在公開版前面 → 訪客查商品拿到 401
- PATCH /:tour_id 宣告在 PATCH /status 前面 → 上架 API 永遠走不到
"""
import uuid

from conftest import auth_header

PUBLIC = "/api/v1/user/product/search"
ADMIN = "/api/v1/admin/product"
NOT_FOUND_ROUTE = "找不到此網站"  # server.js 的 404 handler


def test_guest_can_reach_public_tour_detail(api):
    # detailsSchema 規定 lang 必填
    r = api.get(f"{PUBLIC}/{uuid.uuid4()}", params={"lang": "zh-TW"})
    # 走到公開版的 middleware：查無此行程，而不是被 admin 的 auth 擋成 401
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_guest_tour_list_is_not_blocked_by_admin_auth(api):
    # queryschema 規定 page／limit／sort_by／order／lang 必填，不帶會是 400（跟 admin auth 無關）
    r = api.get(PUBLIC, params={"page": 1, "limit": 10, "sort_by": "date", "order": "asc", "lang": "zh-TW"})
    assert r.status_code == 200, r.text


def test_admin_status_route_is_reachable(api, make_user):
    admin = make_user(role="admin")
    r = api.patch(
        f"{ADMIN}/status",
        headers=auth_header(admin),
        json={"tour_ids": [str(uuid.uuid4())], "tour_status": "1"},
    )
    # 走到 patch_tourStatus：tour_ids 都不存在 → 404，而不是被 /:tour_id 當成 tour_id='status'
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此項目"


def test_admin_detail_still_requires_admin(api, make_user):
    user = make_user(role="User")
    assert api.get(f"{ADMIN}/{uuid.uuid4()}").status_code == 401
    assert api.get(f"{ADMIN}/{uuid.uuid4()}", headers=auth_header(user)).status_code == 403


def test_admin_routes_not_exposed_under_user_prefix(api, make_user):
    admin = make_user(role="admin")
    r = api.post(f"{PUBLIC}/add", headers=auth_header(admin))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NOT_FOUND_ROUTE


def test_public_routes_not_exposed_under_admin_prefix(api):
    r = api.get(f"{ADMIN}/{uuid.uuid4()}/reviews")
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NOT_FOUND_ROUTE


def test_admin_patch_tour_is_reachable(api, db, make_user):
    # 走到 PATCH /:tour_id（而不是被 /status 或 404 吃掉）。送一個驗證器必定拒絕的 body：
    # tour_product 存在、travel.features 型別錯誤 → middleware 回 400，不會進 controller，也就不會改資料。
    admin = make_user(role="admin")
    tour_id, updated_at = db.execute(
        "SELECT t.tour_id, t.updated_at FROM tour t JOIN tour_detail d USING (tour_id) "
        "WHERE t.status = 1 ORDER BY t.title LIMIT 1"
    ).fetchone()
    r = api.patch(
        f"{ADMIN}/{tour_id}",
        headers=auth_header(admin),
        json={"tour_product": {}, "travel": {"features": "not-an-array"}},
    )
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "欄位未填寫正確"
    after = db.execute("SELECT updated_at FROM tour WHERE tour_id = %s", (tour_id,)).fetchone()[0]
    assert after == updated_at  # 沒有改到 seed
