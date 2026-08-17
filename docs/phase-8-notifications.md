# Fase 8: workflow notificador de resultados

## Recursos n8n

- Workflow: `Script Phase 8 Notifier`
- Workflow ID: `16cYVCoO48LxBxl4`
- URL: https://n8n.adalgarcia.com/workflow/16cYVCoO48LxBxl4
- Data Table: `script_job_launches`
- Data Table ID: `9YfdvJehSSUf9iK2`
- Credencial del canal: `Telegram account` (id `Z3r0YRo0ftwFvRYO`, tipo `telegramApi`)
- Chat de destino: `744884859` (chat privado del operador `Aodaru`, bot `TeaPartyDev_bot`)
- Estado: **activo con canal Telegram publicado** desde el 2026-08-17 (ver "Cambio posterior: canal Gmail → Telegram")

## Columnas nuevas en la Data Table

Añadidas en esta fase para marcar la notificación y evitar duplicados:

| Columna | Tipo | Uso |
|---|---|---|
| `last_notified_at` | date | Timestamp UTC de la última notificación; `null` mientras no se haya notificado |
| `notified_result` | string | Tipo de notificación enviado (`success`, `token_expired`, `permission_denied`, `timeout`, `error`), para auditoría |

## Flujo

1. **Schedule Trigger** (`Every 5 Minutes`, cada 5 minutos, configurable a 1 minuto en el nodo). Timezone del workflow: `UTC`.
2. **Data Table Get Rows** consulta `script_job_launches` con `returnAll: true` y filtro equivalente a *estado terminal Y `last_notified_at IS NULL`*. El nodo Data Table no expone operadores `IN` ni `isNull`, así que el filtro se expresa como `state != starting`, `state != running`, `state != cancelled`, `state != launch_failed` **y** `last_notified_at isEmpty` (AND). Para el dominio de estados definido (contrato Fase 1 + `launch_failed` de Fase 6) esto selecciona exactamente `success`, `failed` y `timeout` sin notificar. Si no hay filas, la cadena termina sin error.
3. **Classify Result** (Code, `runOnceForEachItem`) clasifica cada fila en uno de 5 tipos y construye el mensaje:
   - `state=success` → `success` (permiso disponible / solicitud completada).
   - `state=failed` y `result`/`error` contienen `token_expired` o `100004` → `token_expired`.
   - `state=failed` y `result`/`error` contienen `request_rejected`, `permission_blocked`, `100001`, `is_pass=4`, `button_state=2/3` o `apply_result=3/4` → `permission_denied`.
   - `state=timeout` → `timeout`.
   - `state=failed` con causa desconocida o ausente → `error`. Cualquier otro estado que superara el filtro cae también en `error`.
   El mensaje incluye `job_id`, máscara del token (`****xxxx` basada en `token_fingerprint`), tipo, estado, `exit_code`, `finished_at`, `timeout_at`, resultado y error redactados. El nodo redacta por defensa cualquier cadena larga tipo base64 (`[A-Za-z0-9+/]{40,}={0,2}` → `[REDACTED]`) y descarta filas ya notificadas (`last_notified_at` con valor) como defensa adicional anti-duplicados.
4. **Send a text message** (Telegram, `message/sendMessage`, credencial `Telegram account` → bot `TeaPartyDev_bot`) envía el `body` del paso anterior en texto plano (`parse_mode: none`) al chat `744884859` del operador. Nodo de salida **aislado**: no contiene lógica de negocio y es reemplazable sin tocar los pasos 1-3 ni el 5. Configuración de tolerancia: `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput` para que un fallo del canal no bloquee el resto de trabajos.
5. **Data Table Update Row** actualiza la fila por `job_id` escribiendo **solo** `last_notified_at` (timestamp UTC) y `notified_result` (el tipo clasificado) — únicamente estos dos campos (restaurado el 2026-08-17 tras el review: las escrituras `token_slot/timeshift/exit_code/check_count = 0` que viajaban en un autosave se eliminaron para no resetear `exit_code`/`check_count` de filas terminales reales, contrato Fase 1). Tras esto, la fila deja de cumplir el filtro `isEmpty` y no vuelve a seleccionarse.

Nunca se envían tokens completos: el flujo solo maneja `token_fingerprint` (huella SHA-256 ya almacenada en Fase 6), muestra una máscara `****xxxx` y redacta cualquier cadena tipo token que apareciera en `result`/`error`.

## Configuración requerida

1. La credencial `Telegram account` (`telegramApi`, id `Z3r0YRo0ftwFvRYO`) está asociada al nodo `Send a text message`.
2. `chatId` configurado: `744884859` (chat privado del operador `Aodaru`, el mismo chat que usan los workflows operativos activos `Brute Force - Reporte Diario` y `AsisVirtual Telegram Bot`).
3. `text` = `={{ $json.body }}` (mensaje completo redactado generado por `Classify Result`).
4. `parse_mode: none`: sin esto, el parse mode por defecto (Markdown) degradaba la máscara `****b855` → `b855` y `timeout_at` → `timeoutat` en el mensaje enviado.
5. Publicado y **activo** el 2026-08-17 tras probar un ciclo con fila terminal sintética (envíos reales de prueba, ver tabla de pruebas).
6. Validación pendiente de un ciclo real contra una fila terminal del launcher (requiere que exista tal fila en producción).

## Divergencias respecto a las decisiones de la spec

| Spec | Realidad implementada | Motivo |
|---|---|---|
| `token_hash` (D5) | La columna real se llama `token_fingerprint` | La columna se creó así en Fase 6; el workflow usa `token_fingerprint` siempre. |
| Canal email SMTP (D1) | Canal Telegram (`n8n-nodes-base.telegram` message/sendMessage; credencial `Telegram account` `Z3r0YRo0ftwFvRYO` → bot `TeaPartyDev_bot`; chat `744884859`) | No existe credencial SMTP en la instancia; el 2026-08-17 el canal Gmail OAuth2 se sustituyó por Telegram (ver "Cambio posterior"), el canal donde el operador ya recibe las notificaciones operativas. El nodo de salida queda aislado y reemplazable, respetando la intención de D1. |
| Filtro `state IN (...) AND last_notified_at IS NULL` (criterio 2.1) | Filtro equivalente con `neq` por estado no terminal + `last_notified_at isEmpty` | El nodo Data Table v1.1 no expone operadores `IN` ni `isNull`; para el dominio de estados actual el filtro es funcionalmente idéntico. |
| `sendTo` / destinatario email | `chatId` = `744884859` (chat privado del operador `Aodaru`) | El destinatario del operador no está definido en ninguna spec; se resolvió por evidencia de los workflows Telegram activos existentes en la instancia (mismo chat usado por `Brute Force - Reporte Diario` y `AsisVirtual Telegram Bot`). |

## Pruebas realizadas (pin data, nodos Data Table reales)

Metodología: `prepare_test_pin_data` + `test_workflow`. Se pinnearon Schedule Trigger y `Data Table Get Rows` con filas sintéticas terminales (excepto donde se indica). `Classify Result`, `Data Table Update Row` y el nodo de canal ejecutaron de verdad (los tests 1-8 corresponden al canal Gmail, con el nodo Gmail pineado; los tests 9-10 corresponden al canal Telegram con envío real).

| Test | Escenario | Ejecución | Resultado |
|---|---|---|---|
| 1 | Job `success` → notificación tipo `success` | 8206 | `notification_type=success`, body con `****b855`, Update Row OK |
| 2 | Job `failed` + `token_expired`/`100004` → `token_expired` | 8207 | `notification_type=token_expired` |
| 3 | Job `failed` + `request_rejected`/`permission_blocked` → `permission_denied` | 8208 | `notification_type=permission_denied` |
| 4 | Job `timeout` → `timeout` | 8209 | `notification_type=timeout` |
| 5 | Job `failed` causa desconocida → `error` | 8210 | `notification_type=error` |
| 6 | Fila ya con `last_notified_at` → no se re-notifica | 8211 | Code descarta (0 salidas), Gmail/Update no ejecutan |
| 7 | Token largo en `result`/`error` → redactado | 8212 | `[REDACTED]` en cuerpo y campos; token completo ausente |
| 8 | Sin trabajos pendientes (Get Rows `[]`) | 8213 | Workflow `success`, sin envíos ni actualizaciones |
| — | Get Rows real contra tabla viva | 8215 | Filtro real devuelve 0 filas (las filas heredadas de Fase 6/7 están `running` y quedan excluidas); flujo termina sin error |
| 9 | Canal Telegram: fila `success` sintética con envío REAL (nodo Telegram sin pinear) | 8299 | Mensaje entregado por `TeaPartyDev_bot` al chat `744884859` (message_id 489, `ok: true`). Hallazgo: el parse mode por defecto degradaba `****b855` → `b855` y `timeout_at` → `timeoutat` |
| 10 | Canal Telegram con `parse_mode: none` (envío REAL) | 8301 | Mensaje en texto plano (message_id 490): `Token: ****b855`, `timeout_at` e `is_pass=1` intactos. Flujo completo `success` y Update Row OK |

En todos los tests el nodo `Data Table Update Row` ejecutó con `success` (con `job_id` sintéticos no matcheó filas reales, por lo que no escribió nada: comportamiento esperado en sandbox).

## Pruebas pendientes

- ~~Envío real del email Gmail~~ → superado: el canal ahora es Telegram y se validó con envíos reales (ejecuciones 8299 y 8301).
- Escritura real de `last_notified_at`/`notified_result` contra una fila terminal real del launcher (requiere que exista tal fila).
- Verificación con datos reales de que la fila notificada no se vuelve a seleccionar en el siguiente ciclo (mecanismo verificado: filtro `isEmpty` + defensa en Code).
- Ciclo completo integrado (launcher → monitor → notifier) con el contenedor real (Fase 9).

## Cambio posterior: canal Gmail → Telegram

- **Fecha**: 2026-08-17
- **Motivo**: el operador recibe sus notificaciones operativas por Telegram (chat privado `744884859`, bot `TeaPartyDev_bot` vía la credencial `Telegram account`); Gmail no es el canal de contacto habitual. Se sustituye el nodo `Send Email Notification` (Gmail OAuth2, `eN5CQPJBOkcyRCuw`) por el nodo `Send a text message` (`n8n-nodes-base.telegram` 1.2), que ya existía conectado en el draft sin configurar.
- **Cambios aplicados** (workflow `16cYVCoO48LxBxl4`, sin recrear el workflow ni tocar los pasos 1-3/5):
  - `chatId` = `744884859` (valor real de la instancia; los workflows activos `Brute Force - Reporte Diario` y `AsisVirtual Telegram Bot` envían a ese mismo chat).
  - `text` = `={{ $json.body }}` (el `body` ya redactado de `Classify Result`).
  - `additionalFields.parse_mode` = `none` (texto plano; el parse mode por defecto eliminaba `_`/`*` del mensaje, degradando la máscara del token).
  - Credencial `Telegram account` (`Z3r0YRo0ftwFvRYO`, tipo `telegramApi`).
  - Tolerancia: `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput` (criterio 6, intacto).
  - Eliminado el nodo huérfano `Send Email Notification` (sin conexiones en el draft).
- **Publicación**: el workflow, que ya estaba **activo**, se republicó con la versión `ef4c9be2-4d7b-41c4-b681-b74809419260`; el canal Telegram quedó efectivo sin cambios de settings globales (timezone UTC, `executionOrder v1`, `executionTimeout 600` intactos).
- **Prueba real**: ejecución 8299 (envío real, message_id 489) confirmó credencial y `chatId`; la 8301 confirmó el mensaje en texto plano con la máscara intacta.
- El token completo nunca aparece en el mensaje: el `body` solo usa `token_mask` (`****xxxx`) y redacta cadenas largas (verificado en las ejecuciones 8299/8301).