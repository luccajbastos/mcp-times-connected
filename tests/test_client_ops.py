import json
from pathlib import Path

import httpx
import pytest
import respx

from connected_mcp.client import ApiError, ConnectedClient, Slot

BASE = "https://example.test/"
FX = Path(__file__).parent / "fixtures"
LOGIN = json.loads((FX / "login.json").read_text())
DAY = json.loads((FX / "day_by_day.json").read_text())
NEXT = json.loads((FX / "next_classes.json").read_text())
NEXT_ONE = json.loads((FX / "next_classes_one.json").read_text())


def make():
    return ConnectedClient("me", "pw", base_url=BASE)


def mock_login():
    respx.post(BASE + "api/auth/student-login").respond(200, json=LOGIN)


def first_expected():
    ct = DAY[0]["classType"]
    ac = DAY[0]["availableClasses"][0]
    hr = ac["arrayOfClassByHourDto"][0]
    t = hr["arrayOfClassByTeacher"][0]
    return Slot(
        class_id=str(ac["classId"]),
        date=ac["date"],
        hour=hr["hour"],
        teacher_id=str(t["teacher"]["id"]),
        teacher_name=t["teacher"].get("nickname") or t["teacher"].get("name"),
        class_type=ct.get("name") or t.get("typeClass"),
        booked=t.get("studentIn"),
    )


@respx.mock
async def test_list_available_parses_fixture():
    mock_login()
    route = respx.post(BASE + "api/class-type/day-by-day-new").respond(200, json=DAY)
    c = make()
    slots = await c.list_available("2026-11-16", "2026-11-20")
    assert slots and slots[0] == first_expected()
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "beginDate": "2026-11-16",
        "endDate": "2026-11-20",
        "studentId": str(LOGIN["studentId"]),
        "typeClass": "1",
    }


@respx.mock
async def test_list_available_flattens_each_teacher():
    mock_login()
    respx.post(BASE + "api/class-type/day-by-day-new").respond(200, json=DAY)
    total = sum(
        len(h["arrayOfClassByTeacher"])
        for e in DAY
        for a in e["availableClasses"]
        for h in a["arrayOfClassByHourDto"]
    )
    assert len(await make().list_available("2026-11-16", "2026-11-20", "2")) == total


@respx.mock
async def test_list_my_classes_parses_fixture():
    mock_login()
    respx.get(BASE + "api/next-classes").respond(200, json=NEXT)
    assert await make().list_my_classes() == []


@respx.mock
async def test_list_my_classes_single_object():
    mock_login()
    respx.get(BASE + "api/next-classes").respond(200, json=NEXT_ONE)
    assert await make().list_my_classes() == [
        Slot(
            class_id="19",
            date="2026-11-16",
            hour="17:00",
            teacher_id="1414",
            teacher_name="Teacher Maria",
            class_type="Lesson 18",
        )
    ]


@respx.mock
async def test_list_my_classes_non_empty_synthetic():
    mock_login()
    payload = {
        "status": "success",
        "data": [
            {
                "class_id": 7,
                "date": "2026-11-17",
                "hour": "18:00",
                "teacher_id": 3,
                "teacher": {"nickname": "Ana"},
            },
            {
                "classId": 8,
                "date": "2026-11-18",
                "hour": "09:00",
                "teacher": {"id": 4, "name": "Bob"},
            },
        ],
    }
    respx.get(BASE + "api/next-classes").respond(200, json=payload)
    got = await make().list_my_classes()
    assert [(s.class_id, s.date, s.hour, s.teacher_id, s.teacher_name) for s in got] == [
        ("7", "2026-11-17", "18:00", "3", "Ana"),
        ("8", "2026-11-18", "09:00", "4", "Bob"),
    ]


@respx.mock
async def test_empty_lists_return_empty():
    mock_login()
    respx.post(BASE + "api/class-type/day-by-day-new").respond(200, json=[])
    respx.get(BASE + "api/next-classes").respond(200, json={"status": "success", "data": None})
    c = make()
    assert await c.list_available("2026-11-16", "2026-11-20") == []
    assert await c.list_my_classes() == []


@respx.mock
async def test_book_posts_expected_body():
    mock_login()
    route = respx.post(BASE + "api/student-history").respond(
        200, json={"status": "success", "message": "Aula agendada"}
    )
    msg = await make().book("19", "2026-11-16", "17:00", "5")
    assert msg == "Aula agendada"
    assert json.loads(route.calls.last.request.content) == {
        "classId": "19",
        "date": "2026-11-16",
        "hour": "17:00",
        "teacherId": "5",
        "studentId": str(LOGIN["studentId"]),
    }


@respx.mock
async def test_book_generic_message_when_none():
    mock_login()
    respx.post(BASE + "api/student-history").respond(200, json={"status": "success"})
    assert await make().book("19", "2026-11-16", "17:00", "5")


@respx.mock
async def test_cancel_calls_custom_destroy():
    mock_login()
    route = respx.delete(BASE + "api/student-history/custom-destroy").respond(
        200, json={"message": "Cancelada"}
    )
    msg = await make().cancel("19", "2026-11-16", "17:00", "5")
    assert msg == "Cancelada"
    assert json.loads(route.calls.last.request.content) == {
        "classId": "19",
        "date": "2026-11-16",
        "hour": "17:00",
        "teacherId": "5",
        "studentId": str(LOGIN["studentId"]),
    }


@pytest.mark.parametrize(
    "body",
    [
        {"status": "error", "message": "Sem vaga"},
        {"status": "fail", "msg": "Sem vaga"},
        {"success": False, "message": "Sem vaga"},
    ],
)
@respx.mock
async def test_business_error_in_200_raises_api_error(body):
    mock_login()
    respx.post(BASE + "api/student-history").respond(200, json=body)
    with pytest.raises(ApiError, match="Sem vaga"):
        await make().book("19", "2026-11-16", "17:00", "5")


@respx.mock
async def test_timeout_during_book_not_retried():
    mock_login()
    route = respx.post(BASE + "api/student-history").mock(
        side_effect=httpx.ReadTimeout("slow")
    )
    with pytest.raises(ApiError):
        await make().book("19", "2026-11-16", "17:00", "5")
    assert route.call_count == 1


BOOK_TIMEOUT_MSG = (
    "Tempo esgotado; o agendamento pode ter sido efetuado. "
    "Verifique com listar_minhas_aulas antes de tentar de novo."
)
CANCEL_TIMEOUT_MSG = (
    "Tempo esgotado; o cancelamento pode ter sido efetuado. "
    "Verifique com listar_minhas_aulas antes de tentar de novo."
)


@respx.mock
async def test_book_timeout_message_and_single_call():
    mock_login()
    route = respx.post(BASE + "api/student-history").mock(
        side_effect=httpx.ReadTimeout("slow")
    )
    with pytest.raises(ApiError) as ei:
        await make().book("19", "2026-11-16", "17:00", "5")
    assert ei.value.message == BOOK_TIMEOUT_MSG
    assert route.call_count == 1


@respx.mock
async def test_cancel_timeout_message_and_single_call():
    mock_login()
    route = respx.delete(BASE + "api/student-history/custom-destroy").mock(
        side_effect=httpx.ConnectTimeout("slow")
    )
    with pytest.raises(ApiError) as ei:
        await make().cancel("19", "2026-11-16", "17:00", "5")
    assert ei.value.message == CANCEL_TIMEOUT_MSG
    assert route.call_count == 1


@respx.mock
async def test_http_error_includes_api_message():
    mock_login()
    respx.post(BASE + "api/student-history").respond(422, json={"message": "Aula lotada"})
    with pytest.raises(ApiError, match="Aula lotada") as ei:
        await make().book("19", "2026-11-16", "17:00", "5")
    assert "422" in ei.value.message
    assert "17:00" not in ei.value.message


@respx.mock
async def test_http_error_includes_laravel_errors_dict():
    mock_login()
    respx.post(BASE + "api/student-history").respond(
        422, json={"errors": {"hour": ["Hora inválida"], "date": ["Data passada"]}}
    )
    with pytest.raises(ApiError) as ei:
        await make().book("19", "2026-11-16", "17:00", "5")
    assert "Hora inválida" in ei.value.message
    assert "Data passada" in ei.value.message


@respx.mock
async def test_http_error_non_json_body_still_raises():
    mock_login()
    respx.post(BASE + "api/student-history").respond(500, text="boom")
    with pytest.raises(ApiError, match="HTTP 500"):
        await make().book("19", "2026-11-16", "17:00", "5")


@respx.mock
async def test_list_available_skips_non_dict_elements():
    mock_login()
    data = [
        None,
        {
            "classType": None,
            "availableClasses": [
                None,
                {
                    "classId": 1,
                    "date": "2026-11-16",
                    "arrayOfClassByHourDto": [
                        "x",
                        {
                            "hour": "10:00",
                            "arrayOfClassByTeacher": [None, {"teacher": {"id": 3, "name": "Ana"}}],
                        },
                    ],
                },
            ],
        },
    ]
    respx.post(BASE + "api/class-type/day-by-day-new").respond(200, json=data)
    slots = await make().list_available("2026-11-16", "2026-11-20")
    assert [(s.class_id, s.hour, s.teacher_id) for s in slots] == [("1", "10:00", "3")]


@pytest.mark.parametrize("status,content", [(200, b""), (200, b"OK"), (204, b"")])
@respx.mock
async def test_cancel_tolerates_non_json_2xx(status, content):
    mock_login()
    respx.delete(BASE + "api/student-history/custom-destroy").respond(
        status, content=content
    )
    msg = await make().cancel("19", "2026-11-16", "17:00", "5")
    assert msg == "Aula cancelada com sucesso."


@respx.mock
async def test_book_tolerates_non_json_2xx():
    mock_login()
    respx.post(BASE + "api/student-history").respond(200, content=b"")
    msg = await make().book("19", "2026-11-16", "17:00", "5")
    assert msg == "Aula agendada com sucesso."


@respx.mock
async def test_cancel_non_2xx_still_raises():
    mock_login()
    respx.delete(BASE + "api/student-history/custom-destroy").respond(
        422, json={"message": "Nope"}
    )
    with pytest.raises(ApiError, match="Nope"):
        await make().cancel("19", "2026-11-16", "17:00", "5")


@respx.mock
async def test_list_available_fills_booked_from_student_in():
    mock_login()
    entry = lambda extra: {"teacher": {"id": 1, "name": "T"}, "typeClass": "online", **extra}
    day = [{
        "classType": {"name": "Conv"},
        "availableClasses": [{
            "date": "2026-11-16", "classId": 19,
            "arrayOfClassByHourDto": [{"hour": "17:00", "arrayOfClassByTeacher": [
                entry({"studentIn": True}),
                entry({"student_in": False}),
                entry({}),
            ]}],
        }],
    }]
    respx.post(BASE + "api/class-type/day-by-day-new").respond(200, json=day)
    slots = await make().list_available("2026-11-16", "2026-11-16")
    assert [s.booked for s in slots] == [True, False, None]


@respx.mock
async def test_list_my_classes_booked_is_none():
    mock_login()
    respx.get(BASE + "api/next-classes").respond(200, json=NEXT)
    assert all(s.booked is None for s in await make().list_my_classes())
