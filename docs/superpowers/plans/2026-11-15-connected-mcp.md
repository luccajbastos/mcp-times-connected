# Connected MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Servidor MCP local (Python) que lista horários, lista aulas, agenda e cancela aulas no Times Connected com a conta do usuário.

**Architecture:** `ConnectedClient` (httpx, sem MCP) fala com a API REST `controllercore.timescontroller.com.br`; `server.py` expõe 4 ferramentas FastMCP que delegam ao cliente. Credenciais via env vars; token só em memória.

**Tech Stack:** Python 3.12+, uv, `mcp` (FastMCP), httpx, pytest, respx.

**Spec:** `docs/superpowers/specs/2026-11-15-connected-mcp-design.md`

## Global Constraints

- Base URL padrão: `https://controllercore.timescontroller.com.br/` (override via `CONNECTED_API_BASE`).
- Credenciais: `CONNECTED_USER`, `CONNECTED_PASSWORD`. Nunca logar, imprimir, commitar ou incluir a senha/token em mensagens de erro ou fixtures.
- Timeout HTTP: 20s. Sem retry em erro de rede. Exatamente um re-login em 401.
- Nada persistido em disco em runtime.
- Ferramentas (nomes exatos): `listar_horarios_disponiveis`, `listar_minhas_aulas`, `agendar_aula`, `cancelar_aula`.
- Nenhuma chamada de escrita (agendar/cancelar) na API real sem confirmação explícita do usuário no momento.

## Review Focus

1. Token expirado no meio da sessão → re-login transparente, uma vez (teste em Task 2).
2. Credenciais erradas → erro claro sem vazar a senha (teste em Task 2).
3. API retorna 200 com erro de negócio no corpo (ex.: `success:false`/`message`) → tratar como erro, não sucesso (teste em Task 3; formato real confirmado na Task 1).
4. Timeout de rede durante `agendar_aula` → erro claro e nenhuma repetição da chamada (teste em Task 3).
5. Listagem vazia (sem aulas/horários) → lista vazia, não exceção (teste em Task 3).

---

### Task 1: Scaffold + descoberta da API real (somente leitura)

**Files:**
- Create: `pyproject.toml` (pacote `connected_mcp`, script `connected-mcp = "connected_mcp.server:main"`, deps `mcp`, `httpx`; dev `pytest`, `respx`)
- Create: `connected_mcp/__init__.py`
- Create: `scripts/discover.py`
- Create: `tests/fixtures/*.json` (respostas sanitizadas)
- Create: `docs/api-notes.md`

**Interfaces:**
- Produces: fixtures `login.json`, `next_classes.json`, `day_by_day.json`; `docs/api-notes.md` registrando: header de auth, caminho do token e do `student_id` na resposta de login, formato de `date`/`hour`, valores válidos de `typeClass`, formato de erro, campos de cada item das listagens.

- [ ] **Step 1:** `uv init`/`pyproject.toml` e `uv sync`; verificar com `uv run python -c "import mcp, httpx"` (sem erro).
- [ ] **Step 2:** Escrever `scripts/discover.py`: lê credenciais das env vars, faz `POST api/auth/student-login`, `GET api/next-classes`, `POST api/class-type/day-by-day-new` (hoje → +7 dias); grava respostas em `tests/fixtures/` substituindo token, e-mail, CPF, telefone e nomes por placeholders. Nunca chama `student-history`.
- [ ] **Step 3:** Pedir ao usuário para rodar com as credenciais (`! $env:CONNECTED_USER=...; $env:CONNECTED_PASSWORD=...; uv run python scripts/discover.py`). Se `typeClass` exigir valor, testar os candidatos do código (`get-allowed-classes-by-student`).
- [ ] **Step 4:** Inspecionar fixtures (`grep` por token/senha deve retornar vazio) e escrever `docs/api-notes.md`. **Se algum endpoint divergir da spec, parar e reportar ao usuário.**
- [ ] **Step 5:** Commit `chore: scaffold e notas da API`.

### Task 2: `ConnectedClient` — autenticação

**Files:**
- Create: `connected_mcp/client.py`
- Test: `tests/test_client_auth.py`

**Interfaces:**
- Consumes: `docs/api-notes.md`, `tests/fixtures/login.json`.
- Produces: `class AuthError(Exception)`, `class ApiError(Exception)` (atributo `message: str`); `ConnectedClient(user: str, password: str, base_url: str = DEFAULT_BASE, timeout: float = 20.0)`; `async login() -> None`; `async _request(method: str, path: str, json: dict | None = None) -> Any` (adiciona auth, faz login preguiçoso, re-login 1x em 401, converte erros); atributo `student_id: str`.

- [ ] **Step 1:** Testes (respx):
  - `test_login_stores_token_and_student_id` — após `login()`, `client.student_id` = valor da fixture e próxima requisição leva o header de auth.
  - `test_lazy_login_on_first_request` — `_request` sem login prévio chama login uma vez.
  - `test_relogin_once_on_401` — 1ª chamada 401, 2ª 200 → retorna dados; login chamado 2x no total.
  - `test_second_401_raises_auth_error` — 401 duas vezes → `AuthError`.
  - `test_bad_credentials_message_has_no_password` — login falha → `AuthError` cuja `str()` cita `CONNECTED_USER` e não contém a senha.
  - `test_network_timeout_raises_api_error_without_retry` — `httpx.TimeoutException` → `ApiError`, rota chamada exatamente 1x.
- [ ] **Step 2:** `uv run pytest tests/test_client_auth.py -v` → FAIL (import error).
- [ ] **Step 3:** Implementar conforme Interfaces, com `httpx.AsyncClient`.
- [ ] **Step 4:** `uv run pytest tests/test_client_auth.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: autenticação do ConnectedClient`.

### Task 3: `ConnectedClient` — operações e normalização

**Files:**
- Modify: `connected_mcp/client.py`
- Test: `tests/test_client_ops.py`

**Interfaces:**
- Consumes: `_request`, `student_id`, `ApiError` (Task 2); fixtures da Task 1.
- Produces: `@dataclass Slot(class_id: str, date: str, hour: str, teacher_id: str, teacher_name: str | None, class_type: str | None)`; `async list_available(begin_date: str, end_date: str, class_type: str | None = None) -> list[Slot]`; `async list_my_classes() -> list[Slot]`; `async book(class_id, date, hour, teacher_id) -> str` (mensagem da API); `async cancel(class_id, date, hour, teacher_id) -> str`. Datas de entrada em `YYYY-MM-DD`; conversão para o formato da API (api-notes) fica no cliente.

- [ ] **Step 1:** Testes:
  - `test_list_available_parses_fixture` — `day_by_day.json` → lista de `Slot` com os campos da 1ª entrada iguais aos da fixture; corpo enviado tem `beginDate`, `endDate`, `studentId`, `typeClass`.
  - `test_list_my_classes_parses_fixture` — idem com `next_classes.json`.
  - `test_empty_lists_return_empty` — respostas vazias → `[]`.
  - `test_book_posts_expected_body` — `POST api/student-history` com `{classId, date, hour, teacherId, studentId}`.
  - `test_cancel_calls_custom_destroy` — método conforme api-notes (DELETE por padrão) em `api/student-history/custom-destroy` com o mesmo corpo.
  - `test_business_error_in_200_raises_api_error` — corpo de erro no formato de api-notes → `ApiError` com a mensagem da API.
- [ ] **Step 2:** `uv run pytest tests/test_client_ops.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → todos PASS.
- [ ] **Step 5:** Commit `feat: operações de aulas no ConnectedClient`.

### Task 4: Servidor MCP + configuração

**Files:**
- Create: `connected_mcp/server.py`
- Create: `README.md` (instalação, entrada do `.claude.json`)
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `ConnectedClient`, `Slot`, `AuthError`, `ApiError`.
- Produces: `mcp = FastMCP("connected")`; ferramentas `listar_horarios_disponiveis(data_inicio: str, data_fim: str, tipo_aula: str | None = None) -> list[dict]`, `listar_minhas_aulas() -> list[dict]`, `agendar_aula(class_id: str, date: str, hour: str, teacher_id: str) -> str`, `cancelar_aula(...) -> str`; `main()` lê env vars e roda stdio. Erros do cliente viram mensagem de erro da ferramenta (texto da exceção). Descrições de `agendar_aula`/`cancelar_aula` contêm: "Altera a agenda real do aluno. Confirme data, hora e professor com o usuário antes de chamar."

- [ ] **Step 1:** Testes (cliente fake injetado):
  - `test_tools_registered` — os 4 nomes exatos estão registrados.
  - `test_list_tool_returns_dicts_with_ids` — itens têm `class_id`, `date`, `hour`, `teacher_id`.
  - `test_write_tools_description_requires_confirmation` — descrições contêm "Confirme".
  - `test_missing_env_vars_fails_clearly` — `main()` sem env → erro citando `CONNECTED_USER`.
- [ ] **Step 2:** `uv run pytest tests/test_server.py -v` → FAIL.
- [ ] **Step 3:** Implementar; README com:
  ```json
  "connected": {"command": "uv", "args": ["run", "--directory", "<caminho-do-projeto>", "connected-mcp"],
                "env": {"CONNECTED_USER": "...", "CONNECTED_PASSWORD": "..."}}
  ```
- [ ] **Step 4:** `uv run pytest -v` → PASS; `npx @modelcontextprotocol/inspector` opcional para listar as tools.
- [ ] **Step 5:** Commit `feat: servidor MCP do Connected`.

### Task 5: Validação real com o usuário

- [ ] **Step 1:** Usuário adiciona a entrada ao `.claude.json` (credenciais preenchidas por ele) e reinicia o Claude Code; `/mcp` mostra `connected` conectado.
- [ ] **Step 2:** Chamar `listar_minhas_aulas` e `listar_horarios_disponiveis` (próximos 7 dias) e conferir com o site.
- [ ] **Step 3:** Com confirmação explícita do usuário, agendar um horário escolhido por ele; conferir no site.
- [ ] **Step 4:** Cancelar esse mesmo agendamento; conferir no site. Se o método de cancelamento falhar, ajustar (Task 3) com teste e repetir.
- [ ] **Step 5:** Commit de ajustes, se houver.
