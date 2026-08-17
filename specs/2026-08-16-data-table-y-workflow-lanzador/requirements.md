# Requisitos - Data Table y workflow lanzador

## Alcance

Esta fase define e implementa el workflow n8n que recibe exactamente dos
tokens, crea cuatro trabajos independientes y los lanza en el contenedor remoto
sin mantener una sesion SSH abierta durante la espera.

### Incluido

- Contrato de entrada con exactamente dos tokens y `timeshift` validado.
- Generacion de un `execution_id` y cuatro `job_id` unicos por ejecucion.
- Definicion de la Data Table con una fila por trabajo.
- Creacion remota de `/workspace/jobs/<job_id>/` para cada trabajo.
- Lanzamiento del CLI Python mediante la credencial SSH gestionada por n8n y
  una sesion desacoplada.
- Registro del PID remoto, rutas, estado `running` y fechas de lanzamiento.
- Validacion de fallos parciales, aislamiento y redaccion de secretos.
- Exportacion/documentacion del workflow y actualizacion del README cuando
  corresponda.

### No incluido

- Monitorizacion periodica de trabajos; corresponde a la Fase 7.
- Lectura de `status.json` y `output.log` despues del lanzamiento, salvo la
  comprobacion minima necesaria para confirmar la preparacion inicial.
- Notificaciones al operador y resultados por token; corresponden a la Fase 8.
- Reintentos, cancelacion y politica completa de timeout; se documentan como
  decisiones pendientes o se resuelven en fases posteriores.
- Extraccion de tokens mediante Playwright.
- Desbloqueo fisico del telefono, `fastboot` o comandos arbitrarios.

## Decisiones

| ID | Decision | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Una entrada valida contiene exactamente dos tokens no vacios, distintos y validables antes de crear trabajos. | Evita ejecuciones parciales y fija la cardinalidad requerida por la primera entrega. | Aceptar una lista de longitud variable o completar tokens faltantes. |
| D2 | Cada ejecucion genera un `execution_id` y exactamente cuatro `job_id`; dos trabajos corresponden a cada token. | Permite trazabilidad y concurrencia determinista sin usar secretos en identificadores. | Reutilizar un `job_id`, derivarlo del token o crear trabajos bajo demanda. |
| D3 | La Data Table conserva una fila por trabajo con `token_fingerprint`, no el token completo. | La tabla sirve para estado y auditoria; el secreto solo es necesario durante el lanzamiento. | Persistir el token completo en una columna de n8n. |
| D4 | Los `job_id` solo usan el patron seguro del CLI y las rutas remotas son constantes bajo `/workspace/jobs`. | Evita traversal, colisiones y comandos construidos con datos no confiables. | Permitir nombres o rutas recibidos desde la entrada. |
| D5 | El proceso se inicia con SSH desacoplado mediante `tmux`; n8n espera solo la preparacion y el acuse de lanzamiento. | Los trabajos pueden durar mas de un dia sin depender de una conexion SSH abierta. | Ejecutar el CLI en primer plano dentro del nodo SSH. |
| D6 | Una fila pasa a `running` solo tras obtener un PID y confirmar que el directorio remoto existe. | Impide que el monitor futuro interprete como activo un trabajo que nunca se lanzo. | Marcar todas las filas como `running` antes de ejecutar SSH. |
| D7 | Los fallos parciales conservan las filas creadas y usan un estado de fallo de lanzamiento distinto de los estados finales del motor. | Mantiene trazabilidad sin falsificar `failed` como resultado de Xiaomi. | Borrar filas fallidas o marcar trabajos no iniciados como `running`. |

## Contexto

El motor `SCRIPT_PERMISO_DESBLOQUEO.py` acepta `--token`, `--timeshift` y
`--job-id`, crea los artefactos en un directorio propio y rechaza `job_id`
existentes. Los estados del motor son `starting`, `running`, `success`,
`failed`, `timeout` y `cancelled`; el workflow de esta fase solo debe registrar
la preparacion y el lanzamiento, no inferir un resultado final.

El contenedor se publica como `script` en la red externa
`ix-internal-n8n-n8n-net`, mantiene `/workspace/jobs` persistente y expone SSH
por el puerto del host definido para n8n (`2223`). La credencial SSH debe ser una
credencial gestionada por n8n y no una contraseña o clave escrita en el
workflow.

### Columnas de la Data Table

| Columna | Tipo | Requerido | Uso |
|---|---|---:|---|
| `execution_id` | string | Si | Agrupa los cuatro trabajos de una ejecucion. |
| `job_id` | string | Si | Identificador remoto unico y trazable. |
| `token_slot` | integer | Si | Posicion 1 o 2 del token de entrada. |
| `token_fingerprint` | string | Si | Huella no reversible para correlacionar sin exponer el token. |
| `state` | string | Si | `starting`, `running` o estado de lanzamiento fallido. |
| `remote_dir` | string | Si | Ruta fija `/workspace/jobs/<job_id>`. |
| `status_path` | string | Si | Ruta de `status.json` esperada. |
| `output_path` | string | Si | Ruta de `output.log` esperada. |
| `pid_path` | string | Si | Ruta de `process.pid` esperada. |
| `remote_pid` | integer/string | No | PID devuelto por el lanzamiento desacoplado. |
| `timeshift` | integer | Si | Valor validado enviado al CLI. |
| `created_at` | datetime/string ISO 8601 | Si | Alta de la fila. |
| `launched_at` | datetime/string ISO 8601 | No | Confirmacion del lanzamiento. |
| `launch_error` | string | No | Error tecnico redactado, sin token ni comando sensible. |

El token completo no se almacena en la Data Table ni se incluye en `execution_id`,
`job_id`, rutas, mensajes o errores. El workflow debe evitar que la
configuracion de ejecucion de n8n persista el payload secreto mas alla de lo
necesario para completar el lanzamiento.

## Dependencias

- **Fase 1**: contrato de argumentos, estados y codigos del motor.
- **Fase 2**: entrada no interactiva y validacion/redaccion de tokens.
- **Fase 3**: artefactos persistentes y aislamiento por `job_id`.
- **Fase 4**: pruebas locales del motor y sus limites.
- **Fase 5**: imagen `script`, SSH, tmux, red externa y `/workspace/jobs`.
- **Fase 7**: consumira las filas `running` y los artefactos remotos.
- **`specs/mission.md`**: exige trazabilidad, no interaccion y proteccion de secretos.
- **`specs/tech-stack.md`**: fija n8n Data Table, OpenSSH, tmux y timeout operativo.

## Riesgos identificados

| Riesgo | Mitigacion |
|--------|------------|
| El workflow persiste el token completo en el historial de n8n o en una fila. | Usar el token solo en el nodo de lanzamiento, almacenar una huella y revisar ejecuciones anonimizadas. |
| SSH devuelve exito antes de que tmux cree el proceso o se pierde el PID. | Hacer la creacion del directorio y el lanzamiento atomicos por trabajo, devolver PID y registrar cualquier acuse incompleto como fallo de lanzamiento. |
| Un fallo en uno de los cuatro trabajos deja una ejecucion inconsistente. | Crear las cuatro filas primero, conservar todas y registrar el resultado individual de cada intento. |
| El shell interpreta caracteres del token o parametros. | Validar formato, no interpolar comandos arbitrarios y usar quoting seguro en el comando remoto. |
| Reejecutar el workflow genera colisiones o trabajos duplicados. | Generar identificadores nuevos, rechazar directorios existentes y documentar la politica de reejecucion. |
| La Data Table no tiene el tipo o disponibilidad esperados en la instancia. | Validar columnas en un entorno de prueba y bloquear el lanzamiento si la tabla no esta preparada. |
