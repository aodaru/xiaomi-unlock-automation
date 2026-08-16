# Validacion - Entrada no interactiva

## Estado de la fase

**⬜ PENDIENTE**

## Criterios de exito

### 1. Interfaz y validacion

- [ ] El script acepta `token`, `timeshift` y `job_id` mediante la interfaz
      documentada.
- [ ] La ejecucion no lee `token.txt` ni `timeshift.txt`.
- [ ] La ausencia de cualquier entrada produce un error y el codigo `20`.
- [ ] Un token vacio, un `job_id` vacio o inseguro y un `timeshift` no numerico,
      no finito o fuera de rango se rechazan antes de iniciar la red.

### 2. Ausencia de interaccion

- [ ] No quedan llamadas a `input()` en el flujo ejecutable.
- [ ] Las respuestas que antes pedian `Yes/No` tienen una decision automatica
      documentada y no conceden permiso por defecto.
- [ ] Los errores no esperan Enter ni requieren una sesion de terminal abierta.
- [ ] Una ejecucion sin stdin disponible termina o espera por la logica del
      trabajo, pero nunca queda bloqueada esperando entrada humana.

### 3. Errores y secretos

- [ ] Token caducado y permiso rechazado devuelven codigo `10` sin token completo.
- [ ] Error de red, JSON invalido o respuesta desconocida devuelven codigo `30`
      conforme a la politica de reintentos definida.
- [ ] `job_id` se conserva para trazabilidad sin aparecer mezclado con el token.
- [ ] Busquedas de salida y errores no encuentran el token completo ni
      credenciales en ejemplos o logs de prueba.

### 4. Compatibilidad documental

- [ ] `README.md` y la spec describen la misma interfaz de lanzamiento.
- [ ] La implementacion conserva la solicitud `apply/bl-auth` permitida por la
      mision, sin incluir desbloqueo fisico ni `fastboot`.
- [ ] La fase no implementa `status.json`, timeout persistente, Docker, n8n ni
      Playwright.

## Como verificar

```bash
python3 -m py_compile SCRIPT_PERMISO_DESBLOQUEO.py
rg "input\(" SCRIPT_PERMISO_DESBLOQUEO.py
python3 SCRIPT_PERMISO_DESBLOQUEO.py --help
```

Pruebas locales adicionales, usando valores ficticios y sin llamadas reales:

```text
1. Ejecutar sin cada argumento obligatorio y confirmar codigo 20.
2. Ejecutar con timeshift invalido y job_id inseguro y confirmar rechazo previo.
3. Ejecutar sin stdin y confirmar que no aparece ningun prompt.
4. Simular token caducado, respuesta bloqueada, JSON invalido y error de red.
5. Confirmar codigos 10/30 y revisar que el token no aparece completo.
```

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] PR abierto.
- [ ] Validacion manual ejecutada.
- [ ] No existen llamadas interactivas ni dependencias de archivos compartidos.

## Anti-criterios (lo que NO debe pasar)

- ❌ El proceso no debe solicitar un numero de linea ni leer tokens por posicion.
- ❌ El proceso no debe quedar esperando `Yes/No` o Enter.
- ❌ Una entrada invalida no debe iniciar consultas a Xiaomi.
- ❌ Una cuenta bloqueada o una respuesta desconocida no debe clasificarse como
  permiso concedido automaticamente.
- ❌ El token completo no debe aparecer en consola, excepciones, rutas ni
  documentacion.
