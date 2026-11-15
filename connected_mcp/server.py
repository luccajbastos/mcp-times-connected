"""Servidor MCP (stdio) para o site de agendamento Times Connected."""
import os
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from connected_mcp.client import DEFAULT_BASE, ApiError, AuthError, ConnectedClient

mcp = FastMCP("connected")

_client = None


def set_client(client) -> None:
    """Injeta (ou limpa) o cliente; usado em testes."""
    global _client
    _client = client


def _get_client():
    global _client
    if _client is None:
        user = os.environ.get("CONNECTED_USER")
        password = os.environ.get("CONNECTED_PASSWORD")
        if not user or not password:
            raise RuntimeError(
                "Variáveis de ambiente CONNECTED_USER e CONNECTED_PASSWORD são obrigatórias."
            )
        _client = ConnectedClient(
            user, password, os.environ.get("CONNECTED_API_BASE") or DEFAULT_BASE
        )
    return _client


def _error_text(exc: Exception) -> str:
    return getattr(exc, "message", None) or str(exc)


@mcp.tool()
async def listar_horarios_disponiveis(
    data_inicio: str, data_fim: str, tipo_aula: str | None = None
) -> list[dict]:
    """Lista os horários de aula disponíveis para agendamento.

    As datas usam o formato YYYY-MM-DD. Os resultados (class_id, date, hour,
    teacher_id) alimentam a ferramenta agendar_aula. tipo_aula é opcional.
    booked=true significa que o aluno já está nesse horário.
    """
    try:
        slots = await _get_client().list_available(data_inicio, data_fim, tipo_aula)
    except (AuthError, ApiError) as exc:
        raise RuntimeError(_error_text(exc)) from None
    return [asdict(s) for s in slots]


@mcp.tool()
async def listar_minhas_aulas() -> list[dict]:
    """Retorna a próxima aula agendada do aluno (a API expõe apenas a próxima),
    útil para cancelar_aula."""
    try:
        slots = await _get_client().list_my_classes()
    except (AuthError, ApiError) as exc:
        raise RuntimeError(_error_text(exc)) from None
    return [asdict(s) for s in slots]


@mcp.tool()
async def agendar_aula(class_id: str, date: str, hour: str, teacher_id: str) -> str:
    """Agenda uma aula. Altera a agenda real do aluno. Confirme data, hora e professor com o usuário antes de chamar.

    Use os valores retornados por listar_horarios_disponiveis (data YYYY-MM-DD, hora HH:MM).
    Em caso de timeout, verifique com listar_minhas_aulas antes de tentar de novo.
    """
    try:
        return await _get_client().book(class_id, date, hour, teacher_id)
    except (AuthError, ApiError) as exc:
        raise RuntimeError(_error_text(exc)) from None


@mcp.tool()
async def cancelar_aula(class_id: str, date: str, hour: str, teacher_id: str) -> str:
    """Cancela uma aula agendada. Altera a agenda real do aluno. Confirme data, hora e professor com o usuário antes de chamar.

    Use os valores retornados por listar_minhas_aulas (data YYYY-MM-DD, hora HH:MM).
    Em caso de timeout, verifique com listar_minhas_aulas antes de tentar de novo.
    """
    try:
        return await _get_client().cancel(class_id, date, hour, teacher_id)
    except (AuthError, ApiError) as exc:
        raise RuntimeError(_error_text(exc)) from None


def main() -> None:
    _get_client()  # falha cedo se faltarem variáveis de ambiente
    mcp.run()


if __name__ == "__main__":
    main()
