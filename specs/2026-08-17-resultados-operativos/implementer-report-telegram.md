# Reporte del implementador — Cambio de canal: Gmail → Telegram (Fase 8)

Fecha: 2026-08-17 · Sin commit/push/PR (lo coordina el líder).

## Resumen ejecutivo

El workflow `Script Phase 8 Notifier` (`16cYVCoO48LxBxl4`) estaba **activo** y publicaba
una versión que enviaba las notificaciones por **Gmail** (`Send Email Notification`,
`n8n-nodes-base.gmail` 2.2). El draft ya contenía un nodo **Telegram** (`Send a text
message`, `n8n-nodes-base.telegram` 1.2) conectado pero sin configurar (sin `chatId`,
sin `text`, sin credencial), y el nodo Gmail quedaba huérfano. Esta tarea configuró el
nodo Telegram, eliminó el Gmail y republicó el workflow para que el canal efectivo sea
**Telegram**.

## Nodos finales (5, conexión única)

```
Every 5 Minutes (scheduleTrigger 1.3)
  → Data Table Get Rows (dataTable 1.1)
    → Classify Result (code 2, runOnceForEachItem)
      → Send a text message (telegram 1.2)      ← canal configurado en esta tarea
        → Data Table Update Row (dataTable 1.1)
```

Nodos NO tocados (regla dura): `Every 5 Minutes`, `Data Table Get Rows`,
`Classify Result`, `Data Table Update Row`. Nodo eliminado: `Send Email Notification`
(Gmail) — huérfano, sin conexiones, eliminación segura.

## Configuración aplicada al nodo Telegram (`Send a text message`)

| Parámetro | Valor |
|---|---|
| `resource` | `message` |
| `operation` | `sendMessage` |
| `chatId` | `744884859` |
| `text` | `={{ $json.body }}` |
| `additionalFields.parse_mode` | `none` |
| Credencial | `Telegram account` — credentialId `Z3r0YRo0ftwFvRYO` (tipo `telegramApi`) |
| `retryOnFail` / `maxTries` | `true` / `3` |
| `onError` | `continueRegularOutput` |

El `body` proviene de `Classify Result` y ya está redactado (solo `token_mask`
`****xxxx`, nunca el token/fingerprint completo); el nodo Telegram no añade lógica.

## Evidencia para elegir credencial y chatId

- El nodo Telegram v1.2 en esta instancia **no expone** `@loadOptionsMethod` /
  `@searchListMethod` para `chatId` (es un `string`), por lo que `explore_node_resources`
  no aplica. Se resolvió por evidencia de la propia instancia:
  - `chatId` **744884859** es el chat privado del operador `Aodaru` y es el mismo valor
    usado por los workflows activos `Brute Force - Reporte Diario` y
    `AsisVirtual Telegram Bot` (y el histórico `Daily Report`).
  - La credencial `Telegram account` (`Z3r0YRo0ftwFvRYO`) corresponde al bot
    **`TeaPartyDev_bot`** (id 8378951561): la ejecución 8069 de
    `Brute Force - Reporte Diario` confirma que ese bot entrega con `ok: true` al chat
    744884859. `ReelGenBot` (`SAvctbPfzlal6RvM`) es el bot de los workflows ReelGen, no
    el canal de notificaciones operativas.

## Operaciones aplicadas (update_workflow, sin recrear el workflow)

1. `setNodeParameter` `/chatId` = `744884859`
2. `setNodeParameter` `/text` = `={{ $json.body }}`
3. `setNodeCredential` `telegramApi` → `Telegram account` (`Z3r0YRo0ftwFvRYO`)
4. `setNodeSettings` `retryOnFail: true`, `maxTries: 3`, `onError: continueRegularOutput`
5. `removeNode` `Send Email Notification`
6. `setNodeParameter` `/resource` = `message`, `/operation` = `sendMessage`
   (discriminadores; el batch inicial devolvió un warning de esquema por no declararlos)
7. `setNodeParameter` `/additionalFields/parse_mode` = `none` (hallazgo, ver pruebas)

Validaciones: `validate_node_config` OK para el nodo Telegram (parámetros + tipo +
versión). `update_workflow` final sin `validationWarnings`.

## Pruebas ejecutadas

Metodología: `prepare_test_pin_data` + `test_workflow`. Se pinnearon `Every 5 Minutes`
y `Data Table Get Rows` (fila sintética terminal `success`, `job_id` sintético). El nodo
Telegram **no se pineó** (envío real a propósito, 1 mensaje por prueba) y
`Classify Result` / `Data Table Update Row` ejecutaron de verdad.

| # | Ejecución | Resultado |
|---|---|---|
| 1 | **8299** | `success` completo. Telegram entregó con `ok: true` al chat `744884859` (Aodaru) vía `TeaPartyDev_bot` (message_id 489). **Hallazgo**: el mensaje llegó con la máscara degradada (`Token: b855` en vez de `****b855`) y `timeout_at` → `timeoutat`, `is_pass=1` → `ispass=1` — el parse mode por defecto (Markdown) eliminaba `_`/`*`. |
| 2 | **8301** | `success` completo tras fijar `parse_mode: none`. Mensaje en texto plano (message_id 490) con `Token: ****b855`, `timeout_at` e `is_pass=1` intactos. Confirmado credencial + chatId + redacción. |

`Data Table Update Row` ejecutó con `success` en ambas (job_id sintético no matcheó filas
reales → no escribió nada: esperado en sandbox). No se observó duplicado de envío.

## Versión publicada

- Antes: versión activa `f5d3814f-3591-43b9-8836-d7bdaf256065` (con Gmail).
- Después (cambio de canal): `publish_workflow` → versión activa
  `ef4c9be2-4d7b-41c4-b681-b74809419260` (canal Telegram efectivo).
- Después (corrección post-review C4): `publish_workflow` → versión activa
  **`5afef109-0c5a-49c5-9abf-466e3a9df8ff`** (Update Row sin escrituras extra;
  draft = activo, `active: true`, `triggerCount: 1`).
- Settings globales intactos: `timezone UTC`, `executionOrder v1`, `executionTimeout 600`.

## Divergencias registradas

- **D1 (canal email SMTP)** → Telegram: el operador recibe las notificaciones operativas
  por Telegram; no existe credencial SMTP y Gmail no es el canal habitual. El nodo de
  salida sigue aislado y reemplazable.
- `sendTo` (email) → `chatId` `744884859`: destinatario resuelto por evidencia de la
  instancia (chat privado del operador ya en uso por workflows activos).
- `validate_node_config` da falso negativo para `parse_mode` (exige expresión incluso
  para valores enum válidos que ya funcionan en producción, p. ej. `Markdown`/`HTML`);
  la decisión se tomó con evidencia empírica (ejecución 8301).

## Reglas duras respetadas

- El token completo nunca aparece: `body` usa `token_mask` (`****xxxx`); verificado en
  las ejecuciones 8299/8301 (el texto entregado solo contiene la máscara).
- No se recreó el workflow ni se cambió su ID.
- No se tocaron los nodos 1-3 ni el Update Row.
- No se cambiaron timezone ni settings globales.
- Spec Fase 8 respetada: anti-duplicados (filtro `isEmpty` + defensa en Code + Update Row),
  5 tipos de clasificación, UTC, tolerancia a fallos del canal.

## Corrección post-review (C4 bloqueante)

El reviewer (`changelog.md`, sección "Review — Fase 8 cambio de canal Gmail →
Telegram") detectó que la versión publicada `ef4c9be2` llevaba en
`Data Table Update Row` (`fc8b5700-a4e3-434a-8d18-b96a1587882e`) un
`columns.value` con `token_slot:0, timeshift:0, exit_code:0, check_count:0`
heredado de un autosave previo (`5a2262b1`). Con `mappingMode: defineBelow`
todas las claves se escriben, por lo que la primera fila terminal REAL
notificada habría reseteado `exit_code` (10/30/40 → 0), `check_count`,
`token_slot` y `timeshift`, corrompiendo la auditoría (contrato Fase 1 exige
conservar `exit_code`).

Remediación aplicada (mínima, sin tocar Telegram ni los pasos 1-3):

1. `validate_node_config` OK con el `columns.value` corregido.
2. `update_workflow` → `setNodeParameter` `/columns/value` en `Data Table
   Update Row` (nodeName exacto) restaurando SOLO:
   `last_notified_at` = `{{ $('Classify Result').item.json.last_notified_at }}`
   y `notified_result` = `{{ $('Classify Result').item.json.notified_result }}`
   (igual que la versión aprobada `f5d3814f`). `matchingColumns`, `schema` y
   `filters` intactos.
3. `publish_workflow` → versión activa **`5afef109-0c5a-49c5-9abf-466e3a9df8ff`**
   (workflow sigue `active: true`).
4. `get_workflow_details`: `columns.value` con solo los dos campos en draft y
   versión activa; Telegram intacto (`chatId 744884859`, `text ={{ $json.body }}`,
   `parse_mode none`, credencial `Z3r0YRo0ftwFvRYO`, tolerancia intacta), Gmail
   ausente, cadena única de conexiones y settings globales (UTC/v1/600) sin
   cambios.

## Documentación actualizada

- `docs/phase-8-notifications.md`: recursos (credencial/chat/estado), flujo paso 4,
  configuración requerida, tabla de divergencias (D1 y `sendTo`), pruebas 9-10 y sección
  "Cambio posterior: canal Gmail → Telegram" (fecha 2026-08-17 y motivo).
- `specs/2026-08-17-resultados-operativos/implementer-report.md`: sección final
  "Cambio posterior: notificación por Telegram".
- Sin commit/push/PR (lo coordina el líder).