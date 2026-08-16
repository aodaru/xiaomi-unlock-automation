# Validacion - Contrato y diagnostico del script

## Estado de la fase

**✅ COMPLETADA**

## Criterios de exito

### 1. Cobertura del diagnostico

- [x] El contrato documenta `token`, `timeshift` y `job_id`.
- [x] Se registran las lecturas interactivas y de archivos que existen hoy.
- [x] Se identifican las rutas actuales que usan `input()` y `exit()`.
- [x] Se documenta la diferencia entre la solicitud API `apply/bl-auth` y el desbloqueo físico posterior.

### 2. Contrato de estado

- [x] `status.json` tiene esquema minimo, tipos, fechas, campos terminales y
      reglas de escritura.
- [x] Se definen los seis estados validos y las transiciones permitidas.
- [x] Se define un limite por trabajo con referencia de 26 horas.
- [x] Se define la necesidad de aislar artefactos por `job_id`.

### 3. Respuestas y errores

- [x] Se clasifican los codigos `100004`, `100001` y `100003`.
- [x] Se clasifican `is_pass`, `button_state`, `apply_result` y
      `deadline_format`.
- [x] Se incluyen JSON invalido, respuesta vacia, error de red y respuesta
      desconocida.
- [x] Cada categoria tiene un resultado o causa contractual provisional.

### 4. Coherencia documental

- [x] La spec referencia y no contradice `specs/mission.md` ni
      `specs/tech-stack.md`.
- [x] El alcance no incluye implementacion de Python, Docker, n8n o
      Playwright.
- [x] Las decisiones pendientes y los riesgos tienen mitigacion o siguiente
      fase asignada.

## Como verificar

```bash
python3 -m py_compile SCRIPT_PERMISO_DESBLOQUEO.py
```

La compilacion solo comprueba que el diagnostico se basa en un archivo Python
valido; no confirma el contrato ni ejecuta llamadas contra Xiaomi.

Verificacion documental manual:

```text
1. Comparar requirements.md con README.md, specs/mission.md y specs/tech-stack.md.
2. Confirmar que todos los items de roadmap.md de la Fase 1 aparecen en plan.md.
3. Confirmar que cada codigo o campo observado en el script aparece en la tabla de respuestas.
4. Confirmar que no se han incluido tokens reales en la documentacion.
```

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] PR abierto.
- [x] Validacion manual ejecutada.
- [x] La decisión sobre `apply/bl-auth` queda resuelta: la solicitud API está
      permitida y el desbloqueo físico posterior queda fuera del alcance.

## Anti-criterios (lo que NO debe pasar)

- ❌ La spec no debe recomendar depender de `input()` o de una sesion SSH abierta.
- ❌ `status.json` no debe depender solamente del PID.
- ❌ No se deben registrar tokens completos en `output.log`, errores o avisos.
- ❌ La Fase 1 no debe cambiar el comportamiento del script ni enviar solicitudes reales.
- ❌ Una respuesta Xiaomi desconocida no debe clasificarse automaticamente como permiso concedido.
