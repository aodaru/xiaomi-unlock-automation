# Validación — Resultados operativos

## Estado de la fase

**🟡 EN PROGRESO** — workflow `Script Phase 8 Notifier` creado (inactivo), columnas añadidas, tests 1-8 ejecutados con éxito. Pendiente: configuración del destinatario real, validación de ciclo real contra el contenedor y activación (Fase 9 / liderazgo).

## Criterios de éxito

### 1. Workflow notifier creado y configurado

- [x] Workflow `Script Phase 8 Notifier` existe en n8n (ID `16cYVCoO48LxBxl4`).
- [x] Schedule Trigger activo cada 5 minutos (configurable a 1 min).
- [x] Timezone configurado en UTC (coherente con contrato Fase 1).
- [x] Workflow desactivado hasta configurar la credencial del canal de notificación.

### 2. Consulta y filtro de trabajos notificables

- [x] Nodo Data Table Get Rows filtra estado terminal (`success`, `failed`,
      `timeout`) Y `last_notified_at IS NULL`.
      Nota: el nodo Data Table v1.1 no expone operadores `IN`/`isNull`; se
      expresa como `state != starting/running/cancelled/launch_failed` AND
      `last_notified_at isEmpty`, funcionalmente idéntico para el dominio de
      estados definido (ver `implementer-report.md`, hallazgo 3).
- [x] No selecciona trabajos `starting`, `running` ni `cancelled`.
- [x] No selecciona trabajos terminales ya notificados (`last_notified_at` con valor).
- [x] Maneja caso sin trabajos pendientes (flujo vacío sin error).

### 3. Clasificación del resultado

- [x] `success` → notificación tipo `success`.
- [x] `failed` con causa `token_expired` → notificación tipo `token_expired`.
- [x] `failed` con causa `request_rejected` o `permission_blocked` →
      notificación tipo `permission_denied`.
- [x] `timeout` → notificación tipo `timeout`.
- [x] `failed` con causa desconocida o ausente → notificación tipo `error`.
- [x] `exit_code` y `result`/`error` redactados se conservan en el mensaje para
      diagnóstico (sin token completo).

### 4. Redacción del token

- [x] El mensaje identifica por `job_id` y `token_hash` (o máscara `****xxxx`).
      Columna real: `token_fingerprint` (divergencia documentada).
- [x] El token completo **nunca** aparece en la notificación.
- [x] El token completo **nunca** aparece en logs ni en columnas escritas por el workflow.

### 5. Anti-duplicados

- [x] Tras notificar, la fila recibe `last_notified_at` (timestamp UTC) y `notified_result` (tipo).
- [x] En ciclos siguientes, la fila no vuelve a seleccionarse.
- [x] Una fila con `last_notified_at` asignado no recibe una segunda notificación.

### 6. Tolerancia a fallos

- [x] Fallo del canal de notificación no bloquea el resto de trabajos pendientes.
- [x] `retryOnFail`/`maxTries` configurados en el nodo de notificación (3 reintentos).
- [x] `continueRegularOutput` configurado donde aplica (nodo de notificación).

### 7. Pruebas funcionales

- [x] Test 1: Job `success` → notificación tipo `success`.
- [x] Test 2: Job `failed` con `token_expired` → notificación tipo `token_expired`.
- [x] Test 3: Job `failed` con `request_rejected`/`permission_blocked` → notificación tipo `permission_denied`.
- [x] Test 4: Job `timeout` → notificación tipo `timeout`.
- [x] Test 5: Job `failed` con causa desconocida → notificación tipo `error`.
- [x] Test 6: Segunda ejecución no re-notifica trabajos con `last_notified_at`.
- [x] Test 7: Token completo ausente en notificación, logs y Data Table.
- [x] Test 8: Sin trabajos pendientes → notifier termina sin enviar nada ni fallar.

## Cómo verificar

```bash
# 1. Verificar workflow existe en n8n
n8n-mcp-aod_search_workflows --query "Phase 8 Notifier" --limit 5

# 2. Verificar columnas en Data Table
# script_job_launches debe tener last_notified_at y notified_result

# 3. Ejecutar notifier manualmente con pin data (test)
n8n-mcp-aod_prepare_test_pin_data --workflowId <WORKFLOW_ID>
n8n-mcp-aod_test_workflow --workflowId <WORKFLOW_ID> --pinData <PIN_DATA>

# 4. Simular cada tipo de resultado
# - Insertar fila terminal con state/result/error correspondiente y
#   last_notified_at = null
# - Ejecutar notifier → debe enviar la notificación del tipo esperado
#   y marcar last_notified_at + notified_result

# 5. Simular anti-duplicado
# - Re-ejecutar notifier con la misma fila ya notificada
# - Debe terminar sin enviar notificación para esa fila

# 6. Verificar redactado de tokens
# - Inspeccionar el mensaje enviado y los logs del workflow
# - No debe contener el token completo, solo hash/máscara
```

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] PR abierto.
- [ ] Validación manual ejecutada (tests 1-8 arriba).
- [ ] Workflow notifier publicado/activado en n8n (tras configurar canal).
      ⬅ Pendiente: el workflow queda inactivo hasta configurar el destinatario
      real y validar un ciclo real contra el contenedor.
- [ ] Documentación `docs/phase-8-notifications.md` creada.
- [ ] Items de Fase 8 marcados en `specs/roadmap.md`.

## Anti-criterios (lo que NO debe pasar)

- ❌ El token completo aparece en la notificación, logs del workflow o columnas
      escritas por el notifier.
- ❌ Un trabajo recibe más de una notificación (duplicados).
- ❌ El notifier procesa trabajos `running`, `starting` o `cancelled`.
- ❌ Un fallo del canal de notificación bloquea el resto de trabajos o rompe el
      monitor.
- ❌ Fechas comparadas o escritas en zona horaria local en vez de UTC.
- ❌ Columnas `last_notified_at` / `notified_result` no se actualizan tras notificar.
- ❌ El notifier depende de credenciales o contraseñas embebidas (debe usar
      credential n8n del canal elegido).
