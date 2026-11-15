# Desenvolvimento

## Ambiente

```bash
uv sync          # instala dependências, incluindo as de desenvolvimento
uv run pytest    # roda a suíte
```

Os testes não acessam a rede: as chamadas HTTP são simuladas com [respx](https://lundberg.github.io/respx/) e os testes assíncronos usam `pytest-asyncio` (`asyncio_mode = auto`).

## Estrutura

```
connected_mcp/
  client.py      # ConnectedClient, Slot, AuthError, ApiError
  server.py      # ferramentas FastMCP e main()
scripts/
  discover.py    # descoberta da API real, somente leitura
tests/
  fixtures/      # respostas reais sanitizadas
  test_client_auth.py
  test_client_ops.py
  test_server.py
docs/
```

## Fixtures e o script de descoberta

`scripts/discover.py` faz apenas chamadas de leitura (login, próxima aula, horários, tipos de aula permitidos) e grava as respostas em `tests/fixtures/`. Antes de gravar, ele:

- substitui por `<redacted>` os valores de chaves como token, password, email, cpf, phone, name, link e meet_password;
- remove qualquer string com cara de JWT (`eyJ...`).

```bash
CONNECTED_USER=<login> CONNECTED_PASSWORD=<senha> uv run python scripts/discover.py
```

**Revise as fixtures antes de commitar.** Ids numéricos (aluno, agendamento) não são removidos automaticamente; troque-os por valores fictícios.

## Testando contra a API real

Não há testes automáticos de escrita contra a API real. Para validar agendamento e cancelamento, use o cliente diretamente com a sua conta, num horário que você possa cancelar:

```python
import asyncio, os
from connected_mcp.client import ConnectedClient

async def main():
    c = ConnectedClient(os.environ["CONNECTED_USER"], os.environ["CONNECTED_PASSWORD"])
    for s in await c.list_available("2026-11-17", "2026-11-17"):
        print(s)
    await c.aclose()

asyncio.run(main())
```

## Quando a API mudar

1. Rode `scripts/discover.py` para ver o formato atual das respostas.
2. Atualize [api.md](api.md) e as fixtures.
3. Escreva primeiro um teste que reproduza o novo formato e só então ajuste `client.py`.

## Histórico de design

A especificação e o plano originais estão em `docs/superpowers/`.
