# Ferramentas

O servidor expõe quatro ferramentas MCP. Datas usam o formato `YYYY-MM-DD` e horas, `HH:MM`.

## Slot

As duas ferramentas de listagem devolvem uma lista de objetos com estes campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `class_id` | string | Id do tipo de aula (ex.: `19` = Lesson 18, `41` = Song Class) |
| `date` | string | Data da aula |
| `hour` | string | Hora de início |
| `teacher_id` | string | Id do professor |
| `teacher_name` | string ou null | Apelido do professor |
| `class_type` | string ou null | Nome do tipo de aula |
| `booked` | bool ou null | `true` se você já está inscrito nesse horário; `null` quando a API não informa |

Os campos `class_id`, `date`, `hour` e `teacher_id` são exatamente os que `agendar_aula` e `cancelar_aula` recebem.

## listar_horarios_disponiveis

```
listar_horarios_disponiveis(data_inicio, data_fim, tipo_aula=None) -> list[Slot]
```

Lista os horários do intervalo, com um item por combinação de data, hora e professor. A lista inclui todos os tipos de aula liberados para o aluno (Lessons, Conversations, Song Class, Movie Class etc.).

Como `listar_minhas_aulas` mostra só a próxima aula, filtre esta lista por `booked == true` para ver todas as aulas agendadas no período.

## listar_minhas_aulas

```
listar_minhas_aulas() -> list[Slot]
```

Devolve a **próxima** aula agendada (lista com um item) ou uma lista vazia. A API não expõe as demais aulas por este endpoint.

## agendar_aula

```
agendar_aula(class_id, date, hour, teacher_id) -> str
```

Agenda a aula e devolve a mensagem da API (ex.: "Aula agendada com sucesso."). A descrição da ferramenta pede ao Claude que confirme data, hora e professor com você antes de chamá-la.

## cancelar_aula

```
cancelar_aula(class_id, date, hour, teacher_id) -> str
```

Cancela a aula e devolve "Aula cancelada com sucesso." quando a API aceita. Também pede confirmação antes.

## Erros

| Situação | Mensagem |
|---|---|
| Credenciais ausentes | O servidor não sobe e cita `CONNECTED_USER`/`CONNECTED_PASSWORD` |
| Login recusado | Pede para conferir as credenciais (a senha nunca aparece) |
| Token expirado | Login refeito automaticamente, uma vez |
| Recusa da API (lotada, prazo vencido etc.) | Status HTTP mais a mensagem da API |
| Tempo esgotado ao agendar/cancelar | Avisa que a operação **pode ter sido feita** e pede para conferir antes de repetir |

Não há retentativa automática em erros de rede, para evitar agendamentos duplicados.
