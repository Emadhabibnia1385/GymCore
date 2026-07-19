# Telegram vs Bale — platform differences

GymCore runs one shared codebase on both Telegram and Bale. Bale exposes a
Telegram-compatible Bot API (`https://tapi.bale.ai`), so a single `BotClient`
and one set of handlers serve both. Where the platforms genuinely differ, the
behaviour is preserved and the *interaction* is adapted through `BotContext`
capabilities — no unsupported feature is ever faked.

| Capability | Telegram | Bale | How GymCore adapts |
|---|---|---|---|
| Inline "glass" keyboards | ✅ | ✅ | Same inline keyboards on both. |
| Web App / Mini App (`web_app` button) | ✅ | ❌ | «سفارش برنامه» is a plain **URL button** on both (opens the signup site directly, not a Mini App). |
| Coloured buttons (`style`: primary/success/danger) | ✅ (Bot API, Feb 2026) | ❌ not yet | `BotContext.supports_button_style` is `True` only on Telegram — the client menu buttons carry `style` (blue register/order, green my-classes/programs, red contact). Bale gets plain buttons (the field is omitted so it is never rejected). Toggle via the `button_style_enabled` setting. Old Telegram clients (pre-Feb 2026) just show buttons uncoloured. |
| Inline-button URL schemes | http/https/tg only | http/https/tg only | `mailto:`/`tel:` are invalid as inline buttons (BUTTON_URL_INVALID) — the coach's email/phone links are rendered as copyable **text**, other links as buttons. |
| Editing a message that carries an inline keyboard | ✅ reliable | ⚠️ unreliable | `BotContext.supports_edit` is `True` for Telegram (screens update in place) and `False` for Bale (every screen is sent as a **fresh message**). Navigation therefore always works on Bale. |
| `answerCallbackQuery` | ✅ | ⚠️ may be absent | Callbacks are always answered, but the call is best-effort — a failure is swallowed and never blocks the handler. |
| Sending files | by `file_id` or upload | by `file_id` or upload | Program delivery tries the stored `file_id` first (fast path on the same platform), then an uploaded file, then a text-only caption. |
| Owner / admin IDs | `TELEGRAM_OWNER_IDS` | `BALE_OWNER_IDS` | Admin authorization is **per platform**: a Telegram owner is not automatically an admin on Bale and vice-versa. Numeric IDs only — usernames are never trusted. |
| Contact links | shared | shared | The same `ContactLink` rows render on both. An optional `platform` hint features a link on its own platform (e.g. the Telegram link first on Telegram); the coach can add a Bale contact link from the admin panel. |

## Cross-platform file delivery

A program uploaded through one platform stores that platform's `file_id`. Re-sending
it on the **same** platform is instant. On the **other** platform the `file_id` is
not valid, so delivery falls back to the caption (and, when an uploaded copy exists
under the access-controlled upload dir, to re-uploading that copy). For programs that
must reach clients on both platforms, upload the file rather than relying only on a
platform `file_id`.

## Identity

A `Person` is the shared human identity and owns all data (courses, programs,
attendance, payments). Each `ChannelIdentity` links one platform account
(`TELEGRAM` or `BALE`) to that person, so a client may switch platforms and the
coach can link both accounts to the same person from the admin panel.
