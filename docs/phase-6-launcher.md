# Fase 6: workflow lanzador

## Recursos n8n

- Workflow: `Script Phase 6 Launcher`
- Workflow ID: `b424EDpsd0lMDN1Y`
- Data Table: `script_job_launches`
- Data Table ID: `9YfdvJehSSUf9iK2`
- Estado inicial: inactivo, hasta configurar la credencial SSH.

## Entrada

El endpoint recibe `POST` con este contrato:

```json
{
  "tokens": ["<token-1>", "<token-2>"],
  "timeshift": 1400
}
```

Se rechazan antes de crear filas o lanzar SSH las entradas que no tengan
exactamente dos tokens no vacíos, tengan tokens duplicados o usen un
`timeshift` fuera de `0..86400000` milisegundos.

## Flujo

1. El nodo Code valida la entrada, calcula una huella SHA-256 y genera un
   `execution_id` más cuatro `job_id` aleatorios.
2. Data Table inserta cuatro filas en estado `starting` con rutas aisladas bajo
   `/workspace/jobs`.
3. SSH recibe cada comando fijo con el token escapado como argumento y crea una
   sesión `tmux` desacoplada.
4. El comando confirma el directorio y `process.pid`; solo entonces la fila
   pasa a `running`.
5. Un fallo individual conserva la fila y la marca `launch_failed` con un
   mensaje truncado y redactado.

El endpoint responde inmediatamente con el acuse de n8n. La monitorización de
`status.json` y `output.log` queda fuera de este workflow y pertenece a la fase
7.

## Configuración requerida

1. Crear una credencial n8n de tipo SSH con clave privada para el servicio
   remoto `script`.
2. Asociarla al nodo `Launch Detached Process Over SSH`, que usa la referencia
   `Script container SSH private key`.
3. Confirmar que el usuario remoto puede ejecutar
   `/workspace/SCRIPT_PERMISO_DESBLOQUEO.py`, usar `tmux` y escribir
   `/workspace/jobs`.
4. Probar con dos tokens de prueba antes de publicar el workflow.

La credencial no está incluida en el workflow ni en el repositorio. Los tokens
completos no se escriben en la Data Table, identificadores, rutas ni errores de
lanzamiento.

## Pruebas pendientes de infraestructura

La instancia n8n usada para crear el workflow no expone credenciales SSH, por lo
que quedan pendientes la prueba contra el contenedor, la comprobación de los
cuatro PIDs y la simulación de fallos SSH/tmux. La validación estructural del
workflow y de sus nodos sí fue completada.
