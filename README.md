# mcp-times-connected

Servidor [MCP](https://modelcontextprotocol.io) para consultar horários, agendar e cancelar aulas no **Times Connected** ([timesconnected.com.br](https://timesconnected.com.br)), a plataforma de aulas da Times Idiomas, direto pelo Claude (Claude Code, Claude Desktop ou qualquer cliente MCP).

> Projeto pessoal e não oficial, sem vínculo com a Times Idiomas. Ele usa a mesma API que o app web chama e pode quebrar se a API mudar. Use com a sua própria conta.

## Exemplos

- "Quais aulas tem na terça entre 11h e 17h?"
- "Agenda a Song Class de terça às 14h."
- "Qual é a minha próxima aula?"
- "Cancela a aula de quinta."

O Claude lista os horários, confirma o horário e o professor com você e só então agenda ou cancela.

## Requisitos

- Python 3.11 ou superior (o uv instala automaticamente)
- [uv](https://docs.astral.sh/uv/)
- Uma conta de aluno no Times Connected

## Instalação

### 1. Instale o uv (uma vez só)

O plugin roda em Python através do [uv](https://docs.astral.sh/uv/).

Windows (PowerShell):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Instale o plugin

**Claude Desktop:** Customize → Plugins → **+ Add** → adicione o marketplace `luccajbastos/mcp-times-connected` e instale **Times Connected**.

**Claude Code:**
```
/plugin marketplace add luccajbastos/mcp-times-connected
/plugin install times-connected@mcp-times-connected
```

### 3. Informe login e senha

Ao ativar o plugin, o Claude pede o seu login e a sua senha do Times Connected. A senha fica no cofre de credenciais do sistema, nunca em arquivo. Para alterar depois, use `/plugin configure times-connected@mcp-times-connected`.

Pronto: peça ao Claude "quais aulas tem amanhã?".

## Instalação manual (sem plugin)

Para outros clientes MCP, ou se preferir configurar à mão:

```bash
git clone https://github.com/luccajbastos/mcp-times-connected.git
cd mcp-times-connected
uv sync
```

Adicione a `mcpServers` no arquivo de configuração do cliente:

```json
"connected": {
  "command": "uv",
  "args": ["run", "--directory", "<caminho-do-projeto>", "connected-mcp"],
  "env": {
    "CONNECTED_USER": "<seu-login>",
    "CONNECTED_PASSWORD": "<sua-senha>"
  }
}
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `CONNECTED_USER` | sim | Login do aluno (o mesmo do site) |
| `CONNECTED_PASSWORD` | sim | Senha do aluno |
| `CONNECTED_API_BASE` | não | URL base alternativa da API |

As credenciais ficam apenas na configuração do cliente MCP. O servidor não grava nada em disco, e o token de sessão fica só na memória.

## Ferramentas

| Ferramenta | O que faz |
|---|---|
| `listar_horarios_disponiveis` | Horários livres num intervalo de datas. O campo `booked` indica os horários em que você já está inscrito. |
| `listar_minhas_aulas` | A sua próxima aula agendada (a API só informa a próxima). |
| `agendar_aula` | Agenda uma aula. |
| `cancelar_aula` | Cancela uma aula. |

Detalhes em [docs/ferramentas.md](docs/ferramentas.md).

## Documentação

- [docs/ferramentas.md](docs/ferramentas.md): parâmetros, retornos e erros de cada ferramenta
- [docs/arquitetura.md](docs/arquitetura.md): como o servidor é organizado
- [docs/api.md](docs/api.md): a API do Times Connected, mapeada a partir do app web
- [docs/desenvolvimento.md](docs/desenvolvimento.md): testes, fixtures e como contribuir
