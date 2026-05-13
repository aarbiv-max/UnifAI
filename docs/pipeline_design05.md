## PHASE 1: DESIGN

# Migrate UnifAI Secrets to HashiCorp Vault via OpenShift Vault Operator

**Jira Ticket:** GENIE-948  
**Status:** Code Review  
**Assignee:** Saar Fireshtein

---

## 1. Overview

- **Problem Statement:** UnifAI stores sensitive credentials (Gemini API keys, encryption keys, client secrets, Slack tokens, Redis passwords) in GitHub repositories and Kubernetes ConfigMaps via Jenkins presync/postsync hooks. ConfigMaps are plaintext in etcd and Git history is permanent — both represent significant security exposure.
- **Proposed Solution:** Migrate all sensitive values to the company's existing HashiCorp Vault instance. Use the OpenShift Vault Operator to inject secrets as in-memory files (`/vault/secrets/`) into pods. Add a `VaultFileSource` to the application's config system to read from injected files with graceful fallback for local development.
- **Success Metrics:**
  - All secrets removed from Git repos and ConfigMaps
  - Pods start and read secrets from `/vault/secrets/` tmpfs volume
  - Old credentials revoked and rotated
  - CI/CD deploys without hardcoded secrets
  - Vault audit log captures all access
  - Zero change to local developer workflow (`.env` still works)

---

## 2. Affected Components

| Layer | Component | Action (New/Modified) | File Path |
|-------|-----------|----------------------|-----------|
| Domain — Config | `VaultFileSource` | New | `global_utils/src/global_utils/config/sources.py` |
| Domain — Config | `SharedConfig` source chain | Modified | `global_utils/src/global_utils/config/config.py` |
| Adapter — Helm | Backend deployment annotations | Modified | `helm/backend/unifai-backend/templates/deployment.yaml` |
| Adapter — Helm | Multiagent BE deployment | Modified | `helm/multiagent/be/templates/be-deployment.yaml` |
| Adapter — Helm | Temporal worker deployment | Modified | `helm/multiagent/temporal-worker/templates/be-deployment.yaml` |
| Adapter — Helm | RAG server deployment | Modified | `helm/rag/unifai-rag-server/templates/deployment.yaml` |
| Adapter — Helm | RAG celery deployment | Modified | `helm/rag/unifai-rag-celery/templates/deployment.yaml` |
| Adapter — Helm | Identity deployment | Modified | `helm/shared-resources/identity/templates/deployment.yaml` |
| Adapter — Helm | Global config values | Modified | `helm/values/global-config.yaml` |
| Adapter — Helm | ServiceAccount annotations | Modified | All `templates/serviceaccount.yaml` |
| Adapter — CI/CD | Multiagent presync hook | Modified | `helm/scripts/multiagent-presync.sh` |
| Adapter — CI/CD | Identity presync hook | Modified | `helm/scripts/identity-presync.sh` |
| Adapter — CI/CD | Shared-resources postsync hook | Modified | `helm/scripts/shared-resources-postsync.sh` |
| Adapter — CI/CD | RAG presync hook | Modified | `helm/scripts/rag-presync.sh` |
| Config / Infra | Vault policy doc | New | `helm/vault/policy.hcl` |
| Config / Infra | Vault seeding script | New | `scripts/vault_seed.sh` |

---

## 3. Technical Design

### 3.1 Vault KV Structure

```
apps/automation-and-tools/unifai/
├── shared/          (REDIS_PASSWORD, UMAMI_USERNAME, UMAMI_PASSWORD)
├── backend/         (admin_allowed_users)
├── multiagent/      (CREDENTIAL_ENCRYPTION_KEY, MCP_AUTH_STATE_SECRET, admin_allowed_users)
├── identity/        (client_secret, secret_key, admin_allowed_users)
└── rag/             (default_slack_bot_token, default_slack_user_token)
```

### 3.2 VaultFileSource

**Purpose:** Read key=value files injected by Vault Agent into `/vault/secrets/`.

**Interface:**

```python
class VaultFileSource(ConfigSource):
    def __init__(self, vault_path: str = "/vault/secrets"):
        self._vault_path = Path(vault_path)

    def load(self) -> Dict[str, Any]:
        # Returns {} if path doesn't exist (local dev fallback)
        # Reads all files, parses key=value lines, returns merged dict
```

**Integration:** Inserted into `SharedConfig.settings_customise_sources` between `env` and `DotEnvSource`:

```python
(init, env, VaultFileSource().load, DotEnvSource().load, YamlSource().load, JsonSource().load, fs)
```

### 3.3 OpenShift Vault Operator Annotations

Each deployment gains pod annotations:

```yaml
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/role: "unifai"
vault.hashicorp.com/agent-inject-secret-shared: "apps/automation-and-tools/unifai/shared"
vault.hashicorp.com/agent-inject-secret-<service>: "apps/automation-and-tools/unifai/<service>"
vault.hashicorp.com/agent-inject-template-shared: |
  {{- with secret "apps/automation-and-tools/unifai/shared" -}}
  {{- range $k, $v := .Data.data }}{{ $k }}={{ $v }}
  {{ end }}{{- end -}}
```

Secrets rendered to `/vault/secrets/shared` and `/vault/secrets/<service>` as tmpfs (never touches etcd).

### 3.4 KSA Authentication

- Vault `kubernetes` auth backend bound to OpenShift cluster API
- Role `unifai` bound to ServiceAccounts in UnifAI namespace
- Policy `unifai-read` grants `read` on `apps/automation-and-tools/unifai/*`

### 3.5 Presync Hook Migration

| Hook | Remove (secrets) | Keep (non-secret) |
|------|-----------------|-------------------|
| `multiagent-presync.sh` | `CREDENTIAL_ENCRYPTION_KEY`, `MCP_AUTH_STATE_SECRET` | — |
| `identity-presync.sh` | `client_secret`, `secret_key` | `keycloak_base_url`, `client_id`, `keycloak_realm` |
| `shared-resources-postsync.sh` | `REDIS_PASSWORD`, `UMAMI_PASSWORD` | IPs, ports, URLs |
| `rag-presync.sh` | Entire `unifai-rag-secrets` Secret | — |

### 3.6 Vault Seeding Script

`scripts/vault_seed.sh` — one-time script to write secrets into Vault KV:

```bash
vault kv put apps/automation-and-tools/unifai/shared \
  REDIS_PASSWORD="$REDIS_PASSWORD" UMAMI_PASSWORD="$UMAMI_PASSWORD" ...
```

---

## 4. Data Flow

1. Pod starts → Vault Operator injects vault-agent init container + sidecar
2. vault-agent authenticates via pod ServiceAccount JWT to Vault kubernetes auth
3. vault-agent fetches secrets from configured KV paths
4. Secrets rendered as key=value files at `/vault/secrets/` (tmpfs)
5. Application container starts → `SharedConfig` → `VaultFileSource` reads `/vault/secrets/*`
6. `AppConfig` fields populated from Vault-sourced values
7. vault-agent sidecar continues running for secret rotation refresh

---

## 5. Edge Cases & Risks

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Vault unavailable at pod start | Pod fails init (CrashLoopBackOff) | Vault HA; retry annotations; alert on restart count |
| Vault token expiry mid-operation | No impact — app reads from file, agent auto-renews | File-based injection decoupled from token lifecycle |
| Secret rotation in Vault | Agent re-renders file; app reads at startup only | Restart pod on rotation or add file-watcher (future) |
| Local dev — no `/vault/secrets/` | `VaultFileSource` returns `{}` | `.env` provides values — no workflow change |
| Migration overlap — ConfigMap + Vault both set | Env vars (ConfigMap) take priority over Vault files | Intentional for safe parallel run; remove ConfigMap entries after validation |
| OpenShift Vault Operator not installed | No sidecar injected; annotations are no-ops | App falls through to env/ConfigMap — system functions |

**External Dependency Failure Modes:**

| Dependency | Failure | Behavior | Degradation |
|------------|---------|----------|-------------|
| HashiCorp Vault | 503/timeout at init | Noisy — pod CrashLoopBackOff | Vault HA prevents prolonged outage; alert |
| HashiCorp Vault | 403 auth failure | Noisy — init fails | Fix KSA binding/role/namespace |
| OpenShift API (SA token) | Timeout | Noisy — agent can't get token | Same-cluster; extremely unlikely |

---

## 6. Open Questions

1. Is the OpenShift Vault Operator already deployed in the UnifAI namespace?
2. What is the exact Vault kubernetes auth mount path for this cluster?
3. Does the existing AppRole have `read` on target KV, or do we need new KSA auth config?
4. Should `admin_allowed_users` move to Vault or remain in ConfigMap?
5. Is Jenkins upgrade (GENIE-1526) complete? Vault Jenkins Plugin depends on it.
6. Is hot-reload of secrets needed, or is pod restart on rotation acceptable?
7. Should we purge historical secrets from Git with `git filter-repo` / BFG?

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
Migration touches config domain (new `VaultFileSource`), 6 Helm deployment templates (Vault annotations), 4 presync hooks (secret removal), and new infra artifacts (policy + seeding script). Local dev unaffected. Main blockers: Vault Operator deployment status and GENIE-1526 Jenkins upgrade dependency.

### Items Addressed in Revision Loops
None — first pass.
