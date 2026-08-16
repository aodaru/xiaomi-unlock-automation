# Plan - Pruebas locales del motor

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Arnes de pruebas y aislamiento de dependencias

1. [x] Definir fixtures y dobles locales para la API, el reloj y la espera sin
   realizar llamadas externas.
2. [x] Preparar una forma determinista de ejecutar el CLI sin stdin, tokens
   reales ni dependencias de archivos compartidos.
3. [x] Asegurar que cada prueba use un directorio temporal y un `job_id`
   independiente.

## Grupo 2: Validacion de entradas y ausencia de interaccion

4. [x] Verificar que una ejecucion valida termina sin leer stdin y conserva la
   interfaz `--token`, `--timeshift` y `--job-id`.
5. [x] Verificar argumentos ausentes, `timeshift` invalido y `job_id` inseguro,
   incluyendo sus codigos de salida.
6. [x] Verificar que los mensajes de error y la salida operativa no contienen el
   token completo.

## Grupo 3: Respuestas funcionales y errores del motor

7. [x] Probar token caducado, cuenta bloqueada, permiso ya concedido y estados
   funcionales no permitidos.
8. [x] Probar respuestas desconocidas, JSON invalido, errores HTTP y errores de
   red, verificando el codigo `30` cuando corresponda.
9. [x] Probar la respuesta ambigua `code=100003` y la consulta posterior, sin
   dejar un resultado falso de permiso.

## Grupo 4: Estados persistentes, timeout y concurrencia

10. [x] Verificar las secuencias `starting -> running -> success` y
    `starting -> running -> failed` con los artefactos esperados.
11. [x] Simular una espera superior al limite y verificar `timeout`, `timeout_at`
    y el codigo `40` sin ocultar errores.
12. [x] Ejecutar dos trabajos concurrentes y comprobar que sus estados, logs y
    PID no se mezclan.
13. [x] Verificar el comportamiento ante proceso interrumpido, `status.json`
    ausente/corrupto y fallo de persistencia.

## Grupo 5: Documentacion y cierre de la fase

14. [x] Actualizar `README.md` con la orden de pruebas, escenarios cubiertos y
    limites de las pruebas locales.
15. [x] Marcar la Fase 4 como completada en `specs/roadmap.md` solo cuando los
    criterios de validacion esten satisfechos.
16. [x] Ejecutar la suite completa, revisar que no use red ni secretos reales y
    registrar cualquier limitacion residual.

## Grupo 6: Documentacion y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de exito
- [ ] Mergear y limpiar
