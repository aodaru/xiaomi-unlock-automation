# Requisitos - Pruebas locales del motor

## Alcance

Esta fase establece una suite local y determinista para demostrar que el motor
Python cumple los contratos definidos en las Fases 1, 2 y 3. Las pruebas deben
ejecutarse sin interaccion humana, sin tokens reales y sin llamadas a Xiaomi.

### Incluido

- Prueba de la interfaz CLI y de todas sus validaciones de entrada.
- Verificacion de ejecucion sin stdin, confirmaciones ni archivos compartidos.
- Casos de token caducado, cuenta bloqueada, permiso ya concedido y estados no
  permitidos.
- Casos de error de red, HTTP, JSON y respuesta desconocida.
- Verificacion de `code=100003` y de su consulta posterior.
- Verificacion de codigos de salida `0`, `10`, `20`, `30` y `40` cuando aplique.
- Verificacion de estados, marcas de tiempo, resultado/error y artefactos por
  `job_id`.
- Pruebas de timeout, interrupcion, persistencia defectuosa y aislamiento de
  trabajos concurrentes.
- Fixtures y dobles locales que hagan reproducibles las respuestas y esperas.
- Actualizacion de `README.md` y de `specs/roadmap.md` al cerrar la fase.

### No incluido

- Tokens reales, credenciales reales o acceso de red a Xiaomi.
- Construccion o cambios de Docker Compose, SSH, tmux o directorios persistentes
  del contenedor; corresponden a la Fase 5.
- Data Table, workflows n8n, monitor remoto o notificaciones.
- Extraccion de tokens mediante Playwright.
- Desbloqueo fisico del telefono o comandos `fastboot`.
- Pruebas de disponibilidad, rendimiento o carga de la infraestructura remota.

## Decisiones

| ID | Decision | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Las pruebas sustituiran la red y el reloj por dobles controlados. | Permite probar todas las ramas sin depender de Xiaomi, DNS o tiempo real. | Ejecutar pruebas contra la API real. |
| D2 | Cada caso usara un directorio temporal y un `job_id` unico. | Evita contaminacion entre pruebas y valida el aislamiento exigido. | Compartir `jobs/` entre casos. |
| D3 | La ausencia de stdin sera parte explicita de la prueba de ejecucion. | El motor debe ser apto para n8n, SSH y segundo plano. | Simular confirmaciones mediante entrada automatica. |
| D4 | Los escenarios se verificaran desde el codigo de salida y `status.json`. | Ambos contratos son observables para el lanzador y el monitor futuro. | Inferir el resultado desde texto de `output.log`. |
| D5 | Los secretos de prueba seran marcadores no validos y siempre se comprobara su redaccion. | Reduce el riesgo de fuga y prueba la proteccion contractual. | Incluir tokens validos anonimizados. |
| D6 | Los errores de persistencia nunca podran producir un `success` falso. | La persistencia es necesaria para que el resultado sea auditable. | Considerar suficiente el codigo de salida del proceso. |

## Contexto

`SCRIPT_PERMISO_DESBLOQUEO.py` recibe `token`, `timeshift` y `job_id` por CLI,
clasifica respuestas de Xiaomi y escribe `status.json`, `output.log` y
`process.pid` en el directorio aislado del trabajo. La referencia operativa del
timeout es de 26 horas y el estado `timeout` usa el codigo `40`, segun la
documentacion actual de `README.md`.

La suite debe reforzar los contratos de `specs/mission.md` y
`specs/tech-stack.md`: ejecuciones no interactivas, secretos fuera de logs,
estados persistentes y resultados auditables sin una sesion SSH abierta. Los
casos deben cubrir las rutas que la revision previa identifico como faltantes,
incluidos `code=100003`, respuestas JSON/red y los codigos desde `main`.

### Archivos candidatos

- `SCRIPT_PERMISO_DESBLOQUEO.py`: puntos de inyeccion o ajustes minimos para
  hacer deterministas las pruebas.
- `tests/test_cli.py`: casos de CLI, respuestas, estados, timeout y secretos.
- `README.md`: instrucciones y alcance de la verificacion local.
- `specs/roadmap.md`: marcar los items de la Fase 4 al finalizar.

No se presupone modificar `build/docker-compose.yml`, `build/Dockerfile` ni
workflows n8n en esta fase.

## Dependencias

- **Fase 1**: clasificacion de respuestas, estados y codigos de salida.
- **Fase 2**: CLI no interactivo, validaciones y redaccion de secretos.
- **Fase 3**: artefactos, timeout y aislamiento por `job_id`.
- **Fase 5**: consumira la confianza local obtenida antes de empaquetar el motor.
- **`specs/mission.md`**: exige automatizacion, trazabilidad y proteccion de tokens.
- **`specs/tech-stack.md`**: fija Python 3.12 y el timeout de referencia.

## Riesgos identificados

| Riesgo | Mitigacion |
|--------|------------|
| Un doble no reproduce una respuesta real y oculta una rama defectuosa. | Mantener fixtures para cada clasificacion documentada y revisar el contrato junto al README. |
| Una prueba depende accidentalmente de red, stdin o tiempo real. | Ejecutar con stdin cerrado, aislar el transporte y usar reloj/espera controlados. |
| Las pruebas dejan artefactos o secretos en el repositorio. | Usar temporales, marcadores invalidos y aserciones de limpieza/redaccion. |
| Un timeout deja un proceso activo. | Simular la espera, comprobar el estado final y verificar la politica de terminacion. |
| La concurrencia produce resultados intermitentes. | Usar `job_id` y directorios unicos, sincronizacion explicita y reintentos prohibidos en la prueba. |
