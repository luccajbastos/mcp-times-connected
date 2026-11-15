"""Cliente HTTP assíncrono para a API Times Connected."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE = "https://controllercore.timescontroller.com.br/"
LOGIN_PATH = "api/auth/student-login"


BOOK_TIMEOUT_MSG = (
    "Tempo esgotado; o agendamento pode ter sido efetuado. "
    "Verifique com listar_minhas_aulas antes de tentar de novo."
)
CANCEL_TIMEOUT_MSG = (
    "Tempo esgotado; o cancelamento pode ter sido efetuado. "
    "Verifique com listar_minhas_aulas antes de tentar de novo."
)


class AuthError(Exception):
    """Falha de autenticação."""


class ApiError(Exception):
    """Falha de comunicação ou resposta de erro da API."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class Slot:
    class_id: str
    date: str
    hour: str
    teacher_id: str
    teacher_name: str | None
    class_type: str | None
    booked: bool | None = None


def _s(value: Any) -> str:
    return "" if value is None else str(value)


def _check_business_error(body: Any) -> None:
    if not isinstance(body, dict):
        return
    if body.get("status") in ("error", "fail") or body.get("success") is False:
        msg = body.get("message") or body.get("msg") or "A API retornou um erro."
        raise ApiError(_s(msg))


def _error_detail(resp: httpx.Response) -> str:
    """Extrai a mensagem de erro da API (message|msg ou errors estilo Laravel)."""
    try:
        body = resp.json()
    except ValueError:
        return ""
    if not isinstance(body, dict):
        return ""
    msg = body.get("message") or body.get("msg")
    if msg:
        return _s(msg)
    errors = body.get("errors")
    if isinstance(errors, dict):
        parts: list[str] = []
        for v in errors.values():
            if isinstance(v, (list, tuple)):
                parts.extend(_s(x) for x in v[:1])
            elif v:
                parts.append(_s(v))
        return "; ".join(p for p in parts if p)
    return ""


def _dicts(value: Any) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _first(d: dict, *keys: str) -> Any:
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


def _parse_my_class(item: Any) -> Slot | None:
    if not isinstance(item, dict):
        return None
    teacher = item.get("teacher") if isinstance(item.get("teacher"), dict) else {}
    teacher_id = _first(item, "teacherId", "teacher_id")
    if teacher_id is None:
        teacher_id = teacher.get("id")
    name = teacher.get("nickname") or teacher.get("name")
    ctype = item.get("class_name")
    if not ctype:
        ctype = _first(item, "classType", "class_type")
        if isinstance(ctype, dict):
            ctype = ctype.get("name")
    if not ctype:
        ctype = item.get("type_class")
    return Slot(
        class_id=_s(_first(item, "classId", "class_id")),
        date=_s(item.get("date")),
        hour=_s(item.get("hour")),
        teacher_id=_s(teacher_id),
        teacher_name=name,
        class_type=ctype if isinstance(ctype, str) else None,
    )


class ConnectedClient:
    def __init__(
        self,
        user: str,
        password: str,
        base_url: str = DEFAULT_BASE,
        timeout: float = 20.0,
    ):
        self._user = user
        self._password = password
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self._token: str | None = None
        self.student_id: str = ""

    async def login(self) -> None:
        fail = AuthError(
            "Falha no login: verifique CONNECTED_USER e CONNECTED_PASSWORD."
        )
        try:
            resp = await self._http.post(
                LOGIN_PATH, json={"user": self._user, "password": self._password}
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Erro de rede no login: {type(exc).__name__}") from None
        if not resp.is_success:
            raise fail
        try:
            data = resp.json()
        except ValueError:
            raise fail from None
        if not isinstance(data, dict) or not data.get("token"):
            raise fail
        if data.get("studentId") in (None, ""):
            raise AuthError("Login sem studentId na resposta da API.")
        self._token = data["token"]
        self.student_id = str(data["studentId"])

    async def _send(
        self,
        method: str,
        path: str,
        json: dict | None,
        timeout_msg: str | None = None,
    ) -> httpx.Response:
        try:
            return await self._http.request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.TimeoutException as exc:
            if timeout_msg:
                raise ApiError(timeout_msg) from None
            raise ApiError(f"Erro de rede: {type(exc).__name__}") from None
        except httpx.HTTPError as exc:
            raise ApiError(f"Erro de rede: {type(exc).__name__}") from None

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        timeout_msg: str | None = None,
        allow_empty: bool = False,
    ) -> Any:
        if self._token is None:
            await self.login()
        resp = await self._send(method, path, json, timeout_msg)
        if resp.status_code == 401:
            await self.login()
            resp = await self._send(method, path, json, timeout_msg)
            if resp.status_code == 401:
                raise AuthError(
                    "Não autorizado mesmo após novo login; verifique CONNECTED_USER e CONNECTED_PASSWORD."
                )
        if not resp.is_success:
            text = f"HTTP {resp.status_code} em {method} {path}"
            detail = _error_detail(resp)
            raise ApiError(f"{text}: {detail}" if detail else text)
        try:
            body = resp.json()
        except ValueError:
            if allow_empty:
                return None
            raise ApiError(f"Resposta não-JSON em {method} {path}") from None
        _check_business_error(body)
        return body

    async def _ensure_student_id(self) -> str:
        if self._token is None:
            await self.login()
        return self.student_id

    async def list_available(
        self, begin_date: str, end_date: str, class_type: str | None = None
    ) -> list[Slot]:
        sid = await self._ensure_student_id()
        data = await self._request(
            "POST",
            "api/class-type/day-by-day-new",
            {
                "beginDate": begin_date,
                "endDate": end_date,
                "studentId": sid,
                "typeClass": class_type if class_type is not None else "1",
            },
        )
        slots: list[Slot] = []
        for entry in _dicts(data):
            ct = entry.get("classType")
            ctype = ct.get("name") if isinstance(ct, dict) else None
            for avail in _dicts(entry.get("availableClasses")):
                for hr in _dicts(avail.get("arrayOfClassByHourDto")):
                    for t in _dicts(hr.get("arrayOfClassByTeacher")):
                        teacher = t.get("teacher")
                        if not isinstance(teacher, dict):
                            teacher = {}
                        booked = _first(t, "studentIn", "student_in")
                        slots.append(
                            Slot(
                                class_id=_s(avail.get("classId")),
                                date=_s(avail.get("date")),
                                hour=_s(hr.get("hour")),
                                teacher_id=_s(teacher.get("id")),
                                teacher_name=teacher.get("nickname") or teacher.get("name"),
                                class_type=ctype or t.get("typeClass"),
                                booked=booked if isinstance(booked, bool) else None,
                            )
                        )
        return slots

    async def list_my_classes(self) -> list[Slot]:
        body = await self._request("GET", "api/next-classes")
        data = body.get("data") if isinstance(body, dict) else body
        if isinstance(data, dict) and ("class_id" in data or "classId" in data):
            data = [data]
        elif isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), None)
        if not isinstance(data, list):
            return []
        return [s for s in map(_parse_my_class, data) if s is not None]

    def _class_body(self, class_id, date, hour, teacher_id) -> dict:
        return {
            "classId": _s(class_id),
            "date": date,
            "hour": hour,
            "teacherId": _s(teacher_id),
            "studentId": self.student_id,
        }

    @staticmethod
    def _message(body: Any, default: str) -> str:
        if isinstance(body, dict):
            msg = body.get("message") or body.get("msg")
            if msg:
                return _s(msg)
        return default

    async def book(self, class_id, date, hour, teacher_id) -> str:
        await self._ensure_student_id()
        body = await self._request(
            "POST",
            "api/student-history",
            self._class_body(class_id, date, hour, teacher_id),
            timeout_msg=BOOK_TIMEOUT_MSG,
            allow_empty=True,
        )
        return self._message(body, "Aula agendada com sucesso.")

    async def cancel(self, class_id, date, hour, teacher_id) -> str:
        await self._ensure_student_id()
        body = await self._request(
            "DELETE",
            "api/student-history/custom-destroy",
            self._class_body(class_id, date, hour, teacher_id),
            timeout_msg=CANCEL_TIMEOUT_MSG,
            allow_empty=True,
        )
        return self._message(body, "Aula cancelada com sucesso.")

    async def aclose(self) -> None:
        await self._http.aclose()
