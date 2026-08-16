# Plan - Contrato y diagnostico del script

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Inventario del comportamiento actual

1. [ ] Revisar el flujo de entrada, lectura de archivos, llamadas HTTP y finalizacion de `SCRIPT_PERMISO_DESBLOQUEO.py`.
2. [ ] Separar el comportamiento observado de las decisiones del contrato futuro.
3. [ ] Registrar la discrepancia entre la mision, que no envia solicitudes de desbloqueo, y la llamada actual a `apply/bl-auth`.

## Grupo 2: Contrato de entrada y ejecucion

4. [ ] Definir el significado, formato, obligatoriedad y validacion de `token`, `timeshift` y `job_id`.
5. [ ] Definir que la ejecucion debe ser no interactiva y no depender de `token.txt` ni `timeshift.txt`.
6. [ ] Definir el limite operativo por trabajo, con referencia inicial de 26 horas y configuracion explicita.

## Grupo 3: Estado persistente y resultados

7. [ ] Definir el esquema minimo de `status.json`, incluyendo identificacion, estado, PID, fechas, resultado y error.
8. [ ] Definir las transiciones validas entre `starting`, `running`, `success`, `failed`, `timeout` y `cancelled`.
9. [ ] Definir los codigos de salida y su correspondencia con estados y errores.
10. [ ] Definir las reglas de redaccion de tokens y datos sensibles en `output.log`.

## Grupo 4: Clasificacion de respuestas y validacion documental

11. [ ] Clasificar los codigos y campos de respuesta actualmente observados en la API Xiaomi.
12. [ ] Identificar respuestas desconocidas, JSON invalido, respuestas vacias, errores de red y respuestas ambiguas.
13. [ ] Revisar la spec contra `README.md`, `specs/mission.md` y `specs/tech-stack.md`.
14. [ ] Validar que la spec no incluye implementacion ni cambios de Docker, n8n o Playwright.

## Grupo 5: Documentacion y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de exito
- [ ] Mergear y limpiar
