# Requisitos - Contenedor reproducible y scripts FFmpeg

## Alcance

Esta fase consolida un único contenedor externo de scripts audiovisuales para que
n8n ejecute operaciones mediante SSH. El contenedor reúne el motor Python y
los contratos de estados de las Fases 1-4 con FFmpeg, FFprobe y los scripts de
vídeo.

### Incluido

- Imagen ligera con Python, FFmpeg, FFprobe y servidor OpenSSH.
- Usuario no root `video`, SSH solo con claves, sin root ni contraseñas.
- Servicio `video-scripts` conectado a
  `ix-internal-n8n-n8n-net`, sin puertos publicados.
- Volumen `/mnt/Aodnas/Docker/videos:/workspace/videos`.
- Wrapper único `video-tool` con cinco operaciones permitidas.
- Scripts de inspección, preparación, extracción, mezcla y exportación de vídeo.
- Validación estricta de rutas bajo `/workspace/videos`, sin `eval` ni `sh -c`.
- Estados, logs, solicitudes y publicación atómica por trabajo.
- Documentación de TrueNAS, SSH, n8n, operaciones y pruebas con vídeo real.

### No incluido

- Modificar o contenerizar n8n, PostgreSQL o Redis/Valkey.
- Servicio HTTP, `ffmpeg-api` o puertos publicados al host.
- CUDA, NVIDIA, NVENC o `runtime: nvidia`.
- Claves privadas, contraseñas o credenciales reales en Git.
- Comandos FFmpeg arbitrarios desde SSH.
- Automatización Playwright, que pasa a la Fase 11.
- Desbloqueo físico, `fastboot` o procesamiento GPU.

## Decisiones

| ID | Decisión | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Un solo contenedor integra el motor Python anterior y FFmpeg. | TrueNAS desplegará una unidad operativa y n8n seguirá siendo externo. | Separar el motor Xiaomi y las operaciones de vídeo en servicios distintos. |
| D2 | SSH será el transporte y `video-tool` el único punto de entrada. | Mantiene la ejecución remota de n8n y limita la superficie de comandos. | Exponer una API HTTP o aceptar `ffmpeg` directamente. |
| D3 | El procesamiento será CPU-only. | El despliegue objetivo no requiere ni debe depender de GPU. | CUDA, NVIDIA, NVENC o `runtime: nvidia`. |
| D4 | El volumen externo será la única raíz válida de trabajo. | n8n y el contenedor deben observar los mismos vídeos. | Permitir rutas arbitrarias del host. |
| D5 | Las salidas finales se publicarán atómicamente. | Evita que n8n consuma MP4 incompletos. | Renombrar o copiar archivos parciales directamente al resultado final. |
| D6 | Se conservan los estados y artefactos previos donde aplique. | El contenedor no debe romper la trazabilidad de las Fases 1-4. | Crear un contrato paralelo e incompatible. |

## Contexto

El despliegue se realizará manualmente desde la GUI de TrueNAS. La red
`ix-internal-n8n-n8n-net` y el volumen de vídeos pertenecen al entorno
existente; este repositorio solo aporta el contenedor de scripts. n8n ya existe
y utilizará una credencial SSH basada en clave pública.

La misión y el stack (`specs/mission.md` y `specs/tech-stack.md`) exigen
ejecuciones no interactivas, aislamiento por trabajo, secretos fuera de logs y
resultados auditables. La Fase 10 extiende esos contratos al procesamiento
local de vídeo sin introducir servicios del despliegue de n8n.

## Dependencias

- **Fases 1-4**: motor Python, CLI no interactivo, estados, timeout, artefactos
  y pruebas locales.
- **Fase 5**: esta especificación completa sus decisiones de contenedor, SSH,
  persistencia y ejecución remota en un único contenedor.
- **Fases 6-8**: n8n consumirá el wrapper y los estados, pero no se modifica en
  esta fase.
- **TrueNAS**: red externa, volumen compartido y despliegue manual.

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| Un usuario SSH puede intentar ejecutar comandos no autorizados. | Claves, usuario restringido, wrapper único y rechazo de argumentos arbitrarios. |
| Una ruta puede escapar del volumen compartido. | Resolución canónica y validación de prefijo bajo `/workspace/videos`. |
| n8n puede consumir un archivo incompleto. | Archivos `.partial`, `fsync`/rename atómico y resultado final solo al completar. |
| La configuración local puede incluir secretos. | `.gitignore`, clave pública inyectada localmente y ninguna clave privada en Git. |
| El entorno externo no tiene la red o volumen esperados. | Healthcheck, validaciones de despliegue y pruebas de visibilidad desde ambos contenedores. |
