# Validacion - Pruebas locales del motor

## Estado de la fase

**COMPLETADA**

## Criterios de exito

### 1. Ejecucion no interactiva

- [x] La suite ejecuta el CLI sin leer stdin y no queda bloqueada esperando
      confirmaciones o Enter.
- [x] Se conservan `--token`, `--timeshift` y `--job-id`, junto con sus
      validaciones y el codigo `20` para entradas invalidas.
- [x] Ningun caso usa tokens reales, credenciales reales o acceso de red.

### 2. Respuestas y codigos

- [x] Token caducado, cuenta bloqueada y estados no permitidos producen `failed`
      y codigo `10` con detalle determinista.
- [x] Permiso ya concedido y permiso aplicado producen `success` y codigo `0`
      cuando corresponda.
- [x] Error de red, HTTP, JSON o respuesta desconocida produce `failed` y codigo
      `30` despues de la politica de reintentos definida.
- [x] `code=100003` ejecuta la consulta posterior y no concede permiso por
      defecto.

### 3. Estados, timeout y aislamiento

- [x] Una ejecucion correcta verifica `starting -> running -> success` y sus
      artefactos `status.json`, `output.log` y `process.pid`.
- [x] Un fallo verifica `failed`, el codigo de salida, el error redactado y las
      marcas de tiempo necesarias.
- [x] Una espera que supera el limite verifica `timeout`, `timeout_at` y el
      codigo `40`.
- [x] Dos trabajos concurrentes conservan directorios, estados, logs y PID sin
      interferencia.
- [x] Un fallo de persistencia o un `status.json` corrupto no se presenta como
      un `success` falso.

### 4. Secretos y documentacion

- [x] El token completo no aparece en stdout, stderr, `output.log`,
      `status.json`, rutas ni excepciones verificadas.
- [x] `README.md` documenta como ejecutar la suite y que escenarios quedan fuera.
- [x] `specs/roadmap.md` refleja la Fase 4 solo despues de completar las pruebas.

## Como verificar

```bash
python3 -m py_compile SCRIPT_PERMISO_DESBLOQUEO.py
python3 SCRIPT_PERMISO_DESBLOQUEO.py --help
python3 -m unittest discover -s tests -v
```

Validaciones adicionales:

```text
1. Ejecutar la suite con stdin cerrado y sin conectividad de red.
2. Inspeccionar los codigos de salida y status.json de cada respuesta simulada.
3. Ejecutar dos job_id concurrentes y comparar sus artefactos.
4. Simular timeout, interrupcion y fallo de escritura; verificar que no haya
   un success falso ni procesos abandonados.
5. Buscar el token marcador en todos los artefactos y salidas capturadas.
```

## Criterio de merge a main

- [x] Todos los criterios marcados.
- [x] Suite automatizada ejecutada sin red ni secretos reales.
- [x] Validacion automatizada de no interaccion y aislamiento ejecutada.
- [x] README y roadmap actualizados sin contradecir las fases posteriores.
- [ ] PR abierto.

## Anti-criterios (lo que NO debe pasar)

- ❌ Una prueba debe depender de Xiaomi, DNS, SSH, Docker o un token real.
- ❌ El motor debe solicitar `input()` o quedar esperando stdin.
- ❌ Una cuenta bloqueada o un estado desconocido debe convertirse en permiso.
- ❌ Dos trabajos deben escribir sobre el mismo artefacto.
- ❌ Un fallo de persistencia debe terminar en un `success` observable.
- ❌ El token completo debe aparecer en logs, rutas, excepciones o resultados.
