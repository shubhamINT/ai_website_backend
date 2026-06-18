# Ponytail Audit — over-engineering findings

Repo-wide scan for bloat/dead code/reinvented stdlib. Ranked biggest cut first.
One-shot report — nothing applied. Verify each before cutting.

Tags: `delete:` dead code · `stdlib:` stdlib ships it · `native:` platform does it · `yagni:` speculative · `shrink:` same logic fewer lines.

## Findings

| # | tag | what to cut | replacement | path | ~lines |
|---|-----|-------------|-------------|------|--------|
| 1 | delete | whole `async_db_usage_example.py` — stray SQLAlchemy example, never imported, project uses Beanie/Mongo | delete file | assets/plans/async_db_usage_example.py | -38 |
| 2 | shrink | hand-rolled brace-depth JSON extractor (escape + string-literal tracking) | `json.JSONDecoder().raw_decode(buffer, idx)` | src/services/llm/ui_agent.py:123-170 | -43 |
| 3 | delete | `_resolve_snapshot()` copy-pasted verbatim in two tools | pull into a shared snapshot helper mixin | email.py:28-70 + whatsapp.py:12-53 | -42 |
| 4 | shrink | per-tool form preview/submit boilerplate (payload→packet→snapshot) | one `_publish_form_state(form_type, data)` helper | forms.py, meeting.py | ~-40 |
| 5 | shrink | `_format_metadata_value()` reinvents JSON parse + title-casing | title-key + `json.loads` + str | vector_search.py:14-39 | -20 |
| 6 | yagni | `_get_snapshot_at_offset()` general clamp/safety; offset only ever 0–2 | inline at call sites | state.py:109-123 | -15 |
| 7 | shrink | two mail modules each carry global `_TEMPLATE` + loader + `global` | `@functools.lru_cache` | submission_receipt.py:45-63, context_email.py:21-40 | -10 |
| 8 | yagni | `RotatingFileHandler` (5MB×N) — not a stated requirement | plain `FileHandler` | core/logger.py:31-38 | -6 |
| 9 | delete | cosmetic `asyncio.sleep(0.3/0.5)` "visual effect" delays — form render instant | remove | forms.py:56,91 meeting.py:126 | -5 |
| 10 | delete | `close_db()` defined, never called (no shutdown hook) | remove | core/database.py:23-27 | -5 |
| 11 | shrink | startup handler-cleanup loop over-defensive (runs once) | drop | core/logger.py:14-17 | -4 |
| 12 | stdlib | manual SMTP `quit()` | `smtplib.SMTP` supports `with` since 3.3 | mail/calender_invite.py:122-126 | -4 |
| 13 | delete | unused imports: `List`+`ListRoomsRequest`+`CreateSIPParticipantRequest` (livekit_svc.py:5,8-11); `Dict` (infographic.py:6); `partial` (email.py:3); `require_admin`+`Annotated` (routes/auth.py:6,13) | remove | multiple | -8 |
| 14 | delete | re-imports inside functions: `re as _re` (whatsapp/context_whatsapp.py:87); `asyncio` ×3 (ui_agent.py:71,187,250) | use module-level | multiple | -4 |
| 15 | delete | commented-out dispatch log | remove | livekit_svc.py:64-65 | -2 |
| 16 | delete | `LogoutResponse` model unused (route returns dict literal) | remove | api_schemas.py:25-26 | -2 |
| 17 | yagni | lazy `_get_session()` risks leaked aiohttp session | create in `__init__` or use ctx manager | map/googlemap/services.py:41-46 | safer, ~0 |

**net: ~-250 lines, -0 deps.** No removable dependency — wins are dedup + stdlib JSON parser, not packages.

## Not bloat (skipped)

- data_handler.py:32-47 commented lines — deliberate privacy design note (agent must not know user name/email). Keep.
- `utcnow()` deprecation + `Optional`→`|` — modernization, no line cut.
