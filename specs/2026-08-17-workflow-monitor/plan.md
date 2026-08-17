# Plan — Workflow monitor

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Diseño del workflow monitor

1. [x] Definir el nodo Schedule Trigger (cron cada 1 o 5 minutos) y timezone
2. [x] Definir consulta a Data Table filtrando `state = 'running'`
3. [x] Definir bucle sobre trabajos running: SSH → leer `status.json` y `output.log`
4. [x] Definir lógica de actualización de estado en Data Table
5. [x] Definir detección de timeout (`timeout_at` superado) y proceso perdido (PID no existe)

## Grupo 2: Implementación del workflow

6. [x] Crear workflow n8n `Script Phase 7 Monitor` con Schedule Trigger
7. [x] Configurar nodo Data Table (Get Rows) con filtro `state = 'running'`
8. [x] Configurar nodo SSH para ejecutar comando de lectura remota por job
9. [x] Configurar nodos de lógica (IF/Code/Set) para parsear `status.json` y decidir acción
10. [x] Configurar nodo Data Table (Update Row) para escribir estado, resultado, error, fechas
11. [x] Manejar casos: success, failed, timeout, proceso perdido → estados terminales

## Grupo 3: Columnas adicionales en Data Table

12. [x] Añadir columna `last_checked_at` (timestamp última comprobación monitor)
13. [x] Añadir columna `check_count` (contador de comprobaciones)
14. [x] Validar que workflow actualiza estas columnas en cada ciclo

## Grupo 4: Pruebas y validación

15. [x] Probar workflow con jobs en estado `running` que terminen en success
16. [x] Probar detección de timeout (simular `timeout_at` en el pasado)
17. [x] Probar detección de proceso perdido (PID file existe pero proceso muerto)
18. [x] Probar que jobs terminales no se re-procesan en siguientes ejecuciones
19. [x] Verificar que tokens completos no aparecen en logs ni Data Table

## Grupo 5: Documentación y merge

- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de éxito
- [ ] Mergear y limpiar
