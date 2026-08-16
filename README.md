# Automatización de scripts con n8n

## Interfaz de Fase 2

`SCRIPT_PERMISO_DESBLOQUEO.py` tiene una única interfaz CLI, adecuada para SSH,
n8n y procesos sin terminal:

```bash
python3 SCRIPT_PERMISO_DESBLOQUEO.py \
  --token '<token-real>' --timeshift 1400 --job-id exec-123-token-1-run-1
```

Los tres argumentos son obligatorios. `--timeshift` es un número finito de
milisegundos entre `0` y `86400000` inclusive. `--job-id` debe coincidir con
`[A-Za-z0-9][A-Za-z0-9._-]{0,127}` y nunca debe contener el token.
La validación ocurre antes de crear la sesión HTTP.

El token se usa únicamente para la cabecera necesaria de Xiaomi. Se redacta en
mensajes y errores y no se guarda en rutas ni artefactos de esta fase.

## Códigos de salida

| Código | Significado |
|---:|---|
| 0 | Permiso solicitado correctamente |
| 10 | Token caducado, permiso rechazado o respuesta funcional que impide continuar |
| 20 | Argumento ausente/inválido o configuración inválida |
| 30 | Red, HTTP, JSON o respuesta desconocida |

Un estado `is_pass=1` ya concedido también finaliza correctamente sin enviar
otra solicitud. `button_state=2/3` y `apply_result=3/4` son rechazos funcionales
(código `10`) y conservan la fecha de bloqueo cuando la API la proporciona;
`code=100003` se trata como ambiguo y se verifica con una consulta posterior.

Las cuentas bloqueadas y los estados desconocidos nunca conceden permiso de
forma automática. Se conserva la solicitud `apply/bl-auth` permitida por la
misión; no se ejecuta desbloqueo físico ni `fastboot`.

## Artefactos y estados de la Fase 3

Para cada ejecución válida se crea `<work-dir>/<job_id>/` (por defecto,
`jobs/<job_id>/`). El directorio contiene únicamente:

- `status.json`: fuente estructurada de estado, escrita atómicamente.
- `output.log`: salida operativa redactada.
- `process.pid`: PID auxiliar del proceso.

`status.json` incluye `schema_version`, `job_id`, `state`, `exit_code`,
`result`, `error`, `created_at`, `started_at`, `updated_at`, `timeout_at` y
`finished_at`. Los estados son `starting`, `running`, `success`, `failed` y
`timeout`; las transiciones finales no se reutilizan. Un `job_id` existente se
rechaza para evitar que dos trabajos compartan artefactos.

El límite se configura con `--timeout-seconds` y por defecto es de 26 horas.
El estado `timeout` devuelve el código `40`. Los estados `success` y `failed`
conservan, respectivamente, el resultado o el error redactado. El token no
se persiste en ningún artefacto.

## Alcance de esta fase

Esta entrega elimina toda interacción humana y las dependencias de archivos
compartidos. No implementa n8n, Docker, SSH/tmux ni Playwright; esos elementos
pertenecen a fases posteriores.

## Arquitectura prevista

n8n recibirá los secretos, generará un `job_id` por trabajo y lanzará este CLI
por SSH. La persistencia y el monitor se añadirán en Fase 3/4.

## Verificación local

```bash
python3 -m py_compile SCRIPT_PERMISO_DESBLOQUEO.py
python3 SCRIPT_PERMISO_DESBLOQUEO.py --help
python3 -m unittest discover -s tests -v
```
