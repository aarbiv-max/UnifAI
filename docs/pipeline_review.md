## PHASE 2: DESIGN REVIEW

# Review of: Migrate UnifAI Secrets to HashiCorp Vault via OpenShift Vault Operator

**Reviewing design:** `docs/pipeline_design.md`  
**Reviewer:** Original pipeline (full instructions)

---

### Critical Findings

1. **`VaultFileSource` is placed in the Domain/Config layer but performs filesystem I/O.** Reading from `/vault/secrets/` is infrastructure behavior. Per hexagonal architecture, this source is an **Adapter** — it should be defined alongside `DotEnvSource` (which is also technically an adapter) in `sources.py`. The existing pattern in the codebase already places all sources in `sources.py` without strict layer separation, so this is an **ALIGNMENT ISSUE** rather than a blocking violation — but the design labels it "Domain — Config" which is misleading.

2. **`settings_customise_sources` signature mismatch.** The design proposes inserting `VaultFileSource().load` into the source chain. However, examining `config.py` (line 32), the lambda receives `(init, env, fs)` — these are pydantic-settings source *classes*, not callables that return dicts. The existing `DotEnvSource().load` call works because pydantic-settings accepts callables in the tuple. This is consistent — **verified, no issue**. The design is correct here.

3. **No UI layer impact — correctly omitted.** This feature has no user-facing UI changes. Layer completeness: PASS.

---

### Architectural Violations

| Issue | Layer | Violation | Severity |
|-------|-------|-----------|----------|
| `VaultFileSource` labeled "Domain — Config" | Config | Filesystem I/O is adapter-level, not domain | ALIGNMENT ISSUE (non-blocking — matches existing `DotEnvSource` pattern) |

No CRITICAL architecture violations. The design correctly places all new logic in config/adapter layers and does not touch domain business logic.

---

### Efficiency Concerns

- **None significant.** `VaultFileSource` reads a handful of small files at startup. No runtime overhead after initialization.
- vault-agent sidecar adds ~30-50MB memory per pod. Acceptable given security benefit.

---

### Duplication & Reusability Issues

- **Good:** The design reuses the existing `ConfigSource` abstract base class and plugs into the existing source chain pattern. No duplication introduced.
- **Opportunity:** `VaultFileSource` and `DotEnvSource` both parse key=value files. Consider whether `VaultFileSource` can delegate to `dotenv_values()` on each file in the directory, avoiding reimplementing the parser.

---

### Risks to Existing System

| Risk | Severity | Mitigation in Design |
|------|----------|---------------------|
| Parallel-run period: same key from both ConfigMap and Vault | Low | Env vars (ConfigMap) take priority — intentional |
| Pod startup time increases (vault-agent init) | Medium | ~2-5s added; documented but no SLA impact stated |
| Presync hooks still run during Phase 1 — redundant writes | Low | Acceptable during transition |
| `lru_cache` on `get_instance()` means config is read once | Low | Vault file changes after startup are NOT picked up without restart — acknowledged in design |

---

### Recommended Improvements

1. **Specify the `vault.hashicorp.com/agent-pre-populate-only` annotation explicitly.** The design mentions it in edge cases but should mandate it for services that don't need real-time rotation (all current services). This avoids keeping the sidecar running and reduces resource usage.

2. **Define the Vault role binding scope.** The design says "bound to all UnifAI namespace ServiceAccounts" — this is overly broad. Should specify which ServiceAccount names (e.g., `unifai-backend`, `unifai-multiagent-be`, etc.) are bound to the role. Principle of least privilege.

3. **Clarify `admin_allowed_users` handling.** The design lists it as both "move to Vault" and "keep in ConfigMap" in different tables. Pick one and be consistent.

4. **Add a rollback plan.** What if Vault integration fails in production? The design should state: "Re-enable presync hook literals and redeploy" as the rollback path.

---

### Safer / Cleaner Alternative Approach

No fundamentally better alternative exists. The Vault Operator + file injection pattern is the standard approach for OpenShift environments. The only alternative worth considering is **External Secrets Operator (ESO)** which syncs Vault secrets into native Kubernetes Secrets — but this puts secrets back into etcd (plaintext), defeating a key goal. The current design's tmpfs approach is superior for the stated security requirements.

---

### Layer Completeness Findings

- **UI layer:** Not needed. No user-facing changes. PASS.
- **Inbound adapter layer:** Not needed. No new HTTP endpoints. PASS.
- **Data/seed layer:** Vault seeding script included. PASS.

---

### Auth / Protocol Realism Findings

- **Vault auth uses Kubernetes SA auth (not OAuth/MCP).** No RFC 9728 / PRM discovery chain applies here.
- **KSA auth flow is well-understood:** Pod SA token → Vault k8s auth → Vault token → secret access. The design correctly describes this.
- **The existing AppRole in `vault.txt`** uses `role_id=automation-and-tools` with `secret_id` — this is for Jenkins/CI, NOT for pod-level access. The design correctly identifies that a **new** kubernetes auth method is needed (separate from the AppRole). However, Open Question #3 should be elevated to a **requirement** — KSA auth MUST be configured; it cannot reuse the AppRole.

---

### External Dependency Failure Modes

All external dependencies have explicit failure modes documented:

| Dependency | Documented | Verdict |
|------------|-----------|---------|
| HashiCorp Vault (503/timeout) | Yes — noisy, CrashLoopBackOff | PASS |
| HashiCorp Vault (403) | Yes — noisy, auth fix needed | PASS |
| OpenShift API (SA token) | Yes — noisy, same-cluster unlikely | PASS |

---

### Adversarial Challenges Applied

1. **Dependency Inversion Test:** If we remove `VaultFileSource`, does the domain still work? YES — `SharedConfig` falls through to `.env` / env vars. The domain has zero dependency on Vault. PASS.

2. **Blast Radius Test:** `config.py` and `sources.py` are imported by ALL services (backend, multiagent, rag, identity). A bug in `VaultFileSource` could prevent all services from starting. **Mitigation:** The `if not self._vault_path.exists(): return {}` guard means local dev and non-Vault clusters are unaffected. However, a parsing error in a malformed Vault-rendered file would crash startup. **Recommendation:** Add try/except around file parsing with a warning log, not a hard failure.

3. **Runtime Failure Trace:** If Vault returns 503 during pod init: vault-agent-init retries (configurable) → eventually fails → pod enters CrashLoopBackOff → Kubernetes backoff timer → Vault recovers → pod restarts and succeeds. The design handles this correctly. No silent data loss.

---

### Codebase Verification Evidence

| File Read | Claim Verified |
|-----------|---------------|
| `global_utils/src/global_utils/config/sources.py` | `ConfigSource` ABC exists with `load() -> Dict[str, Any]` — VaultFileSource can extend it |
| `global_utils/src/global_utils/config/config.py` | `settings_customise_sources` lambda exists, takes `(init, env, fs)`, returns tuple of callables — design's integration approach is valid |
| `multi-agent/config/app_config.py` | `credential_encryption_key` and `mcp_auth_state_secret` fields exist on `AppConfig(SharedConfig)` — confirms these are the secrets that need migration |
| `helm/backend/unifai-backend/templates/deployment.yaml` | `serviceAccountName` is already templated — ServiceAccount exists, can be annotated |
| `helm/scripts/multiagent-presync.sh` | Confirms `CREDENTIAL_ENCRYPTION_KEY` and `MCP_AUTH_STATE_SECRET` are passed as ConfigMap literals — validates migration scope |
| `helm/scripts/identity-presync.sh` | Confirms `client_secret` and `secret_key` stored in a ConfigMap (not even a Secret) — validates urgency |

---

### Verdict

**APPROVE** — Design is sound, proceed to implementation.

The design correctly leverages the existing `ConfigSource` pattern, maintains hexagonal architecture boundaries, provides comprehensive failure mode documentation, and includes a safe parallel-run migration strategy. The recommended improvements (pre-populate-only annotation, least-privilege role binding, error handling in file parsing, rollback plan) are enhancements that can be addressed during implementation rather than design revision blockers.

---

```
--- PIPELINE STATE ---
Pipeline Mode: review-only
Current Phase: Phase 2 — Design Review
Design Iterations: 0/2
Code Iterations: 0/2
QA Iterations: 0/2
Blocking Verdict: NONE
Feedback Items To Address: NONE
ADR File: NONE
--- END STATE ---
```
