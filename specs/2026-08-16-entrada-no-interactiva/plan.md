# Plan - Entrada no interactiva

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Contrato de ejecucion

1. [x] Definir la interfaz explicita para recibir `token`, `timeshift` y
   `job_id` sin leer `token.txt`, `timeshift.txt` ni solicitar datos por
   consola.
2. [x] Definir la validacion previa de presencia, formato, rango y seguridad de
   cada entrada.
3. [x] Definir los mensajes y codigos de salida para entradas invalidas sin
   exponer el token completo.

## Grupo 2: Adaptacion del flujo principal

4. [x] Sustituir la seleccion interactiva del token y la lectura de archivos
   por la interfaz de entrada definida.
5. [x] Propagar `job_id` al contexto de ejecucion sin usarlo para incluir
   secretos en nombres o mensajes.
6. [x] Eliminar toda interacción de confirmaciones, errores y finalizacion.
7. [x] Representar de forma determinista los casos de token caducado, cuenta
   bloqueada, respuesta desconocida y error de red.

## Grupo 3: Salida y seguridad operativa

8. [x] Mantener el comportamiento de consulta y solicitud API sin introducir
   llamadas reales adicionales ni modificar el contrato de estados de la Fase
   3.
9. [x] Redactar tokens y datos sensibles en mensajes de error y salida de
   consola.
10. [x] Documentar el uso no interactivo y los ejemplos de invocacion sin
    secretos reales.

## Grupo 4: Verificacion local

11. [x] Ejecutar validaciones unitarias o de proceso para entradas validas e
    invalidas.
12. [x] Confirmar que una ejecucion sin stdin no queda bloqueada por interacción.
13. [x] Confirmar los codigos de salida definidos para errores de validacion y
    respuestas funcionales.

## Grupo 5: Documentacion y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de exito
- [ ] Mergear y limpiar
