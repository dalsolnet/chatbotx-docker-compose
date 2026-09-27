# ChatbotX adoption decision — 2026-09-27

Status: selected foundation; staged deployment package and pilot read-only adapter implemented. Upstream platform is not deployed or connected yet. This decision supersedes the earlier provisional Chatwoot choice in project documents.

## System boundaries

- ChatbotX Community: operational inbox, conversations, channel delivery, contacts, flows, campaigns and agent membership. Start with unmodified release images, preserve upstream licensing. Maintain a fork for reviewed fixes; custom fork changes require custom images.
- VINCHI commerce extension: Shopify store mapping, order lifecycle and identified checkout recovery. Current private pilot has manual records only. Implement one-way order projections first; do not dual-write conversation or delivery state.
- Shopify: authoritative customers/orders/fulfillments/payments. No Shopify integration implemented in this delivery.
- Mobile: reuse the MIT Expo app after staging API/auth/realtime tests. Only brand configuration draft delivered.
- n8n and agent tools: optional. Do not make them launch dependencies or point them at upstream SaaS by accident.

Separate ChatbotX workspace per store is the conservative initial boundary. Consolidating multiple storefronts into one workspace is a later explicit decision, requiring store IDs on every object and permission tests. Matching a phone number alone must not merge identities across businesses.

## Read-only bridge implemented

`POST /api/connections/chatbotx` accepts only a saved store UUID. Existing owner authentication, same-origin write checks, strict schema and database ownership lookup precede configuration lookup. Runtime secret `CHATBOTX_CONNECTIONS_JSON` maps `(ownerId, storeId)` to an exact upstream workspace, HTTPS origin and contacts/read-only token. URLs and keys are not accepted from the browser.

Calls `GET /api/v1/contacts?page=1&perPage=1`, disables redirects, limits response bytes to 128 KiB, uses an 8-second timeout and returns counts/verification state only. Every returned contact must have the configured workspace ID. An empty result reports reachable without workspace verification. Provider failures return a generic redacted error. No send, import, background sync, customer PII response or permanent connected-channel state exists.

The hostname restrictions reduce configuration mistakes; they are not DNS-based SSRF protection against a malicious operator. Operators must select a controlled public origin. ChatbotX public API tokens are workspace-wide; do not hand them to agents or assume member-specific contact masking applies. Current pilot is owner-only and trusts identity injected by its managed hosting proxy; independent hosting requires a real authentication boundary.

## Targeted source review

All five repositories were cloned and key documentation, licenses, deployment, authentication, public API, channel, mobile and automation paths inspected. This was not a line-by-line audit of all ~8,000 main-repository files, a penetration test, or a full upstream test-suite run.

| Finding | Inspected path | Treatment |
|---|---|---|
| Community/enterprise license split | `LICENSE`, `apps/builder/src/enterprise/LICENSE` | Community only; no bypass; paid features excluded from free promise |
| Demo user created by seed | `packages/database/src/seed/index.ts` | `RUN_DB_SEED=false`; no seed commands |
| Demo credentials, open datastores, dev tools | compose repository `docker-compose.yml` | generated secrets; only proxy ports; remove Adminer/Mailhog |
| Automatic migrations on runtime startup | builder entrypoint | disabled; manual maintenance-profile migration |
| S3 variable typo and signed URL host/path dependency | compose `S3_ENPOINT`, `packages/filesystem/src/lib/uploader.ts` | correct `S3_ENDPOINT`; same-origin `/chatbotx` bucket proxy preserving signature |
| Public bucket prefix configuration | filesystem init | anonymous download-only policy on `public/`; must verify runtime |
| Optional WhatsApp signature enforcement | `integrations/whatsapp/src/lib/signature-policy.ts` | require App Secret and negative signature test |
| Telegram webhook secret not checked in inspected handler | connect action, integration action, webhook handler and outer route | per-bot edge secret gate; one bot initially; re-register secret after reconnect |
| Public API scope differs from member UI restrictions | `docs/developer/workspace-api-tokens.md`, public contacts API | server-only read-only key, owner/store binding |
| No ready Shopify connector located | integrations, packages, builder source search | separate commerce adapter is required |
| Custom brand iOS icon path remains upstream | mobile `app.config.ts` | release blocker for branded iOS app; no build claimed |

Main review snapshot and release hashes are in `sources.lock.json`. Targeted diff against `v1.10.0` confirmed the contacts API/schema, uploader and Docker entrypoints used here; newer Telegram attachment enhancements on main are not promised for that release.

## Deployment constraints

Full stack needs Linux containers and persistent services, not the current Workers-only pilot hosting. Compose is a staging candidate and has not been pulled/booted here. Standalone Caddy 2.10.2 validation and loopback routing/security tests passed. Run `docker compose config --quiet`, repeat Caddy validation, image verification and full acceptance tests on the actual server. Record immutable image digests before production. No cost or account changes were made.

Realtime still uses upstream PartyKit's `dev` runner architecture (now pinned via local `pnpm exec`); validate its operational limits and lifecycle on staging before using at scale. RustFS upstream image is beta. Private attachments, public prefix policy, SMTP, open signup policy, TLS, mobile auth and restart recovery are launch gates.

The Arabic operator runbook is `README_AR.md`. It includes fork instructions, commands, bot registration, backup/rollback boundaries, migration sequence and acceptance gates. No enterprise source is redistributed in this package.
