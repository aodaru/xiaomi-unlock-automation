# Reporte del implementador — Fase 8: notificador de resultados operativos

Fecha: 2026-08-17 · Rama: `feat/resultados-operativos` · Sin commit/push/PR (lo coordina el líder).

## Entregables

### Workflow creado

- **Nombre**: `Script Phase 8 Notifier`
- **Workflow ID**: `16cYVCoO48LxBxl4`
- **URL**: https://n8n.adalgarcia.com/workflow/16cYVCoO48LxBxl4
- **Estado**: **inactivo (no publicado)** ✓ (`active: false`)
- **Proyecto**: personal `lRQsCrsuKfh7kky6`
- **Nodos** (5): `Every 5 Minutes` (scheduleTrigger 1.3, cada 5 min, configurable a 1), `Data Table Get Rows` (dataTable 1.1 row/get, filtro estados no terminales + `last_notified_at isEmpty`, `returnAll: true`), `Classify Result` (code 2 `runOnceForEachItem`, clasificación 5 tipos + redacción + defensa anti-duplicados), `Send Email Notification` (gmail 2.2 message/send, OAuth2, credencial `Gmail account`), `Data Table Update Row` (dataTable 1.1 row/update por `job_id` escribiendo `last_notified_at` y `notified_result`).
- **Settings aplicados**: `timezone UTC`, `executionOrder v1`, `executionTimeout 600` (vía `update_workflow` tras la creación, igual que Fase 7).
- **Tolerancia del canal**: nodo Gmail con `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput` (criterio 6).
- **Validación**: `validate_workflow` OK (5 nodos, 0 warnings) tras corregir con `nodeJson()` las expresiones del Update Row que apuntaban a `$json` (el output del nodo Gmail sustituye al JSON del item; se referencia `$('Classify Result').item.json`).

### Columnas añadidas a `script_job_launches` (2/2)

| Columna | Tipo | id |
|---|---|---|
| `last_notified_at` | date | `YzqZC69bTkSk8IgM` |
| `notified_result` | string | `p1XVz5Dg36gAIPoY` |

Verificadas con `search_data_tables` (índices 22 y 23 de la tabla).

## Pruebas ejecutadas (criterio 7)

Metodología: `prepare_test_pin_data` + `test_workflow`. Se pinnearon `Every 5 Minutes` y `Send Email Notification` (para no enviar correos reales) y `Data Table Get Rows` con filas sintéticas terminales (excepto donde se indica). `Classify Result` y `Data Table Update Row` ejecutaron de verdad.

| # | Escenario | Ejecución | Resultado observado |
|---|---|---|---|
| Test 1 | Job `success` | 8206 | `notification_type=success`, body con `Token: ****b855`, `notified_result=success`, Update Row OK |
| Test 2 | `failed` + `token_expired`/`100004` | 8207 | `notification_type=token_expired` |
| Test 3 | `failed` + `request_rejected`/`is_pass=4` | 8208 | `notification_type=permission_denied` |
| Test 4 | Job `timeout` | 8209 | `notification_type=timeout`, `exit_code=40` conservado |
| Test 5 | `failed` causa desconocida | 8210 | `notification_type=error` |
| Test 6 | Fila ya con `last_notified_at` | 8211 | Code devuelve 0 items; Gmail/Update no ejecutan (anti-duplicado) |
| Test 7 | Token largo en `result`/`error` | 8212 | Campos `result_redacted`/`error_redacted` = `[REDACTED]`; token completo ausente del body |
| Test 8 | Get Rows pineado `[]` | 8213 | Workflow `success`, sin envíos ni actualizaciones |
| — | Get Rows real contra tabla viva | 8215 | Filtro real devuelve 0 filas (las 9 filas heredadas de Fase 6/7 están `running` y quedan excluidas); flujo termina sin error |

En todos los tests el nodo `Data Table Update Row` ejecutó con `success` (con `job_id` sintéticos no matcheó filas reales → no escribió nada: esperado en sandbox).

## Hallazgos y gaps

1. **Columna `token_fingerprint` en vez de `token_hash`**: la spec (D5, contexto) menciona `token_hash`, pero la columna real creada en Fase 6 se llama `token_fingerprint`. El workflow usa SIEMPRE `token_fingerprint` (huella SHA-256). Documentado en `docs/phase-8-notifications.md`.
2. **Canal SMTP (D1) no disponible**: la instancia no tiene credencial SMTP; la única credencial de email disponible es Gmail OAuth2 (`eN5CQPJBOkcyRCuw`). Se usó el nodo Gmail `message/send` como canal por defecto, **aislado** tras la lógica de clasificación (reemplazable por Telegram/Slack/webhook sin tocar los pasos 1-3/5). Divergencia documentada.
3. **Operadores del nodo Data Table**: el nodo v1.1 no expone `IN` ni `isNull` (los `loadOptions` de `getConditionsForColumn` solo devuelven `eq/neq/like/ilike/isEmpty/isNotEmpty/gt/gte/lt/lte/isTrue/isFalse`). El filtro de Get Rows se expresa como `state neq starting/running/cancelled/launch_failed` AND `last_notified_at isEmpty` (AND), funcionalmente idéntico a `state IN ('success','failed','timeout') AND last_notified_at IS NULL` para el dominio de estados definido. Adicionalmente, el Code descarta filas con `last_notified_at` como defensa anti-duplicados.
4. **`launch_failed` excluido**: el estado `launch_failed` (fallo de lanzamiento de Fase 6) queda fuera del alcance notificable de esta fase (la spec solo contempla `success`/`failed`/`timeout`). Si el líder quiere notificarlo como `error`, basta eliminar la condición `neq launch_failed` del filtro.
5. **Destinatario por defecto**: `sendTo` usa `aodarug@gmail.com` (email del propietario de la credencial Gmail, visible en el proyecto). No hay spec que defina el email del operador; se documenta como configuración requerida antes de activar.
6. **Escritura real pendiente**: Update Row ejecutó OK pero sin match real (IDs sintéticos). La escritura real contra filas del launcher se validará cuando existan filas terminales reales y se ejecute el workflow con datos de producción.

## Decisiones tomadas

1. Canal de salida = Gmail OAuth2 (adaptación de D1 a la realidad de credenciales; documentada).
2. Filtro Get Rows = `neq` sobre estados no terminales + `isEmpty` sobre `last_notified_at` (adaptación técnica del criterio 2.1; documentada).
3. Anti-duplicados = filtro Data Table + defensa en Code (`return null` si `last_notified_at` tiene valor) + Update Row que marca la fila (D3 respetado).
4. Clasificación 5 tipos según contrato Fase 1 con `state` + `result`/`error` (D4 respetado); causas nuevas de la API caen en `error` conservando `result`/`error` redactados.
5. Máscara de token = `****xxxx` con los últimos 4 de `token_fingerprint`; nunca el token completo (D5 respetado). Redacción defensiva de cadenas largas en el Code.
6. Workflow inactivo hasta configurar destinatario real y validar un ciclo real (D2 respetado: notifier independiente del monitor).

## Documentación

- `docs/phase-8-notifications.md` (creado, estilo de phase-6-launcher/phase-7-monitor).
- `specs/2026-08-17-resultados-operativos/plan.md` grupos 1-4 marcados; Grupo 5 (commit/push/PR/merge) sin marcar (lo coordina el líder).
- `specs/2026-08-17-resultados-operativos/validation.md`: estado `🟡 EN PROGRESO`; criterios 1-7 marcados salvo el de "workflow publicado/activado" y los criterios de merge (el workflow queda inactivo).
- `specs/roadmap.md`: Fase 8 con los 4 items `[x]`.

## Decisiones pendientes para el líder

1. Confirmar el email real del operador para `sendTo` (por defecto `aodarug@gmail.com`).
2. Decidir si `launch_failed` debe notificarse en una fase posterior (hoy queda excluido).
3. Autorizar la activación del workflow (requiere ciclo real launcher→monitor→notifier contra el contenedor, Fase 9).

## Cambio posterior: notificación por Telegram (2026-08-17)

El canal de notificación del workflow `Script Phase 8 Notifier` (`16cYVCoO48LxBxl4`) pasó de **Gmail a Telegram**. Detalle completo: `specs/2026-08-17-resultados-operativos/implementer-report-telegram.md`.

Resumen:

- Nodo de salida: `Send a text message` (`n8n-nodes-base.telegram` 1.2, `resource=message`, `operation=sendMessage`), conectado `Classify Result` → Telegram → `Data Table Update Row` (conexión ya existente en el draft).
- Credencial: `Telegram account` (`Z3r0YRo0ftwFvRYO`, `telegramApi`) → bot `TeaPartyDev_bot` (id 8378951561).
- `chatId`: `744884859` (chat privado del operador `Aodaru`; mismo chat de los workflows activos `Brute Force - Reporte Diario` y `AsisVirtual Telegram Bot`; confirmado con envío real).
- `text` = `={{ $json.body }}`; `additionalFields.parse_mode = none` (texto plano).
- Eliminado el nodo huérfano `Send Email Notification` (Gmail).
- Tolerancia del canal intacta: `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput`.
- Pruebas reales: ejecuciones **8299** (message_id 489, `ok: true`, chat 744884859) y **8301** (message_id 490, texto plano con máscara `****b855` intacta). Hallazgo intermedio: el parse mode por defecto degradaba la máscara (`****b855`→`b855`) y los guiones bajos; corregido con `parse_mode: none`.
- Publicado: versión activa `ef4c9be2-4d7b-41c4-b681-b74809419260` (workflow seguía activo; sin cambios de settings globales).
- Nodos intocados: `Every 5 Minutes`, `Data Table Get Rows`, `Classify Result`, `Data Table Update Row`. Sin commit/push/PR.