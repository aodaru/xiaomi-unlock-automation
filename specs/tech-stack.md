# Stack tecnológico

## Stack adoptado

| Capa | Tecnología | Uso |
|---|---|---|
| Orquestación | n8n | Workflow lanzador, monitor y notificaciones |
| Persistencia de trabajos | n8n Data Table | Una fila por proceso, estado y resultado |
| Motor de consulta | Python 3.12 | Adaptación de `SCRIPT_PERMISO_DESBLOQUEO.py` |
| HTTP y tiempo | urllib3, ntplib, pytz | Consulta de la API y sincronización con Pekín |
| Ejecución remota | OpenSSH + tmux | Lanzamiento desacoplado y sesiones largas |
| Empaquetado | Docker Compose | Contenedor reproducible de automatización |
| Red | Puerto SSH del host `2223` | Acceso desde n8n al contenedor |

## Contrato de ejecución

El script deberá aceptar como argumentos o entrada explícita `token`,
`timeshift` y `job_id`. No deberá solicitar entrada por consola. Cada trabajo
escribirá `status.json`, `output.log` y su PID en un directorio propio.

Los estados válidos son `starting`, `running`, `success`, `failed`, `timeout` y
`cancelled`. El estado final debe incluir código de salida, resultado o error y
fechas relevantes.

## Persistencia y duración

- n8n conserva la fila de cada trabajo en Data Table.
- El contenedor mantiene vivos los procesos en segundo plano.
- El monitor consulta trabajos `running` mediante SSH cada 1 o 5 minutos.
- El límite operativo inicial será configurable y tendrá como referencia 26
  horas por trabajo.

## Secretos y datos sensibles

- Las credenciales SSH se inyectan mediante `build/.env` y no se documentan con
  valores reales.
- n8n usará una credencial SSH gestionada por n8n, no contraseñas embebidas en
  comandos del workflow.
- El token completo solo se conservará donde sea estrictamente necesario para
  ejecutar y auditar el trabajo; logs y avisos deberán redactarlo.
- `build/.env` debe permanecer fuera del control de versiones.

## Gaps y decisiones pendientes

- Fijar la versión de n8n y confirmar que Data Table está habilitada en la
  instancia objetivo.
- Definir el formato exacto del resultado de la API para distinguir permisos,
  token caducado y errores transitorios.
- Definir la política de reintentos y cancelación.
- Sustituir las credenciales SSH de ejemplo por un secreto real y considerar
  autenticación por clave.
- Añadir pruebas automatizadas para respuestas de API y transición de estados.
- Definir el canal concreto de notificación del operador.
