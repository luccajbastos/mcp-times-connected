import json
from pathlib import Path

import httpx
import pytest
import respx

from connected_mcp.client import ApiError, AuthError, ConnectedClient

BASE = "https://example.test/"
LOGIN = json.loads((Path(__file__).parent / "fixtures" / "login.json").read_text())
PASSWORD = "s3cret-pw"


def make():
    return ConnectedClient("me", PASSWORD, base_url=BASE)


@respx.mock
async def test_login_stores_token_and_student_id():
    respx.post(BASE + "api/auth/student-login").respond(200, json=LOGIN)
    route = respx.get(BASE + "api/x").respond(200, json={"ok": True})
    c = make()
    await c.login()
    assert c.student_id == str(LOGIN["studentId"])
    await c._request("GET", "api/x")
    req = route.calls.last.request
    assert req.headers["Authorization"] == f"Bearer {LOGIN['token']}"
    assert req.headers["Accept"] == "application/json"


@respx.mock
async def test_lazy_login_on_first_request():
    login = respx.post(BASE + "api/auth/student-login").respond(200, json=LOGIN)
    respx.get(BASE + "api/x").respond(200, json={"ok": True})
    c = make()
    assert await c._request("GET", "api/x") == {"ok": True}
    assert login.call_count == 1


@respx.mock
async def test_relogin_once_on_401():
    login = respx.post(BASE + "api/auth/student-login").respond(200, json=LOGIN)
    respx.get(BASE + "api/x").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json={"ok": 1})]
    )
    assert await make()._request("GET", "api/x") == {"ok": 1}
    assert login.call_count == 2


@respx.mock
async def test_second_401_raises_auth_error():
    respx.post(BASE + "api/auth/student-login").respond(200, json=LOGIN)
    respx.get(BASE + "api/x").respond(401)
    with pytest.raises(AuthError):
        await make()._request("GET", "api/x")


@respx.mock
async def test_bad_credentials_message_has_no_password():
    respx.post(BASE + "api/auth/student-login").respond(422, json={"message": "x"})
    with pytest.raises(AuthError) as ei:
        await make().login()
    assert "CONNECTED_USER" in str(ei.value)
    assert PASSWORD not in str(ei.value)


@respx.mock
async def test_network_timeout_raises_api_error_without_retry():
    respx.post(BASE + "api/auth/student-login").respond(200, json=LOGIN)
    route = respx.get(BASE + "api/x").mock(side_effect=httpx.ReadTimeout("t"))
    with pytest.raises(ApiError):
        await make()._request("GET", "api/x")
    assert route.call_count == 1


@respx.mock
async def test_login_without_student_id_raises_auth_error():
    respx.post(BASE + "api/auth/student-login").respond(200, json={"token": "t"})
    with pytest.raises(AuthError) as ei:
        await make().login()
    assert PASSWORD not in str(ei.value)
