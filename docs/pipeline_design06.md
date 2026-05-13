## PHASE 1: DESIGN

# Migrate UnifAI Secrets to HashiCorp Vault via OpenShift Vault Operator

**Jira Ticket:** GENIE-948  
**Status:** Code Review  
**Assignee:** Saar Fireshtein

---

## 1. Overview

- **Problem Statement:** UnifAI stores sensitive credentials (Gemini API keys, encryption keys, client secrets, Slack tokens, Redis passwords) in a GitHub repository and Kubernetes ConfigMaps populated by Jenkins presync/postsync shell hooks. Git history is permanent and ConfigMaps are stored as plaintext in etcd, creating high security exposure.
- **Proposed Solution:** Migrate all sensitive values to the company's existing HashiCorp Vault instance (vault.corp.redhat.com). Use the OpenShift Vault Operator to inject secrets as in-memory files (`/vault/secrets/`) into application pods. Extend the application's `SharedConfig` with a new `VaultFileSource` to read injected files, with automatic fallback to `.env` for local development.
- **Success Metrics:**
  - All sensitive credentials removed from Git and ConfigMaps
  - Pods start successfully, reading secrets from `/vault/secrets/` (tmpfs)
  - Old credentials revoked and rotated
  - CI/CD pipeline deploys using Vault integration (no hardcoded secrets)
  - Vault audit log records all secret access
  - Local developer workflow unchanged (`.env` files continue to work)
  - No downtime during migration (parallel-run strategy)

---

## 2. Affected Components

| Layer | Component | Action (New/Modified) | File Path |
|-------|-----------|----------------------|-----------|
| Domain — Config | `VaultFileSource` | New | `global_utils/src/global_utils/config/sources.py` |
| Domain — Config | `SharedConfig` settings source chain | Modified | `global_utils/src/global_utils/config/config.py` |
| Adapter — Helm | Backend deployment (Vault annotations) | Modified | `helm/backend/unifai-backend/templates/deployment.yaml` |
| Adapter — Helm | Multiagent BE deployment | Modified | `helm/multiagent/be/templates/be-deployment.yaml` |
| Adapter — Helm | Temporal worker deployment | Modified | `helm/multiagent/temporal-worker/templates/be-deployment.yaml` |
| Adapter — Helm | RAG server deployment | Modified | `helm/rag/unifai-rag-server/templates/deployment.yaml` |
| Adapter — Helm | RAG celery deployment | Modified | `helm/rag/unifai-rag-celery/templates/deployment.yaml` |
| Adapter — Helm | Identity deployment | Modified | `helm/shared-resources/identity/templates/deployment.yaml` |
| Adapter — Helm | Global config values (Vault path) | Modified | `helm/values/global-config.yaml` |
| Adapter — Helm | ServiceAccount annotations (all) | Modified | `*/templates/serviceaccount.yaml` |
| Adapter — CI/CD | Multiagent presync hook | Modified | `helm/scripts/multiagent-presync.sh` |
| Adapter — CI/CD | Identity presync hook | Modified | `helm/scripts/identity-presync.sh` |
| Adapter — CI/CD | Shared-resources postsync hook | Modified | `helm/scripts/shared-resources-postsync.sh` |
| Adapter — CI/CD | RAG presync hook | Modified | `helm/scripts/rag-presync.sh` |
| Config / Infra | Vault policy documentation | New | `helm/vault/policy.hcl` |
| Config / Infra | Vault secrets seeding script | New | `scripts/vault_seed.sh` |

---

## 3. Technical Design

### 3.1 Vault KV v2 Secret Structure

```
apps/automation-and-tools/unifai/
├── shared/
│   ├── REDIS_PASSWORD
│   ├── UMAMI_USERNAME
│   └── UMAMI_PASSWORD
├── backend/
│   └── admin_allowed_users
├── multiagent/
│   ├── CREDENTIAL_ENCRYPTION_KEY
│   ├── MCP_AUTH_STATE_SECRET
│   └── admin_allowed_users
├── identity/
│   ├── client_secret
│   ├── secret_key
│   └── admin_allowed_users
└── rag/
    ├── default_slack_bot_token
    └── default_slack_user_token
```

Uses existing AppRole path `apps/automation-and-tools` per `vault.txt` in UnifAI-secrets repo.

### 3.2 VaultFileSource (New Config Source)

**Purpose:** Read secrets from Vault Agent-injected files.

**Interface:**

```python
class VaultFileSource(ConfigSource):
    """Reads key=value pairs from Vault-injected files at /vault/secrets/."""

    def __init__(self, vault_path: str = "/vault/secrets"):
        self._vault_path = Path(vault_path)

    def load(self) -> Dict[str, Any]:
        """
        Scans all files in vault_path directory.
        Each file contains key=value lines (rendered by Vault Agent template).
        Returns merged dict. Returns {} if path doesn't exist (local dev).
        """
```

**Dependencies:** None (reads filesystem only — pure adapter logic).

**Integration into SharedConfig:**

```python
settings_customise_sources=lambda init, env, fs: (
    init,
    env,
    VaultFileSource().load,     # NEW: after env, before .env
    DotEnvSource().load,
    YamlSource().load,
    JsonSource().load,
    fs,
)
```

Priority: `init > env vars > vault files > .env > yaml > json > file settings`

### 3.3 OpenShift Vault Operator Pod Annotations

Each deployment template gains:

```yaml
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "unifai"
        vault.hashicorp.com/agent-inject-secret-shared: "apps/automation-and-tools/unifai/shared"
        vault.hashicorp.com/agent-inject-secret-<service>: "apps/automation-and-tools/unifai/<service>"
        vault.hashicorp.com/agent-inject-template-shared: |
          {{- with secret "apps/automation-and-tools/unifai/shared" -}}
          {{- range $k, $v := .Data.data -}}
          {{ $k }}={{ $v }}
          {{ end -}}
          {{- end -}}
        vault.hashicorp.com/agent-inject-template-<service>: |
          {{- with secret "apps/automation-and-tools/unifai/<service>" -}}
          {{- range $k, $v := .Data.data -}}
          {{ $k }}={{ $v }}
          {{ end -}}
          {{- end -}}
```

Secrets injected to `/vault/secrets/shared` and `/vault/secrets/<service>` on tmpfs.

### 3.4 Kubernetes Service Account Authentication

- **Method:** Vault `kubernetes` auth backend, bound to OpenShift cluster API
- **Role:** `unifai` — bound to all UnifAI namespace ServiceAccounts
- **Policy:** `unifai-read` — `read` capability on `apps/automation-and-tools/unifai/*`

ServiceAccount templates annotated with:
```yaml
vault.hashicorp.com/agent-inject: "true"
```

### 3.5 Presync Hook Cleanup

| Hook | Secrets to Remove | Non-secrets to Keep |
|------|------------------|---------------------|
| `multiagent-presync.sh` | `CREDENTIAL_ENCRYPTION_KEY`, `MCP_AUTH_STATE_SECRET` | `admin_allowed_users` (or move to Vault) |
| `identity-presync.sh` | `client_secret`, `secret_key` | `keycloak_base_url`, `client_id`, `keycloak_realm` |
| `shared-resources-postsync.sh` | `REDIS_PASSWORD`, `UMAMI_PASSWORD` | Service discovery (IPs, ports, URLs) |
| `rag-presync.sh` | `default_slack_bot_token`, `default_slack_user_token` | — (hook becomes no-op or deleted) |

### 3.6 Vault Seeding Script

**Purpose:** One-time script to populate Vault KV with existing secrets.  
**Location:** `scripts/vault_seed.sh`

```bash
#!/bin/bash
# Requires: VAULT_ADDR, VAULT_TOKEN
vault kv put apps/automation-and-tools/unifai/shared \
  REDIS_PASSWORD="$REDIS_PASSWORD" \
  UMAMI_USERNAME="$UMAMI_USERNAME" \
  UMAMI_PASSWORD="$UMAMI_PASSWORD"
# ... repeat for multiagent, identity, rag, backend
```

---

## 4. Data Flow

```
Pod Start
  │
  ├─ Vault Operator injects vault-agent init container + sidecar
  │
  ├─ vault-agent authenticates to Vault via ServiceAccount JWT (k8s auth)
  │
  ├─ vault-agent fetches secrets from KV paths
  │
  ├─ Secrets rendered as key=value files → /vault/secrets/ (tmpfs)
  │
  ├─ Application container starts
  │     │
  │     ├─ SharedConfig.__init__()
  │     │     ├─ env source: reads OS env vars (from ConfigMaps via envFrom)
  │     │     ├─ VaultFileSource: reads /vault/secrets/* → merged dict
  │     │     ├─ DotEnvSource: reads .env (local dev only)
  │     │     └─ remaining sources...
  │     │
  │     └─ AppConfig fields populated (secrets from Vault, non-secrets from ConfigMap)
  │
  └─ vault-agent sidecar: monitors lease, refreshes on rotation
```

---

## 5. Edge Cases & Risks

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Vault unreachable at pod start | Init container fails → CrashLoopBackOff | Vault HA cluster; `vault.hashicorp.com/agent-pre-populate-only: "true"` option; alert on restart count |
| Vault token expires during runtime | No impact — secrets are file-based, agent auto-renews | Decoupled architecture |
| Secret rotated in Vault | Agent re-renders file; app uses startup-loaded values | Pod restart on rotation (or future file-watcher) |
| No `/vault/secrets/` (local dev) | `VaultFileSource.load()` returns `{}` | Next source (`.env`) provides values — zero workflow change |
| Migration parallel-run: ConfigMap + Vault both provide same key | Env vars (ConfigMap/envFrom) take priority over Vault files | Intentional — allows safe validation. Remove from ConfigMap after confirming Vault |
| Vault Operator not installed in cluster | Annotations ignored; no sidecar injected | App falls through to env/ConfigMap — continues working |
| `admin_allowed_users` is a JSON array string | Must be stored as single KV entry in Vault | VaultFileSource parses as raw string; Pydantic handles JSON list parsing |

**External Dependency Failure Modes:**

| Dependency | Failure Mode | Silent/Noisy | Degradation Path |
|------------|-------------|--------------|------------------|
| HashiCorp Vault (503/timeout) | Init container hangs/fails | Noisy (CrashLoopBackOff) | Vault HA; pod won't start until Vault recovers |
| HashiCorp Vault (403 Forbidden) | Auth rejected | Noisy (init fails with error) | Fix: KSA binding, role, namespace config |
| OpenShift API (SA token issuance) | Timeout | Noisy (agent can't get JWT) | Same-cluster; near-zero probability |

**Migration / Backward Compatibility:**

- Phase 1 (parallel): Add Vault annotations + keep presync hooks → both sources active
- Phase 2 (cutover): Remove secret literals from hooks → Vault is sole source
- Phase 3 (cleanup): Revoke old creds, rotate keys, purge Git history

---

## 6. Open Questions

1. Is the OpenShift Vault Operator already deployed and configured in the UnifAI namespace, or must it be installed first?
2. What is the exact Vault kubernetes auth mount path? (may differ from default `auth/kubernetes` in corporate setup)
3. Does the existing AppRole (`automation-and-tools`) suffice, or is a separate kubernetes auth role needed for pod-level KSA access?
4. Should `admin_allowed_users` (non-sensitive access list) move to Vault or remain in ConfigMap?
5. Is Jenkins upgrade (GENIE-1526) complete? The Vault Jenkins Plugin requires it.
6. Is hot-reload of rotated secrets needed (file-watcher) or is pod restart acceptable?
7. Should historical secrets be purged from Git history with `git filter-repo` / BFG Repo-Cleaner?

---

```
--- PIPELINE STATE ---
Pipeline Mode: design-only
Current Phase: Phase 1 — Design
Design Iterations: 0/2
Code Iterations: 0/2
QA Iterations: 0/2
Blocking Verdict: NONE
Feedback Items To Address: NONE
ADR File: NONE
--- END STATE ---
```

---

## DESIGN ONLY COMPLETE

### Input
Jira ticket GENIE-948: "Migrate UnifAI Secrets to HashiCorp Vault via OpenShift Vault Operator"

### Verdict
Design produced

### Findings Summary
The migration requires: (1) new `VaultFileSource` in `global_utils` config sources, (2) Vault Operator annotations on all 6 service deployments, (3) KSA auth configuration, (4) presync hook cleanup removing secret literals, and (5) a one-time Vault seeding script. Local development is unaffected — `VaultFileSource` gracefully returns empty when `/vault/secrets/` doesn't exist. Main blockers: Vault Operator deployment status and Jenkins upgrade dependency (GENIE-1526).

### Items Addressed in Revision Loops
None — first pass.
