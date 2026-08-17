# Plan - Contenedor reproducible y scripts FFmpeg

Plan secuencial para la Fase 5. El contenedor integra el motor de las Fases 1-4 con las
operaciones audiovisuales protegidas para ejecución remota desde n8n.

## Grupo 1: Imagen y usuario seguro

1. [ ] Crear un `Dockerfile` ligero con Python, FFmpeg, FFprobe, OpenSSH server
   y todas las dependencias del motor existente.
2. [ ] Crear el usuario no root `video`, su directorio SSH y el árbol
   `/workspace/videos`.
3. [ ] Configurar `sshd` sin contraseña, sin root, escuchando en el puerto
   interno 22, y permitir claves mediante `authorized_keys` local ignorado.
4. [ ] Copiar el motor Python, scripts y wrapper con permisos mínimos.

## Grupo 2: Compose y despliegue TrueNAS

5. [ ] Crear `docker-compose.yaml` con el servicio `video-scripts`.
6. [ ] Conectar exclusivamente a `ix-internal-n8n-n8n-net` y montar
   `/mnt/Aodnas/Docker/videos:/workspace/videos`.
7. [ ] No publicar puertos al host ni declarar n8n, PostgreSQL o Redis/Valkey.
8. [ ] Añadir healthcheck para SSH, FFmpeg y FFprobe, y documentar el despliegue
   manual desde la GUI de TrueNAS.

## Grupo 3: Wrapper y validación de seguridad

9. [ ] Crear `/usr/local/bin/video-tool` como único punto de entrada remoto.
10. [ ] Aceptar únicamente `probe`, `prepare_video`, `extract_audio`, `mix_audio`
    y `export_reel` con opciones explícitas.
11. [ ] Rechazar comandos FFmpeg arbitrarios, `eval`, `sh -c` y argumentos no
    validados.
12. [ ] Validar que cada ruta esté dentro de `/workspace/videos`, que las
    entradas existan y que las salidas se creen de forma segura.

## Grupo 4: Operaciones de vídeo y audio

13. [ ] Implementar `probe.sh` con JSON de duración, resolución, FPS, streams,
    códecs y bitrate mediante FFprobe.
14. [ ] Implementar `prepare_video.sh` con máster H.264, 30 FPS y audio preparado.
15. [ ] Implementar `extract_audio.sh` con audio mono a 16 kHz compatible con
    Whisper.
16. [ ] Implementar `mix_audio.sh` para voz, música y efectos, normalizando a
    aproximadamente -14 LUFS cuando sea posible.
17. [ ] Implementar `export_reel.sh` para MP4 vertical 9:16, 1080x1920, 30 FPS,
    H.264/AAC, BT.709 y `-movflags +faststart`.
18. [ ] Publicar salidas finales de forma atómica sin exponer archivos parciales.

## Grupo 5: Estados, integración y documentación

19. [ ] Integrar por trabajo `request.json`, `status.json`, `progress.log`,
    `output.partial.mp4` y `output.mp4` con estados permitidos explícitos.
20. [ ] Reutilizar el aislamiento, secretos, timeout y artefactos del motor de
    las Fases 1-4 donde sean aplicables.
21. [ ] Documentar claves SSH, credencial SSH de n8n, operaciones, estados, logs,
    verificaciones y visibilidad compartida del volumen.

## Grupo 6: Pruebas y cierre

22. [ ] Verificar FFmpeg/FFprobe, login SSH por clave y rechazo de comandos
    arbitrarios.
23. [ ] Verificar rechazo de rutas externas y ejecución de todas las operaciones
    sobre un vídeo real.
24. [ ] Confirmar que n8n y el contenedor ven los mismos archivos y que no hay
    puertos publicados al host.
25. [ ] Actualizar `README.md`, `specs/roadmap.md` y la validación de la fase.

## Grupo 7: Documentación y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de éxito
- [ ] Mergear y limpiar
