"""P4 Task 10 fix round 3：Joi 訊息全面掃描（容器內）、原始碼掃描、六類 HTTP 洩漏。"""
import json
import re
import subprocess
import uuid
from pathlib import Path

import pytest
from conftest import CART_API, CHECKOUT_API, DISCOUNT_API, auth_header

ROOT = Path(__file__).resolve().parents[1]
FALLBACK = "輸入的資料格式不正確"

SWEEP_JS = r"""
const b = process.cwd() + '/src/utils/Validator/';
const cart = require(b + 'cart_Validator.js'), disc = require(b + 'discounts_Validatior.js');
const co = require(b + 'checkout_Vaildator.js'), prod = require(b + 'product_Validator.js');
const np = require(process.cwd() + '/src/middlewares/newebpay/index.js');
const ui = require(b + 'userInfo_Validator.js'), up = require(b + 'userprofile_Validator.js');
const au = require(b + 'automation_Validator.js');
const pg = require(b + 'paging_Validator.js'), ord = require(b + 'orders_Validator.js'), pur = require(b + 'purchases_Validator.js');
let userMessage = null;
try { userMessage = require(b + 'joiMessage.js').userMessage; } catch (e) {}
const real = typeof userMessage === 'function';
if (!real) userMessage = (err) => err.details[0].message;
const F = { start_date: '2099-01-01', end_date: '2099-01-02' };
const U = { name: '王小明', email: 'a@b.co', address: '台北市', phone_number: '0912345678' };
const uuid = '7b0e5b2e-3c1f-4c59-9d0a-0d3f5f1f2a11';
const bodyVals = [null, [], {}, true, '', 1e30, -1e30, '1e30', 'x', 1.5, 0, -1, '9007199254740993', 5, '5', 1e-30, '0x10', ' ', 'Infinity', '-0', [1], { a: 1 }, Infinity, -Infinity, NaN];
const queryVals = ['', '1e30', '-1e30', 'x', '1.5', '0', '-1', '9007199254740993', '5', ['1', '2'], { a: '1' }, ' ', 'Infinity', '1e-30', '0x10', '1e400'];
const targets = [
 ['cart.base travel', cart.baseSchema, { type: 'tourgroup', item: 'travel', people: 1, options: { ...F } }, bodyVals, ['type', 'item', 'people', 'options', 'options.start_date', 'options.end_date']],
 ['cart.base hotel', cart.baseSchema, { type: 'backpacker', item: 'hotel', people: 1, options: { ...F, room_type: 'a' } }, bodyVals, ['options.room_type', 'options.start_date', 'options.end_date', 'options']],
 ['cart.base food', cart.baseSchema, { type: 'backpacker', item: 'food', people: 1, options: { start_date: '2099-01-01T10:00' } }, bodyVals, ['options.start_date', 'options']],
 ['cart.params', cart.paramsSchema, { tour_id: uuid }, queryVals, ['tour_id']],
 ['cart.cartID', cart.cartIDSchema, { cart_item_id: uuid }, queryVals, ['cart_item_id']],
 ['cart.common(query)', cart.commonSchema, {}, queryVals, ['page', 'limit', 'lang']],
 ['disc.base point', disc.baseschema, { type: 'point', discount: { point: 5 } }, bodyVals, ['type', 'discount', 'discount.point', 'discount.coupon']],
 ['disc.base coupon', disc.baseschema, { type: 'coupon', discount: { coupon: 'ABC123' } }, bodyVals, ['type', 'discount', 'discount.point', 'discount.coupon']],
 ['disc.orderID', disc.orderIDSchema, { order_id: uuid }, queryVals, ['order_id']],
 ['co.cartID', co.cartIDSchema, { cart_id: uuid }, queryVals, ['cart_id']],
 ['co.orderID', co.orderIDSchema, { order_id: uuid }, queryVals, ['order_id']],
 ['co.post atm', co.postSchema, { user: { ...U }, payment_method: 'atm', discount: { type: 'point', used_point: 1 }, agree_terms: true }, bodyVals, ['user', 'user.name', 'user.email', 'user.address', 'user.phone_number', 'payment_method', 'installment', 'discount', 'discount.type', 'discount.coupon_id', 'discount.used_point', 'agree_terms']],
 ['co.post cc+coupon', co.postSchema, { user: { ...U }, payment_method: 'credit_card', installment: 3, discount: { type: 'coupon', coupon_id: uuid } }, bodyVals, ['installment', 'discount.coupon_id', 'discount.used_point', 'discount.type', 'payment_method']],
 ['userInfo.register', ui.registerSchema, { name: '王小明', email: 'a@b.co', password: 'Abcdefg1', preference: ['a', 'b', 'c'] }, bodyVals, ['name', 'email', 'password', 'preference']],
 ['userprofile.update', up.updateProfile_schema, { name: '王小明', preference: ['a', 'b', 'c'] }, bodyVals, ['name', 'preference']],
 ['paging', pg.pagingSchema, {}, queryVals, ['page', 'limit', 'lang']],
 ['points.paging', pg.pagingSchema, {}, queryVals, ['page', 'limit', 'lang']],
 ['orders.orderID', ord.orderIDSchema, { order_id: uuid }, queryVals, ['order_id']],
 ['purchases.param', pur.paramSchema, { order_item_id: uuid }, queryVals, ['order_item_id']],
 ['purchases.query', pur.querySchema, {}, queryVals, ['lang']],
 ['automation.early', au.early_schema, { notifi_settings_enabled: true }, bodyVals, ['notifi_settings_enabled']],
 ['automation.price', au.price_schema, { price_tracking_enabled: true, country: 'Japan', region: 'Tokyo', max_price: 30000 }, bodyVals, ['price_tracking_enabled', 'country', 'region', 'max_price']],
 ['np.payment', np.paymentSchema, { order_id: uuid }, bodyVals, ['order_id']],
 ['prod.query(search)', prod.queryschema, { page: '1', limit: '10', sort_by: 'date', order: 'asc', lang: 'zh-TW' }, queryVals, ['type', 'item', 'tag', 'country', 'region', 'min_price', 'max_price', 'start_date', 'end_date', 'keyword', 'duration', 'page', 'limit', 'sort_by', 'order', 'lang']],
];
const clone = (o) => JSON.parse(JSON.stringify(o));
function set(o, p, v, del) {
  const ks = p.split('.'); let c = o;
  for (let i = 0; i < ks.length - 1; i++) { if (typeof c[ks[i]] !== 'object' || c[ks[i]] === null) c[ks[i]] = {}; c = c[ks[i]]; }
  if (del) delete c[ks.at(-1)]; else c[ks.at(-1)] = v;
}
const leaks = []; let n = 0, errors = 0;
for (const [label, schema, valid, vals, paths] of targets) {
  const names = new Set(['zqfoo']);
  const collect = (o) => { if (Array.isArray(o)) return; for (const k of Object.keys(o)) { names.add(k); if (o[k] && typeof o[k] === 'object') collect(o[k]); } };
  collect(valid); paths.forEach((p) => p.split('.').forEach((s) => names.add(s)));
  const run = (input, desc) => {
    n++;
    const r = schema.validate(input);
    if (!r.error) return;
    errors++;
    let m;
    try { m = userMessage(r.error); } catch (e) { leaks.push([label, desc, 'THROW ' + e.message]); return; }
    if (typeof m !== 'string' || m === '' || m.includes('"') || [...names].some((k) => m.includes(k))) leaks.push([label, desc, m]);
  };
  const r0 = schema.validate(clone(valid)); if (r0.error) leaks.push([label, 'BASE INVALID', r0.error.details[0].message]);
  for (const p of paths) {
    { const o = clone(valid); set(o, p, 0, true); run(o, p + ' <missing>'); }
    for (const v of vals) { const o = clone(valid); set(o, p, v); run(o, p + '=' + String(v)); }
  }
  { const o = clone(valid); o.zqfoo = '1'; run(o, 'root zqfoo'); }
  for (const k of Object.keys(valid)) if (valid[k] && typeof valid[k] === 'object') { const o = clone(valid); o[k].zqfoo = 1; run(o, k + '.zqfoo'); }
  for (const v of [null, [], 'x', 5, true, undefined]) run(v, 'ROOT=' + String(v));
}
console.log('SWEEP' + JSON.stringify({ real, cases: n, errors, leaks }));
"""


def test_hostile_matrix_has_no_joi_default_leaks():
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "node", "-e", SWEEP_JS],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr
    line = next(l for l in proc.stdout.splitlines() if l.startswith("SWEEP"))
    result = json.loads(line[len("SWEEP"):])
    assert result["cases"] >= 1400, result["cases"]
    assert result["errors"] >= 1000, result["errors"]
    assert result["leaks"] == [], (result["real"], len(result["leaks"]), result["leaks"][:10])
    assert result["real"], "backend/src/utils/Validator/joiMessage.js 的 userMessage 不存在"


# ---- 原始碼掃描：不得在 userMessage 以外讀取 Joi error 的 message／details ----
BACKEND = ROOT / "backend" / "src" / "middlewares"
SCAN_FILES = [BACKEND / "cart" / "index.js", BACKEND / "discounts" / "index.js", BACKEND / "checkout" / "index.js"]


def _search_handler_source() -> str:
    src = (BACKEND / "product" / "index.js").read_text(encoding="utf-8")
    start = src.index("async function get_tourData(")
    end = src.index("async function get_tourDetail(")
    return src[start:end]


def _handler_source(path: str, name: str) -> str:
    src = (BACKEND / path / "index.js").read_text(encoding="utf-8")
    start = src.index(f"async function {name}(")
    nxt = src.find("\nasync function ", start + 1)
    nxt2 = src.find("\nconst upload", start + 1)
    ends = [e for e in (nxt, nxt2) if e != -1]
    return src[start : min(ends)] if ends else src[start:]


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


@pytest.mark.parametrize("name", ["cart", "discounts", "checkout", "newebpay", "product.get_tourData", "userinfo.postuserSignup", "userProfile.patchuserprofileData", "orders", "purchases", "points", "automation"])
def test_middlewares_read_joi_errors_only_through_user_message(name):
    if name == "product.get_tourData":
        src = _search_handler_source()
    elif name == "userinfo.postuserSignup":
        src = _handler_source("userinfo", "postuserSignup")
    elif name == "userProfile.patchuserprofileData":
        src = _handler_source("userProfile", "patchuserprofileData")
    else:
        src = (BACKEND / name / "index.js").read_text(encoding="utf-8")
    src = _strip_comments(src)
    assert not re.search(r"\bdetails\b|\.message\b", src), "不得直接讀取 Joi error 的 details／message"
    assert "userMessage(" in src


# ---- HTTP：六類洩漏 ----
USER = {"name": "王小明", "email": "a@b.co", "address": "台北市", "phone_number": "0912345678"}


def _raw(api, method, url, user, raw_body):
    headers = {**auth_header(user), "Content-Type": "application/json"}
    return api.request(method, url, data=raw_body.encode(), headers=headers, timeout=5)


def _preview(api, user, body):
    return api.patch(f"{CHECKOUT_API}/preview/{uuid.uuid4()}", json=body, headers=auth_header(user), timeout=5)


def _assert_fallback(r):
    assert r.status_code == 400, r.text
    assert r.json()["message"] == FALLBACK
    assert '"' not in r.json()["message"]


def test_http_installment_unsafe_string(api, make_user):
    _assert_fallback(_preview(api, make_user(), {"user": USER, "payment_method": "credit_card", "installment": "9007199254740993"}))


def test_http_json_1e400_cart_people(api, make_user):
    body = '{"type":"tourgroup","item":"travel","people":1e400,"options":{"start_date":"2099-01-01","end_date":"2099-01-02"}}'
    _assert_fallback(_raw(api, "POST", f"{CART_API}/{uuid.uuid4()}", make_user(), body))


def test_http_json_1e400_discount_point(api, make_user):
    body = '{"type":"point","discount":{"point":1e400}}'
    _assert_fallback(_raw(api, "POST", f"{DISCOUNT_API}/{uuid.uuid4()}", make_user(), body))


def test_http_json_1e400_checkout_used_point(api, make_user):
    body = json.dumps({"user": USER, "payment_method": "atm"})[:-1] + ',"discount":{"type":"point","used_point":1e400}}'
    _assert_fallback(_raw(api, "PATCH", f"{CHECKOUT_API}/preview/{uuid.uuid4()}", make_user(), body))


def test_http_checkout_empty_coupon_id(api, make_user):
    _assert_fallback(_preview(api, make_user(), {"user": USER, "payment_method": "atm", "discount": {"type": "coupon", "coupon_id": ""}}))


@pytest.mark.parametrize(
    "body",
    [
        {"user": USER, "payment_method": "atm", "foo": 1},
        {"user": {**USER, "foo": 1}, "payment_method": "atm"},
        {"user": USER, "payment_method": "atm", "discount": {"type": "point", "foo": 1}},
        [],
    ],
    ids=["root-unknown", "user-unknown", "discount-unknown", "root-array"],
)
def test_http_checkout_unknown_keys_and_array_root(api, make_user, body):
    _assert_fallback(_preview(api, make_user(), body))


def test_http_search_unknown_query_key(api):
    r = api.get("/api/v1/user/product/search", params={"foo": 1, "page": 1, "limit": 10, "sort_by": "date", "order": "asc", "lang": "zh-TW"})
    _assert_fallback(r)
