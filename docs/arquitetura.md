# Arquitetura

```
Cliente MCP (Claude) ──stdio──> server.py (FastMCP) ──> client.py (httpx) ──HTTPS──> API Times Connected
```

## Componentes

### `connected_mcp/client.py`: `ConnectedClient`

Cliente HTTP assíncrono, sem nenhuma dependência de MCP. Pode ser usado sozinho em scripts.

- **Autenticação:** faz login na primeira chamada (`POST api/auth/student-login`) e guarda o token e o `studentId` só na memória. Se a API responder 401, refaz o login **uma vez** e repete a chamada.
- **Cabeçalhos:** toda requisição envia `Accept: application/json` (sem ele a API redireciona com 302) e `Authorization: Bearer <token>`.
- **Operações:** `list_available`, `list_my_classes`, `book` e `cancel`. As listagens são convertidas em `Slot` (dataclass).
- **Erros:** `AuthError` para problemas de login e `ApiError` para todo o resto: HTTP fora de 2xx (com a mensagem da API), erro de negócio num 2xx (`status: error` ou `success: false`), rede e tempo esgotado.
- **Timeout:** 20 s, sem retentativa.

### `connected_mcp/server.py`: servidor MCP

Usa FastMCP (`mcp` 1.x), transporte stdio. Cada ferramenta é uma função fina que:

1. obtém o cliente, criado sob demanda a partir das variáveis de ambiente;
2. chama a operação correspondente;
3. converte `Slot` em dicionário, ou `AuthError`/`ApiError` em erro da ferramenta com o texto da mensagem.

`main()` valida as variáveis de ambiente antes de iniciar, para falhar cedo.

## Decisões

- **API direta em vez de automação de navegador:** mais rápido e leve, sem depender do layout do site. Em troca, mudanças na API exigem ajuste no cliente.
- **Sem persistência:** nada é gravado em disco; o token vive enquanto o processo do servidor estiver rodando.
- **Sem retentativas em escrita:** um timeout ao agendar pode ter sido processado pelo servidor; repetir poderia gerar agendamento duplicado.
- **Confirmação antes de escrever:** as descrições de `agendar_aula` e `cancelar_aula` instruem o modelo a confirmar com o usuário. O cliente MCP também costuma pedir permissão a cada chamada.
