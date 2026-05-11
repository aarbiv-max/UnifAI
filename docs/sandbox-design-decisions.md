# Sandbox Design Decisions

Finalized decisions for the agent sandbox architecture.

---

## 1. Retention Policy

**Decision: Teardown on Workflow Completion**

The pod stays alive for the entire duration of the agent's workflow (all serial tasks). It is destroyed only when the workflow ends. All state is additionally persisted at the PVC level, so data survives across sessions even after the pod is torn down.

---

## 2. Data Persistence

**Decision: Persistent (PVC-backed)**

- Use **Persistent Volume Claims (PVCs)** to outlive the pod.
- The workspace record stores a reference to the **PVC ID** so it can be reattached on the next session.
- Enables the agent to resume with the same installed packages, generated files, and git state.

---

## 3. Re-triggering Logic

**Decision: New Pod + PVC Reattach**

When a user returns to a completed workflow:

1. A **brand-new pod** is spawned using the `workflow_id`.
2. The existing **PVC** referenced in the workspace record is automatically attached to the new pod.
3. The agent regains the same filesystem state (code, packages, git history) it had in the previous session.

---

## 4. Pre-installed Tooling

**Decision: Targeted Image**

The container image ships with a focused set of pre-installed tools:

- **Python** — primary language runtime
- **Bash** — shell scripting and automation
- **Git CLI** — version control operations

Everything else is installed by the agent at runtime as needed.

---

## 5. Sandbox Integration Model

**Decision: Sandbox as a Session**

The agent opens a sandbox session at the start of a workflow. The pod stays alive for the duration of the workflow, and the agent sends commands to it serially. This provides:

- **Filesystem continuity** — no remounting between tasks.
- **Process continuity** — background processes (servers, watchers) started in one task remain available to subsequent tasks.
- **Environment continuity** — env vars, working directory, and shell state carry over across tasks.
- **No cold-start overhead** — no pod spin-up/teardown between individual tasks.

The pod lifecycle is **one pod per workflow execution**: created when the workflow starts, destroyed when it ends. The PVC outlives the pod for cross-session persistence (see §2 and §3).

---

## 6. Ownership & Security Responsibility

**Decision: Bring Your Own Cluster (BYOC)**

The sandbox is treated as a tool, comparable to `oc_tool`. The user provides their own OpenShift cluster.

### Required inputs for sandbox creation

| Input | Purpose |
| --- | --- |
| **Cluster address** | OpenShift API endpoint to connect to. |
| **Cluster authentication** | Credentials/token for authenticating against the cluster. |
| **Git repository URL** | Repo to clone into the mounted PVC on first creation. |

### Lifecycle

1. **First run:** The sandbox tool authenticates to the user's cluster, provisions a pod + PVC, and clones the specified git repo into the PVC mount.
2. **Subsequent runs:** A new pod is created and the existing PVC (with the previously cloned repo and any modifications) is reattached.
3. **Security boundary:** The user owns and is responsible for their cluster's security posture and resource costs.

---

## 7. Multi-Agent Concurrency

**Decision: Separate Sandboxes + Git Worktrees**

When multiple agents work on the same repository in parallel (e.g., two agents each handling a separate task), they need isolated environments to avoid corrupting shared git state.

### The problem

Even if agents modify different files, git's internal state (`.git/index`, `HEAD`, refs) is single-writer. Two concurrent `git add` or `git commit` operations on the same working tree will race and corrupt the index. This applies regardless of whether agents share a pod or just a PVC.

### Solution: `git worktree` isolation

Each agent gets its **own pod** and its **own git worktree** on a **shared PVC**.

```
/workspace/
├── repo.git/              # bare clone (shared, read-heavy)
├── worktree-agent-a/      # Agent A's working directory (branch: feat/task-a)
└── worktree-agent-b/      # Agent B's working directory (branch: feat/task-b)
```

### How it works

1. **First agent provisioned:** The sandbox tool clones the repo as a bare repository at `/workspace/repo.git` and creates a worktree (`git worktree add /workspace/worktree-agent-a feat/task-a`).
2. **Second agent provisioned:** A new pod is created, mounting the same PVC. It creates a separate worktree (`git worktree add /workspace/worktree-agent-b feat/task-b`).
3. **During execution:** Each agent operates in its own worktree directory with an independent index, HEAD, and branch. No locking conflicts.
4. **After completion:** The results are two separate branches that can be merged or PR'd independently via standard git workflows.

### Why this works

| Concern | Resolution |
| --- | --- |
| Git index corruption | Each worktree has its own `.git` index — no shared lock file. |
| File conflicts | Each agent has its own directory tree — no overlapping writes. |
| PVC access mode | Requires `ReadWriteMany` (RWX), but concurrent access is safe because each pod writes to a different subtree. |
| Merging results | Standard `git merge` or pull requests reconcile the work afterward. |

### Requirements

- The PVC storage class must support **`ReadWriteMany` (RWX)** access mode.
- The sandbox tool is responsible for creating/managing worktrees automatically when multiple agents target the same workspace.
