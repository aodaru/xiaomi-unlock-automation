# Automatizacion de scripts con n8n

Plan de integracion del script Python con n8n mediante SSH, ejecuciones en segundo plano y una Data Table para controlar trabajos de larga duracion. El contenedor tambien funcionara como base para futuras automatizaciones web con Playwright.

## Objetivo

Permitir que n8n reciba dos tokens y ejecute cada token dos veces, generando cuatro trabajos por ejecucion del workflow, aunque cada proceso pueda tardar mas de un dia.

La ejecucion no mantendra una conexion SSH abierta durante todo el proceso. n8n iniciara los trabajos, cerrara la conexion y otro workflow consultara periodicamente su estado.

## Arquitectura

```text
                    +----------------------+
                    | Workflow lanzador    |
                    | n8n                   |
                    +----------+-----------+
                               |
                 recibe o extrae dos tokens
                               |
                               v
                    +----------------------+
                    | Data Table            |
                    | crea 4 trabajos       |
                    +----------+-----------+
                               |
                               | SSH
                               v
                    +----------------------+
                    | Contenedor automation |
                    | Python + Playwright   |
                    | SSH + tmux            |
                    +----------+-----------+
                               |
                               | estado.json/log
                               v
                    +----------------------+
                    | Workflow monitor      |
                    | n8n por Schedule       |
                    +----------+-----------+
                               |
                         consulta por SSH
                               |
                               v
                    actualiza Data Table
                    y notifica el resultado
```

## Workflow 1: Lanzador

Este workflow inicia los trabajos y finaliza rapidamente.

### Pasos

1. Recibir dos tokens desde un webhook, formulario, credencial u otra fuente.
2. O ejecutar Playwright para iniciar sesion y extraer los tokens.
3. Validar que se obtuvieron los dos valores requeridos.
4. Generar un `execution_id` unico para la ejecucion actual.
5. Crear cuatro filas en la Data Table, dos por cada token.
6. Guardar el token completo y el `timeshift` utilizado.
7. Crear un directorio independiente para cada trabajo en el contenedor.
8. Iniciar cada proceso mediante el nodo SSH en segundo plano.
9. Guardar el PID y cambiar el estado a `running`.

### Identificadores

Cada trabajo debe tener un identificador unico:

```text
execution_id: exec-123
job_id:        exec-123-token-1-run-1
```

Los cuatro trabajos de una ejecucion serian:

```text
exec-123-token-1-run-1
exec-123-token-1-run-2
exec-123-token-2-run-1
exec-123-token-2-run-2
```

Esto evita mezclar logs o estados si se ejecutan varios workflows simultaneamente.

## Workflow 2: Monitor

Este workflow se ejecuta con un `Schedule Trigger`, por ejemplo cada 1 o 5 minutos.

### Pasos

1. Consultar la Data Table buscando filas con `status = running`.
2. Consultar por SSH el estado de cada trabajo.
3. Leer su archivo `status.json` y el log correspondiente.
4. Si sigue ejecutandose, conservar el estado `running`.
5. Si termino correctamente, cambiar a `success`.
6. Si termino con error, cambiar a `failed`.
7. Si supera el limite configurado, cambiar a `timeout`.
8. Guardar el resultado final y la fecha de finalizacion.
9. Enviar una notificacion con el resultado de cada token.

## Data Table

Se recomienda una fila por proceso, no una fila por ejecucion completa.

| Campo | Descripcion | Ejemplo |
|---|---|---|
| `job_id` | Identificador unico del trabajo | `exec-123-token-1` |
| `execution_id` | Identificador del workflow lanzador | `exec-123` |
| `token_index` | Posicion del token | `1` |
| `run_number` | Numero de ejecucion del token | `1` |
| `token` | Token completo utilizado | `valor-del-token` |
| `timeshift` | Desfase utilizado por el script | `1400` |
| `status` | Estado actual del proceso | `running` |
| `pid` | PID del proceso remoto | `845` |
| `started_at` | Fecha de inicio | fecha ISO 8601 |
| `finished_at` | Fecha de finalizacion | fecha ISO 8601 |
| `log_path` | Ruta del log remoto | `/tmp/jobs/exec-123-token-1/output.log` |
| `status_path` | Ruta del estado remoto | `/tmp/jobs/exec-123-token-1/status.json` |
| `result` | Resultado final | texto o JSON |
| `error` | Error final, si existe | texto |
| `last_checked_at` | Ultima consulta del monitor | fecha ISO 8601 |
| `timeout_at` | Limite maximo del trabajo | fecha ISO 8601 |

Los valores completos de los tokens se almacenaran en la Data Table porque forman parte del registro de cada ejecucion.

## Estados de los trabajos

```text
starting -> running -> success
                    -> failed
                    -> timeout
                    -> cancelled
```

## Archivos remotos por trabajo

Cada proceso debe utilizar un directorio aislado:

```text
/tmp/jobs/exec-123-token-1-run-1/
├── token.txt
├── status.json
├── output.log
└── process.pid
```

El archivo de estado debe indicar claramente si el proceso continua activo o ya termino.

Ejemplo mientras esta ejecutandose:

```json
{
  "job_id": "exec-123-token-1",
  "status": "running",
  "pid": 845
}
```

Ejemplo al finalizar correctamente:

```json
{
  "job_id": "exec-123-token-1",
  "status": "success",
  "pid": 845,
  "exit_code": 0,
  "result": "resultado del script"
}
```

No se debe depender solamente del PID, porque un PID puede reutilizarse despues de que el proceso termine.

## Tokens

El workflow no genera tokens ficticios. Los tokens deben provenir de una de estas fuentes:

1. Entrada manual o webhook de n8n.
2. Credenciales o datos proporcionados por otro sistema.
3. Extraccion automatica mediante Playwright.

La estructura esperada para dos tokens es:

```json
{
  "tokens": [
    "token-1",
    "token-2"
  ]
}
```

Cada token recibido se ejecutara dos veces. Si Playwright no devuelve los dos tokens requeridos, el workflow debe detenerse y registrar el error antes de crear trabajos.

## Integracion con Playwright

La extraccion, si se habilita, ocurrira en el Workflow 1 antes de crear los trabajos:

```text
n8n
  |
  | HTTP o Chrome DevTools Protocol
  v
Contenedor Playwright
  |
  ├── abre la pagina
  ├── inicia sesion
  ├── lee las variables JavaScript
  └── devuelve los tokens a n8n
```

El contenedor Playwright deberia exponer una API HTTP o una interfaz compatible con CDP/WebSocket. No se recomienda dar a n8n acceso directo al socket Docker del host.

Playwright se incluira como capacidad reutilizable del contenedor, no como una herramienta exclusiva para extraer estos tokens. Podra utilizarse en futuros workflows para iniciar sesion, navegar, completar formularios, extraer datos, leer variables JavaScript, obtener cookies o `localStorage`, descargar archivos y tomar capturas.

La recomendacion para una implementacion nueva es Playwright por su soporte de Chromium, Firefox y WebKit, sus contextos de navegador aislados, sus esperas automaticas y la posibilidad de guardar estados autenticados mediante `storageState`. Puppeteer continuara siendo una alternativa si ya existe codigo o infraestructura basada en esa herramienta.

## Cambios necesarios en el script

Antes de implementar los workflows, el script debe:

- Aceptar el token directamente, en lugar de pedir el numero de linea con `input()`.
- Aceptar el `timeshift` asociado al token.
- Funcionar sin interaccion humana.
- Eliminar o reemplazar todos los `input()` usados en confirmaciones y errores.
- Escribir un estado inicial `running`.
- Escribir un estado terminal `success` o `failed`.
- Devolver un codigo de salida correcto.
- Guardar el resultado final en `status.json`.
- Tener un limite maximo de ejecucion.
- Evitar mezclar archivos entre ejecuciones.

## Duracion y persistencia

Cada proceso puede esperar casi 24 horas hasta la siguiente medianoche de Pekin y continuar mas tiempo si la API no termina correctamente.

Por eso:

- No se mantendra una conexion SSH abierta durante la espera.
- Los procesos se ejecutaran en segundo plano.
- El monitor consultara el estado periodicamente.
- Cada trabajo tendra un `timeout_at` independiente.
- El contenedor debe permanecer activo durante la ejecucion.
- Los logs y estados deben persistir el tiempo suficiente.
- n8n debe conservar sus ejecuciones y su base de datos.

La ejecucion debe tener un limite operativo, por ejemplo 26 horas:

```text
24 horas de espera maxima
+ 2 horas de margen para la solicitud y las consultas
= 26 horas por trabajo
```

## Acceso SSH

El contenedor expone SSH mediante:

```text
Host: host donde corre Docker
Port: 2223
User: definido en build/.env
Password: definido en build/.env
```

n8n utilizara una credencial SSH para ejecutar comandos de inicio y consulta.

## Contenedor de automatizacion

```text
build/
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh
├── .env
└── .config/tmux/
```

El script principal se copia a `/app/` durante la construccion de la imagen. `token.txt` y `timeshift.txt` se montan desde la carpeta superior como volumenes de solo lectura en la configuracion actual.

La imagen final tendra estas capacidades:

- Python y dependencias del script.
- Node.js, Playwright y navegadores compatibles.
- SSH en el puerto `2223`.
- `tmux` y configuracion para varias sesiones.
- Directorios aislados para trabajos, logs, estados y sesiones de navegador.
- Estructura preparada para agregar mas scripts y automatizaciones.

## Implementacion por fases

### Fase 1: Adaptar el script para n8n

- Recibir el token sin `input()` interactivo.
- Recibir el `timeshift` asociado.
- Aceptar un `job_id` unico.
- Eliminar las confirmaciones interactivas.
- Detectar tokens caducados y utilizables.
- Capturar todas las respuestas relevantes de la API.
- Crear estados `starting`, `running`, `success`, `failed` y `timeout`.
- Escribir `status.json` y `output.log`.
- Devolver codigos de salida consistentes.
- Establecer un limite maximo de ejecucion.
- Probar el script localmente antes de introducir Docker.

### Fase 2: Crear el contenedor de automatizacion

- Instalar Python, dependencias, Node.js, Playwright y navegadores.
- Incorporar el script adaptado.
- Configurar SSH en el puerto `2223`.
- Instalar y configurar `tmux`.
- Preparar soporte para varias sesiones simultaneas.
- Crear directorios de trabajos, logs, estados y sesiones web.
- Mantener la imagen abierta a futuras funciones y scripts.
- Verificar manualmente el acceso SSH y la ejecucion del script.

### Fase 3: Crear el workflow de ejecucion

- Recibir dos tokens.
- Crear cuatro trabajos: dos ejecuciones por cada token.
- Asociar un `timeshift` a cada trabajo.
- Guardar los cuatro trabajos en la Data Table.
- Iniciar los procesos por SSH en segundo plano.
- Registrar PID, rutas, token y estado `running`.
- Verificar que el workflow no espere a que termine cada proceso.

### Fase 4: Crear el workflow de chequeo y resultados

- Ejecutar un `Schedule Trigger` cada 1 o 5 minutos.
- Consultar trabajos con estado `running`.
- Consultar cada proceso por SSH.
- Leer `status.json` y `output.log`.
- Detectar finalizacion, error, timeout o proceso perdido.
- Actualizar la Data Table.
- Guardar resultado, error y fechas.
- Notificar el resultado de cada token y ejecucion.

### Fase 5: Prueba final del ciclo completo

- Recibir dos tokens.
- Ejecutar cuatro trabajos.
- Verificar ejecucion paralela.
- Comprobar procesos de mas de un dia.
- Simular token caducado.
- Simular error de red.
- Simular proceso bloqueado.
- Probar timeout.
- Probar reinicio de n8n.
- Probar desconexion SSH.
- Probar reinicio del contenedor.
- Verificar que los estados y resultados se conservan.

### Fase 6: Automatizacion web con Playwright

- Definir el endpoint HTTP o protocolo CDP/WebSocket.
- Automatizar el inicio de sesion.
- Extraer las variables JavaScript.
- Validar que se obtienen dos tokens.
- Conectar la salida al workflow de ejecucion.
- Reutilizar el contenedor para futuros workflows web.

## Resultado esperado

La solucion final estara compuesta por:

```text
Workflow 1: recibe/extrae dos tokens y lanza cuatro trabajos
Workflow 2: monitoriza trabajos running y notifica resultados
Data Table: almacena token, estado, PID, tiempos y resultado
Contenedor de automatizacion: Python, Playwright, SSH y tmux
SSH: inicia y consulta trabajos remotamente
Playwright: fuente opcional de tokens y plataforma para futuros flujos web
```
