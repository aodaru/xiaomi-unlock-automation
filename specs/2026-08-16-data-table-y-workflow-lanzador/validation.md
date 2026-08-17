# Validacion - Data Table y workflow lanzador

## Estado de la fase

**IMPLEMENTADO; validación remota pendiente de credencial SSH**

## Criterios de exito

### 1. Entrada y secretos

- [x] El workflow acepta exactamente dos tokens no vacios y rechaza cero, uno,
      tres o mas tokens antes de crear filas o procesos.
- [x] Los tokens duplicados, invalidos o mal formados producen un error claro,
      sin incluir el valor completo en ningun mensaje.
- [x] `timeshift` se valida con el contrato del CLI antes del primer SSH.
- [x] Los tokens completos no aparecen en Data Table, `execution_id`, `job_id`,
      rutas, errores, logs ni salidas de los nodos.

### 2. Filas e identificadores

- [x] Una entrada valida genera un `execution_id` unico y exactamente cuatro
      `job_id` unicos, seguros y no derivados de los tokens.
- [x] Se crean exactamente cuatro filas, una por trabajo, con `token_slot`,
      `token_fingerprint`, rutas, `timeshift` y estado inicial.
- [x] Cada fila apunta a un directorio distinto bajo `/workspace/jobs` y no
      comparte `status.json`, `output.log` ni `process.pid`.

### 3. Lanzamiento remoto

- [ ] El workflow crea y verifica los cuatro directorios remotos antes del
      lanzamiento de sus procesos.
- [ ] Los cuatro procesos se lanzan mediante la credencial SSH gestionada por
      n8n en sesiones desacopladas y n8n no queda bloqueado durante la espera.
- [ ] Cada trabajo devuelve un PID o un error tecnico de lanzamiento y solo los
      lanzamientos confirmados pasan a `running`.
- [ ] Un fallo parcial conserva todas las filas y deja identificados los
      trabajos no iniciados sin presentarlos como resultados funcionales.

### 4. Integracion y documentacion

- [x] El comando remoto usa exclusivamente el CLI y rutas permitidas; no acepta
      shell, ruta o comando arbitrario desde la entrada.
- [x] La Data Table esta disponible con las columnas y tipos documentados.
- [x] El workflow se puede exportar/importar sin credenciales ni tokens reales.
- [x] La documentacion distingue el lanzador de la monitorizacion de la Fase 7
      y de las notificaciones de la Fase 8.
- [ ] `specs/roadmap.md` se actualiza a completada solo despues de satisfacer
      todos los criterios anteriores.

## Como verificar

```bash
# Validar la sintaxis y los artefactos exportados del workflow en n8n.
# Ejecutar una entrada valida con dos tokens de prueba y revisar cuatro filas.
# Consultar el contenedor: cuatro directorios, status.json, output.log y PID.
# Confirmar que los procesos siguen vivos tras cerrar la ejecucion SSH/n8n.
```

Validaciones adicionales:

```text
1. Ejecutar entradas con 0, 1, 3 y 4 tokens; no debe crearse ningun trabajo.
2. Ejecutar dos veces la entrada valida y comparar execution_id y job_id.
3. Simular fallo de mkdir, SSH y tmux en cada posicion de trabajo.
4. Buscar marcadores de token en filas, historial, rutas, logs y errores.
5. Confirmar que un trabajo lanzado puede superar la duracion de la sesion SSH.
6. Verificar que el monitor de la Fase 7 podra seleccionar state=running.
```

## Criterio de merge a main

- [ ] Todos los criterios marcados.
- [ ] Pruebas de cardinalidad, aislamiento, SSH desacoplado y fallos parciales
      ejecutadas con secretos de prueba.
- [ ] Workflow exportado sin credenciales reales y documentado.
- [ ] README y roadmap actualizados sin adelantar responsabilidades de Fase 7
      o Fase 8.
- [ ] PR abierto.

## Anti-criterios (lo que NO debe pasar)

- ❌ Una entrada con una cardinalidad distinta de dos tokens debe iniciar trabajos.
- ❌ Un token completo debe quedar persistido en Data Table, logs, rutas o IDs.
- ❌ El workflow debe esperar en primer plano a que termine cualquiera de los
      procesos largos.
- ❌ Dos trabajos deben compartir directorio o artefactos.
- ❌ Un trabajo no confirmado debe aparecer como `running`.
- ❌ Un fallo parcial debe borrar la trazabilidad de las filas restantes.
- ❌ El workflow debe ejecutar comandos arbitrarios recibidos desde la entrada.
