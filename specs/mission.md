# Misión

## Propósito

Automatizar en n8n la determinación del permiso de una cuenta Xiaomi para
solicitar el desbloqueo del bootloader, usando el script Python existente como
motor de consulta y conservando el estado de cada trabajo aunque tarde más de
un día.

## Resultado mínimo exitoso

Para cada token recibido, el sistema debe devolver un resultado estructurado
que indique si la cuenta puede iniciar la solicitud, si está bloqueada, si el
token caducó o si la consulta terminó con error. Debe incluir el estado,
detalle útil, marcas de tiempo y un identificador trazable del trabajo.

El sistema no enviará la solicitud de desbloqueo. La misión termina después de
determinar el permiso.

## Usuarios objetivo

- Operador técnico interno que proporciona los tokens y revisa resultados y
  errores desde n8n.

## Principios

- Las ejecuciones serán no interactivas y aptas para automatización.
- Cada trabajo tendrá aislamiento de archivos y un identificador único.
- Los estados serán explícitos y persistentes; no se confiará únicamente en el
  PID del proceso.
- Los tokens se tratarán como secretos operativos y no se imprimirán en logs ni
  notificaciones.
- Los resultados deben ser reproducibles y auditables sin mantener una sesión
  SSH abierta durante la espera.

## Fuera de alcance

- Envío automático de solicitudes de desbloqueo.
- Gestión de dispositivos físicos o ejecución de comandos fastboot.
- Portal multiusuario o control de acceso de usuarios finales.
- Extracción automática de tokens mediante Playwright en la primera entrega.
