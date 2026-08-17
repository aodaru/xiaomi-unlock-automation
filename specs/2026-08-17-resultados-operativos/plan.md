# Plan — Resultados operativos

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Diseño de la notificación al operador

1. [ ] Definir el canal concreto de notificación (email SMTP por defecto, nodo
   de salida reemplazable por Slack/Telegram/webhook sin tocar la lógica)
2. [ ] Definir el formato del mensaje: `job_id`, `token_hash` (o máscara con
   últimos 4), tipo de resultado, estado, resultado redactado, error redactado,
   `exit_code` y fechas relevantes
3. [ ] Definir la clasificación de 5 resultados usando contrato Fase 1:
   éxito, permiso denegado, token caducado, timeout y error
4. [ ] Definir la regla de redacción del token: nunca completo, solo
   `token_hash` / máscara `****xxxx`

## Grupo 2: Campos anti-duplicados en Data Table

5. [ ] Añadir columna `last_notified_at` (timestamp UTC de la última
   notificación; `null` mientras no se haya notificado)
6. [ ] Añadir columna `notified_result` (tipo de notificación enviado, para
   auditoría)
7. [ ] Validar que la fila terminal no se vuelve a seleccionar una vez
   `last_notified_at` tiene valor

## Grupo 3: Implementación del workflow de notificación

8. [ ] Crear workflow n8n `Script Phase 8 Notifier` con Schedule Trigger
   (5 minutos por defecto, configurable a 1 minuto)
9. [ ] Configurar nodo Data Table (Get Rows) con filtro: estado terminal
   (`success`, `failed`, `timeout`) Y `last_notified_at IS NULL`
10. [ ] Configurar nodos de lógica (Code/IF/Set) para clasificar el resultado
    en uno de los 5 tipos según `state`, `result` y `error`
11. [ ] Configurar nodo de notificación (Send Email) con body redactado y
    credencial n8n (sin contraseñas embebidas)
12. [ ] Configurar nodo Data Table (Update Row) para escribir
    `last_notified_at` y `notified_result`
13. [ ] Configurar `retryOnFail`/`maxTries` y `continueRegularOutput` para que
    un fallo de notificación no bloquee el resto de trabajos

## Grupo 4: Pruebas y validación

14. [ ] Test 1: Job `success` → notificación tipo `success`
15. [ ] Test 2: Job `failed` con causa `token_expired` → notificación tipo
    `token_expired`
16. [ ] Test 3: Job `failed` con causa `request_rejected` / `permission_blocked`
    → notificación tipo `permission_denied`
17. [ ] Test 4: Job `timeout` → notificación tipo `timeout`
18. [ ] Test 5: Job `failed` con causa desconocida → notificación tipo `error`
19. [ ] Test 6: Segunda ejecución del notifier no re-notifica trabajos ya con
    `last_notified_at` asignado
20. [ ] Test 7: El token completo no aparece en notificación, logs ni Data Table
21. [ ] Test 8: Sin trabajos pendientes de notificar → notifier termina sin
    enviar nada ni fallar

## Grupo 5: Documentación y merge

- [ ] Crear `docs/phase-8-notifications.md`
- [ ] Marcar items de Fase 8 en `specs/roadmap.md`
- [ ] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de éxito
- [ ] Mergear y limpiar
