"""mock-newebpay：驗簽、付款頁、簽 notify、交易時限，以及 Python 簽章工具。"""
import json
import re
import time
from urllib.parse import urlencode

import pytest
import requests

import newebpay as nb

MOCK_BASE = "http://localhost:8095"
GATEWAY = f"{MOCK_BASE}/MPG/mpg_gateway"
PAY = f"{MOCK_BASE}/MPG/pay"
NOTIFY_URL = "http://backend:3000/api/v1/health"
RETURN_URL = "http://localhost:3000/api/v1/user/newebpay/return"


def _gateway_fields(trade: dict) -> dict:
    trade_info = nb.encrypt(urlencode(trade))
    return {
        "MerchantID": nb.merchant_id(),
        "TradeInfo": trade_info,
        "TradeSha": nb.trade_sha(trade_info),
        "Version": "2.0",
    }


def _trade(**overrides) -> dict:
    trade = {
        "MerchantID": nb.merchant_id(),
        "RespondType": "JSON",
        "TimeStamp": str(int(time.time())),
        "Version": "2.0",
        "MerchantOrderNo": f"T{int(time.time() * 1000)}",
        "Amt": "1234",
        "ItemDesc": "測試商品",
        "Email": "alice@example.com",
        "NotifyURL": NOTIFY_URL,
        "ReturnURL": RETURN_URL,
        "CREDIT": "1",
    }
    trade.update(overrides)
    return trade


def _open_payment_page(**overrides):
    trade = _trade(**overrides)
    resp = requests.post(GATEWAY, data=_gateway_fields(trade), timeout=10)
    return trade, resp


def _session_id(html: str) -> str:
    m = re.search(r'name="session"\s+value="([^"]+)"', html)
    assert m, html
    return m.group(1)


def _pay(session: str, result: str, headers: dict | None = None):
    return requests.post(
        PAY, data={"session": session, "result": result}, headers=headers or {}, timeout=10
    )


def test_mock_health():
    resp = requests.get(f"{MOCK_BASE}/health", timeout=10)
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_mock_rejects_bad_sha():
    fields = _gateway_fields(_trade())
    sha = fields["TradeSha"]
    fields["TradeSha"] = ("0" if sha[0] != "0" else "1") + sha[1:]
    resp = requests.post(GATEWAY, data=fields, timeout=10)
    assert resp.status_code == 400
    assert "簽章驗證失敗" in resp.text


def test_mock_payment_page_escapes_item_desc():
    _, resp = _open_payment_page(ItemDesc="<script>alert(1)</script>")
    assert resp.status_code == 200
    assert "&lt;script&gt;" in resp.text
    assert "<script>alert(1)</script>" not in resp.text
    assert "付款成功" in resp.text
    assert "付款失敗" in resp.text


def test_mock_success_posts_signed_notify_and_returns():
    trade, page = _open_payment_page()
    resp = _pay(_session_id(page.text), "success")
    assert resp.status_code == 200
    action, fields = nb.parse_payment_form(resp.text)
    assert action == RETURN_URL
    assert fields["TradeSha"] == nb.trade_sha(fields["TradeInfo"])
    body = nb.decode_notify_result(fields)
    assert body["Status"] == "SUCCESS"
    assert body["Result"]["MerchantOrderNo"] == trade["MerchantOrderNo"]
    assert str(body["Result"]["Amt"]) == trade["Amt"]


def test_mock_fail_status():
    _, page = _open_payment_page()
    resp = _pay(_session_id(page.text), "fail")
    assert resp.status_code == 200
    _, fields = nb.parse_payment_form(resp.text)
    assert fields["TradeSha"] == nb.trade_sha(fields["TradeInfo"])
    assert nb.decode_notify_result(fields)["Status"] != "SUCCESS"


def test_mock_refuses_after_trade_limit():
    _, page = _open_payment_page(TradeLimit="60")
    resp = _pay(_session_id(page.text), "success", headers={"X-Mock-Now": str(time.time() + 120)})
    assert resp.status_code == 200
    assert "交易逾時" in resp.text
    assert "<form" not in resp.text


def test_mock_pays_within_trade_limit_without_clock_override():
    _, page = _open_payment_page(TradeLimit="60")
    resp = _pay(_session_id(page.text), "success")
    assert resp.status_code == 200
    assert "交易逾時" not in resp.text
    action, _ = nb.parse_payment_form(resp.text)
    assert action == RETURN_URL


def test_mock_trade_limit_below_minimum_is_clamped_to_60():
    # TradeLimit=1 視為 60：30 秒後仍可付款
    _, page = _open_payment_page(TradeLimit="1")
    resp = _pay(_session_id(page.text), "success", headers={"X-Mock-Now": str(time.time() + 30)})
    assert "交易逾時" not in resp.text
    action, _ = nb.parse_payment_form(resp.text)
    assert action == RETURN_URL


def test_mock_trade_limit_above_maximum_is_clamped_to_900():
    # TradeLimit=5000 視為 900：1000 秒後逾時
    _, page = _open_payment_page(TradeLimit="5000")
    resp = _pay(_session_id(page.text), "success", headers={"X-Mock-Now": str(time.time() + 1000)})
    assert "交易逾時" in resp.text


def test_mock_trade_limit_zero_means_no_limit():
    _, page = _open_payment_page(TradeLimit="0")
    resp = _pay(_session_id(page.text), "success", headers={"X-Mock-Now": str(time.time() + 100000)})
    assert "交易逾時" not in resp.text


def test_mock_session_cannot_pay_twice():
    _, page = _open_payment_page()
    session = _session_id(page.text)
    assert _pay(session, "success").status_code == 200
    second = _pay(session, "success")
    assert second.status_code == 409
    assert "此交易已完成" in second.text


def test_newebpay_helper_round_trip():
    text = "MerchantOrderNo=T1&Amt=100&ItemDesc=中文"
    assert nb.decrypt(nb.encrypt(text)) == text
    # 已知向量：以 backend 容器內相同演算法（AES-256-CBC／SHA256）與本機假金鑰算出
    known_plain = "MerchantOrderNo=T1&Amt=100"
    known_hex = "76de5bf1c0a6a7a41c0d5d583f092223f7e0c4c98775e22d0296ee9233146368"
    known_sha = "072A0C6346B824B6F74D5702D7347D7A22215DDCB82D8380A63CFC6945E5EAB3"
    assert nb.encrypt(known_plain) == known_hex
    assert nb.decrypt(known_hex) == known_plain
    assert nb.trade_sha(known_hex) == known_sha
