"""P5 Task 7：收藏後端（POST／DELETE／GET /user/collection/info）與商品 API 回傳 favorite_id。"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import API_BASE, Api, auth_header

FAV = "/api/v1/user/collection/info"
LIST = f"{FAV}/all"
PRODUCT = "/api/v1/user/product/search"

TOUR_UUID_MSG = "「行程編號」必須是有效的 UUID 格式"
FAV_UUID_MSG = "「收藏編號」必須是有效的 UUID 格式"
NO_TOUR_MSG = "查無此旅遊項目"
NO_FAV_MSG = "查無此收藏項目"
BAD_UUID = "not-a-uuid"
UNKNOWN_UUID = "7b0e5b2e-3c1f-4c59-9d0a-0d3f5f1f2a11"


def favorite(api, user, tour_id):
    return api.post(f"{FAV}/{tour_id}", headers=auth_header(user), json={})


def fav_rows(db, user, tour_id=None):
    sql = "SELECT favorite_id FROM favorite WHERE user_id = %s"
    params = [user["user_id"]]
    if tour_id:
        sql += " AND tour_id = %s"
        params.append(tour_id)
    return db.execute(sql, params).fetchall()


def test_favorite_first_time_is_201(api, db, make_user, make_tour):
    user, tour = make_user(), make_tour()
    r = favorite(api, user, tour["tour_id"])
    assert r.status_code == 201, r.text
    assert r.json()["message"] == "收藏成功"
    fid = r.json()["data"]["favorite_id"]
    assert [str(row[0]) for row in fav_rows(db, user, tour["tour_id"])] == [fid]


def test_favorite_duplicate_returns_original_id(api, db, make_user, make_tour):
    user, tour = make_user(), make_tour()
    first = favorite(api, user, tour["tour_id"])
    second = favorite(api, user, tour["tour_id"])
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["message"] == "已收藏過此行程"
    assert second.json()["data"]["favorite_id"] == first.json()["data"]["favorite_id"]
    assert len(fav_rows(db, user, tour["tour_id"])) == 1


def test_concurrent_favorite_same_tour_returns_same_id(db, make_user, make_tour):
    """Review Focus 3。8 條執行緒、各自 session、Barrier 帶 timeout；
    舊寫法（先查再 INSERT）會讓輸的請求撞 UNIQUE 回 500。"""
    user, tour = make_user(), make_tour()
    n = 8
    barrier = threading.Barrier(n, timeout=10)
    headers = auth_header(user)

    def hit(_):
        session = Api(API_BASE)
        try:
            barrier.wait()
            return session.post(f"{FAV}/{tour['tour_id']}", headers=headers, json={})
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(hit, range(n)))
    codes = [r.status_code for r in results]
    assert set(codes) <= {200, 201}, [(r.status_code, r.text) for r in results]
    assert codes.count(201) == 1, codes
    assert len({r.json()["data"]["favorite_id"] for r in results}) == 1
    assert len(fav_rows(db, user, tour["tour_id"])) == 1


def test_favorite_unlisted_tour_is_404(api, db, make_user, make_tour):
    user, tour = make_user(), make_tour(status=2)
    r = favorite(api, user, tour["tour_id"])
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NO_TOUR_MSG
    assert fav_rows(db, user) == []


def test_favorite_unknown_tour_is_404(api, make_user):
    r = favorite(api, make_user(), UNKNOWN_UUID)
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NO_TOUR_MSG


def test_favorite_bad_uuid_is_400(api, make_user):
    r = favorite(api, make_user(), BAD_UUID)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == TOUR_UUID_MSG


def test_collection_bad_uuid_is_400(api, make_user):
    """原 test_async_errors 的案例（收藏 POST 非 UUID 曾回 500）；從 try 外 reject 的 500 改為驗證 400。"""
    r = api.post(f"{FAV}/{BAD_UUID}", headers=auth_header(make_user()), json={}, timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == TOUR_UUID_MSG
    assert api.get("/api/v1/health").status_code == 200


def test_delete_other_users_favorite_is_404(api, db, make_user, make_tour):
    owner, other, tour = make_user(), make_user(), make_tour()
    fid = favorite(api, owner, tour["tour_id"]).json()["data"]["favorite_id"]
    r = api.delete(f"{FAV}/{fid}", headers=auth_header(other))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NO_FAV_MSG
    assert [str(row[0]) for row in fav_rows(db, owner)] == [fid]


def test_delete_own_favorite(api, db, make_user, make_tour):
    user, tour = make_user(), make_tour()
    fid = favorite(api, user, tour["tour_id"]).json()["data"]["favorite_id"]
    r = api.delete(f"{FAV}/{fid}", headers=auth_header(user))
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "刪除成功"
    assert fav_rows(db, user) == []


def test_delete_bad_uuid_is_400(api, make_user):
    r = api.delete(f"{FAV}/{BAD_UUID}", headers=auth_header(make_user()))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == FAV_UUID_MSG


def test_delete_unknown_favorite_is_404(api, make_user):
    r = api.delete(f"{FAV}/{UNKNOWN_UUID}", headers=auth_header(make_user()))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NO_FAV_MSG


def test_list_capped_at_100_newest_first(api, db, make_user, make_tour):
    user = make_user()
    tours = [make_tour(with_detail=False) for _ in range(101)]
    for i, tour in enumerate(tours):  # created_at 遞增：tours[0] 最舊、tours[100] 最新
        db.execute(
            "INSERT INTO favorite (user_id, tour_id, created_at) VALUES (%s, %s, now() - interval '1 day' + %s * interval '1 second')",
            (user["user_id"], tour["tour_id"], i),
        )
    r = api.get(LIST, headers=auth_header(user), params={"lang": "zh-TW"})
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert len(body["data"]) == 100
    assert body["total"] == 101
    ids = [row["旅遊編號"] for row in body["data"]]
    assert ids[0] == tours[100]["tour_id"]
    assert tours[0]["tour_id"] not in ids


def test_refavorite_after_delete_gets_new_id_and_old_id_404(api, db, make_user, make_tour):
    """Review Focus 5。"""
    user, tour = make_user(), make_tour()
    old = favorite(api, user, tour["tour_id"]).json()["data"]["favorite_id"]
    assert api.delete(f"{FAV}/{old}", headers=auth_header(user)).status_code == 200
    again = favorite(api, user, tour["tour_id"])
    assert again.status_code == 201, again.text
    new = again.json()["data"]["favorite_id"]
    assert new != old
    stale = api.delete(f"{FAV}/{old}", headers=auth_header(user))
    assert stale.status_code == 404, stale.text
    assert [str(row[0]) for row in fav_rows(db, user, tour["tour_id"])] == [new]


@pytest.mark.parametrize("method", ["post", "delete", "get"])
def test_favorite_admin_is_403(api, make_user, method):
    admin = make_user(role="admin")
    url = {"post": f"{FAV}/{UNKNOWN_UUID}", "delete": f"{FAV}/{UNKNOWN_UUID}", "get": LIST}[method]
    r = api.request(method, url, headers=auth_header(admin))
    assert r.status_code == 403, r.text
    assert r.json()["message"] == "您沒有權限進行此操作"


@pytest.mark.parametrize("method", ["post", "delete", "get"])
def test_favorite_without_token_is_401(api, method):
    url = {"post": f"{FAV}/{UNKNOWN_UUID}", "delete": f"{FAV}/{UNKNOWN_UUID}", "get": LIST}[method]
    r = api.request(method, url)
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "請先登入"


def test_list_single_response_and_unlisted_flag(api, db, make_user, make_tour):
    user, listed, hidden = make_user(), make_tour(), make_tour()
    for tour in (listed, hidden):
        assert favorite(api, user, tour["tour_id"]).status_code == 201
    db.execute("UPDATE tour SET status = 2 WHERE tour_id = %s", (hidden["tour_id"],))
    r = api.get(LIST, headers=auth_header(user), params={"lang": "zh-TW"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "查詢成功"
    assert body["data"]["total"] == 2
    by_tour = {row["旅遊編號"]: row for row in body["data"]["data"]}
    assert set(by_tour) == {listed["tour_id"], hidden["tour_id"]}
    assert by_tour[hidden["tour_id"]]["上下架狀態"] == 2
    assert by_tour[listed["tour_id"]]["上下架狀態"] == 1
    assert "偏好分類" in by_tour[listed["tour_id"]] and "favorite_id" in by_tour[listed["tour_id"]]


def test_list_empty(api, make_user):
    r = api.get(LIST, headers=auth_header(make_user()))
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "查無資料"
    assert r.json()["data"] == {"data": [], "total": 0}


def test_detail_returns_favorite_id(api, make_user, make_tour):
    user, tour = make_user(), make_tour()
    url = f"{PRODUCT}/{tour['tour_id']}"
    before = api.get(url, headers=auth_header(user), params={"lang": "zh-TW"}).json()["data"]
    assert before["is_favorited"] is False and before["favorite_id"] is None
    fid = favorite(api, user, tour["tour_id"]).json()["data"]["favorite_id"]
    after = api.get(url, headers=auth_header(user), params={"lang": "zh-TW"}).json()["data"]
    assert after["is_favorited"] is True
    assert after["favorite_id"] == fid
    guest = api.get(url, params={"lang": "zh-TW"}).json()["data"]
    assert guest["favorite_id"] is None


def test_search_returns_favorite_id(api, make_user, make_tour):
    user, tour = make_user(), make_tour()
    fid = favorite(api, user, tour["tour_id"]).json()["data"]["favorite_id"]
    params = {"page": 1, "limit": 20, "sort_by": "date", "order": "asc", "lang": "zh-TW", "keyword": tour["title"]}
    r = api.get(PRODUCT, headers=auth_header(user), params=params)
    assert r.status_code == 200, r.text
    rows = {row["旅遊編號"]: row for row in r.json()["data"]}
    assert rows[tour["tour_id"]]["收藏編號"] == fid
