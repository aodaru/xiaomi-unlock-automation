# Fase 7: workflow monitor

## Recursos n8n

- Workflow: `Script Phase 7 Monitor`
- Workflow ID: `YfNC1o1Qo38RWSQQ`
- Data Table: `script_job_launches`
- Data Table ID: `9YfdvJehSSUf9iK2`
- Credencial SSH: `SSH N8N-SCRIPT` (id `sgAi6cqXq5TrR7ZH`, tipo `sshPrivateKey`)
- Estado inicial: **inactivo** hasta validar contra el contenedor y publicar.

## Columnas nuevas en la Data Table

Añadidas en esta fase para que el monitor pueda escribir el resultado de cada
comprobación:

| Columna | Tipo | Uso |
|---|---|---|
| `updated_at` | date | Última escritura del monitor (siempre, cada ciclo) |
| `finished_at` | date | Instante de finalización cuando el estado es terminal |
| `timeout_at` | date | Límite operativo (ISO 8601 UTC), propagado desde `status.json` o fila |
| `exit_code` | number | Código de salida: `0`, `10`, `20`, `30`, `40` |
| `result` | string | Resultado estructurado redactado (solo estados terminales) |
| `error` | string | Diagnóstico redactado sin token completo |
| `last_checked_at` | date | Timestamp UTC de la última comprobación del monitor |
| `check_count` | number | Contador de comprobaciones (incrementa en 1 cada ciclo) |

## Flujo

1. **Schedule Trigger** (`Every 5 Minutes`) ejecuta el workflow cada 5 minutos
   (configurable a 1 minuto en el nodo). Timezone del workflow: `UTC`.
2. **Data Table Get Rows** consulta `script_job_launches` con filtro
   `state = 'running'` y `returnAll: true`. Si no hay filas, la cadena termina
   sin error (requisito 2.3).
3. **SSH Read Job Artifacts** ejecuta un único comando por job que lee
   `status.json`, las últimas 100 líneas de `output.log` y el marcador de PID
   (`alive` / `lost` / `no_pid`) desde las rutas de la fila. El nodo tiene
   `retryOnFail: true`, `maxTries: 3` y `onError: continueRegularOutput` para
   que un fallo SSH de un job no bloquee los demás.
4. **Decide Job Action** (Code, `runOnceForEachItem`) parsea el `status.json`
   del stdout y decide:
   - `status.json` ilegible o SSH fallido → transitorio: mantiene `running` con
     `error = status_unreadable` (solo refresca `last_checked_at` / `check_count`).
   - Estado terminal en `status.json` (`success`, `failed`, `timeout`) →
     propaga `state`, `result`, `error`, `exit_code`, `finished_at`, `timeout_at`.
   - `running` y `now > timeout_at` (UTC) → `timeout`, `exit_code = 40`.
   - `running`, sin timeout y PID `lost` (o `no_pid` con `remote_pid` no vacío) →
     `failed`, `exit_code = 30`, `error = process_lost`.
   - `running` y todo correcto → mantiene `running` sin tocar `result`/`error`.
5. **Data Table Update Row** actualiza la fila por `job_id` escribiendo `state`,
   `result`, `error`, `exit_code`, `finished_at`, `timeout_at`, `updated_at`,
   `last_checked_at` y `check_count`.

Nunca se escriben tokens completos: el flujo no recibe tokens y el nodo Code
redacta cualquier cadena tipo token que apareciera en `stdout`/`stderr`.

## Configuración requerida

1. La credencial `SSH N8N-SCRIPT` (clave privada) ya está asociada al nodo
   `SSH Read Job Artifacts`.
2. Confirmar que el usuario remoto puede `cat`/`tail` los artefactos de cada
   job en `/workspace/jobs/<job_id>/`.
3. Ejecutar un ciclo contra un job real del launcher y revisar que la fila se
   actualice de `running` a su estado terminal.
4. Publicar (activar) el workflow solo después de la prueba anterior.

## Pruebas realizadas (pin data, nodos Data Table reales)

| Test | Escenario | Ejecución | Resultado |
|---|---|---|---|
| 1 | Job termina `success` → propagar resultado | 8126 | `state=success`, `exit_code=0`, `result` conservado, `finished_at` de `status.json` |
| 2 | `timeout_at` superado | 8127 | `state=timeout`, `exit_code=40`, error `se alcanzó el límite operativo` |
| 3 | Proceso perdido (PID `lost`) | 8128 | `state=failed`, `exit_code=30`, error `process_lost` |
| 4 | 4 jobs running concurrentes | 8129 | Los 4 procesados con sus estados (running/success/timeout/failed), `check_count` incrementado |
| 5 | `status.json` ilegible / ruta ausente | 8131 | Transitorio: `running` con `error=status_unreadable`, `check_count=1` |
| 6 | Sin jobs running | 8133 | Get Rows devuelve 0 items, workflow termina `success` sin actualizaciones |
| 7 | Get Rows real contra tabla viva | 8130 | Filtro selecciona 9 filas `running` reales (launcher 8113/8115/8117); con SSH pinnado vacío no se escribió nada y el flujo terminó sin error |

En todos los tests el nodo `Data Table Update Row` se ejecutó con `success`
(aunque con `job_id` sintéticos no matcheó filas reales, por lo que no escribió
nada: comportamiento esperado en el sandbox).

## Pruebas pendientes

- Ejecución real del comando SSH contra el contenedor (los artefactos existen
  para los jobs 8113/8115/8117; el monitor reconciliará esas 9 filas `running`).
- Verificación de que una fila terminal no se re-procesa en el siguiente ciclo
  con datos reales (mecanismo verificado: filtro `state = 'running'`).
- Confirmación de que `output.log` del contenedor no contiene tokens completos
  (el script ya redacta; comprobación de infraestructura pendiente, Fase 9).
- Timeout del nodo SSH: el nodo `n8n-nodes-base.ssh` v1 no expone un parámetro
  de timeout por comando (docs n8n: solo credential/command/working directory).
  Mitigación aplicada: comando acotado (cat/tail de archivos existentes),
  reintentos (`maxTries=3`), `continueRegularOutput` y un guarda global
  `executionTimeout: 600` (settings del workflow).