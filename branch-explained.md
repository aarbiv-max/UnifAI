## Workspace Model — `GENIE-1341/story/workspace-model`

Transforms the platform from single-user ownership (`user_id` strings) to **identity-scoped multi-tenancy** supporting both personal and team workspaces.

---

### 1. Identity Model

Canonical definition in `global_utils/src/global_utils/identity.py`, re-exported by `mas.core.identity` and `sso-backend/identity/models`.

```python
class IdentityType(str, Enum):
    USER = "user"
    TEAM = "team"

class Identity(BaseModel):
    type: IdentityType
    id: str
    display_name: str = ""
    email: str = ""
```

Factory methods: `Identity.user(...)`, `Identity.team(...)`.
Convenience properties: `identity.is_user`, `identity.is_team`.

---

### 2. MongoDB Schema Migration

All collections migrated from flat `user_id` to nested `identity` subdocument:

| Collection | Old | New |
|---|---|---|
| `blueprints` | `user_id` | `identity` |
| `resources` | `user_id` | `identity` |
| `workflow_sessions` | `user_id`, `run_context.user_id` | `identity`, `run_context.identity` |
| `shares` | `sender_user_id`, `recipient_user_id` | `sender_identity`, `recipient_identity` |
| `templates` | `user_id` | `identity` |

Bidirectional migration script: `scripts/migrate_user_id_to_identity.py` (dry-run by default, `--apply` to execute, `--reverse` to roll back). Handles index cleanup, team-type correction, and nested fields.

---

### 3. API Layer — `@with_identity` Decorator

All identity-scoped endpoints use the **`@with_identity`** decorator (`inbound/flask/decorators.py`). It reads `userId`, `identityType`, `displayName` from query params or JSON body, builds an `Identity`, and injects it as the `identity` kwarg. Returns 400 automatically for missing/invalid params.

```python
@bp.route("/resources.list", methods=["GET"])
@require_identity_authorization
@with_identity
@from_query({"category": fields.Str(required=False)})
def list_resources(identity, category=None):
    resources, total = svc.find_resources(identity=identity, category=category)
    ...
```

Internally delegates to `resolve_identity()` in `identity_helpers.py`. Flat params (`userId` + `identityType`) are used consistently across GET and POST for a uniform API shape. `identityType` defaults to `"user"`.

**Request flow:**
```
GET /resources.list?userId=alpha-team&identityType=team&category=provider
→ @with_identity → Identity(type=TEAM, id="alpha-team")
→ Service → Mongo filter: {"identity.type": "team", "identity.id": "alpha-team"}
```

---

### 4. Team Management

Full CRUD for teams with structured members (direct users + LDAP groups). Teams live in both SSO backend and a secondary backend service.

- Members can be **users** (direct) or **groups** (LDAP groups that expand to individual usernames)
- Team creator can delete — triggers cascade cleanup of all team-owned resources, blueprints, and sessions via `workspace.cleanup`
- Directory integration: pluggable LDAP provider for user/group search

---

### 5. Collaboration Hub

Redis-backed real-time presence for team workspaces:
- **Participants**: Hash per session tracking who's in
- **Heartbeats**: TTL-based presence keys (300s), lazily pruned
- **Typing indicators**: Auto-expiring keys (5s)
- **Team session index**: Set of active session IDs per team
- **Edit locks** (team workspace, when Redis is up): cooperative locks on **resources** and **blueprints** (`mas:collab:editlock:team:…`, ~180s TTL, client heartbeat). REST: `/collaboration/edit_lock.*` — UI disables edit actions and shows who holds the lock; saves are not yet validated against the lock on the server.

Multiple users in the same team session see identical data — sessions, chat, and live streaming events are all scoped to the team identity.

---

### 6. UI

- **`ViewContext.tsx`**: manages private/team mode switching, fetches user's teams and LDAP groups on mount
- **`use-workspace-data.ts`**: derives `userId` + `identityType` for every API call based on current view mode
- Team settings modal, directory-powered user search, collaboration hub view, team-aware pages

---

### 7. Sharing to Teams

Extended share/clone flow supports team contributions. `ShareCloner` deep-clones resources (with full dependency graphs) into the team workspace, setting `identity.type="team"` and `contributed_by` metadata on each clone.
