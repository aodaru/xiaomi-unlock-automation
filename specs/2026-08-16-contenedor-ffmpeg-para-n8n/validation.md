# Validacion - Contenedor reproducible y scripts FFmpeg

## Estado de la fase

**PENDIENTE**

## Criterios de exito

### 1. Imagen, usuario y SSH

- [ ] La imagen instala `ffmpeg`, `ffprobe`, OpenSSH y las dependencias del
      motor Python anterior.
- [ ] El servicio ejecuta operaciones como `video`, no como root.
- [ ] SSH escucha en el puerto interno 22, acepta claves y rechaza contraseña,
      root y comandos no permitidos.
- [ ] No hay claves privadas ni credenciales reales en Git.

### 2. Red, volumen y despliegue

- [ ] `video-scripts` usa la red externa `ix-internal-n8n-n8n-net`.
- [ ] Se monta exactamente `/mnt/Aodnas/Docker/videos:/workspace/videos`.
- [ ] No se publican puertos al host ni se declaran servicios n8n, PostgreSQL o
      Redis/Valkey.
- [ ] El healthcheck confirma que SSH, FFmpeg y FFprobe funcionan.

### 3. Wrapper y operaciones

- [ ] `video-tool` solo acepta `probe`, `prepare_video`, `extract_audio`,
      `mix_audio` y `export_reel`.
- [ ] Se rechazan comandos FFmpeg arbitrarios, `eval`, `sh -c` y rutas externas.
- [ ] `probe` genera JSON con duración, resolución, FPS, streams, códecs y
      bitrate.
- [ ] Las operaciones de vídeo producen los formatos, códecs, FPS, audio,
      relación 9:16 y metadatos requeridos.
- [ ] El procesamiento no usa CUDA, NVIDIA, NVENC ni runtime de GPU.
- [ ] Las salidas finales se publican atómicamente.

### 4. Estado y documentación

- [ ] Cada trabajo conserva `request.json`, `status.json`, `progress.log` y los
      archivos parcial/final definidos.
- [ ] Solo se usan los estados `queued`, `running`, `completed`, `failed` y
      `cancelled`.
- [ ] Los códigos de salida y errores son observables por SSH sin leer secretos.
- [ ] El README documenta TrueNAS, red, volumen, SSH, credencial n8n,
      operaciones, estados y logs.

### 5. Pruebas funcionales

- [ ] `ffmpeg -version` y `ffprobe -version` funcionan dentro del contenedor.
- [ ] El login SSH por clave funciona para el usuario `video`.
- [ ] Las rutas fuera de `/workspace/videos` son rechazadas.
- [ ] `probe`, `prepare_video`, `extract_audio` y `export_reel` funcionan con un
      vídeo real; `mix_audio` funciona con sus entradas válidas.
- [ ] n8n y el contenedor observan los mismos archivos del volumen.
- [ ] No existe ningún puerto publicado al host.

## Como verificar

```bash
docker compose -f docker-compose.yaml config
docker compose -f docker-compose.yaml build
docker compose -f docker-compose.yaml up -d
docker compose -f docker-compose.yaml ps
ssh -i <clave-privada-local> video@<host> video-tool probe \
  --input /workspace/videos/input/video.mp4 \
  --workdir /workspace/videos/work/job-123
```

La verificación requiere un vídeo de prueba y el entorno TrueNAS real. No debe
subir claves privadas, tokens ni credenciales al repositorio.

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] Validación local de imagen, SSH, volumen y operaciones ejecutada.
- [ ] README y roadmap actualizados.
- [ ] PR abierto.

## Anti-criterios (lo que NO debe pasar)

- ❌ El contenedor no debe reemplazar ni incluir n8n, PostgreSQL o Redis/Valkey.
- ❌ No debe publicar puertos al host ni exponer una API HTTP.
- ❌ No debe permitir comandos FFmpeg arbitrarios.
- ❌ No debe aceptar rutas fuera de `/workspace/videos`.
- ❌ No debe usar root, contraseña SSH, CUDA, NVIDIA, NVENC o GPU.
- ❌ No debe publicar un archivo parcial como resultado final.
