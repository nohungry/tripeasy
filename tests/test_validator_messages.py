"""P4 Task 10：購物車、優惠、結帳驗證訊息改用中文標籤（spec §10），以及購物車列表預設分頁。"""
import uuid

import pytest
from conftest import CART_API, CHECKOUT_API, DISCOUNT_API, add_to_cart, auth_header

LIST_URL = f"{CART_API}/list"
FUTURE = {"start_date": "2099-01-01", "end_date": "2099-01-02"}
RAW_NAMES = (
    "people", "room_type", "cart_id", "keyword", "used_point", "installment", "min_price", "max_price", "duration", "sort_by", "tour_id", "cart_item_id", "order_id", "page", "limit", "lang", "type", "item", "options",
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
        ({"page": "1e30"}, "「頁數」數值超出範圍"),
        ({"limit": "1e30"}, "「每頁筆數」數值超出範圍"),
        ({"foo": "1"}, "請求參數含有不支援的欄位"),
        ({"lang": "fr-FR"}, "「語言」僅支援：zh-TW, en-US"),
    ],
    ids=lambda v: str(v),
)
def test_cart_list_query_messages(api, make_user, query, expected):
    r = api.get(LIST_URL, params=query, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    _no_raw_names(r.json()["message"])


def test_cart_list_without_paging_uses_defaults(api, make_user, make_tour):
    user = make_user()
    for _ in range(5):
        assert add_to_cart(api, user, make_tour()).status_code == 201
    r = api.get(LIST_URL, headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    body = r.json().get("data")
    assert body is not None, r.text
    assert len(body["data"]) == 4  # 預設每頁 4 筆
    assert body["summary"]["total_items"] == 5
    r2 = api.get(LIST_URL, params={"page": 2}, headers=auth_header(user), timeout=5)
    assert r2.status_code == 200, r2.text
    assert len(r2.json()["data"]["data"]) == 1


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


# ---- cart / discounts 的 Joi 內建訊息 ----

def _bad_body(**over):
    body = _valid_body()
    for k, v in over.items():
        if v is _DEL:
            del body[k]
        else:
            body[k] = v
    return body


_DEL = object()

CART_BODY_CASES = [
    (_bad_body(type=_DEL), "請填寫「大分類」"),
    (_bad_body(type="zzz"), "「大分類」僅能為 backpacker 或 tourgroup"),
    (_bad_body(type=5), "「大分類」僅能為 backpacker 或 tourgroup"),
    (_bad_body(item=_DEL), "請填寫「小分類」"),
    (_bad_body(item="zzz"), "「小分類」僅能為 hotel、food、spot 或 travel"),
    (_bad_body(people=_DEL), "請填寫「人數」"),
    (_bad_body(people=1.5), "「人數」必須是整數"),
    (_bad_body(people="x"), "「人數」必須是數字"),
    (_bad_body(people=0), "「人數」至少為 1 人"),
    (_bad_body(people=1e30), "「人數」數值超出範圍"),
    (_bad_body(people="9007199254740993"), "「人數」數值超出範圍"),
    (_bad_body(options="x"), "「選項」必須是物件"),
    (_bad_body(options={**FUTURE, "foo": 1}), "「選項」含有不支援的欄位"),
    (_bad_body(foo=1), "請求內容含有不支援的欄位"),
    (_bad_body(item="hotel", options={**FUTURE, "room_type": ""}), "「房型」不可為空"),
    (_bad_body(item="hotel", options={**FUTURE, "room_type": 5}), "「房型」必須是文字"),
]


@pytest.mark.parametrize("body, expected", CART_BODY_CASES, ids=lambda v: str(v))
def test_cart_post_body_messages(api, make_user, body, expected):
    r = _post_cart(api, make_user(), str(uuid.uuid4()), body)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    _no_raw_names(r.json()["message"])


@pytest.mark.parametrize("body, expected", CART_BODY_CASES, ids=lambda v: str(v))
def test_cart_patch_body_messages(api, make_user, body, expected):
    r = api.patch(f"{CART_API}/{uuid.uuid4()}", json=body, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    _no_raw_names(r.json()["message"])


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
        ({"type": "point", "discount": {"point": 1e30}}, "「旅遊積分」數值超出範圍"),
        ({"type": "coupon", "discount": "x"}, "「優惠內容」必須是物件"),
        ({"type": "coupon", "discount": {"coupon": ""}}, "「優惠券代碼」不可為空"),
        ({"type": "coupon", "discount": {"coupon": 123456}}, "「優惠券代碼」必須是文字"),
        ({"type": "coupon", "discount": {"coupon": "ABC123", "foo": 1}}, "「優惠內容」含有不支援的欄位"),
        ({"type": 5, "discount": {"coupon": "ABC123"}}, "「優惠方式」只能是優惠券或旅遊積分"),
        ({"type": "coupon", "discount": {"coupon": "ABC123"}, "foo": 1}, "請求內容含有不支援的欄位"),
    ],
    ids=lambda v: str(v),
)
def test_discount_body_messages(api, make_user, body, expected):
    r = api.post(f"{DISCOUNT_API}/{uuid.uuid4()}", json=body, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    _no_raw_names(r.json()["message"])


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


def test_checkout_invalid_cart_id_message(api, make_user):
    r = api.post(f"{CHECKOUT_API}/order/not-a-uuid", headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「購物車編號」必須是有效的 UUID 格式"
    assert "cart_id" not in r.json()["message"]


PREVIEW_USER = {"name": "王小明", "email": "a@b.co", "address": "台北市", "phone_number": "0912345678"}


def _preview_body(**over):
    body = {"user": dict(PREVIEW_USER), "payment_method": "atm"}
    body.update(over)
    return body


def _with_user(**over):
    return _preview_body(user={**PREVIEW_USER, **over})


CHECKOUT_BODY_CASES = [
    (_preview_body(discount={"type": "point", "used_point": 1e30}), "旅遊積分數值超出範圍"),
    (_preview_body(user=None), "使用者資料必須是物件"),
    (_preview_body(user={}), "「姓名」為必填欄位"),
    (_with_user(name=None), "「姓名」必須是文字"),
    (_with_user(email=None), "Email 必須是文字"),
    (_with_user(email=""), "Email 為必填欄位"),
    (_with_user(address=""), "地址為必填欄位"),
    (_with_user(phone_number=None), "電話必須是文字"),
    (_with_user(phone_number=""), "電話為必填欄位"),
    (_preview_body(discount=None), "優惠內容必須是物件"),
    (_preview_body(discount={"type": "point", "coupon_id": []}), "優惠券代碼必須是文字"),
]


@pytest.mark.parametrize("body, expected", CHECKOUT_BODY_CASES, ids=lambda v: str(v))
def test_checkout_preview_body_messages(api, make_user, body, expected):
    r = api.patch(f"{CHECKOUT_API}/preview/{uuid.uuid4()}", json=body, headers=auth_header(make_user()), timeout=5)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == expected
    _no_raw_names(r.json()["message"])
