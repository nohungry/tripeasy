"""P4 Task 10：購物車、優惠、結帳驗證訊息改用中文標籤（spec §10），以及購物車列表預設分頁。"""
import uuid

import pytest
from conftest import CART_API, CHECKOUT_API, DISCOUNT_API, add_to_cart, auth_header

LIST_URL = f"{CART_API}/list"
FUTURE = {"start_date": "2099-01-01", "end_date": "2099-01-02"}
RAW_NAMES = (
    "tour_id", "cart_item_id", "order_id", "page", "limit", "lang", "type", "item", "options",
    "coupon", "point", "discount", "start_date", "end_date",
)


def _no_raw_names(message):
    for name in RAW_NAMES:
        assert name not in message, (name, message)


def _post_cart(api, user, tour_id, body):
    return api.post(f"{CART_API}/{tour_id}", json=body, headers=auth_header(user), timeout=5)


def _valid_body(**over):
    body = {"type": "tourgroup", "item": "travel", "people": 1, "options": FUTURE}
    body.update(over)
    return body


# ---- cart ----

def test_cart_post_invalid_tour_id_message(api, make_user):
    r = _post_cart(api, make_user(), "not-a-uuid", _valid_body())
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「旅遊項目編號」必須是有效的 UUID 格式"
    _no_raw_names(r.json()["message"])


def test_cart_delete_invalid_item_id_message(api, make_user):
    r = api.delete(f"{CART_API}/not-a-uuid", headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「購物車項目編號」必須是有效的 UUID 格式"


def test_cart_patch_invalid_item_id_message(api, make_user):
    r = api.patch(f"{CART_API}/not-a-uuid", json=_valid_body(), headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「購物車項目編號」必須是有效的 UUID 格式"


@pytest.mark.parametrize(
    "query, expected",
    [
        ({"page": 0}, "「頁數」至少是 1"),
        ({"page": "x"}, "「頁數」必須是數字"),
        ({"page": 1.5}, "「頁數」必須是整數"),
        ({"limit": 0}, "「每頁筆數」至少是 1"),
        ({"limit": "x"}, "「每頁筆數」必須是數字"),
        ({"lang": "fr-FR"}, "「語言」僅支援：zh-TW, en-US"),
    ],
    ids=lambda v: str(v),
)
def test_cart_list_query_messages(api, make_user, query, expected):
    r = api.get(LIST_URL, params=query, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    _no_raw_names(expected)


def test_cart_list_without_paging_uses_defaults(api, make_user, make_tour):
    user = make_user()
    assert add_to_cart(api, user, make_tour()).status_code == 201
    r = api.get(LIST_URL, headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    data = r.json().get("data")
    assert data is not None, r.text
    assert len(data["data"]) == 1


def test_cart_list_empty_without_paging_is_200(api, make_user):
    r = api.get(LIST_URL, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 200, r.text


def test_cart_post_combo_message(api, make_user, make_tour):
    r = _post_cart(api, make_user(), make_tour()["tour_id"], _valid_body(type="backpacker", item="travel"))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「大分類」與「小分類」的組合不合法"


def test_cart_post_type_item_mismatch_with_tour_message(api, make_user, make_tour):
    tour = make_tour()
    other = {"tourgroup": ("backpacker", "spot"), "backpacker": ("tourgroup", "travel")}[tour["type"]]
    body = _valid_body(type=other[0], item=other[1])
    r = _post_cart(api, make_user(), tour["tour_id"], body)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「大分類」與「小分類」的組合不合法"


def test_cart_post_options_missing_message(api, make_user, make_tour):
    body = _valid_body()
    del body["options"]
    r = _post_cart(api, make_user(), make_tour()["tour_id"], body)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "請提供「選項」設定"


def test_cart_post_options_null_message(api, make_user, make_tour):
    r = _post_cart(api, make_user(), make_tour()["tour_id"], _valid_body(options=None))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「選項」不可為 null"


# ---- discounts ----

@pytest.mark.parametrize(
    "body, expected",
    [
        ({"discount": {"coupon": "ABC123"}}, "請填寫「優惠方式」"),
        ({"type": "zzz", "discount": {"coupon": "ABC123"}}, "「優惠方式」只能是優惠券或旅遊積分"),
        ({"type": "coupon"}, "「優惠內容」為必填欄位"),
        ({"type": "coupon", "discount": {"coupon": "abc"}}, "「優惠券代碼」必須是 6 碼大寫英數組合"),
        ({"type": "point", "discount": {"point": "x"}}, "「旅遊積分」必須是數字"),
        ({"type": "point", "discount": {"point": 1.5}}, "「旅遊積分」必須是整數"),
        ({"type": "point", "discount": {"point": -5}}, "「旅遊積分」最小值為 0"),
        ({"type": "coupon", "discount": {"coupon": "ABC123", "point": 5}}, "「優惠券代碼」與「旅遊積分」只能擇一填寫"),
        ({"type": "coupon", "discount": {}}, "「優惠券代碼」與「旅遊積分」必須擇一填寫"),
    ],
    ids=lambda v: str(v),
)
def test_discount_body_messages(api, make_user, body, expected):
    r = api.post(f"{DISCOUNT_API}/{uuid.uuid4()}", json=body, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    for name in ("order_id", "discount", "type"):
        assert name not in expected


def test_discount_invalid_order_id_message(api, make_user):
    body = {"type": "coupon", "discount": {"coupon": "ABC123"}}
    r = api.post(f"{DISCOUNT_API}/not-a-uuid", json=body, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「訂單編號」必須是有效的 UUID 格式"
    r = api.get(f"{DISCOUNT_API}/not-a-uuid", headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「訂單編號」必須是有效的 UUID 格式"


# ---- checkout ----

def test_checkout_invalid_order_id_message(api, make_user):
    user = make_user()
    for url in (f"{CHECKOUT_API}/userinfo/not-a-uuid", f"{CHECKOUT_API}/summary/not-a-uuid"):
        r = api.get(url, headers=auth_header(user), timeout=5)
        assert r.status_code == 400, (url, r.text)
        assert r.json()["message"] == "「訂單編號」必須是有效的 UUID 格式", url
        assert "order_id" not in r.json()["message"]
