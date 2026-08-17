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

- [x] Crear el estado inicial `starting`.
- [x] Escribir `running` antes de la espera prolongada.
- [x] Escribir `success` con el resultado de la consulta.
- [x] Escribir `failed` con error y código de salida.
- [x] Escribir `timeout` cuando se alcance el límite.
- [x] Aislar `status.json`, `output.log` y `process.pid` por trabajo.

## Fase 4: Pruebas locales del motor

- [x] Probar ejecución sin interacción humana.
- [x] Probar token caducado y estados no permitidos.
- [x] Probar error de red y respuestas inválidas.
- [x] Probar finalización correcta y códigos de salida.

## Fase 5: Contenedor reproducible y scripts FFmpeg

- [x] Consolidar en un único contenedor el motor Python, estados, artefactos,
      FFmpeg y FFprobe.
- [x] Fijar dependencias Python y del procesamiento audiovisual.
- [x] Crear imagen ligera con usuario no root, OpenSSH y acceso exclusivamente
      mediante claves.
- [x] Conectar la red externa `ix-internal-n8n-n8n-net` y montar
      `/mnt/Aodnas/Docker/videos:/workspace/videos`, sin puertos publicados.
- [x] Verificar directorios persistentes, aislamiento de trabajos y estados.
- [x] Crear `video-tool` y los scripts `probe`, `prepare_video`, `extract_audio`,
      `mix_audio` y `export_reel`.
- [x] Validar rutas, bloquear comandos arbitrarios y publicar salidas
      atómicamente.
- [x] Documentar despliegue TrueNAS, SSH, n8n y pruebas con vídeo real.

## Fase 6: Data Table y workflow lanzador

- [x] Definir las columnas de la Data Table.
- [x] Validar exactamente dos tokens de entrada.
- [x] Generar un `execution_id` y cuatro `job_id` únicos.
- [x] Crear una fila por cada trabajo.
- [x] Crear el directorio remoto de cada trabajo.
- [x] Lanzar los cuatro procesos por SSH sin bloquear n8n.
- [x] Guardar PID, rutas y estado `running`.

## Fase 7: Workflow monitor

- [x] Configurar `Schedule Trigger` cada 1 o 5 minutos.
- [x] Seleccionar únicamente trabajos `running`.
- [x] Leer `status.json` y `output.log` por SSH.
- [x] Actualizar estado, resultado, error y fechas.
- [x] Detectar proceso perdido y superar `timeout_at`.

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
