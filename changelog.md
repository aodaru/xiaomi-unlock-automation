# Review — feature workflow-monitor (Fase 7)

**Veredicto:** APPROVED

Revisión independiente con MCP (`get_workflow_details`, `get_workflow_version`,
`search_data_tables`, `search_workflows`, `list_credentials`, `get_execution`
8126-8133, `get_node_types` ssh v1). No existen `init.sh`, `CHECKPOINTS.md`,
`progress/current.md`, `docs/architecture.md` ni `docs/conventions.md` en este
repo (documentado en revisión previa); se aplica `validation.md` del spec como
criterio de verificación.

## Criterios de validation.md

- C1.1: [x] Workflow `Script Phase 7 Monitor` (id `YfNC1o1Qo38RWSQQ`) existe, `active: false`, `executionOrder v1`.
- C1.2: [x] Schedule Trigger `Every 5 Minutes` (`minutesInterval: 5`, typeVersion 1.3), configurable.
- C1.3: [x] Timezone del workflow `UTC` (settings).
- C1.4: [x] Workflow inactivo. La credencial `SSH N8N-SCRIPT` (`sgAi6cqXq5TrR7ZH`, `sshPrivateKey`) ya existe, por lo que el motivo literal "hasta configurar credencial" está superado; mantenerlo inactivo hasta la validación real contra el contenedor es la postura correcta (ver Hallazgos 2 y 5).
- C2.1: [x] Data Table Get Rows con `matchType: allConditions`, filtro `state eq running`, `returnAll: true`.
- C2.2: [x] Filtro estricto: no selecciona `starting` ni terminales. Evidencia real: ejecución 8130 seleccionó solo las 9 filas `running`.
- C2.3: [x] Sin filas running → Get Rows devuelve 0 items y el workflow termina `success` (ejecución 8133 verificada).
- C3.1: [x] SSH `command/execute` con `authentication: privateKey` lee `status.json`, `tail -n 100 output.log` y marcador de PID en un único comando.
- C3.2: [x] Sin contraseñas embebidas; credencial n8n de clave privada (ver Hallazgo 2 sobre verificación de adjunción).
- C3.3: [x] Rutas desde columnas de la fila (`status_path`, `output_path`, `pid_path`); el launcher las escribe como `/workspace/jobs/<job_id>/...`.
- C3.4: [ ] No cumplible tal cual: `get_node_types` confirma que `n8n-nodes-base.ssh` v1 `command/execute` solo expone `authentication/command/cwd`, sin parámetro de timeout. **Mitigación razonable y aceptada para Fase 7**: comando acotado (cat/tail/kill -0 sobre rutas deterministas), `retryOnFail` + `maxTries: 3` + `onError: continueRegularOutput`. Se recomienda añadir `executionTimeout` a nivel de workflow antes de activar (guardia opcional; decisión de líder).
- C4.1: [x] Parseo de `status.json` verificado en ejecuciones 8126-8129 (Code node `Decide Job Action`, `runOnceForEachItem`, `pairedItem` correcto por item).
- C4.2: [x] Estado terminal (`success/failed/timeout`) propaga `state/result/error/exit_code/finished_at` y no se re-procesa (filtro C2.1 + evidencia 8129-e2).
- C4.3: [x] Timeout: `now > timeout_at` en UTC → `state=timeout`, `exit_code=40`, `finished_at=now UTC` (8127 y 8129-e3 verificadas).
- C4.4: [x] Proceso perdido: `kill -0 <pid>` falla (`lost`) o `no_pid` con `remote_pid` → `failed`, `exit_code=30`, error `process_lost` (8128 y 8129-e4 verificadas).
- C4.5: [x] `running` sin timeout ni pérdida → solo `last_checked_at`/`check_count`/`updated_at` (8129-e1 verificada).
- C5.1: [x] Update Row por `job_id` escribe state/result/error/exit_code/finished_at/timeout_at/updated_at/last_checked_at/check_count.
- C5.2: [x] `last_checked_at` = `now.toISOString()` UTC.
- C5.3: [x] `check_count` incrementa (0→1 en 8126, 3→4 en 8127, etc.).
- C5.4: [x] El flujo nunca recibe tokens; el Code redacta cadenas ≥64 chars tipo base64 en `result`/`error`; el stdout SSH no se persiste.
- C6.1: [x] Columna `last_checked_at` (id `caaDnpRxEQpoyTY6`, date) confirmada en `search_data_tables`.
- C6.2: [x] Columna `check_count` (id `wVVHUTzpZFBgxYA7`, number) confirmada. Las 8 columnas nuevas existen con los IDs exactos del reporte.
- C7.1-C7.6: [x] Tests 1-6 verificados en las ejecuciones reales 8126-8133 (todas `success`), incluida 8130 (filtro contra tabla viva).

## Anti-criterios

- ✅ Monitor NO procesa `starting`: filtro `state eq running` estricto.
- ✅ Monitor NO re-procesa terminales: filtro `state eq running` + terminales salen del conjunto.
- ✅ Token completo no aparece en Data Table/logs/errores: el flujo no recibe tokens; redacción defensiva en Code; `output.log` solo se lee, nunca se escribe.
- ⚠️ Schedule sin solapamiento: no hay guarda explícita anti-solapamiento; la afirmación D6 del requirements ("n8n no solapa por defecto") no es verificable vía MCP. Riesgo bajo hoy (ejecución <1s); revisar en Fase 9.
- ✅/⚠️ Falla SSH de un job no bloquea a los demás: fallos de lectura por-job (exit code != 0 en stdout) no bloquean (tratados como `status_unreadable` transitorio); un fallo de *conexión* SSH afecta a todos los items de esa ejecución (limitación del nodo), mitigado con retry 3× + `continueRegularOutput`.
- ✅ `timeout_at` comparado en UTC (ms absolutos, `Date.parse` sobre ISO normalizada).
- ✅ `last_checked_at` / `check_count` se actualizan cada ciclo.
- ✅ Sin credenciales hardcodeadas: `authentication: privateKey` + credencial n8n.

## Hallazgos

1. **Criterio 3.4 (timeout SSH)** — Confirmado que `n8n-nodes-base.ssh` v1 `command/execute` no expone timeout (`get_node_types`: solo `authentication/command/cwd`). La mitigación aplicada es razonable para un comando local (`cat`+`tail`+`kill -0` en el contenedor, sin I/O de red); no bloquea la aprobación. Antes de activar el schedule se recomienda fijar `executionTimeout` a nivel de workflow (p. ej. 300-600s) como guarda contra un SSH colgado.
2. **Adjunción de credencial al nodo SSH** — `get_workflow_details` y `get_workflow_version` no exponen `node.credentials` vía MCP; el implementador reporta auto-asignación de `SSH N8N-SCRIPT`. La credencial existe en el proyecto correcto. Confirmar la adjunción en el editor al momento de activar.
3. **Edge case del Code node (`Decide Job Action`)** — `new Date(timeoutAtRaw).toISOString()` (línea ~`timeoutAt` y `finished` de estados terminales) lanza `RangeError` si `timeout_at`/`finished_at` es una fecha inválida dentro de un JSON válido, rompiendo la ejecución en lugar de tratarse como transitorio. Contrato Fase 1 exige ISO 8601 UTC, por lo que es aceptable, pero conviene envolver en try/catch (Fase 9).
4. **`remote_pid='pending'` + `no_pid` → `process_lost`** — El launcher (`Normalize Launch Result`) fija `remote_pid='pending'` al confirmar el lanzamiento. Si el monitor corre en la ventana previa a que el script escriba `process.pid` (línea 284 de `SCRIPT_PERMISO_DESBLOQUEO.py`, inmediata al arranque), `pidState=no_pid` + `remote_pid` truthy marcaría `failed/process_lost` como falso positivo. Improbable a cadencia 5 min; más probable a 1 min.
5. **9 filas `running` heredadas del launcher** (jobs 8113/8115/8117, `remote_pid=pending`, `timeout_at=null`): la primera pasada real las reconciliará contra el contenedor (probable `failed/process_lost`). Revisarlas/limpiarlas antes de activar (el MCP no expone borrado de filas).
6. **Update Row sin match real en tests** — En 8126-8133 el Update Row corrió con `success` pero con `job_id` sintéticos (`main: [[]]`); la coerción de tipos `date` (`timeout_at`, `updated_at`, `last_checked_at`) contra la tabla viva queda pendiente de la primera pasada real.
7. **Cambios fuera del alcance de Fase 7 en el working tree** — `build/Dockerfile` (UID 568, `usermod --unlock`+`passwd -d`) y `build/docker-compose.yml` (imagen `udocker`, volúmenes `/mnt/Aodnas/Docker/utils-docker/...`) están modificados sin commitear. No son entregables de esta fase (spec los excluye); no deben entrar en el PR de Fase 7 sin revisión separada.
8. **Solapamiento de schedule (anti-criterio)** — No hay configuración explícita anti-solapamiento; con ejecuciones de <1s el riesgo es despreciable, pero el `check_count` se computa read-modify-write (no atómico) si dos ejecuciones coincidieran. Revisar en Fase 9.

## Notas de verificación

- `git status`/`git log` confirman: sin commit de Fase 7 (coherente con plan Grupo 5 sin marcar).
- `roadmap.md` Fase 7 con 5 items `[x]`, coherentes con la implementación verificada.
- `validation.md` marca 3.4 como `[ ]` y el estado de fase como `EN PROGRESO`; los criterios de merge quedan pendientes — correcto.
- `docs/phase-7-monitor.md` y README Fase 7 reflejan fielmente el workflow real.
