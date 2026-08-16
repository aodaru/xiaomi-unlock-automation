# Requisitos - Entrada no interactiva

## Alcance

Esta fase adapta `SCRIPT_PERMISO_DESBLOQUEO.py` para que pueda ser lanzado por
n8n, SSH o un proceso en segundo plano sin depender de una persona leyendo o
respondiendo a la consola. Implementa el contrato de entradas definido en la
Fase 1 y prepara el motor para las fases posteriores.

### Incluido

- Recepcion explicita de `token`, `timeshift` y `job_id`.
- Validacion de las tres entradas antes de iniciar consultas a la API.
- Eliminacion de la seleccion interactiva y de la lectura de
  `token.txt`/`timeshift.txt`.
- Eliminacion de todos los `input()` y de las rutas que esperan Enter o una
  confirmacion `Yes/No`.
- Tratamiento determinista de token caducado, cuenta bloqueada y respuestas no
  reconocidas como resultados no interactivos.
- Codigos de salida coherentes con el contrato documentado en la Fase 1.
- Redaccion del token en errores, mensajes y salida operativa.
- Actualizacion de `README.md` o de esta documentacion cuando la interfaz final
  quede decidida.

### No incluido

- Escritura de `status.json`, `output.log` o `process.pid`; corresponde a la
  Fase 3.
- Implementacion del timeout operativo y de las transiciones persistentes de
  estado.
- Workflows n8n, Data Table, Docker Compose, SSH o tmux.
- Pruebas contra la API Xiaomi con tokens reales.
- Extraccion de tokens mediante Playwright.
- Desbloqueo fisico del telefono o comandos `fastboot`.

## Decisiones

| ID | Decision | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | El motor recibira los tres valores como entradas explicitas y fallara si falta cualquiera. | Es el contrato de `specs/tech-stack.md` y permite que cada trabajo sea reproducible. | Inferir valores desde archivos compartidos o stdin interactivo. |
| D2 | La validacion ocurrira antes de crear la sesion HTTP o consultar la API. | Evita trabajos parcialmente iniciados por configuracion invalida. | Detectar errores durante la primera solicitud. |
| D3 | Los casos que hoy preguntan si continuar se resolveran sin interaccion y no concederan permiso por defecto. | Un proceso automatizado no puede asumir consentimiento humano ni quedar bloqueado. | Preguntar `Yes/No` o continuar siempre. |
| D4 | `job_id` sera obligatorio, no vacio y seguro como identificador logico; no incluira el token. | Mantiene trazabilidad y evita filtrar secretos. | Derivar el identificador del token o del PID. |
| D5 | La interfaz concreta de transporte podra ser CLI o una entrada equivalente, pero quedara documentada y sera unica para la implementacion. | Permite integracion con SSH/n8n sin fijar una capa de orquestacion en esta fase. | Soportar varias interfaces ambiguas o conservar compatibilidad interactiva. |

## Contexto

El script actual solicita un numero de linea con `input()`, lee el token y el
desfase desde `token.txt` y `timeshift.txt`, y vuelve a solicitar confirmacion
en varias respuestas de la API. Tambien espera Enter en rutas de error. Estas
conductas son incompatibles con ejecuciones desacopladas de n8n.

El contrato de la Fase 1 establece:

- `token`: cadena no vacia y secreta.
- `timeshift`: numero finito expresado en milisegundos, con rango definido por
  la implementacion antes de aceptar el valor.
- `job_id`: cadena no vacia, estable y segura para trazabilidad.
- Codigo `20` para entrada invalida o configuracion ausente.
- Codigo `10` para token caducado, permiso rechazado u otra respuesta funcional
  que impida continuar.
- Codigo `30` para error de red, HTTP, JSON o respuesta desconocida tras la
  politica de reintentos.

El token puede aparecer en la cabecera HTTP porque es necesario para la API,
pero no debe aparecer completo en excepciones, consola, documentacion ni
identificadores. La solicitud `apply/bl-auth` sigue permitida por la mision; el
desbloqueo posterior en el telefono sigue fuera de alcance.

## Dependencias

- **Fase 1**: Contrato de entradas, clasificacion inicial de respuestas y
  codigos de salida.
- **Fase 3**: Consumira los resultados y codigos para escribir estados
  persistentes y aislar los artefactos por trabajo.
- **`specs/mission.md`**: Exige ejecuciones no interactivas y proteccion de
  secretos.
- **`specs/tech-stack.md`**: Define Python 3.12 y el contrato de ejecucion.

## Riesgos identificados

| Riesgo | Mitigacion |
|--------|------------|
| Un `timeshift` fuera de rango puede provocar una espera incorrecta o negativa. | Validar finitud, unidad y rango antes de iniciar; rechazar valores no definidos. |
| Una respuesta bloqueada puede interpretarse como permiso si se elimina la confirmacion sin reemplazo. | Convertirla en resultado bloqueado y codigo no exitoso, sin continuar por defecto. |
| Excepciones de librerias o respuestas HTTP pueden incluir cabeceras con el token. | Centralizar la redaccion antes de imprimir o propagar errores. |
| El script puede bloquearse por un `input()` residual. | Buscar todas las llamadas y probar la ejecucion sin stdin disponible. |
| Cambiar la interfaz puede romper instrucciones del README. | Actualizar la documentacion de invocacion en la misma fase y validar ejemplos sin secretos. |
