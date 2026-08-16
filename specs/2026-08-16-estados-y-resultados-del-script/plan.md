# Plan - Estados y resultados del script

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Contrato de artefactos

1. [x] Definir el esquema JSON de `status.json`, incluyendo `job_id`, estado,
   codigo de salida, resultado o error y marcas de tiempo.
2. [x] Definir los estados validos `starting`, `running`, `success`, `failed`,
   `timeout` y `cancelled`, junto con sus transiciones permitidas.
3. [x] Definir la politica de escritura atomica, codificacion y comportamiento
   ante un `status.json` ausente o corrupto.

## Grupo 2: Ciclo de ejecucion del script

4. [x] Crear el estado inicial `starting` despues de validar los argumentos y
   antes de iniciar la actividad remota.
5. [x] Escribir `running` antes de entrar en la espera prolongada o realizar la
   consulta que pueda durar mas que una sesion SSH.
6. [x] Mapear los resultados funcionales, errores remotos y excepciones a
   `success` o `failed` sin cambiar la redaccion de secretos.
7. [x] Escribir `timeout` cuando se alcance el limite operativo configurable y
   devolver el codigo de salida definido para ese caso.

## Grupo 3: Aislamiento por trabajo

8. [x] Crear y validar un directorio exclusivo para cada `job_id` sin permitir
   traversal ni colisiones entre trabajos.
9. [x] Escribir `status.json`, `output.log` y `process.pid` unicamente dentro
   del directorio del trabajo.
10. [x] Registrar en `output.log` la salida operativa sin tokens completos ni
    credenciales, manteniendo el `job_id` como referencia.
11. [ ] Definir la limpieza y conservacion de artefactos cuando el proceso
    termina correctamente, falla o supera el timeout.

## Grupo 4: Pruebas locales y documentacion

12. [x] Probar cada estado final y las transiciones invalidas sin llamadas reales
    a la API Xiaomi.
13. [x] Probar concurrencia o aislamiento de dos `job_id` y la ausencia de
    interferencia entre sus artefactos.
14. [ ] Probar timeout, proceso interrumpido y fallo al escribir un artefacto.
15. [x] Actualizar `README.md` y las pruebas para describir el contrato final de
    estados y resultados.

## Grupo 5: Documentacion y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de exito
- [ ] Mergear y limpiar
