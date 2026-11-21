# AI provider keys: the master key and how to look after it

Each coaching pastes its own AI provider keys (Anthropic, OpenAI, Google, OpenRouter) into the app
(Admin → AI, from M5's web steps; the API is `PUT /api/v1/ai/keys/{provider}`). The app never stores a
key as typed. It **seals** it (AES-256-GCM) with a **master key** that lives only in the server's
environment, never in the database. So a stolen database backup holds nothing a thief can use, and
one coaching's sealed key cannot be opened as another's. The design is
[ADR-0023](../architecture/adr/0023-ai-keys-encryption-and-provider-access.md).

**You** make and keep the master key. Never paste it, or a provider key, into a chat, an issue or a file
in this repository.

## 1. Make a master key (once)

In PowerShell (it asks the operating system for 32 random bytes and prints them as text):

```powershell
$b = New-Object byte[] 32; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($b); [Convert]::ToBase64String($b)
```

Copy the line it prints. Put it in two places:

1. Your **password manager**, with a name such as "Question bank master key k1". This is the copy that
   survives if the PC is lost. It must **not** live in the same backup as the database dump (K-16), or the
   backup would hold both the lock and its key.
2. The `.env` file next to `compose.yaml` (never committed):

   ```text
   AI_KEYS_MASTER_KEY=the-line-you-copied
   ```

Then restart the stack so the API reads it:

```powershell
docker compose up -d
```

Without a master key the app works as before and keys simply cannot be stored: the API answers
`AI_NOT_CONFIGURED` and the AI screen says to ask whoever runs the server.

A key that is not 32 bytes of base64 stops the app at start with a message that names the setting and
never prints the value.

## 2. What losing it means

If the master key is lost, the stored provider keys **cannot be opened**. Nothing else is lost: an admin
pastes each provider key again. Keep the password manager copy so that does not happen.

## 3. Change it (rotation)

Do this if the key may have leaked, or on a schedule. The old key stays available until every stored key has
been sealed again.

1. Make a new key as in section 1. Give it a new id.
2. In `.env`, move the old settings and add the new ones (ids are lower-case letters, digits, `-` or `_`):

   ```text
   AI_KEYS_MASTER_KEY=the-new-key
   AI_KEYS_MASTER_KEY_ID=k2
   AI_KEYS_PREVIOUS=k1=the-old-key
   ```

3. Restart (`docker compose up -d`), then seal every stored key again under the new one:

   ```powershell
   docker compose run --rm migrate qbank rotate-ai-keys
   ```

   It prints, per coaching, how many keys it resealed. It stops with a message for any coaching whose keys
   it could not open (for example, `AI_KEYS_PREVIOUS` was left out) and leaves that coaching unchanged.
   Running it again is harmless.
4. Once it reports nothing left to reseal, remove the `AI_KEYS_PREVIOUS` line and restart. Keep the old
   key in the password manager for as long as you keep database backups made before the rotation: those
   backups hold keys sealed with it.

## 4. What is and is not visible

- The API and the screen show only whether a key is stored and its **last four characters**.
- The audit log records who stored, replaced or removed a key, and the last four characters, never the key.
- Log lines and error messages never carry a key or the master key (the logging safety net blanks the field
  names, and the code logs identifiers only).
- A provider's own console is the place to set a spending limit and to revoke a key you think has leaked;
  replacing a key in the app does not revoke the old one at the provider.

## 5. After a key is stored: the model list and trying a key

- **Models** (`GET /api/v1/ai/models`, admins): press Refresh for a provider
  (`POST /api/v1/ai/models/refresh`). A background job asks the provider for its list with the stored
  key and fills the coaching's model table. New models start **disabled**; an admin enables the ones
  faculty may use and can enter capabilities and prices the provider does not publish (the admin's entry
  wins). A model that disappears from a later list stays on record as unavailable. The list shows when
  it was last fetched and, if the last try failed, the kind of failure (`AUTH`, `RATE_LIMITED`,
  `TIMEOUT`, `UNAVAILABLE`); a failed refresh is not retried by itself. The background worker needs the
  same `AI_KEYS_MASTER_KEY` as the API (the compose file passes it to both).
- **Try a key and an adapter for real.** CI never calls a provider, so this is how you find out that an
  adapter and a key work together. It prints what happened and never the key:

  ```powershell
  docker compose run --rm migrate qbank ai-smoke --organization <coaching id> --provider anthropic
  docker compose run --rm migrate qbank ai-smoke --organization <coaching id> --provider anthropic --model <model id>
  ```

  The first lists the provider's models; the second also asks that model for a tiny answer (it costs a
  fraction of a cent). Until you have run this once per provider, the adapters are checked only against
  the providers' published documents.

## 6. Defaults, the rate and budgets

Admins set these (`/api/v1/ai/settings`, `/operations`, `/budgets`; the Admin → AI screen comes with
M5's web steps):

- **Rate.** Providers bill in US dollars; budgets are in rupees. Enter today's rupees-per-dollar rate.
  Without it no budget can be applied, so a spending limit does nothing until the rate is set. Change it
  when the rate moves: each cost keeps the rate it was written at.
- **Default monthly budget** per person (rupees; empty = no limit) and a **budget of their own** for any
  member (`0` = may not use AI). The month runs from the 1st to the last day in India time.
- **Per operation** (tag, translate, solve, verify): the model offered first, Now or Economy, and up to
  two fallback models tried in order if the first fails in a way that may pass. A model must be enabled,
  still listed by the provider and able to return JSON; Economy only for a model you have marked as
  offering batch runs. If you later disable a model that is a default, the screen shows it and runs
  refuse it until you choose another.

Each save needs the version you last read, so two admins cannot overwrite each other unseen, and each is
in the audit log with before and after.
