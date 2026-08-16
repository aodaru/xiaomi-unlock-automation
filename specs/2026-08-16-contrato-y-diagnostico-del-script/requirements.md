# Requisitos - Contrato y diagnostico del script

## Alcance

Esta fase documenta el contrato que necesitara el motor Python para ser
ejecutado por n8n de forma no interactiva y monitorizado durante trabajos de
larga duracion. El diagnostico se basa en `SCRIPT_PERMISO_DESBLOQUEO.py`,
`README.md`, `specs/mission.md` y `specs/tech-stack.md`.

### Incluido

- Documentacion de las entradas `token`, `timeshift` y `job_id`.
- Inventario del comportamiento interactivo y de las dependencias de archivos.
- Esquema minimo y reglas de escritura de `status.json`.
- Estados validos, transiciones y condiciones de finalizacion.
- Tabla de codigos de salida previstos para la siguiente fase.
- Clasificacion de respuestas conocidas de los endpoints Xiaomi usados por el
  script.
- Definicion del limite maximo por trabajo, tomando 26 horas como referencia
  operativa inicial.
- Identificacion de riesgos y decisiones que deben resolverse antes de adaptar
  el script.

### No incluido

- Cambios en `SCRIPT_PERMISO_DESBLOQUEO.py`.
- Creacion o modificacion de workflows n8n o Data Table.
- Construccion del contenedor, SSH, tmux o Docker Compose.
- Extraccion de tokens mediante Playwright.
- Desbloqueo físico posterior en el teléfono o ejecución de comandos `fastboot`.
- Pruebas de integracion contra la API Xiaomi con tokens reales.

## Decisiones

| ID | Decision | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | El contrato futuro recibira `token`, `timeshift` y `job_id` como entradas explicitas. | Es el contrato indicado por `specs/tech-stack.md` y permite aislar cada trabajo. | Seleccionar una linea de `token.txt` y `timeshift.txt` dentro del proceso. |
| D2 | `job_id` sera obligatorio y se propagara a todos los artefactos del trabajo. | Evita mezclar cuatro ejecuciones concurrentes y permite trazabilidad. | Identificar trabajos solo por PID o por nombre del token. |
| D3 | Los estados persistentes seran `starting`, `running`, `success`, `failed`, `timeout` y `cancelled`. | Coincide con el contrato tecnico y permite que el monitor sobreviva a la perdida del proceso. | Inferir el estado unicamente desde el PID o el contenido del log. |
| D4 | El limite inicial de referencia sera de 26 horas por trabajo y debera quedar configurable. | El script puede esperar hasta el siguiente dia en horario de Pekin; se reserva margen operativo. | Mantener un proceso sin limite o depender del timeout de SSH. |
| D5 | Esta fase distingue respuestas observadas de respuestas confirmadas por documentacion oficial o pruebas controladas. | El script no contiene un contrato formal de la API y los valores pueden cambiar. | Tratar cualquier respuesta no reconocida como exito o permiso. |
| D6 | `apply/bl-auth` forma parte del flujo permitido: envía la solicitud remota de autorización. | La misión distingue la solicitud API del desbloqueo físico posterior en el teléfono. | Eliminar la llamada y limitar el sistema a una consulta de estado. |

## Contexto

El script actual, en `SCRIPT_PERMISO_DESBLOQUEO.py`, presenta estas
caracteristicas relevantes:

- Solicita mediante `input()` el numero de linea del token.
- Lee el token y el `timeshift` desde archivos locales.
- Genera un `device_id` por ejecucion y consulta la API Xiaomi con
  `new_bbs_serviceToken`.
- Consulta `sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state` antes de
  esperar al horario objetivo.
- Espera hasta la medianoche de Pekin menos el desfase configurado.
- Reintenta solicitudes POST dentro de un bucle sin limite de tiempo definido.
- No escribe `status.json`, `output.log` ni `process.pid` por trabajo.
- Usa `exit()` e `input()` en varias rutas de error o confirmacion, sin contrato
  de codigo de salida.

El contrato documentado debera respetar la mision del proyecto: conservar
estado persistente, no exponer tokens en logs o notificaciones, y devolver un
resultado trazable sin mantener una sesion SSH abierta.

### Contrato de entradas

| Campo | Tipo | Obligatorio | Regla |
|---|---|---:|---|
| `token` | cadena | Si | No vacia; se trata como secreto y nunca se imprime completo. |
| `timeshift` | numero | Si | Desfase en milisegundos, convertible a numero finito y con rango acordado antes de implementar. |
| `job_id` | cadena | Si | Identificador no vacio, estable y seguro para usar como componente de ruta. |

La fuente exacta de argumentos (CLI, variables de entorno o entrada equivalente)
se decidira en la Fase 2, pero no se permitira lectura interactiva.

### Esquema minimo de `status.json`

```json
{
  "job_id": "exec-123-token-1-run-1",
  "status": "running",
  "pid": 845,
  "started_at": "2026-08-16T00:00:00Z",
  "updated_at": "2026-08-16T00:00:01Z",
  "finished_at": null,
  "exit_code": null,
  "result": null,
  "error": null,
  "timeout_at": "2026-08-17T02:00:00Z"
}
```

Reglas del esquema:

- `job_id` y `status` son obligatorios en toda escritura.
- Las fechas usan ISO 8601 en UTC.
- `started_at` se fija al iniciar el trabajo; `updated_at` cambia en cada
  transicion o actualizacion relevante.
- `finished_at` y `exit_code` son obligatorios en estados terminales.
- `result` solo contiene un resultado estructurado y redactado; `error` solo
  contiene un diagnostico util sin token completo.
- `timeout_at` se calcula por trabajo y no se sustituye por el timeout de SSH.
- El archivo debe escribirse de forma que el monitor no lea JSON parcialmente.

### Estados y transiciones

```text
starting -> running -> success
                   -> failed
                   -> timeout
                   -> cancelled
```

Solo `starting` puede pasar a `running`, y solo `running` puede pasar a un
estado terminal. Los estados terminales no tienen transiciones posteriores.
`cancelled` queda reservado para una cancelacion explicita implementada en una
fase posterior; no se inferira por la desaparicion del PID.

### Codigos de salida

Los valores son el contrato previsto para la adaptacion del script; el codigo
actual no los implementa.

| Codigo | Estado | Significado |
|---:|---|---|
| `0` | `success` | Consulta completada y resultado valido, incluido permiso disponible o bloqueado. |
| `10` | `failed` | Token caducado, permiso rechazado o respuesta funcional que impide continuar. |
| `20` | `failed` | Entrada invalida, configuracion ausente o `job_id` inseguro. |
| `30` | `failed` | Error de red, HTTP, JSON o respuesta desconocida despues de la politica de reintentos. |
| `40` | `timeout` | Se alcanzo `timeout_at` antes de obtener un resultado final. |
| `50` | `cancelled` | El trabajo fue cancelado explicitamente. |

El monitor debe tratar cualquier codigo distinto de los anteriores como
`failed` con causa `unknown_exit_code` y conservar el valor observado para
diagnostico.

### Clasificacion inicial de respuestas Xiaomi

Esta tabla refleja lo que el script actual interpreta; no constituye aun una
garantia de la API.

| Endpoint o codigo/campo | Interpretacion actual | Clasificacion contractual inicial |
|---|---|---|
| `bl-switch/state`, `code=100004` | Cookie/token expirado. | `failed`, causa `token_expired`. |
| `bl-switch/state`, `is_pass=4`, `button_state=1` | Puede enviar solicitud. | Resultado `permission_available`. |
| `bl-switch/state`, `is_pass=4`, `button_state=2` | Bloqueado hasta `deadline_format`; hoy solicita confirmacion. | Resultado `permission_blocked`, sin interaccion en automatizacion. |
| `bl-switch/state`, `is_pass=4`, `button_state=3` | Cuenta con menos de 30 dias; hoy solicita confirmacion. | Resultado `permission_blocked`, causa `account_too_new`. |
| `bl-switch/state`, `is_pass=1` | Solicitud aprobada previamente. | Resultado `permission_available`, sujeto a confirmacion de negocio. |
| `apply/bl-auth`, `code=0`, `apply_result=1` | Solicitud aprobada y luego verifica estado. | Solicitud remota aceptada; después verificar `bl-switch/state`. |
| `apply/bl-auth`, `code=0`, `apply_result=3` | Limite alcanzado hasta una fecha. | Resultado `permission_blocked`, con `deadline_format`. |
| `apply/bl-auth`, `code=0`, `apply_result=4` | Bloqueo hasta una fecha. | Resultado `permission_blocked`, con `deadline_format`. |
| `code=100001` | Peticion rechazada. | `failed`, causa `request_rejected`. |
| `code=100003` | Puede haber sido aprobada; vuelve a verificar. | Respuesta ambigua; requiere consulta posterior acotada. |
| Codigo desconocido, codigo ausente o JSON invalido | El script solo imprime el problema. | `failed`, causa `unknown_response` o `invalid_response`. |
| Respuesta vacia, timeout o error de red | El script devuelve `None` o reintenta. | Error transitorio sujeto a politica de reintentos de Fase 2. |

## Dependencias

- **Fase 2**: Implementara la entrada no interactiva y las validaciones del
  contrato definido aqui.
- **Fase 3**: Implementara `status.json`, estados, resultados, timeout y
  aislamiento de archivos por trabajo.
- **Fase 4**: Convertira este diagnostico en pruebas locales del motor.
- **`specs/mission.md`**: Permite la solicitud remota mediante la API, pero no
  el desbloqueo físico posterior ni comandos `fastboot`.
- **`specs/tech-stack.md`**: Define Python 3.12, ejecucion remota desacoplada,
  estados validos y referencia de 26 horas.

## Riesgos identificados

| Riesgo | Mitigacion |
|--------|------------|
| La API Xiaomi puede cambiar codigos o campos sin aviso. | Conservar respuesta redactada, clasificar desconocidos como error y cubrir casos con pruebas controladas. |
| La solicitud remota mediante `apply/bl-auth` puede confundirse con el desbloqueo físico. | Mantener explícita la separación entre la llamada API y el desbloqueo posterior en el teléfono. |
| Un bucle de reintento sin limite puede superar la duracion del contenedor. | Hacer configurable `timeout_at` y convertir su vencimiento en `timeout`. |
| Los `input()` pueden bloquear un trabajo remoto indefinidamente. | Eliminar toda interaccion en Fase 2 y representar decisiones como estados/resultados. |
| El token puede filtrarse en logs, errores o rutas. | Redactar logs, evitar el token en nombres de archivo y limitar su persistencia a los lugares estrictamente necesarios. |
| Un PID reutilizado puede hacer parecer activo otro proceso. | Usar `status.json` y `job_id` como fuente primaria; el PID solo es evidencia auxiliar. |
