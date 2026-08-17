# Requisitos — Workflow monitor

## Alcance

Esta fase implementa el workflow monitor que se ejecuta periódicamente para
comprobar el estado de los trabajos `running`, leer sus artefactos remotos y
actualizar la Data Table. El monitor es el puente entre la ejecución desacoplada
en el contenedor y la visibilidad en n8n.

### Incluido

- Workflow n8n con `Schedule Trigger` configurable (1 o 5 minutos).
- Consulta a Data Table `script_job_launches` filtrando `state = 'running'`.
- Lectura remota por SSH de `status.json` y `output.log` por cada trabajo.
- Actualización atómica de la fila en Data Table con:
  - `state` (desde `status.json`),
  - `result` (resultado estructurado redactado),
  - `error` (diagnóstico sin token completo),
  - `started_at`, `updated_at`, `finished_at`, `timeout_at`,
  - `exit_code`, `last_checked_at`, `check_count`.
- Detección de timeout: hora actual > `timeout_at` → estado `timeout`.
- Detección de proceso perdido: `process.pid` existe pero proceso no corre →
  estado `failed` con error `process_lost`.
- Transiciones válidas respetando el contrato de Fase 1:
  `running` → `success` | `failed` | `timeout`.
- No re-procesar trabajos ya en estado terminal (`success`, `failed`, `timeout`).

### No incluido

- Notificaciones al operador técnico (Fase 8).
- Diferenciación de tipos de error en notificaciones (Fase 8).
- Campo `last_notified_at` o lógica anti-duplicados de notificación (Fase 8).
- Pruebas de resiliencia: 4 jobs concurrentes, >1 día, reinicios, fallos de red
  (Fase 9).
- Cambios en el script Python `SCRIPT_PERMISO_DESBLOQUEO.py` (ya soporta
  `status.json` y `timeout_at`).
- Cambios en Docker Compose, SSH, tmux (ya validados en Fase 5-6).

## Decisiones

| ID | Decisión | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Schedule Trigger cada 5 minutos por defecto, configurable a 1 min. | Equilibra carga SSH y latencia de detección; 26h / 5min = 312 checks máx. | Schedule fijo a 1 minuto (más carga) o 10 minutos (más latencia). |
| D2 | Leer `status.json` y `output.log` en un solo comando SSH por job. | Minimiza conexiones SSH; el contenedor ya tiene los archivos. | Leer en dos comandos separados o vía SFTP. |
| D3 | Actualizar Data Table solo si el estado cambió o `updated_at` es nuevo. | Evita escrituras innecesarias y conflictos de concurrencia. | Actualizar en cada ciclo incondicionalmente. |
| D4 | `last_checked_at` y `check_count` en Data Table para auditoría. | Permite saber cuándo se vio por última vez y cuántas veces. | Solo confiar en `updated_at` del monitor (pierde info si no hay cambio). |
| D5 | Proceso perdido = PID en `process.pid` pero `kill -0 <pid>` falla. | Detección fiable sin depender de `ps` output parsing. | Parsear `ps aux` o `/proc` (más frágil). |
| D6 | Timeout = `now > timeout_at` (UTC), no depende de PID. | Coherente con contrato Fase 1: `timeout_at` es fuente de verdad. | Timeout solo si PID sigue vivo y pasó tiempo (más complejo). |
| D7 | Workflow monitor independiente del launcher (no sub-workflow). | Desacopla ciclo de vida: launcher = trigger, monitor = polling. | Un solo workflow con dos triggers (webhook + schedule) más acoplado. |

## Contexto

- **Data Table**: `script_job_launches` (ID: `9YfdvJehSSUf9iK2`), creada en Fase 6.
  Columnas actuales: `execution_id`, `job_id`, `token_hash`, `state`,
  `remote_path`, `pid`, `started_at`, `updated_at`, `finished_at`,
  `timeout_at`, `exit_code`, `result`, `error`, `created_at`.
- **Contenedor**: servicio `script` en red `ix-internal-n8n-n8n-net`, volúmenes
  `/workspace/jobs` y `/workspace/videos`. SSH en puerto 2223 del host.
- **Credencial SSH**: n8n credential tipo SSH con clave privada, referenciada
  como `Script container SSH private key` en Fase 6.
- **Python script**: ya escribe `status.json` atómico con `state`,
  `timeout_at`, `exit_code`, `result`, `error`, fechas ISO 8601 UTC.
  Estados válidos: `starting`, `running`, `success`, `failed`, `timeout`.
- **Roadmap Fase 7 items**:
  - Configurar Schedule Trigger cada 1 o 5 minutos.
  - Seleccionar únicamente trabajos `running`.
  - Leer `status.json` y `output.log` por SSH.
  - Actualizar estado, resultado, error y fechas.
  - Detectar proceso perdido y superar `timeout_at`.

## Dependencias

- **Fase 6**: Data Table `script_job_launches` y workflow launcher operativos.
- **Fase 5**: Contenedor con SSH, tmux, Python script adaptado, volúmenes.
- **Fase 3**: Contrato `status.json`, estados, `timeout_at`, códigos de salida.
- **`specs/mission.md`**: Estados persistentes, no exponer tokens, trazabilidad.
- **`specs/tech-stack.md`**: n8n Data Table, SSH + tmux, referencia 26 horas.

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| SSH falla intermitentemente (red, contenedor reiniciando). | Reintento a nivel de nodo n8n (`retryOnFail`, `maxTries=3`); error no bloquea otros jobs. |
| `status.json` leído parcialmente (escritura atómica en script). | Script usa escritura atómica (`replace()`); monitor tolera JSON inválido como error transitorio. |
| Race condition: launcher crea fila `starting` → monitor la ve antes de `running`. | Monitor filtra `state = 'running'` estricto; `starting` se ignora hasta que launcher la pase a `running`. |
| Varios monitores concurrentes (si se solapan ejecuciones). | Schedule Trigger en n8n no solapa ejecuciones por defecto; `check_count` detecta anomalías. |
| Token filtrado en `output.log` o error SSH. | Script ya redacta token en logs; monitor no escribe token en Data Table (solo hash). |
| `timeout_at` en zona horaria distinta a UTC. | Contrato Fase 1 exige ISO 8601 UTC; monitor parsea en UTC. |
| Job tarda >26h y monitor marca timeout pero proceso sigue vivo. | `timeout` es estado terminal; Fase 9 definirá política de kill/limpieza. |
