"""Servidor MCP (stdio) para o site de agendamento Times Connected."""
import os
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from connected_mcp.client import DEFAULT_BASE, ApiError, AuthError, ConnectedClient

INSTRUCTIONS = """\
Agenda de aulas de inglês do usuário na escola Times Idiomas, pela plataforma
Times Connected (timesconnected.com.br).

Use estas ferramentas sempre que o usuário falar das aulas de inglês dele, da
escola de inglês, de "Times", "Times Idiomas" ou "Connected": horários livres,
aulas da semana, próxima aula, marcar/agendar, desmarcar/cancelar. "Times"
aqui é a escola de inglês, não o Microsoft Teams nem o Google Calendar.

Tipos de aula: Lesson (aula regular do livro), Conversation (Insight e
Know-how), Song Class, Movie Class e Special Class.

Para "essa semana", "amanhã" etc., converta para datas YYYY-MM-DD a partir da
data de hoje e chame listar_horarios_disponiveis. Os horários com booked=true
são as aulas que o aluno já marcou. Antes de agendar ou cancelar, confirme
dia, hora, tipo de aula e professor com o usuário.
"""

mcp = FastMCP("connected", instructions=INSTRUCTIONS)

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
    """Lista as aulas de inglês disponíveis na Times Idiomas (Times Connected) num período.

    Use para perguntas como "quais aulas de inglês tem essa semana?", "tem aula
    amanhã à noite?" ou "quais aulas eu marquei?" (filtre booked=true).
    Inclui todos os tipos: Lesson, Conversation, Song Class, Movie Class, Special Class.
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
    """Retorna a próxima aula de inglês agendada do aluno na Times Idiomas (Times Connected).

    A API expõe apenas a próxima aula; para ver todas as aulas marcadas num período,
    use listar_horarios_disponiveis e filtre booked=true. Útil para cancelar_aula."""
    try:
        slots = await _get_client().list_my_classes()
    except (AuthError, ApiError) as exc:
        raise RuntimeError(_error_text(exc)) from None
    return [asdict(s) for s in slots]


@mcp.tool()
async def agendar_aula(class_id: str, date: str, hour: str, teacher_id: str) -> str:
    """Agenda (marca) uma aula de inglês na Times Idiomas (Times Connected). Altera a agenda real do aluno. Confirme data, hora e professor com o usuário antes de chamar.

    Use os valores retornados por listar_horarios_disponiveis (data YYYY-MM-DD, hora HH:MM).
    Em caso de timeout, verifique com listar_minhas_aulas antes de tentar de novo.
    """
    try:
        return await _get_client().book(class_id, date, hour, teacher_id)
    except (AuthError, ApiError) as exc:
        raise RuntimeError(_error_text(exc)) from None


@mcp.tool()
async def cancelar_aula(class_id: str, date: str, hour: str, teacher_id: str) -> str:
    """Cancela (desmarca) uma aula de inglês agendada na Times Idiomas (Times Connected). Altera a agenda real do aluno. Confirme data, hora e professor com o usuário antes de chamar.

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
