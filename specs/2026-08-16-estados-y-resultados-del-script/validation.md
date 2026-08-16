# Validacion - Estados y resultados del script

## Estado de la fase

**EN VALIDACION**

## Criterios de exito

### 1. Contrato de estados

- [x] Cada ejecucion valida crea `status.json` con estado inicial `starting`.
- [x] `running` se persiste antes de la espera prolongada.
- [x] Una ejecucion correcta termina en `success` con resultado y codigo `0`.
- [x] Un rechazo funcional o error del motor termina en `failed` con detalle
      redactado y el codigo correspondiente.
- [x] Una ejecucion que alcanza el limite termina en `timeout` con marcas de
      tiempo y codigo definido.
- [ ] Las transiciones invalidas se rechazan sin corromper el ultimo estado.

### 2. Artefactos y aislamiento

- [x] Cada `job_id` valido tiene un directorio propio y no puede escapar de la
      raiz configurada mediante traversal.
- [x] `status.json`, `output.log` y `process.pid` se crean dentro del directorio
      correcto y no se comparten entre trabajos.
- [x] `status.json` siempre es JSON completo y legible por otro proceso.
- [x] Los artefactos no contienen el token completo ni credenciales.
- [ ] El contenido conserva `job_id`, `started_at` y el estado final necesario
      para una auditoria posterior.

### 3. Compatibilidad funcional

- [ ] La interfaz CLI de la Fase 2 conserva sus argumentos y validaciones.
- [ ] Los casos `already_allowed`, permiso aplicado, token caducado, bloqueo,
      respuesta desconocida y error de red producen estados deterministas.
- [x] El timeout es configurable y su valor por defecto respeta la referencia
      de 26 horas.
- [ ] Un fallo de persistencia se reporta de forma segura y no se presenta como
      un `success` falso.

### 4. Pruebas y documentacion

- [ ] Las pruebas cubren estados finales, timeout y aislamiento de dos trabajos.
- [ ] Las pruebas no requieren tokens reales, stdin ni acceso de red.
- [x] `README.md` documenta rutas, esquema, estados y codigos de salida.
- [ ] La documentacion no incluye secretos reales ni contradice el roadmap.

## Como verificar

```bash
python3 -m py_compile SCRIPT_PERMISO_DESBLOQUEO.py
python3 -m unittest discover -s tests -v
python3 SCRIPT_PERMISO_DESBLOQUEO.py --help
```

Validaciones adicionales con dependencias simuladas:

```text
1. Ejecutar un trabajo valido y verificar la secuencia starting -> running ->
   success y los tres artefactos aislados.
2. Simular rechazo funcional, error remoto y excepcion; verificar failed, el
   codigo esperado y la ausencia del token completo.
3. Simular una espera superior al limite; verificar timeout y timeout_at.
4. Ejecutar dos job_id concurrentes y verificar que no comparten archivos.
5. Interrumpir una escritura o leer durante ella y verificar que nunca aparece
   JSON parcial.
```

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] PR abierto.
- [ ] Validacion automatizada y manual ejecutada.
- [ ] El monitor futuro puede consumir el contrato sin parsear texto ambiguo.

## Anti-criterios (lo que NO debe pasar)

- ❌ El estado no debe depender unicamente de que exista un PID.
- ❌ Un proceso no debe marcar `success` si no pudo persistir su resultado.
- ❌ Dos trabajos no deben escribir sobre el mismo `status.json` o `output.log`.
- ❌ El timeout no debe ocultar un error ni dejar un resultado funcional falso.
- ❌ El token completo no debe aparecer en estados, logs, rutas o excepciones.
- ❌ Esta fase no debe introducir workflows n8n, Data Table, Docker ni Playwright.
