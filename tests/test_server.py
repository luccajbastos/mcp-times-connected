import pytest

from connected_mcp import server
from connected_mcp.client import ApiError, Slot

EXPECTED = {
    "listar_horarios_disponiveis",
    "listar_minhas_aulas",
    "agendar_aula",
    "cancelar_aula",
}


class FakeClient:
    async def list_available(self, begin_date, end_date, class_type=None):
        return [Slot("1", "2026-11-20", "10:00", "7", "Ana", "Regular")]

    async def list_my_classes(self):
        return []

    async def book(self, class_id, date, hour, teacher_id):
        return "ok"

    async def cancel(self, *args, **kwargs):
        return "ok"


@pytest.fixture(autouse=True)
def fake():
    server.set_client(FakeClient())
    yield
    server.set_client(None)


async def test_tools_registered():
    tools = await server.mcp.list_tools()
    assert {t.name for t in tools} == EXPECTED


async def test_list_tool_returns_dicts_with_ids():
    result = await server.listar_horarios_disponiveis("2026-11-20", "2026-11-21")
    assert result
    for key in ("class_id", "date", "hour", "teacher_id"):
        assert key in result[0]


async def test_write_tools_description_requires_confirmation():
    tools = {t.name: t for t in await server.mcp.list_tools()}
    for name in ("agendar_aula", "cancelar_aula"):
        assert "Confirme" in tools[name].description


def test_missing_env_vars_fails_clearly(monkeypatch):
    server.set_client(None)
    monkeypatch.delenv("CONNECTED_USER", raising=False)
    monkeypatch.delenv("CONNECTED_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="CONNECTED_USER"):
        server.main()


class RecordingClient(FakeClient):
    def __init__(self):
        self.calls = []

    async def book(self, *args):
        self.calls.append(("book", args))
        return "agendada"

    async def cancel(self, *args):
        self.calls.append(("cancel", args))
        return "cancelada"


async def test_agendar_aula_calls_client_and_returns_string():
    rec = RecordingClient()
    server.set_client(rec)
    assert await server.agendar_aula("1", "2026-11-20", "10:00", "7") == "agendada"
    assert rec.calls == [("book", ("1", "2026-11-20", "10:00", "7"))]


async def test_cancelar_aula_calls_client_and_returns_string():
    rec = RecordingClient()
    server.set_client(rec)
    assert await server.cancelar_aula("1", "2026-11-20", "10:00", "7") == "cancelada"
    assert rec.calls == [("cancel", ("1", "2026-11-20", "10:00", "7"))]


class FailingClient(FakeClient):
    async def book(self, *args):
        raise ApiError("Aula lotada")

    async def cancel(self, *args):
        raise ApiError("Já cancelada")


@pytest.mark.parametrize(
    "tool,msg", [("agendar_aula", "Aula lotada"), ("cancelar_aula", "Já cancelada")]
)
async def test_write_tool_api_error_becomes_tool_error(tool, msg):
    from mcp.server.fastmcp.exceptions import ToolError

    server.set_client(FailingClient())
    with pytest.raises(ToolError) as ei:
        await server.mcp.call_tool(
            tool, {"class_id": "1", "date": "2026-11-20", "hour": "10:00", "teacher_id": "7"}
        )
    assert msg in str(ei.value)


async def test_write_tool_docstrings_mention_timeout_check():
    tools = {t.name: t for t in await server.mcp.list_tools()}
    for name in ("agendar_aula", "cancelar_aula"):
        assert "listar_minhas_aulas" in tools[name].description
        assert "timeout" in tools[name].description.lower()


def test_server_instructions_mention_english_school():
    text = (server.mcp.instructions or "").lower()
    for word in ("inglês", "times idiomas", "times connected", "aula"):
        assert word in text


async def test_list_tools_descriptions_are_discoverable():
    tools = {t.name: t for t in await server.mcp.list_tools()}
    desc = tools["listar_horarios_disponiveis"].description.lower()
    for word in ("inglês", "times idiomas", "semana"):
        assert word in desc
    assert "inglês" in tools["listar_minhas_aulas"].description.lower()


def test_server_instructions_ask_for_table_output():
    text = server.mcp.instructions or ""
    assert "tabela" in text.lower()
    assert "✅" in text
