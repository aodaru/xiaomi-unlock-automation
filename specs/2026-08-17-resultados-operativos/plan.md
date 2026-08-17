# Plan — Resultados operativos

Plan secuencial. Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

## Grupo 1: Diseño de la notificación al operador

1. [x] Definir el canal concreto de notificación (email SMTP por defecto, nodo
   de salida reemplazable por Slack/Telegram/webhook sin tocar la lógica).
   Realidad: sin credencial SMTP en la instancia → canal Gmail OAuth2 aislado y
   reemplazable (divergencia documentada en implementer-report.md)
2. [x] Definir el formato del mensaje: `job_id`, `token_hash` (o máscara con
   últimos 4; columna real `token_fingerprint`), tipo de resultado, estado,
   resultado redactado, error redactado, `exit_code` y fechas relevantes
3. [x] Definir la clasificación de 5 resultados usando contrato Fase 1:
   éxito, permiso denegado, token caducado, timeout y error
4. [x] Definir la regla de redacción del token: nunca completo, solo
   `token_hash` / máscara `****xxxx`

## Grupo 2: Campos anti-duplicados en Data Table

5. [x] Añadir columna `last_notified_at` (timestamp UTC de la última
   notificación; `null` mientras no se haya notificado)
6. [x] Añadir columna `notified_result` (tipo de notificación enviado, para
   auditoría)
7. [x] Validar que la fila terminal no se vuelve a seleccionar una vez
   `last_notified_at` tiene valor

## Grupo 3: Implementación del workflow de notificación

8. [x] Crear workflow n8n `Script Phase 8 Notifier` con Schedule Trigger
   (5 minutos por defecto, configurable a 1 minuto)
9. [x] Configurar nodo Data Table (Get Rows) con filtro: estado terminal
   (`success`, `failed`, `timeout`) Y `last_notified_at IS NULL`
   (expresado con `neq` de estados no terminales + `isEmpty`, ver reporte)
10. [x] Configurar nodos de lógica (Code/IF/Set) para clasificar el resultado
    en uno de los 5 tipos según `state`, `result` y `error`
11. [x] Configurar nodo de notificación (Send Email) con body redactado y
    credencial n8n (sin contraseñas embebidas)
12. [x] Configurar nodo Data Table (Update Row) para escribir
    `last_notified_at` y `notified_result`
13. [x] Configurar `retryOnFail`/`maxTries` y `continueRegularOutput` para que
    un fallo de notificación no bloquee el resto de trabajos

## Grupo 4: Pruebas y validación

14. [x] Test 1: Job `success` → notificación tipo `success`
15. [x] Test 2: Job `failed` con causa `token_expired` → notificación tipo
    `token_expired`
16. [x] Test 3: Job `failed` con causa `request_rejected` / `permission_blocked`
    → notificación tipo `permission_denied`
17. [x] Test 4: Job `timeout` → notificación tipo `timeout`
18. [x] Test 5: Job `failed` con causa desconocida → notificación tipo `error`
19. [x] Test 6: Segunda ejecución del notifier no re-notifica trabajos ya con
    `last_notified_at` asignado
20. [x] Test 7: El token completo no aparece en notificación, logs ni Data Table
21. [x] Test 8: Sin trabajos pendientes de notificar → notifier termina sin
    enviar nada ni fallar

## Grupo 5: Documentación y merge

- [x] Crear `docs/phase-8-notifications.md`
- [x] Marcar items de Fase 8 en `specs/roadmap.md`
- [x] Commit de todos los cambios
- [x] Push de la rama
- [x] Crear PR
- [x] Validar criterios de éxito
- [x] Mergear y limpiar
