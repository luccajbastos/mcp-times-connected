# Connected MCP — Design

Data: 2026-11-15

## Objetivo

Servidor MCP local, de uso pessoal (uma conta), para que o Claude liste horários, liste aulas agendadas, agende e cancele aulas no Times Connected (https://timesconnected.com.br) via linguagem natural.

**Sucesso:** pedir "agende minha aula de quinta às 19h" ou "cancele a aula de amanhã" no Claude Code/Desktop e a ação ser executada na conta real, com confirmação prévia.

**Fora de escopo:** múltiplas contas, automação recorrente, créditos/histórico/financeiro, automação de navegador.

## Abordagem

Chamar diretamente a API REST usada pelo app web (Flutter). Endpoints extraídos de `main.dart.js`.

Base: `https://controllercore.timescontroller.com.br/`

| Função | Método | Path | Corpo |
|---|---|---|---|
| Login | POST | `api/auth/student-login` | `{user, password}` |
| Horários disponíveis | POST | `api/class-type/day-by-day-new` | `{beginDate, endDate, studentId, typeClass}` |
| Minhas aulas | GET | `api/next-classes` | — |
| Agendar | POST | `api/student-history` | `{classId, date, hour, teacherId, studentId}` |
| Cancelar | DELETE (a confirmar) | `api/student-history/custom-destroy` | `{classId, date, hour, teacherId, studentId}` |

`student_id` vem de `data.student_id` na resposta do login.

**Hipóteses a validar no primeiro passo:** formato das respostas, formato do token/header `Authorization` (provavelmente `Bearer`), formato de `date`/`hour`, valores de `typeClass`, método HTTP do cancelamento.

## Stack

Python 3.12+, `uv`, FastMCP (`mcp` SDK oficial), `httpx`, `pytest` + `respx`. Transporte stdio.

## Componentes

### `connected_mcp/client.py` — `ConnectedClient`
Cliente HTTP sem conhecimento de MCP.
- Lê credenciais do construtor (o servidor passa as env vars).
- `login()`: obtém token e `student_id`, guarda em memória.
- Login preguiçoso na primeira chamada; em 401 refaz login uma vez e repete a chamada.
- Métodos: `list_available(begin_date, end_date, class_type)`, `list_my_classes()`, `book(class_id, date, hour, teacher_id)`, `cancel(class_id, date, hour, teacher_id)`.
- Timeout 20s; sem retry em erros de rede.
- Exceções: `AuthError`, `ApiError(message)`.

### `connected_mcp/server.py` — ferramentas FastMCP
- `listar_horarios_disponiveis(data_inicio, data_fim, tipo_aula?)`
- `listar_minhas_aulas()`
- `agendar_aula(class_id, date, hour, teacher_id)`
- `cancelar_aula(class_id, date, hour, teacher_id)`

As listagens retornam itens normalizados contendo `class_id`, `date`, `hour`, `teacher_id` (mais nome do professor/tipo de aula quando disponível), permitindo ao Claude encadear listar → agendar/cancelar. Descrições de `agendar_aula` e `cancelar_aula` instruem o Claude a confirmar com o usuário antes de chamar.

### Configuração
Env vars `CONNECTED_USER`, `CONNECTED_PASSWORD` (e opcional `CONNECTED_API_BASE`) na entrada `connected` do `.claude.json`, executando `uv run --directory <projeto> connected-mcp`.

## Tratamento de erros
- Falha de login → mensagem pedindo para conferir as credenciais; nunca expõe a senha.
- 401 → um re-login; se falhar de novo, erro.
- Erro de negócio da API → repassa a mensagem da API ao Claude.
- Rede/timeout → mensagem clara, sem retry (evita agendamento duplicado).
- Nada persistido em disco.

## Testes
1. **Script de descoberta (somente leitura)** com credenciais reais: login, `next-classes`, `day-by-day-new`; salva respostas (sem token) para servirem de fixtures.
2. **Unitários** (pytest + respx) com a API mockada: login, re-login em 401, corpos das requisições, mapeamento de erros, normalização das listagens.
3. **Validação manual de escrita** com o usuário: agendar um horário escolhido e cancelá-lo, confirmando o método do cancelamento.
