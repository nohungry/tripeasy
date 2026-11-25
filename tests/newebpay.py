"""藍新簽章工具（測試端）：與 backend、mock-newebpay 相同的 AES-256-CBC／SHA256 演算法。

金鑰從環境變數或專案根目錄 .env 讀（本機假金鑰，不是真的藍新金鑰）。
"""
import hashlib
import json
import os
import re
import time
import uuid
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _key() -> str:
    return os.environ["HASHKEY"]


def _iv() -> str:
    return os.environ["HASHIV"]


def merchant_id() -> str:
    return os.environ["MerchantID"]


def _cipher():
    return Cipher(algorithms.AES(_key().encode()), modes.CBC(_iv().encode()))


def encrypt(plain: str) -> str:
    padder = padding.PKCS7(128).padder()
    data = padder.update(plain.encode("utf-8")) + padder.finalize()
    enc = _cipher().encryptor()
    return (enc.update(data) + enc.finalize()).hex()


def decrypt(hex_str: str) -> str:
    dec = _cipher().decryptor()
    data = dec.update(bytes.fromhex(hex_str)) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(data) + unpadder.finalize()).decode("utf-8")


def trade_sha(trade_info_hex: str) -> str:
    text = f"HashKey={_key()}&{trade_info_hex}&HashIV={_iv()}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def build_notify(
    merchant_order_no: str,
    amt: int,
    status: str = "SUCCESS",
    message: str = "授權成功",
    trade_no: str | None = None,
) -> dict[str, str]:
    """藍新 notify 的 form 欄位（格式同 mock）。"""
    body = {
        "Status": status,
        "Message": message,
        "Result": {
            "MerchantID": merchant_id(),
            "Amt": amt,
            "TradeNo": trade_no or f"MOCK{uuid.uuid4().hex[:12].upper()}",
            "MerchantOrderNo": merchant_order_no,
            "PaymentType": "CREDIT",
            "PayTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
    trade_info = encrypt(json.dumps(body, ensure_ascii=False))
    return {
        "Status": status,
        "MerchantID": merchant_id(),
        "Version": "2.0",
        "TradeInfo": trade_info,
        "TradeSha": trade_sha(trade_info),
    }


def parse_payment_form(html: str) -> tuple[str, dict[str, str]]:
    """從 HTML 取第一個 form 的 action 與 hidden 欄位。"""
    form = re.search(r'<form\b[^>]*\baction="([^"]*)"', html)
    assert form, html
    fields: dict[str, str] = {}
    for tag in re.findall(r"<input\b[^>]*>", html):
        if not re.search(r'type="hidden"', tag):
            continue
        name = re.search(r'name="([^"]*)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[unescape(name.group(1))] = unescape(value.group(1)) if value else ""
    return unescape(form.group(1)), fields


def decode_trade_info(fields: dict) -> dict[str, str]:
    """MPG 請求的 TradeInfo（URL query string）。"""
    return dict(parse_qsl(decrypt(fields["TradeInfo"]), keep_blank_values=True))


def decode_notify_result(fields: dict) -> dict:
    """notify／ReturnURL 的 TradeInfo（JSON）。"""
    return json.loads(decrypt(fields["TradeInfo"]))
