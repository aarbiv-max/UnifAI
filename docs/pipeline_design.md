## PHASE 1: DESIGN

# Migrate UnifAI Secrets to HashiCorp Vault via OpenShift Vault Operator

**Jira Ticket:** GENIE-948  
**Status:** Code Review  
**Assignee:** Saar Fireshtein

---

## 1. Executive Summary

| Section | Details |
|---------|---------|
| **Problem Statement** | UnifAI currently stores sensitive credentials (Gemini API keys, encryption keys, client secrets, Slack tokens, passwords) in GitHub repositories and Kubernetes ConfigMaps via Jenkins presync/postsync shell hooks. Git history is permanent and ConfigMaps are stored in plaintext in etcd, creating significant security risk. |
| **High-Level Solution** | Migrate all sensitive values from ConfigMaps/presync hooks to the company's existing HashiCorp Vault instance, using the OpenShift Vault Operator to inject secrets as in-memory volumes (`/vault/secrets/`) into pods at deployment time. Update the application's `SharedConfig` / `AppConfig` to support reading from Vault-injected files alongside environment variables. |
| **Success Metrics** | All secrets removed from Git and ConfigMaps; pods start successfully reading from `/vault/secrets/`; old credentials revoked and rotated; CI/CD pipeline deploys without hardcoded secrets; Vault audit log captures all secret access. |

---

## 2. Affected Components

| Layer | Component | Action | File Path |
|-------|-----------|--------|-----------|
| Config — Domain | `VaultFileSource` | New | `global_utils/src/global_utils/config/sources.py` |
| Config — Domain | `SharedConfig` settings source chain | Modified | `global_utils/src/global_utils/config/config.py` |
| Adapter — Infra/Helm | Vault Operator annotations on Deployments | Modified | `helm/backend/unifai-backend/templates/deployment.yaml` |
| Adapter — Infra/Helm | Vault Operator annotations on Deployments | Modified | `helm/multiagent/be/templates/be-deployment.yaml` |
| Adapter — Infra/Helm | Vault Operator annotations on Deployments | Modified | `helm/multiagent/temporal-worker/templates/be-deployment.yaml` |
| Adapter — Infra/Helm | Vault Operator annotations on Deployments | Modified | `helm/rag/unifai-rag-server/templates/deployment.yaml` |
| Adapter — Infra/Helm | Vault Operator annotations on Deployments | Modified | `helm/rag/unifai-rag-celery/templates/deployment.yaml` |
| Adapter — Infra/Helm | Vault Operator annotations on Deployments | Modified | `helm/shared-resources/identity/templates/deployment.yaml` |
| Adapter — Infra/Helm | Helm values — Vault path config | Modified | `helm/values/global-config.yaml` |
| Adapter — Infra/Helm | ServiceAccount annotations for Vault KSA auth | Modified | All `templates/serviceaccount.yaml` |
| Adapter — CI/CD | Presync hooks — remove secret literals | Modified | `helm/scripts/multiagent-presync.sh` |
| Adapter — CI/CD | Presync hooks — remove secret literals | Modified | `helm/scripts/identity-presync.sh` |
| Adapter — CI/CD | Presync hooks — remove secret literals | Modified | `helm/scripts/shared-resources-postsync.sh` |
| Adapter — CI/CD | Presync hooks — remove secret literals | Modified | `helm/scripts/rag-presync.sh` |
| Config / Infra | Vault policy & AppRole for UnifAI | New | `helm/vault/policy.hcl` (documentation artifact) |
| Config / Infra | Vault KV secrets seeding script | New | `scripts/vault_seed.sh` |

---

## 3. Technical Design

### 3.1 Vault Secret Organization (KV v2)

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

The Vault path is `apps/automation-and-tools/unifai/<service>`. This follows the existing AppRole structure found in the secrets repo (`vault.txt`).

### 3.2 OpenShift Vault Operator — Pod Injection

The OpenShift Vault Operator uses **pod annotations** to declare which secrets to inject. Each deployment template gains:

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

This renders secrets as key=value files at `/vault/secrets/shared` and `/vault/secrets/<service>`.

### 3.3 Vault Authentication — Kubernetes Service Account (KSA)

**Purpose:** Allow UnifAI pods to authenticate to Vault without embedded credentials.

- **Method:** Vault's `kubernetes` auth backend bound to the OpenShift cluster's API.
- **Role:** `unifai` — bound to ServiceAccount(s) in the UnifAI namespace.
- **Policy:** `unifai-read` — grants `read` on `apps/automation-and-tools/unifai/*`.

ServiceAccount templates require the annotation:

```yaml
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
```

### 3.4 Application Config — `VaultFileSource`

**Purpose:** Read secrets from Vault-injected files at `/vault/secrets/` and merge them into the config hierarchy.

**Interface:**

```python
class VaultFileSource(ConfigSource):
    def __init__(self, vault_path: str = "/vault/secrets"):
        self._vault_path = Path(vault_path)

    def load(self) -> Dict[str, Any]:
        """
        Reads all files in vault_path. Each file contains key=value pairs.
        Returns merged dict of all key-value pairs found.
        Falls back to empty dict if path doesn't exist (local dev).
        """
```

**Integration into SharedConfig:**

```python
settings_customise_sources=lambda init, env, fs: (
    init,
    env,
    VaultFileSource().load,     # NEW — highest priority after env
    DotEnvSource().load,
    YamlSource().load,
    JsonSource().load,
    fs,
)
```

**Priority order:** `init > env vars > vault files > .env > yaml > json > file settings`

This means Vault-injected values are used in cluster, but local `.env` still works for development (since `/vault/secrets/` won't exist locally).

### 3.5 Presync Hook Migration

Current presync hooks inject secrets as ConfigMap literals from Jenkins environment variables. Migration path:

| Hook | Secret Values to Remove | Remains (non-secret) |
|------|------------------------|----------------------|
| `multiagent-presync.sh` | `CREDENTIAL_ENCRYPTION_KEY`, `MCP_AUTH_STATE_SECRET` | `admin_allowed_users` (move to Vault too) |
| `identity-presync.sh` | `client_secret`, `secret_key` | `keycloak_base_url`, `client_id`, `keycloak_realm` (non-secret, keep in ConfigMap) |
| `shared-resources-postsync.sh` | `REDIS_PASSWORD`, `UMAMI_PASSWORD` | Service discovery literals (IPs, ports, URLs — keep) |
| `rag-presync.sh` | Entire `unifai-rag-secrets` Secret | — (delete hook or make it a no-op) |

### 3.6 Vault Seeding Script

**Purpose:** One-time script to write existing secrets into Vault KV.

**Location:** `scripts/vault_seed.sh`

```bash
#!/bin/bash
# Requires: VAULT_ADDR, VAULT_TOKEN set
# Reads values from environment or prompts

vault kv put apps/automation-and-tools/unifai/shared \
  REDIS_PASSWORD="$REDIS_PASSWORD" \
  UMAMI_USERNAME="$UMAMI_USERNAME" \
  UMAMI_PASSWORD="$UMAMI_PASSWORD"

vault kv put apps/automation-and-tools/unifai/multiagent \
  CREDENTIAL_ENCRYPTION_KEY="$CREDENTIAL_ENCRYPTION_KEY" \
  MCP_AUTH_STATE_SECRET="$MCP_AUTH_STATE_SECRET" \
  admin_allowed_users="$admin_allowed_users"

# ... repeat for identity, rag, backend
```

---

## 4. Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Deployment (e.g. multiagent-be)                                │
│                                                                 │
│  ┌────────────────────┐    ┌──────────────────────────────┐    │
│  │  Vault Agent Sidecar│    │  Application Container       │    │
│  │  (injected by       │    │                              │    │
│  │   Vault Operator)   │    │  SharedConfig loads:         │    │
│  │                     │    │   1. OS env vars (ConfigMap)  │    │
│  │  1. Auth via KSA ──────────▶ Vault k8s auth             │    │
│  │  2. Fetch secrets   │    │   2. /vault/secrets/* files   │    │
│  │  3. Write to        │    │   3. .env (local dev only)   │    │
│  │     /vault/secrets/ │    │                              │    │
│  │     (tmpfs volume)  │    │  AppConfig.get_instance()    │    │
│  └────────────────────┘    └──────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

External:
  HashiCorp Vault (vault.corp.redhat.com:8200)
    └─ KV v2: apps/automation-and-tools/unifai/{shared,backend,multiagent,identity,rag}
    └─ Auth: kubernetes (bound to UnifAI namespace ServiceAccounts)
    └─ Policy: unifai-read (read on apps/automation-and-tools/unifai/*)
```

**Sequence:**
1. Pod starts → Vault Operator injects init container (vault-agent-init) + sidecar (vault-agent).
2. vault-agent authenticates to Vault using the pod's ServiceAccount JWT token.
3. vault-agent fetches secrets from the configured KV paths.
4. Secrets are rendered as key=value files into `/vault/secrets/` (tmpfs — never hits etcd).
5. Application container starts, `SharedConfig` loads `VaultFileSource` which reads `/vault/secrets/*`.
6. `AppConfig` fields are populated with Vault-sourced values.
7. vault-agent sidecar continues running, refreshing secrets on rotation (lease-based).

---

## 5. Risk & Reliability

### 5a. Edge Cases & Failure Modes

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Vault unavailable at pod start | Pod fails init (vault-agent-init can't authenticate) | Vault HA cluster + retry annotations; consider `vault.hashicorp.com/agent-pre-populate-only: "true"` to allow restart from cached secrets |
| Vault token expires mid-operation | vault-agent auto-renews; app reads from file (unchanged until next refresh) | No impact — file-based injection is decoupled from token lifecycle |
| Secret rotation in Vault | vault-agent detects new version, re-renders file | App reads config at startup; for hot-reload, would need file-watcher (out of scope) |
| Local dev — no `/vault/secrets/` | `VaultFileSource.load()` returns `{}` | Next source (`.env`) provides values — no change to developer workflow |
| Migration period — both ConfigMap and Vault have values | Env vars (from ConfigMap) override Vault files in priority | Intentional: allows gradual rollout. Remove from ConfigMap once Vault confirmed working |

### 5b. External Dependency Failure Modes

| Dependency | Failure | Silent/Noisy | Degradation |
|------------|---------|--------------|-------------|
| HashiCorp Vault (vault.corp.redhat.com) | 503 / timeout at pod init | **Noisy** — init container fails, pod enters CrashLoopBackOff | Pod does not start. Alert on pod restart count. Vault HA should prevent prolonged outage. |
| HashiCorp Vault (vault.corp.redhat.com) | 403 / auth failure | **Noisy** — vault-agent logs auth error, init fails | Fix: verify KSA binding, role, namespace. No secret fallback. |
| OpenShift API (for KSA token) | Timeout | **Noisy** — vault-agent cannot get projected SA token | Extremely unlikely (same cluster). Pod would fail init. |

### 5c. Local Development & Partial-Access Deployment

| Dependency | Local Dev Strategy | Partial-Access Strategy |
|------------|-------------------|------------------------|
| HashiCorp Vault | **Not required.** `VaultFileSource` returns `{}` when `/vault/secrets/` doesn't exist. Developers continue using `.env` files as today. No change to local workflow. | **Graceful fallback.** If Vault Operator is not deployed (e.g., dev/sandbox cluster without Vault), no annotations are processed, no sidecar injected. App falls through to env vars / ConfigMaps / `.env`. System starts normally. |

### 5d. Backward Compatibility & Migration

- **Phase 1 (parallel):** Vault annotations added, but presync hooks still populate ConfigMaps. Both sources provide values. Env vars (ConfigMap) take priority. This validates Vault injection without risk.
- **Phase 2 (cutover):** Remove secret literals from presync hooks. Vault files become the effective source.
- **Phase 3 (cleanup):** Revoke old credentials, rotate keys, delete from Git history (BFG or `git filter-repo`).

---

## 6. Open Questions

| # | Question | Owner | Impact |
|---|----------|-------|--------|
| 1 | Is the OpenShift Vault Operator already deployed in the UnifAI namespace, or does it need to be installed? | Platform / Harel Hadad | Blocks deployment annotations |
| 2 | What is the exact Vault kubernetes auth mount path? (Default is `auth/kubernetes` but may differ in corporate setup) | Harel Hadad | Affects annotation `vault.hashicorp.com/auth-path` |
| 3 | Does the existing AppRole (`automation-and-tools`) have `read` on the target KV path, or do we need a new policy/role for pod-level KSA auth? | Harel Hadad | KSA auth is different from AppRole — likely needs new auth method config |
| 4 | Should `admin_allowed_users` (a non-sensitive list) also move to Vault, or remain in ConfigMap? | Team decision | Affects presync hook simplification |
| 5 | Jenkins upgrade (GENIE-1526) — is it complete? Vault Jenkins Plugin depends on it. | CI team | Blocks CI pipeline integration |
| 6 | Do we need hot-reload of secrets (file-watcher) or is restart-on-rotation acceptable? | Product/Ops | If hot-reload needed, adds `watchdog` dependency to `VaultFileSource` |
| 7 | Git history cleanup — should we use `git filter-repo` or BFG to purge historical secrets from the main repo? | Security/DevOps | Affects all developers (force-push to main) |

---

## DESIGN COMPLETE

### Input
Jira ticket GENIE-948: "Migrate UnifAI Secrets to HashiCorp Vault via OpenShift Vault Operator"

### Verdict
Design produced

### Findings Summary
The migration requires changes across 3 layers: (1) a new `VaultFileSource` in the config system to read injected files, (2) Helm deployment annotations for the Vault Operator on all 6 service deployments, and (3) presync hook cleanup to remove hardcoded secret literals. The application's existing `pydantic-settings` source chain makes integration clean — Vault files slot in as a new source with graceful fallback. Local development is unaffected. The main blockers are coordination with Harel Hadad on Vault Operator setup and the Jenkins upgrade dependency (GENIE-1526).
