# Roadmap

Este orden convierte las fases descritas en `README.md` en incrementos
pequeños. No existe `TODO.md` en el repositorio; por tanto, este roadmap usa
el apartado **Implementación por fases** del README como fuente de orden.

## Fase 1: Contrato y diagnóstico del script

- [x] Documentar argumentos `token`, `timeshift` y `job_id`.
- [x] Documentar el esquema de `status.json` y los códigos de salida.
- [x] Clasificar las respuestas conocidas de la API Xiaomi.
- [x] Definir el límite máximo y las transiciones de estado.

## Fase 2: Entrada no interactiva

- [x] Reemplazar la lectura de token por argumento o entrada explícita.
- [x] Reemplazar la lectura de timeshift por argumento o entrada explícita.
- [x] Eliminar toda interacción de confirmaciones y errores.
- [x] Validar token, timeshift y `job_id` antes de iniciar.

## Fase 3: Estados y resultados del script

- [ ] Crear el estado inicial `starting`.
- [ ] Escribir `running` antes de la espera prolongada.
- [ ] Escribir `success` con el resultado de la consulta.
- [ ] Escribir `failed` con error y código de salida.
- [ ] Escribir `timeout` cuando se alcance el límite.
- [ ] Aislar `status.json`, `output.log` y `process.pid` por trabajo.

## Fase 4: Pruebas locales del motor

- [ ] Probar ejecución sin interacción humana.
- [ ] Probar token caducado y estados no permitidos.
- [ ] Probar error de red y respuestas inválidas.
- [ ] Probar finalización correcta y códigos de salida.

## Fase 5: Contenedor reproducible

- [ ] Fijar dependencias Python y revisar la instalación en build.
- [ ] Construir la imagen con el script adaptado.
- [ ] Verificar directorios persistentes y aislamiento de trabajos.
- [ ] Verificar acceso SSH en el puerto `2223`.
- [ ] Verificar lanzamiento manual en tmux y ejecución en segundo plano.

## Fase 6: Data Table y workflow lanzador

- [ ] Definir las columnas de la Data Table.
- [ ] Validar exactamente dos tokens de entrada.
- [ ] Generar un `execution_id` y cuatro `job_id` únicos.
- [ ] Crear una fila por cada trabajo.
- [ ] Crear el directorio remoto de cada trabajo.
- [ ] Lanzar los cuatro procesos por SSH sin bloquear n8n.
- [ ] Guardar PID, rutas y estado `running`.

## Fase 7: Workflow monitor

- [ ] Configurar `Schedule Trigger` cada 1 o 5 minutos.
- [ ] Seleccionar únicamente trabajos `running`.
- [ ] Leer `status.json` y `output.log` por SSH.
- [ ] Actualizar estado, resultado, error y fechas.
- [ ] Detectar proceso perdido y superar `timeout_at`.

## Fase 8: Resultados operativos

- [ ] Definir la notificación al operador técnico.
- [ ] Notificar resultado por token sin exponer el token completo.
- [ ] Diferenciar éxito, permiso denegado, token caducado, timeout y error.
- [ ] Registrar `last_checked_at` y evitar notificaciones duplicadas.

## Fase 9: Resiliencia del ciclo completo

- [ ] Probar cuatro trabajos concurrentes.
- [ ] Probar trabajos que superen un día.
- [ ] Probar reinicio de n8n y desconexión SSH.
- [ ] Probar reinicio del contenedor y persistencia de estados.
- [ ] Probar errores de red, proceso bloqueado y timeout.

## Fase 10: Playwright opcional

- [ ] Definir el endpoint HTTP o protocolo CDP/WebSocket.
- [ ] Automatizar inicio de sesión solo si se habilita esta fuente.
- [ ] Extraer y validar dos tokens.
- [ ] Conectar la salida al workflow lanzador.
