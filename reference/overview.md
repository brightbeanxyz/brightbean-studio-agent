# Brightbean Studio Agent — surface map

```
Organization
└── Workspace                    ← API key is bound to ONE workspace
    ├── SocialAccount (linkedin_personal, "Acme on LinkedIn")
    ├── SocialAccount (instagram,        "@acme")
    ├── SocialAccount (linkedin_company, "Acme Inc.")
    └── ApiKey (bb_studio_…)     ← Allowlists a SUBSET of the workspace's accounts
        └── Post                 ← Workspace-scoped
            └── PlatformPost     ← One per targeted SocialAccount
                ↓
            PublishEngine        ← Polls every ~15s, publishes due rows
```

## Key facts an agent needs

- **Multi-tenant.** Every resource lives inside an Organization → Workspace.
- **Keys are workspace-scoped.** Each `ApiKey` belongs to exactly one
  Workspace; a key can never see resources in another workspace, even in
  the same organization.
- **Accounts are allowlisted.** An `ApiKey` carries an explicit list of
  `SocialAccount` IDs it may target. Anything else returns 403/404.
- **Posts have per-platform children.** `Post` holds the shared content;
  `PlatformPost` rows (one per `SocialAccount`) own the editorial state
  (`draft → scheduled → publishing → published`).
- **Publishing is asynchronous.** The Agent API never calls the social
  platform directly — it just writes `PlatformPost` rows. The publisher
  polls every ~15 seconds and dispatches them. So:
  - A `POST /posts/ {action: schedule}` doesn't immediately reach LinkedIn.
  - The actual publish happens at the next poll cycle after `scheduled_at`.
  - `platform_post_id` is filled in by the publisher after success.

## Auth surface

Single header, every request:

```
Authorization: Bearer bb_studio_<random>_<lookup>
```

- HTTPS required in production (over plain HTTP the request gets a generic
  401 to avoid fingerprinting).
- The token is hashed at rest (HMAC-SHA256, peppered from `SECRET_KEY` via
  HKDF) — server DB compromise doesn't leak plaintext tokens.
- Revocation propagates immediately via an in-process cache bust + signal
  handlers on `m2m_changed` and `post_save`.

## State machine

```
draft ─────► scheduled ─────► publishing ─────► published    (terminal)
  ▲          │   ▲              │
  └──────────┘   │              ▼
                 │            failed
                 │              │
                 └──── retry ───┘
```

The Agent API exposes these transitions:

- `create_post(status=draft)` — birth as draft
- `create_post(status=scheduled)` — birth as scheduled
- `POST /posts/{id}/schedule` — draft → scheduled
- `POST /posts/{id}/cancel` — scheduled → draft

`publishing`, `published`, `failed` are owned by the publisher and not
directly addressable from the agent surface.

## Permissions you'll deal with

The composer permission model splits these into two tiers:

| Permission         | What it gates                                              |
|--------------------|------------------------------------------------------------|
| `create_posts`     | Drafting and editing a `Post` / `PlatformPost`             |
| `publish_directly` | Transitioning to `scheduled` — required by both `POST /posts {action: schedule}` and `POST /posts/{id}/schedule` |

A key with only `create_posts` can draft and edit; it cannot schedule.
This mirrors the editor / publisher split in the composer's HTMX UI.

If the user's workspace has `approval_workflow_mode` set to
`required_internal*`, NEITHER `create_posts` NOR `publish_directly` lets
an agent skip approval — `create_post(status=scheduled)` will return
422 with a message about routing through the approval workflow.

## Related concepts (not in Brightbean's API)

- The Agent API doesn't manage social-platform OAuth — connect/disconnect
  happens in the studio UI, not via API.
- The Agent API doesn't expose analytics, inbox messages, or media uploads
  via the v1 surface; if the user asks for those, you can't help via this
  skill.
