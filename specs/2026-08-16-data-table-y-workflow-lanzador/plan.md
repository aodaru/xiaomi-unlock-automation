# Plan - Data Table y workflow lanzador

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Contrato de entrada y modelo de datos

1. [x] Definir el contrato del payload de entrada con exactamente dos tokens y
   los parametros operativos comunes, incluyendo `timeshift`.
2. [x] Definir la Data Table y sus tipos, valores iniciales, restricciones y
   columnas de auditoria por trabajo.
3. [x] Validar los dos tokens antes de crear filas, procesos o directorios y
   rechazar entradas ausentes, duplicadas o invalidas sin revelar secretos.

## Grupo 2: Identificadores y preparacion de trabajos

4. [x] Generar un `execution_id` unico por ejecucion y cuatro `job_id` unicos,
   seguros y no derivados de ningun token.
5. [x] Crear exactamente una fila por trabajo con estado inicial, fechas,
   rutas esperadas y huella no reversible del token asociado.
6. [x] Crear y comprobar el directorio remoto aislado de cada trabajo bajo
   `/workspace/jobs` antes de iniciar el proceso.

## Grupo 3: Lanzamiento remoto desacoplado

7. [x] Construir el comando del CLI con argumentos validados y escape seguro,
   sin permitir comandos o rutas controlados por el token.
8. [x] Lanzar cada proceso por SSH mediante una sesion desacoplada (`tmux` u
   otra tecnica equivalente) y evitar que n8n espere la duracion del trabajo.
9. [x] Capturar el PID remoto, escribir `running` y guardar rutas y marcas de
   tiempo solo despues de confirmar el lanzamiento.
10. [x] Definir el tratamiento de fallos parciales: filas y directorios de los
    trabajos no lanzados deben quedar trazables y no simular `running`.

## Grupo 4: Pruebas del workflow y cierre de la fase

11. [ ] Probar entrada valida con cuatro trabajos y comprobar aislamiento de
    filas, `job_id`, directorios y procesos.
12. [ ] Probar cero, uno, tres y mas de dos tokens, tokens duplicados, errores de
    SSH y fallos al crear directorios.
13. [ ] Comprobar que tokens completos no aparecen en Data Table, logs,
    identificadores, errores ni salida del workflow.
14. [ ] Documentar importacion, credencial SSH, parametros y rollback del
    workflow sin incluir secretos reales.
15. [ ] Marcar la Fase 6 como completada en `specs/roadmap.md` solo cuando se
    satisfagan los criterios de validacion.

## Grupo 5: Documentacion y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de exito
- [ ] Mergear y limpiar
