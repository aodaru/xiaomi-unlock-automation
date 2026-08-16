# Requisitos - Estados y resultados del script

## Alcance

Esta fase anade persistencia local y trazabilidad al motor Python de la Fase 2.
Cada ejecucion debe publicar su estado y resultado en un directorio aislado,
para que un monitor posterior pueda consultar el trabajo sin mantener una
sesion SSH abierta.

### Incluido

- Escritura de `starting` antes de iniciar consultas o esperas.
- Escritura de `running` antes de la espera prolongada.
- Escritura de `success` con el resultado estructurado de la consulta.
- Escritura de `failed` con error redactado y codigo de salida.
- Escritura de `timeout` al alcanzar un limite configurable.
- Aislamiento de `status.json`, `output.log` y `process.pid` por `job_id`.
- Contrato estable para que el monitor de la Fase 7 pueda leer estados y fechas.
- Pruebas locales sin tokens reales ni llamadas reales a Xiaomi.
- Actualizacion de `README.md` y de las pruebas afectadas.

### No incluido

- Data Table, workflows n8n o notificaciones; corresponden a las Fases 6-8.
- Construccion o cambios de Docker Compose, SSH o tmux; corresponden a la Fase 5.
- Monitor remoto periodico, deteccion de procesos perdidos o reintentos globales.
- Extraccion de tokens mediante Playwright.
- Desbloqueo fisico del telefono o comandos `fastboot`.
- Persistencia del token en `status.json`, `output.log`, `process.pid` o rutas.

## Decisiones

| ID | Decision | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Cada trabajo tendra un directorio derivado de un `job_id` validado y seguro. | Evita colisiones y permite consultar trabajos de forma independiente. | Usar un directorio compartido con nombres genericos. |
| D2 | `status.json` sera la fuente estructurada de verdad; `output.log` sera solo salida operativa. | Facilita el monitor y evita parsear texto para conocer el estado. | Inferir el estado desde el PID o el contenido del log. |
| D3 | Las escrituras de estado seran atomicas y conservaran la ultima version valida. | Un monitor no debe leer JSON parcialmente escrito. | Sobrescribir directamente el archivo final. |
| D4 | El timeout sera configurable y tendra como referencia 26 horas. | El trabajo puede superar un dia, pero necesita un limite observable. | Usar un limite fijo embebido o depender solo del proceso. |
| D5 | Los errores y resultados se redactaran antes de persistirse. | Los artefactos son duraderos y pueden ser leidos por operadores. | Guardar excepciones completas aunque incluyan cabeceras o tokens. |
| D6 | `process.pid` sera un dato auxiliar, no la unica prueba de vida. | Un PID puede reciclarse o desaparecer tras un reinicio. | Tratar un PID existente como estado `running` definitivo. |

## Contexto

`SCRIPT_PERMISO_DESBLOQUEO.py` ya acepta `token`, `timeshift` y `job_id` por CLI,
valida las entradas y devuelve los codigos `0`, `10`, `20` y `30`. Actualmente
solo imprime el resultado y la Fase 2 excluye expresamente los tres artefactos.
La Fase 3 debe conservar la consulta API y la proteccion de secretos, pero
envolver el ciclo de ejecucion con estados persistentes.

La arquitectura de `specs/mission.md` exige ejecuciones no interactivas,
aislamiento por trabajo, estados explicitos y resultados auditables. Segun
`specs/tech-stack.md`, el motor es Python 3.12, el limite de referencia es de
26 horas y el monitor futuro consultara los estados mediante SSH.

### Archivos candidatos

- `SCRIPT_PERMISO_DESBLOQUEO.py`: ciclo de estados, timeout y artefactos.
- `tests/test_cli.py`: pruebas de contrato, aislamiento y errores.
- `README.md`: interfaz de ejecucion y esquema de resultados.
- `specs/roadmap.md`: marcar la Fase 3 cuando se implemente.

No se presupone modificar `build/docker-compose.yml` ni
`build/docker-entrypoint.sh` en esta fase.

## Dependencias

- **Fase 1**: estados validos, codigos de salida y clasificacion de respuestas.
- **Fase 2**: interfaz CLI no interactiva y redaccion del token.
- **Fase 4**: consumira este contrato para pruebas locales del motor.
- **Fase 7**: leera `status.json` y `output.log` mediante el workflow monitor.
- **`specs/mission.md`**: persistencia, trazabilidad y secretos operativos.
- **`specs/tech-stack.md`**: Python 3.12, aislamiento y limite de 26 horas.

## Riesgos identificados

| Riesgo | Mitigacion |
|--------|------------|
| Un lector observa un JSON incompleto durante una escritura. | Escribir en temporal dentro del mismo directorio y reemplazar de forma atomica. |
| El proceso muere antes de escribir el estado final. | Mantener `running`, registrar el PID y dejar la deteccion de proceso perdido al monitor. |
| El timeout deja una llamada remota o un proceso activo. | Definir la señal y la politica de terminacion antes de marcar `timeout`; probarla localmente. |
| Dos ejecuciones reutilizan un `job_id`. | Validar el identificador y rechazar directorios existentes salvo una politica explicita de reanudacion. |
| Una excepcion contiene el token completo. | Aplicar la funcion de redaccion antes de imprimir o serializar cualquier error. |
| El limite de 26 horas no coincide con la espera efectiva. | Persistir `started_at`, `timeout_at` y usar un valor configurable validado. |
