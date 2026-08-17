# Reporte del implementador — Fase 7: workflow monitor

Fecha: 2026-08-17 · Rama: `feat/workflow-monitor` · Sin commit/push (lo coordina el líder).

## Entregables

### Workflow creado

- **Nombre**: `Script Phase 7 Monitor`
- **Workflow ID**: `YfNC1o1Qo38RWSQQ`
- **URL**: https://n8n.adalgarcia.com/workflow/YfNC1o1Qo38RWSQQ
- **Estado**: inactivo (no publicado) ✓
- **Proyecto**: personal `lRQsCrsuKfh7kky6`
- **Nodos** (5): `Every 5 Minutes` (scheduleTrigger 1.3, cada 5 min, configurable), `Data Table Get Rows` (dataTable 1.1 row/get, filtro `state = running`, `returnAll: true`), `SSH Read Job Artifacts` (ssh 1 command/execute, privateKey, credencial `SSH N8N-SCRIPT`), `Decide Job Action` (code 2 `runOnceForEachItem`), `Data Table Update Row` (dataTable 1.1 row/update por `job_id`).
- **Settings aplicados**: timezone `UTC`, `executionOrder v1`; nodo SSH con `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput`.
- **Validación**: `validate_workflow` OK (5 nodos); `create_workflow_from_code` con credencial auto-asignada.

### Columnas añadidas a `script_job_launches` (8/8)

| Columna | Tipo | id |
|---|---|---|
| `updated_at` | date | `F2cuSRhtW0kKXpPA` |
| `finished_at` | date | `FugVa1XtaLAwTMaS` |
| `timeout_at` | date | `zxSHXZm5qDxFfvmV` |
| `exit_code` | number | `Q0eqWn1jSTOG3y9U` |
| `result` | string | `mdtkL0SXpuNlgrEi` |
| `error` | string | `BDR9Czc0AwhIS3J3` |
| `last_checked_at` | date | `caaDnpRxEQpoyTY6` |
| `check_count` | number | `wVVHUTzpZFBgxYA7` |

## Pruebas ejecutadas (criterio 7)

Metodología: `prepare_test_pin_data` + `test_workflow`. Los nodos Data Table no
necesitan pin y ejecutan de verdad; se pinnearon Schedule Trigger, Data Table
Get Rows (filas sintéticas `running`) y SSH (stdout simulado). El nodo
`Data Table Update Row` ejecutó con `success` en todas las ejecuciones (con
`job_id` sintéticos no matcheó filas reales → no escribió nada: esperado en
sandbox).

| # | Escenario | Ejecución | Resultado observado |
|---|---|---|---|
| Test 1 | Job termina `success` | 8126 | `state=success`, `exit_code=0`, `result` conservado, `finished_at` propagado, `check_count` 0→1 |
| Test 2 | `timeout_at` en el pasado (2020) | 8127 | `state=timeout`, `exit_code=40`, error `se alcanzó el límite operativo`, `finished_at`=now UTC, `check_count` 3→4 |
| Test 3 | PID `lost` (kill -0 falla) | 8128 | `state=failed`, `exit_code=30`, error `process_lost`, `check_count` 2→3 |
| Test 4 | 4 jobs running concurrentes | 8129 | 4 salidas del Code: running-ok, success, timeout, failed; `Data Table Update Row` ejecutado tras todas |
| Test 5 | `status.json` ilegible / ruta ausente | 8131 | Transitorio: `state=running`, `error=status_unreadable`, `check_count`=1, sin marcar terminal |
| Test 6 | Sin jobs running (pin Get Rows=[]) | 8133 | Get Rows devuelve 0 items, workflow `success`, sin actualizaciones |
| — | Get Rows real contra tabla viva | 8130 | Filtro seleccionó las **9 filas `running` reales** del launcher (8113/8115/8117); con SSH pinnado vacío no hubo escrituras y el flujo terminó sin error |

## Hallazgos y gaps

1. **Timeout SSH (criterio 3.4, NO cumplido como tal)**: el nodo
   `n8n-nodes-base.ssh` v1 no expone parámetro de timeout por comando (solo
   credential/command/working directory; confirmado en docs n8n y type defs).
   Mitigación aplicada: comando acotado (`cat` + `tail -n 100` de rutas
   deterministas), `retryOnFail` 3× y `continueRegularOutput`. **Decisión
   necesaria**: ¿se acepta esta mitigación para la fase 7 o se exige un
   `executionTimeout` global del workflow (p. ej. 600 s) o un wrapper `timeout`
   en el comando remoto (coreutils disponible en la imagen)?
2. **Tabla viva con 9 filas `running` de pruebas Fase 6** (jobs 8113/8115/8117,
   `remote_pid=pending`, `timeout_at=null`): al activar el monitor, la primera
   pasada las reconciliará contra el contenedor. Como `remote_pid=pending` no
   está vacío, si el `pid_path` no existe o el PID está muerto se marcarán
   `failed/process_lost` (comportamiento correcto según D5, pero conviene
   revisarlas antes de activar el schedule).
3. **Test 4 (terminal no reprocesado)**: verificado por construcción (filtro
   `state = 'running'` + sin `alwaysOutputData`) y con evidencia real en 8130
   (solo se seleccionaron filas `running`). No había filas terminales en la
   tabla viva para una prueba determinista de reprocesado; pendiente en Fase 9.
4. **Tokens**: el flujo no recibe tokens; el Code redacta cualquier cadena
   ≥64 chars tipo base64. La comprobación de `output.log` del contenedor sin
   tokens completos requiere infraestructura (Fase 9).
5. **Update real pendiente**: el nodo Update ejecutó OK pero sin match real
   (IDs sintéticos). La escritura real contra filas del launcher se validará
   cuando se ejecute el monitor con SSH real contra el contenedor.

## Documentación

- `docs/phase-7-monitor.md` (creado, estilo de phase-6-launcher).
- `README.md` (sección `## Fase 7: workflow monitor` añadida; Arquitectura
  actualizada).
- `plan.md` grupos 1-4 marcados; Grupo 5 (commit/push/PR/merge) sin marcar.
- `validation.md`: estado `🟡 EN PROGRESO`; criterios 1-7 marcados salvo 3.4
  (timeout SSH) y criterios de merge.
- `roadmap.md`: Fase 7 con los 5 items `[x]`.

## Decisiones pendientes para el líder

1. Aceptar la mitigación de timeout SSH (criterio 3.4) o exigir guarda extra.
2. Autorizar la activación del workflow (requiere primera pasada real contra el
   contenedor y revisión de las 9 filas `running` heredadas del launcher).
3. Confirmar si las filas de prueba 8113/8115/8117 deben limpiarse antes de
   activar el monitor (no hay herramienta de borrado de filas en el MCP).
