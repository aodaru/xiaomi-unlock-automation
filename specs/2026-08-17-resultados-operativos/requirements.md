# Requisitos — Resultados operativos

## Alcance

Esta fase implementa la notificación al operador técnico cuando cada trabajo
alcanza un estado terminal, diferenciando el resultado (éxito, permiso
denegado, token caducado, timeout o error), redactando el token y evitando
notificaciones duplicadas mediante un campo `last_notified_at`. Es la fase que
cierra el flujo de resultados visibles de la misión: el operador deja de
depender de consultar manualmente la Data Table.

### Incluido

- Definición del canal de notificación (email SMTP por defecto, nodo de salida
  reemplazable).
- Workflow n8n `Script Phase 8 Notifier` con `Schedule Trigger` (5 minutos por
  defecto, configurable a 1 minuto).
- Consulta a Data Table `script_job_launches` filtrando estados terminales
  (`success`, `failed`, `timeout`) con `last_notified_at IS NULL`.
- Clasificación del resultado en 5 tipos según el contrato Fase 1:
  - `success` → éxito (cuenta puede solicitar desbloqueo).
  - `permission_denied` → permiso denegado/bloqueado (`request_rejected`,
    `permission_blocked`).
  - `token_expired` → token caducado (`token_expired`).
  - `timeout` → se superó `timeout_at`.
  - `error` → cualquier otro fallo (red, HTTP, JSON, respuesta desconocida).
- Redacción del token: la notificación identifica por `job_id` y `token_hash`
  (o máscara con últimos 4); el token completo nunca aparece en notificación,
  logs ni Data Table.
- Actualización de la fila tras notificar: `last_notified_at` (timestamp UTC) y
  `notified_result` (tipo enviado), garantizando una única notificación por
  trabajo.
- Tolerancia a fallos de notificación: `retryOnFail`, `maxTries` y
  `continueRegularOutput` para que un canal caído no bloquee el resto de
  trabajos ni al monitor.
- Documentación `docs/phase-8-notifications.md`.

### No incluido

- Pruebas de resiliencia del ciclo completo (Fase 9): 4 jobs concurrentes,
  trabajos >1 día, reinicios de n8n/contenedor, desconexión SSH.
- Extracción automática de tokens con Playwright (Fase 10).
- Cambios en el script Python `SCRIPT_PERMISO_DESBLOQUEO.py` (el resultado y
  `error` ya se escriben redactados).
- Cambios en Docker Compose, SSH, tmux o el workflow launcher/monitor
  (Fase 5-7).
- Cancelación explícita de trabajos (`cancelled` queda reservado a fase
  posterior).
- Portal multiusuario o interfaz para el operador (fuera de misión).

## Decisiones

| ID | Decisión | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Canal de notificación = email SMTP (nodo `Send Email`), reemplazable por Slack/Telegram/webhook sin tocar la lógica. | `specs/tech-stack.md` deja pendiente "definir el canal concreto"; email SMTP es el más universal en n8n y el nodo de salida queda aislado tras la lógica de clasificación. | Fijar Telegram/Slack como canal único (requiere credenciales externas y disponibilidad). |
| D2 | Workflow notifier independiente del monitor (no sub-workflow). | Coherente con D7 de Fase 7: launcher = trigger, monitor = polling, notifier = reporte. Desacopla ciclo de vida y permisos. | Integrar la notificación dentro del monitor (acopla reporte con polling y reenvía lógica de negocio). |
| D3 | Anti-duplicados mediante `last_notified_at` + `notified_result` en Data Table. | Garantiza una única notificación por trabajo terminal; `notified_result` da trazabilidad de lo enviado. | Booleano `notified` (pierde timestamp) o dedupe por `execution_id` (frágil). |
| D4 | Clasificación de 5 resultados a partir de `state` + `result`/`error` del contrato Fase 1, no solo por `exit_code`. | `exit_code` agrupa varias causas (p. ej. 10 cubre token caducado y permiso rechazado); `error`/`result` redactados distinguen la causa exacta. | Clasificar solo por `state` (no distingue permiso denegado vs token caducado). |
| D5 | La notificación usa `job_id` y `token_hash` (o máscara `****xxxx`), nunca el token completo. | La misión exige no exponer tokens en logs ni notificaciones; `token_hash` ya existe en Data Table desde Fase 6. | Enviar token completo al operador (viola misión) o sin identificador (no trazable). |
| D6 | El roadmap Fase 8 dice "registrar `last_checked_at`", pero esa columna ya existe desde Fase 7; se interpreta como registrar la última notificación → `last_notified_at`. | Evita re-trabajo y respeta la intención de la fase (anti-duplicados de notificación). | Añadir duplicado de `last_checked_at`. |

## Contexto

- **Data Table**: `script_job_launches` (ID: `9YfdvJehSSUf9iK2`), creada en Fase 6.
  Columnas actuales: `execution_id`, `job_id`, `token_hash`, `state`,
  `remote_path`, `pid`, `started_at`, `updated_at`, `finished_at`,
  `timeout_at`, `exit_code`, `result`, `error`, `created_at`,
  `last_checked_at`, `check_count`. La Fase 8 añadirá `last_notified_at` y
  `notified_result`.
- **Workflow monitor**: `Script Phase 7 Monitor` ya filtra `state = 'running'`,
  lee `status.json`/`output.log` por SSH y actualiza la fila con estados
  terminales (`success`, `failed`, `timeout`) y `last_checked_at`/`check_count`.
  No toca notificaciones (declarado "No incluido" en Fase 7).
- **Contrato Fase 1** (respuestas Xiaomi):
  - `token_expired`: `bl-switch/state`, `code=100004`.
  - `request_rejected`: `code=100001`.
  - `permission_blocked`: `is_pass=4`, `button_state=2/3`, o `apply_result=3/4`.
  - `permission_available`: `is_pass=4`, `button_state=1`, o `is_pass=1`.
  - Códigos de salida: `0` success, `10` failed (token caducado/permiso
    rechazado/respuesta funcional), `20` entrada inválida, `30` red/HTTP/JSON,
    `40` timeout, `50` cancelled.
- **Credenciales**: la credencial SSH n8n se usa para lectura; la notificación
  requerirá una credencial de email (SMTP) o del canal elegido, sin contraseñas
  embebidas en el workflow.
- **Estados válidos** (contrato Fase 1): `starting`, `running`, `success`,
  `failed`, `timeout`, `cancelled`. Solo los terminales notificables son
  `success`, `failed`, `timeout`.

## Dependencias

- **Fase 7**: Monitor que deja los trabajos en estado terminal con `result`,
  `error`, `exit_code` y fechas correctas.
- **Fase 6**: Data Table `script_job_launches` con `token_hash`, `state`,
  `result`, `error`, `exit_code`.
- **Fase 5**: Contenedor con SSH; no requiere cambios.
- **Fase 1**: Contrato de estados, códigos de salida y clasificación de
  respuestas Xiaomi (fuente de la clasificación de 5 resultados).
- **`specs/mission.md`**: Resultado estructurado por token, no exponer tokens,
  trazabilidad.
- **`specs/tech-stack.md`**: n8n, Data Table, ejecución desacoplada, definición
  del canal de notificación (gap que esta fase cierra).

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| SMTP/canal de notificación no configurado en n8n al desplegar. | Workflow creado desactivado; activación exige credencial configurada. Nodo de salida aislado y reemplazable (D1). |
| Fallo del canal de notificación (SMTP caído, cuota). | `retryOnFail`/`maxTries` a nivel de nodo y `continueRegularOutput`; el error queda en `error` de la fila si el Update Row escribe diagnóstico, sin bloquear otros jobs. |
| Notificación duplicada si dos ciclos del notifier se solapan. | Filtro estricto `last_notified_at IS NULL` y Schedule Trigger sin solapamiento en n8n; `notified_result` permite auditar. |
| Token filtrado en el cuerpo de la notificación o en logs del workflow. | La lógica solo construye el mensaje con `token_hash`/máscara; revisión anti-criterio en pruebas (Test 7). |
| Filas terminales existentes antes del despliegue podrían notificarse en masa. | Validar el primer ciclo con pin data y, si procede, marcar `last_notified_at` de filas históricas antes de activar. |
| Clasificación incorrecta de una causa nueva de la API. | Cualquier causa no mapeada cae en `error`; `result`/`error` se conservan redactados para diagnóstico posterior. |
| `last_notified_at`/`notified_result` no presentes en Data Table al ejecutar el workflow. | Las columnas se añaden en Grupo 2 antes de implementar el workflow (Grupo 3). |
