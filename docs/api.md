# API do Times Connected

> Mapeada a partir do app web (Flutter) e validada com chamadas reais em 2026-11-15. Não é documentação oficial; pode mudar sem aviso.

Base: `https://controllercore.timescontroller.com.br/`

## Requisitos gerais
- Toda requisição DEVE enviar `Accept: application/json` (sem ele o Laravel responde 302).
- Auth: `Authorization: Bearer <token>`.

## POST api/auth/student-login
Body `{"user","password"}`. Resposta plana:
`{"token": str, "studentId": int, "preClassWatched", "termsAndConditionsAccepted", "startDate", "actuallyDate", "studentContractValidity"}`.
Usar `studentId` de nível superior (enviar como string nos corpos).

## GET api/auth/student-session
Mesmo formato plano do login; renova o token (novo JWT a cada chamada).

## GET api/next-classes
Retorna apenas a PRÓXIMA aula, como objeto único em `data` (ou `null` se não houver):
`{"status":"success","data":{"id","class_id","student_id","date","hour","teacher_id","date_hour","class_name":"Lesson 18","type_class":"online","teacher":{id,name,nickname},"class_type":{id,name}}}`.
Sem aulas: `{"status":"success","data":null}`.

## POST api/student-history (agendar)
Retornou `message: "Aula agendada com sucesso."` (validado em 2026-11-15).

## GET api/student-history
A resposta não é JSON.

## GET api/student/get-allowed-classes-by-student/{studentId}
Lista de tipos de aula.

## POST api/class-type/day-by-day-new
Body: `{"beginDate":"YYYY-MM-DD","endDate":"YYYY-MM-DD","studentId":"<id>","typeClass":"1"}`.
`typeClass` "1" e "2" retornaram o mesmo. Resposta 200, lista:
```
[{"classType": {id, name, ..., duration},
  "availableClasses": [{"date": "2026-11-16", "classId": 19,
    "arrayOfClassByHourDto": [{"hour": "17:00",
      "arrayOfClassByTeacher": [{"teacher": {id, name, nickname, email, link, ...},
                                 "numberOfStudents": 0, "typeClass": "online"}]}]}]}]
```

## DELETE api/student-history/custom-destroy
Cancelamento: DELETE com corpo JSON (mesmo corpo do agendamento). Funciona
(validado em 2026-11-15: o slot ficou com `studentIn` false). O corpo da
resposta 2xx NÃO é JSON; o cliente tolera corpo vazio/não-JSON em book/cancel.

## Campo studentIn
Nas entradas de professor (`arrayOfClassByTeacher`) de day-by-day-new,
`studentIn: bool` é true quando o aluno está agendado nesse horário
(exposto como `Slot.booked`).

## Desconhecidos
- Formato de erro.

## Sanitização das fixtures
`scripts/discover.py` redige chaves token/password/email/cpf/phone/telefone/celular/name/nome/link/meet_password/meet_hash e qualquer string com aparência de JWT (`eyJ...`).
