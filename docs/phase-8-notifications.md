# Fase 8: workflow notificador de resultados

## Recursos n8n

- Workflow: `Script Phase 8 Notifier`
- Workflow ID: `16cYVCoO48LxBxl4`
- URL: https://n8n.adalgarcia.com/workflow/16cYVCoO48LxBxl4
- Data Table: `script_job_launches`
- Data Table ID: `9YfdvJehSSUf9iK2`
- Credencial del canal: `Gmail account` (id `eN5CQPJBOkcyRCuw`, tipo `gmailOAuth2`)
- Estado inicial: **inactivo** hasta configurar el destinatario real y validar un ciclo contra datos reales.

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
4. **Send Email Notification** (Gmail, `message/send`, OAuth2) envía el mensaje en texto plano con `subject` y `body` del paso anterior. Nodo de salida **aislado**: no contiene lógica de negocio y es reemplazable por Telegram/Slack/webhook sin tocar los pasos 1-3 ni el 5. Configuración de tolerancia: `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput` para que un fallo del canal no bloquee el resto de trabajos.
5. **Data Table Update Row** actualiza la fila por `job_id` escribiendo `last_notified_at` (timestamp UTC) y `notified_result` (el tipo clasificado). Tras esto, la fila deja de cumplir el filtro `isEmpty` y no vuelve a seleccionarse.

Nunca se envían tokens completos: el flujo solo maneja `token_fingerprint` (huella SHA-256 ya almacenada en Fase 6), muestra una máscara `****xxxx` y redacta cualquier cadena tipo token que apareciera en `result`/`error`.

## Configuración requerida

1. La credencial `Gmail account` (`gmailOAuth2`) ya está asociada al nodo `Send Email Notification`.
2. Configurar el destinatario: el nodo usa por defecto `aodarug@gmail.com` (email del propietario de la cuenta Gmail). Cambiar este valor al email real del operador técnico antes de activar.
3. Ejecutar un ciclo contra una fila terminal real y comprobar que llega el email y la fila queda marcada con `last_notified_at`/`notified_result`.
4. Publicar (activar) el workflow solo después de la prueba anterior.

## Divergencias respecto a las decisiones de la spec

| Spec | Realidad implementada | Motivo |
|---|---|---|
| `token_hash` (D5) | La columna real se llama `token_fingerprint` | La columna se creó así en Fase 6; el workflow usa `token_fingerprint` siempre. |
| Canal email SMTP (D1) | Canal Gmail OAuth2 (`n8n-nodes-base.gmail` message/send) | No existe credencial SMTP en la instancia; la única credencial de email disponible es Gmail OAuth2 (`eN5CQPJBOkcyRCuw`). El nodo de salida queda aislado y reemplazable, respetando la intención de D1. |
| Filtro `state IN (...) AND last_notified_at IS NULL` (criterio 2.1) | Filtro equivalente con `neq` por estado no terminal + `last_notified_at isEmpty` | El nodo Data Table v1.1 no expone operadores `IN` ni `isNull`; para el dominio de estados actual el filtro es funcionalmente idéntico. |
| `sendTo` | Valor por defecto `aodarug@gmail.com`, configurable en el nodo | El destinatario del operador no está definido en ninguna spec; se deja explícito como configuración requerida. |

## Pruebas realizadas (pin data, nodos Data Table reales)

Metodología: `prepare_test_pin_data` + `test_workflow`. Se pinnearon Schedule Trigger y el nodo Gmail (para no enviar correos reales) y Data Table Get Rows con filas sintéticas terminales (excepto donde se indica). `Classify Result` y `Data Table Update Row` ejecutaron de verdad.

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

En todos los tests el nodo `Data Table Update Row` ejecutó con `success` (con `job_id` sintéticos no matcheó filas reales, por lo que no escribió nada: comportamiento esperado en sandbox).

## Pruebas pendientes

- Envío real del email Gmail a un destinatario real (el nodo se pineó en todos los tests para no generar correos).
- Escritura real de `last_notified_at`/`notified_result` contra una fila terminal real del launcher (requiere que exista tal fila).
- Verificación con datos reales de que la fila notificada no se vuelve a seleccionar en el siguiente ciclo (mecanismo verificado: filtro `isEmpty` + defensa en Code).
- Ciclo completo integrado (launcher → monitor → notifier) con el contenedor real (Fase 9).