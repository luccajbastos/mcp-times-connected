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

- Claude Desktop ou Claude Code
- [uv](https://docs.astral.sh/uv/)
- Uma conta de aluno no Times Connected

## Instalação no Claude Desktop

São 4 passos, cerca de 5 minutos. Você não precisa baixar este repositório: o Claude Desktop busca o código direto do GitHub.

### Passo 1: instale o uv (uma vez só)

O servidor é escrito em Python e roda pelo [uv](https://docs.astral.sh/uv/), que baixa o Python e as dependências sozinho.

**Windows:** abra o **PowerShell** (menu Iniciar → digite "PowerShell" → Enter), cole o comando abaixo e aperte Enter:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS:** abra o **Terminal**, cole o comando abaixo e aperte Enter:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Para conferir, **feche e abra o terminal de novo** e rode `uvx --version`. Se aparecer um número de versão, está pronto.

### Passo 2: abra o arquivo de configuração do Claude Desktop

No Claude Desktop, abra **Settings → Developer → Edit Config**. Isso mostra o arquivo `claude_desktop_config.json` na pasta dele. Abra esse arquivo com o Bloco de Notas (Windows) ou o TextEdit (macOS).

Se não encontrar o menu, o arquivo fica em:

| Sistema | Caminho |
|---|---|
| Windows (instalado do site) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Windows (Microsoft Store) | `%LOCALAPPDATA%\Claude-Data\<pasta-do-claude>\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

### Passo 3: adicione o servidor

Troque `SEU_LOGIN` e `SUA_SENHA` pelo login e pela senha que você usa no site do Times Connected.

**Se o arquivo estiver vazio ou não existir**, deixe ele exatamente assim:

```json
{
  "mcpServers": {
    "times-connected": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/luccajbastos/mcp-times-connected", "connected-mcp"],
      "env": {
        "CONNECTED_USER": "SEU_LOGIN",
        "CONNECTED_PASSWORD": "SUA_SENHA"
      }
    }
  }
}
```

**Se o arquivo já tiver conteúdo**, não apague nada. Adicione o bloco `"times-connected": { ... }` dentro de `"mcpServers"`, ou crie a chave `"mcpServers"` no nível principal, separando do conteúdo anterior com vírgula. Se quiser conferir se o JSON ficou válido, cole o conteúdo em [jsonlint.com](https://jsonlint.com).

Salve o arquivo.

### Passo 4: reinicie o Claude Desktop por completo

Fechar a janela não basta, porque o Claude continua rodando em segundo plano.

- **Windows:** na barra de tarefas, clique na setinha **^** perto do relógio, clique com o **botão direito** no ícone do Claude e escolha **Quit**. Depois abra o Claude pelo menu Iniciar.
- **macOS:** com o Claude em primeiro plano, aperte **Cmd+Q**. Depois abra o Claude de novo.

### Pronto: teste

Abra uma **conversa nova** e pergunte:

> Quais aulas tem na Times Connected na quinta-feira?

Acima da resposta deve aparecer **"Used Times-connected"**. Na primeira vez, a resposta pode levar alguns segundos, enquanto o uv baixa o código.

### Se não funcionar

| Sintoma | O que fazer |
|---|---|
| O Claude não usa a ferramenta e fala de Microsoft Teams ou do seu calendário | O servidor não carregou. Confira se o JSON do passo 3 está válido e se você reiniciou com **Quit** (passo 4). |
| O log mostra `spawn uvx ENOENT` | O Desktop não achou o `uvx`. Em `"command"`, troque `"uvx"` pelo caminho completo: no Windows, `C:\\Users\\<seu-usuario>\\.local\\bin\\uvx.exe`; no macOS, rode `which uvx` no Terminal e use o resultado. |
| Erro de login | Confira `CONNECTED_USER` e `CONNECTED_PASSWORD`. Teste o mesmo login e a mesma senha no site. |

O log do servidor fica na pasta de logs do Claude, no arquivo `mcp-server-times-connected.log`:
- **Windows:** `%LOCALAPPDATA%\Claude\logs\` (ou `%APPDATA%\Claude\logs\`, conforme a instalação)
- **macOS:** `~/Library/Logs/Claude/`

> **Não use o menu Plugins do Desktop para este projeto.** O Desktop não aceita os campos de login e senha do plugin e descarta o servidor. Use a configuração acima.

## Instalação no Claude Code

Com o uv instalado (passo 1 acima), rode no Claude Code:

```
/plugin marketplace add luccajbastos/mcp-times-connected
/plugin install times-connected@mcp-times-connected
```

O Claude Code pede o login e a senha, e a senha fica no cofre de credenciais do sistema. Reinicie o Claude Code e confira com `/mcp`. Para trocar a senha depois, use `/plugin configure times-connected@mcp-times-connected`.

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `CONNECTED_USER` | sim | Login do aluno (o mesmo do site) |
| `CONNECTED_PASSWORD` | sim | Senha do aluno |
| `CONNECTED_API_BASE` | não | URL base alternativa da API |

O servidor não grava nada em disco, e o token de sessão fica só na memória. Na configuração do Claude Desktop, a senha fica em texto puro no `claude_desktop_config.json`; não compartilhe esse arquivo.

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
