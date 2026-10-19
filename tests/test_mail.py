"""忘記密碼的信要寄到 Mailpit（本機替代 SendGrid）。"""
import time

import requests

from conftest import MAILPIT_BASE


def _messages_to(address):
    r = requests.get(
        f"{MAILPIT_BASE}/api/v1/search", params={"query": f"to:{address}"}, timeout=10
    )
    r.raise_for_status()
    return r.json()["messages"]


def _wait_for_messages(address, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        messages = _messages_to(address)
        if messages:
            return messages
        time.sleep(0.5)
    return []


def test_forget_password_sends_reset_mail(api, make_user):
    user = make_user()

    r = api.post("/api/v1/auth/userinfo/forgetpw", json={"email": user["email"]})

    assert r.status_code == 200, r.text
    messages = _wait_for_messages(user["email"])
    assert len(messages) == 1
    assert messages[0]["Subject"] == "TripEasy 密碼重設連結"
    detail = requests.get(
        f"{MAILPIT_BASE}/api/v1/message/{messages[0]['ID']}", timeout=10
    ).json()
    assert "resetpw?token=" in detail["HTML"]
