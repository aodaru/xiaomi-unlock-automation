# Validación — Workflow monitor

## Estado de la fase

**🟡 EN PROGRESO** — workflow creado, columnas añadidas y pruebas de lógica con pin data completadas. Falta activación (requiere validación real contra el contenedor y decisión del líder).

## Criterios de éxito

### 1. Workflow monitor creado y configurado

- [x] Workflow `Script Phase 7 Monitor` existe en n8n.
- [x] Schedule Trigger activo cada 5 minutos (configurable a 1 min).
- [x] Timezone configurado (UTC o Asia/Shanghai según convención).
- [x] Workflow desactivado hasta configurar credencial SSH.

### 2. Consulta y filtro de trabajos running

- [x] Nodo Data Table Get Rows filtra `state = 'running'`.
- [x] No selecciona trabajos en `starting`, `success`, `failed`, `timeout`.
- [x] Maneja caso sin trabajos running (flujo vacío sin error).

### 3. Lectura remota por SSH

- [x] Para cada job running, ejecuta comando SSH que lee `status.json` y `output.log`.
- [x] Comando SSH usa credencial n8n (clave privada), sin contraseñas en workflow.
- [x] Ruta remota construida desde la fila (columnas `status_path` / `output_path` / `pid_path`, ej. `/workspace/jobs/<job_id>`).
- [ ] Timeout SSH configurado (ej. 30s) para no bloquear schedule. — *No aplicable al nodo `n8n-nodes-base.ssh` v1 (no expone parámetro de timeout por comando). Mitigación: reintentos, `continueRegularOutput` y comando acotado. Ver reporte.*

### 4. Parseo y decisión de estado

- [x] Parsea `status.json` (JSON válido) y extrae `state`, `result`, `error`, `exit_code`, `timeout_at`, fechas.
- [x] Si `state` terminal (`success`, `failed`, `timeout`) → actualiza Data Table y no re-procesa.
- [x] Si `state = 'running'` y `now > timeout_at` → marca `timeout`, `exit_code = 40`.
- [x] Si `state = 'running'` y proceso perdido (`kill -0 <pid>` falla) → marca `failed`, `exit_code = 30`, error `process_lost`.
- [x] Si `state = 'running'` y sin timeout ni proceso perdido → actualiza `last_checked_at`, `check_count`, `updated_at`.

### 5. Actualización Data Table

- [x] Nodo Data Table Update Row escribe: `state`, `result`, `error`, `exit_code`, `finished_at` (si terminal), `updated_at`, `last_checked_at`, `check_count`.
- [x] `last_checked_at` = timestamp UTC de la comprobación actual.
- [x] `check_count` incrementado en 1 cada ciclo.
- [x] Tokens completos **nunca** escritos en Data Table, logs ni errores del workflow.

### 6. Columnas Data Table añadidas

- [x] Columna `last_checked_at` (tipo date/string ISO 8601) existe y se actualiza.
- [x] Columna `check_count` (tipo number) existe y se incrementa.

### 7. Pruebas funcionales

- [x] Test 1: Job termina en `success` → monitor detecta y actualiza a `success` con `result`. (Ejecución 8126)
- [x] Test 2: Job supera `timeout_at` → monitor detecta y actualiza a `timeout` con `exit_code=40`. (Ejecución 8127)
- [x] Test 3: Proceso muerto (PID no existe) → monitor detecta y actualiza a `failed` con error `process_lost`. (Ejecución 8128)
- [x] Test 4: Job ya terminal no se re-procesa en siguiente ejecución del monitor. (Mecanismo: filtro `state = 'running'`; verificado en ejecución real 8130 donde solo se seleccionaron filas `running`.)
- [x] Test 5: 4 jobs concurrentes running → monitor procesa todos en una ejecución. (Ejecución 8129)
- [x] Test 6: Sin jobs running → monitor termina sin error ni actualizaciones. (Ejecución 8133; también 8130 con filas reales y SSH pinnado vacío.)

## Cómo verificar

```bash
# 1. Verificar workflow existe en n8n
n8n-mcp-aod_search_workflows --query "Phase 7 Monitor" --limit 5

# 2. Verificar Data Table columnas (via n8n UI o API)
# Debe mostrar last_checked_at y check_count en script_job_launches

# 3. Ejecutar monitor manualmente con pin data (test)
n8n-mcp-aod_prepare_test_pin_data --workflowId <WORKFLOW_ID>
n8n-mcp-aod_test_workflow --workflowId <WORKFLOW_ID> --pinData <PIN_DATA>

# 4. Simular job running con timeout_at en el pasado
# - Insertar fila en Data Table con state=running, timeout_at=2020-01-01T00:00:00Z
# - Ejecutar monitor → debe marcar timeout

# 5. Simular proceso perdido
# - Insertar fila con state=running, pid=99999 (inexistente), timeout_at futuro
# - Ejecutar monitor → debe marcar failed con error process_lost

# 6. Verificar redactado de tokens
# - Revisar output.log del contenedor: no debe contener token completo
# - Revisar Data Table: columnas result/error no deben tener token completo
```

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] PR abierto.
- [ ] Validación manual ejecutada (tests 1-6 arriba).
- [ ] Workflow monitor publicado/activado en n8n.
- [ ] Documentación `docs/phase-7-monitor.md` creada.

## Anti-criterios (lo que NO debe pasar)

- ❌ Monitor procesa trabajos en estado `starting` (solo `running`).
- ❌ Monitor re-procesa trabajos ya en `success`, `failed`, `timeout`.
- ❌ Token completo aparece en Data Table, logs del workflow, o errores n8n.
- ❌ Schedule Trigger se ejecuta en cascada (solapamiento de ejecuciones).
- ❌ Falla SSH de un job bloquea el procesamiento de los demás.
- ❌ `timeout_at` comparado en zona horaria local en vez de UTC.
- ❌ Columnas `last_checked_at` / `check_count` no se actualizan.
- ❌ Workflow monitor depende de credenciales hardcodeadas (debe usar credential n8n).
