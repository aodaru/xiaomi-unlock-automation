# Validación — Resultados operativos

## Estado de la fase

**⬜ PENDIENTE** — spec creada; falta implementación del workflow, columnas y pruebas.

## Criterios de éxito

### 1. Workflow notifier creado y configurado

- [ ] Workflow `Script Phase 8 Notifier` existe en n8n.
- [ ] Schedule Trigger activo cada 5 minutos (configurable a 1 min).
- [ ] Timezone configurado en UTC (coherente con contrato Fase 1).
- [ ] Workflow desactivado hasta configurar la credencial del canal de notificación.

### 2. Consulta y filtro de trabajos notificables

- [ ] Nodo Data Table Get Rows filtra estado terminal (`success`, `failed`,
      `timeout`) Y `last_notified_at IS NULL`.
- [ ] No selecciona trabajos `starting`, `running` ni `cancelled`.
- [ ] No selecciona trabajos terminales ya notificados (`last_notified_at` con valor).
- [ ] Maneja caso sin trabajos pendientes (flujo vacío sin error).

### 3. Clasificación del resultado

- [ ] `success` → notificación tipo `success`.
- [ ] `failed` con causa `token_expired` → notificación tipo `token_expired`.
- [ ] `failed` con causa `request_rejected` o `permission_blocked` →
      notificación tipo `permission_denied`.
- [ ] `timeout` → notificación tipo `timeout`.
- [ ] `failed` con causa desconocida o ausente → notificación tipo `error`.
- [ ] `exit_code` y `result`/`error` redactados se conservan en el mensaje para
      diagnóstico (sin token completo).

### 4. Redacción del token

- [ ] El mensaje identifica por `job_id` y `token_hash` (o máscara `****xxxx`).
- [ ] El token completo **nunca** aparece en la notificación.
- [ ] El token completo **nunca** aparece en logs ni en columnas escritas por el workflow.

### 5. Anti-duplicados

- [ ] Tras notificar, la fila recibe `last_notified_at` (timestamp UTC) y `notified_result` (tipo).
- [ ] En ciclos siguientes, la fila no vuelve a seleccionarse.
- [ ] Una fila con `last_notified_at` asignado no recibe una segunda notificación.

### 6. Tolerancia a fallos

- [ ] Fallo del canal de notificación no bloquea el resto de trabajos pendientes.
- [ ] `retryOnFail`/`maxTries` configurados en el nodo de notificación.
- [ ] `continueRegularOutput` configurado donde aplica.

### 7. Pruebas funcionales

- [ ] Test 1: Job `success` → notificación tipo `success`.
- [ ] Test 2: Job `failed` con `token_expired` → notificación tipo `token_expired`.
- [ ] Test 3: Job `failed` con `request_rejected`/`permission_blocked` → notificación tipo `permission_denied`.
- [ ] Test 4: Job `timeout` → notificación tipo `timeout`.
- [ ] Test 5: Job `failed` con causa desconocida → notificación tipo `error`.
- [ ] Test 6: Segunda ejecución no re-notifica trabajos con `last_notified_at`.
- [ ] Test 7: Token completo ausente en notificación, logs y Data Table.
- [ ] Test 8: Sin trabajos pendientes → notifier termina sin enviar nada ni fallar.

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
