# UnifAI — Local Development Guide

A step-by-step guide for running UnifAI locally — either the **full stack** in a tmux session or a **single service** in your terminal.

## Quick Start

0. **[Prerequisites](#2-prerequisites)** — make sure you have Python 3.11–3.13, Node.js 22+, pnpm, tmux, and Podman/Docker installed
1. **[Apply local changes](#44-configuration-patching--apply-local-dev-changespy)** — generates `.env` files and patches source files:
   ```bash
   python3 local-development/apply-local-dev-changes.py
   ```
2. **[Edit SSO credentials](#sso-client-credentials-required)** — fill in `client_id` and `client_secret` in `shared-resources/sso-backend/.env`
3. **[Run](#4-running-the-development-environment)** — start the dev environment (add `--setup-venv` on first run):
   ```bash
   ./local-development/start-unifai-dev.sh --setup-venv            # full-stack, first time
   ./local-development/start-unifai-dev.sh --service backend       # or single service
   ```

> Steps 1–2 are one-time setup. On subsequent runs, just use step 3 without `--setup-venv`.

---

## 1. Overview

UnifAI is composed of five services that run side-by-side during local development:


| Service         | Directory                       | Port  | Language   |
| --------------- | ------------------------------- | ----- | ---------- |
| RAG Backend     | `rag/`                          | 13457 | Python     |
| SSO Backend     | `shared-resources/sso-backend/` | 13456 | Python     |
| Multi-Agent API | `multi-agent/`                  | 8002  | Python     |
| Backend         | `backend/`                      | 8005  | Python     |
| UI (Vite)       | `ui/`                           | 5000  | TypeScript |


In addition, two background workers run alongside the services:


| Worker          | Directory      | Purpose                                       |
| --------------- | -------------- | --------------------------------------------- |
| Celery Worker   | `rag/`         | Async RAG pipelines (document & Slack queues) |
| Temporal Worker | `multi-agent/` | Distributed agent workflow execution          |


The `local-development/` directory is structured as a modular Python package:

```
local-development/
├── config/
│   └── local_dev_config.py      # LocalDevConfig — centralized port/host settings
├── core/
│   ├── base_service.py           # BaseService ABC — contract every service implements
│   ├── python_env.py             # Python interpreter detection
│   ├── registry.py               # ServiceRegistry — collects and looks up services
│   └── utils.py                  # .env generation and subprocess helpers
├── services/                     # One file per service (backend, rag, multi_agent, sso, ui, workers)
├── apply-local-dev-changes.py    # Orchestrator — generates .env files and applies source patches
├── start-unifai-dev.sh           # Shell entry point for full-stack and single-service modes
└── start-infra.sh                # Infrastructure container management
```

Each service class (e.g. `RagService`, `BackendService`) implements the `BaseService` abstraction, encapsulating its own venv setup, `.env` entries, source-file patches, and run command. The orchestrator iterates over all registered services via `ServiceRegistry` rather than hardcoding per-service logic.

---

## 2. Prerequisites

### Required

- **Red Hat SSO connection** — you must be connected to the Red Hat SSO (VPN / internal network) for authentication to work
- **Python 3.11 – 3.13** (3.11 or 3.12 recommended; 3.14+ is **not** supported because PyO3's maximum supported version is 3.13)
- **Node.js 22+** and **pnpm** (the UI's `package.json` pins `pnpm` via `packageManager`)
- **MongoDB** — used by all Python backends for persistence
- **Qdrant** — vector database for RAG embeddings
- **tmux** — the startup script creates a multi-pane tmux session (full-stack mode)

### SSO Client Credentials *(Required)*

The SSO backend requires a `client_id` and `client_secret` for Keycloak authentication.

1. **Request credentials** from the team — we will provide the values. (See Slack channel #forum-unifai)
2. **Run the apply script** to generate `.env` files (including placeholders for the credentials):

   ```bash
   python3 local-development/apply-local-dev-changes.py
   ```

3. **Edit** `shared-resources/sso-backend/.env` — replace the placeholders with the actual values:

   ```
   client_id=<your-client-id>
   client_secret=<your-client-secret>
   ```

4. **Start the dev environment** — your `.env` files are preserved automatically on subsequent runs:

   ```bash
   ./local-development/start-unifai-dev.sh --setup-venv
   ```

> [!NOTE]
> The apply script **never overwrites** existing `.env` files — your credentials are safe across restarts. If you need to regenerate `.env` files from scratch (e.g. after a config change), pass `--force-env` and then re-edit the SSO credentials.


### Optional

- **Redis** — distributed streaming (multi-agent)
- **Temporal** — distributed workflow execution (multi-agent)
- **RabbitMQ** — async RAG pipelines (Celery broker)
- **Keycloak** — OAuth 2.0 / OIDC authentication

### Infrastructure via containers

The startup script can auto-create containers for the infrastructure services using **Podman** or **Docker**. Make sure at least one of them is installed and running.


| Container | Ports       | Notes                          |
| --------- | ----------- | ------------------------------ |
| MongoDB   | 27017       |                                |
| RabbitMQ  | 5672, 15672 | 15672 = management UI          |
| Qdrant    | 6333, 6334  | 6333 = HTTP API, 6334 = gRPC   |
| Redis     | 6379        |                                |
| Temporal  | 7233, 8233  | 7233 = gRPC API, 8233 = web UI |


Not every service needs every container. In single-service mode, only the relevant ones are started:


| Service           | MongoDB | RabbitMQ | Qdrant | Redis | Temporal |
| ----------------- | ------- | -------- | ------ | ----- | -------- |
| `backend`         | x       |          |        |       |          |
| `rag`             | x       | x        | x      |       |          |
| `multi-agent`     | x       |          |        | x     | x        |
| `sso`             |         |          |        |       |          |
| `ui`              |         |          |        |       |          |
| `celery-worker`   | x       | x        | x      |       |          |
| `temporal-worker` | x       |          |        | x     | x        |


---

## 3. Setting Up Virtual Environments

> [!NOTE]
> **This step is optional.** The dev script creates virtual environments automatically when you pass `--setup-venv`.
>
> You have three choices:
>
> 1. Run it via a dedicated script — see [3.1 Automated setup](#31-automated-setup)
> 2. Set up manually — see [3.2 Manual setup](#32-manual-setup)
> 3. **Skip to [Section 4](#4-running-the-development-environment) *(Recommended)*** — the dev script handles this for you

### 3.1 Automated setup

Create all venvs at once:

```bash
python3 local-development/apply-local-dev-changes.py --setup-venv
```

Or for a single service:

```bash
./local-development/start-unifai-dev.sh --service backend --setup-venv
```

### 3.2 Manual setup

All commands assume you are in the **repo root**. Python must be 3.11–3.13 (see [Prerequisites](#2-prerequisites)).

Each Python service needs a venv with its own dependencies plus `global_utils` (a shared library) installed as an editable package. The pattern is the same for every service:

```bash
cd <service-dir>
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # or: pip install -e ".[all]" for multi-agent
pip install -e <path-to>/global_utils
deactivate && cd <back-to-root>
```

Service-specific values:


| Service     | Directory                       | Install command                   | `global_utils` path  |
| ----------- | ------------------------------- | --------------------------------- | -------------------- |
| multi-agent | `multi-agent/`                  | `pip install -e ".[all]"`         | `../global_utils`    |
| backend     | `backend/`                      | `pip install -r requirements.txt` | `../global_utils`    |
| rag         | `rag/`                          | `pip install -r requirements.txt` | `../global_utils`    |
| sso         | `shared-resources/sso-backend/` | `pip install -r requirements.txt` | `../../global_utils` |


For the **UI** (React/TypeScript — no Python venv):

```bash
cd ui && pnpm install && cd ..
```

---

## 4. Running the Development Environment

The helper scripts below automate local development. They live inside the repo under `local-development/` and are run directly from the **repo root**.

> ### **⚠️ WARNING — Do NOT push local dev changes**
>
> The setup script patches a few source files for local development. **You MUST revert these changes before pushing to avoid breaking production deployments.** Run the following command from the repo root before any `git add` or `git push`:
>
> ```bash
> git checkout rag/bootstrap/flask_app.py backend/run/dev.py shared-resources/sso-backend/app.py ui/vite.config.ts
> ```
>
> The `.env` files (`rag/.env`, `shared-resources/sso-backend/.env`, `ui/.env.local`) are gitignored and safe — they will **not** appear in `git status`.
>
> **Quick check:** run `git diff --name-only` before pushing. If you see any of the files above, revert them first.

### 4.1 Flags reference

```bash
./local-development/start-unifai-dev.sh [flags]
```


| Flag               | Description                                                               |
| ------------------ | ------------------------------------------------------------------------- |
| *(no flags)*       | Full-stack mode — launches all services + workers in a tmux session       |
| `--service <name>` | Single-service foreground mode — runs one service in your terminal        |
| `--setup-venv`     | Create venv(s) before starting. With `--service`: one venv. Without: all. |
| `--force-env`      | Regenerate `.env` files even if they already exist                        |
| `--no-patch`       | Skip `apply-local-dev-changes.py` entirely (env + source patches)         |
| `--destroy`        | Destroy the tmux session (full-stack mode only)                           |


Services: `backend`, `rag`, `multi-agent`, `sso`, `ui`, `celery-worker`, `temporal-worker`

### 4.2 Error logging

The startup script writes all suppressed error output to a timestamped log file in `/tmp/`:

```
/tmp/unifai-dev-YYYYMMDD-HHMMSS.log
```

The log file path is printed at the start of every run and is shown in the tmux info banner (full-stack mode). It captures stderr from:

- Container operations (create, start, list) — useful for diagnosing port conflicts or image pull failures
- Process cleanup (`lsof`, `kill`) when freeing occupied ports
- Podman/Docker machine detection and startup
- tmux session teardown
- `.env` file sourcing errors

To inspect the log after a run:

```bash
cat /tmp/unifai-dev-*.log      # latest log file
```

> [!TIP]
> If a container fails to start with a "port already in use" error, the details will be in this log file rather than on the terminal.

### 4.3 Python version enforcement

The startup script auto-detects a Python interpreter (prefers `python3.11` → `python3.12` → `python3.13` → `python3`, and rejects anything outside 3.11–3.13). **This detected interpreter is used for every Python execution** in both modes:

- Running `apply-local-dev-changes.py` for patching and `.env` generation
- Creating virtual environments (`--setup-venv`)
- Launching Python services (`exec $PYTHON -m run.dev`, etc.)
- Tmux `send-keys` commands in full-stack mode

Before launching, the script also verifies that each service's venv was built with the **same Python minor version** as the detected interpreter. If there's a mismatch (e.g., venvs built with 3.11 but the script detects 3.12), it exits with a clear error and suggests either recreating the venvs or setting `UNIFAI_PYTHON`.

To override auto-detection, set `UNIFAI_PYTHON` to any supported version (`python3.11`, `python3.12`, or `python3.13`):

```bash
export UNIFAI_PYTHON=python3.11   # or python3.12, python3.13
./local-development/start-unifai-dev.sh
```

To check your current venv versions:

```bash
for d in rag backend multi-agent shared-resources/sso-backend; do
    echo "$d: $($d/venv/bin/python --version 2>&1)"
done
```

### 4.4 Configuration patching — `apply-local-dev-changes.py`

> **First run:** Run this script manually **before** launching the dev script, so you can fill in SSO credentials in the generated `.env` (see [SSO Client Credentials](#sso-client-credentials-required)). On subsequent runs, the script is safe to re-run — it preserves existing `.env` files and re-applies source patches idempotently.

This script configures all services to run side-by-side on `localhost`. It does two things:

1. **Generates `.env` files** (gitignored) — these override Pydantic `SharedConfig` defaults for Python services, and provide environment variables for the Vite dev server. Existing `.env` files are **never overwritten** unless you pass `--force-env`. Since `.env` files are in `.gitignore`, they **cannot be accidentally pushed** to the repo.
2. **Patches a few source files** — bind-host decoupling (`0.0.0.0`) and the `/api3` Vite proxy route. These are minimal changes that can be reverted with `git checkout`.

To run it manually from the repo root:

```bash
python3.XX local-development/apply-local-dev-changes.py
```

The repo root is derived from the script's known location (`local-development/` is always one level below the root). To override, set the `UNIFAI_ROOT` environment variable:

```bash
export UNIFAI_ROOT=/path/to/your/UnifAI
```

**Generated `.env` files (gitignored):**


| File                                | Contents                                                                                                                                                                                                                   |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rag/.env`                          | `hostname_local=127.0.0.1`, `port=13457`                                                                                                                                                                                   |
| `shared-resources/sso-backend/.env` | `keycloak_base_url`, `keycloak_realm`, `client_id`, `client_secret` (placeholders), `hostname_local`, `port`, `frontend_url`, `backend_env` |
| `ui/.env.local`                     | `DEV_PORT=5000`, `DEV_HOST=0.0.0.0`, proxy targets for all backends                                                                                                                                                        |


**Source-file patches (revert with `git checkout`):**


| File                                  | Change                   |
| ------------------------------------- | ------------------------ |
| `rag/bootstrap/flask_app.py`          | Bind host → `0.0.0.0`    |
| `backend/run/dev.py`                  | Bind host → `0.0.0.0`    |
| `shared-resources/sso-backend/app.py` | Bind host → `0.0.0.0`    |
| `ui/vite.config.ts`                   | Adds `/api3` proxy route |


---

### 4.5 Single-service mode

Run **one service at a time** in your terminal with live auto-reload. Only the infrastructure containers that service needs are started.

```bash
./local-development/start-unifai-dev.sh --service backend
```

The script will:

1. Apply source-file patches and generate `.env` files (via `apply-local-dev-changes.py`)
2. Verify the service's venv exists and its Python version matches the detected interpreter
3. Start only the infrastructure containers the service needs (see the [infrastructure map](#infrastructure-via-containers))
4. Source the service's `.env` file (for Python services)
5. Launch the service in your foreground terminal with debug/auto-reload

Press `Ctrl+C` to stop.

**Examples:**

```bash
# Standard usage
./local-development/start-unifai-dev.sh --service rag

# First time — create the venv automatically
./local-development/start-unifai-dev.sh --service rag --setup-venv

# Workers (run in a second terminal alongside their parent service)
./local-development/start-unifai-dev.sh --service celery-worker
./local-development/start-unifai-dev.sh --service temporal-worker
```

---

### 4.6 Full-stack mode (default)

**First time** (creates virtual environments before starting):
```bash
./local-development/start-unifai-dev.sh --setup-venv
```

**Subsequent runs** (venvs already exist):
```bash
./local-development/start-unifai-dev.sh
```

If a previous tmux session is still open, destroy it first and restart:

```bash
./local-development/start-unifai-dev.sh --destroy && ./local-development/start-unifai-dev.sh
```

This will:

1. Verify all venvs exist and their Python version matches the detected interpreter
2. Start all infrastructure containers (MongoDB, RabbitMQ, Qdrant, Redis, Temporal) via Podman/Docker
4. Kill any processes occupying the required ports
5. Create a tmux session (`unifai-dev`) with two windows:

**Window 0 — `services`** (5 panes):


| Pane | Service     | Command                                                                         |
| ---- | ----------- | ------------------------------------------------------------------------------- |
| 0    | RAG         | `cd rag && source venv/bin/activate && $PYTHON -m bootstrap.flask_app`          |
| 1    | SSO Backend | `cd shared-resources/sso-backend && source venv/bin/activate && $PYTHON app.py` |
| 2    | Multi-Agent | `cd multi-agent && source venv/bin/activate && HOSTNAME=0.0.0.0 mas api dev`    |
| 3    | UI          | `cd ui && source .env.local && npm start`                                       |
| 4    | Backend     | `cd backend && source venv/bin/activate && $PYTHON -m run.dev`                  |


**Window 1 — `workers`** (2 panes):


| Pane | Worker   | Command                                                                              |
| ---- | -------- | ------------------------------------------------------------------------------------ |
| 0    | Celery   | `cd rag && source venv/bin/activate && celery -A infrastructure.celery.app worker …` |
| 1    | Temporal | `cd multi-agent && source venv/bin/activate && mas temporal-worker --threads 20`     |


Each Python pane sources the service's `.env` file (`set -a && source .env; set +a`) before launching, so environment variables are available through both Pydantic `SharedConfig` and `os.environ`.

**Useful tmux commands once attached:**


| Action                    | Keys                                                |
| ------------------------- | --------------------------------------------------- |
| Switch to next window     | `Ctrl-b n`                                          |
| Switch to previous window | `Ctrl-b p`                                          |
| Navigate between panes    | `Ctrl-b ←/→/↑/↓`                                    |
| Scroll pane output        | `Ctrl-b [` then arrow keys, `q` to exit             |
| Destroy session           | `./local-development/start-unifai-dev.sh --destroy` |


---

### 4.7 Managing infrastructure containers standalone

You can manage infrastructure containers independently using `start-infra.sh`:

```bash
# Start only what a specific service needs
./local-development/start-infra.sh --for backend      # → mongo
./local-development/start-infra.sh --for rag           # → mongo, rabbitmq, qdrant
./local-development/start-infra.sh --for multi-agent   # → mongo, redis, temporal

# Cherry-pick specific containers
./local-development/start-infra.sh mongo qdrant

# Check what's running
./local-development/start-infra.sh --status

# Stop all infrastructure
./local-development/start-infra.sh --stop
```

---

### 4.8 Verifying the setup

Once all services are running, open a browser and navigate to:

```
http://127.0.0.1:5000
```

The Vite dev server proxies API requests to the backends automatically:


| UI Path   | Backend                  |
| --------- | ------------------------ |
| `/api1/*` | RAG (port 13457)         |
| `/api2/*` | Multi-Agent (port 8002)  |
| `/api3/*` | SSO Backend (port 13456) |
| `/api4/*` | Backend (port 8005)      |


---

## 5. Typical Development Workflows

### "I'm working on the Backend service"

```bash
# Terminal 1 — start the backend (auto-starts MongoDB)
./local-development/start-unifai-dev.sh --service backend

# Edit code in your IDE → Flask auto-reloads → see changes immediately
# Test: curl http://127.0.0.1:8005/api/health
```

### "I'm working on the RAG service"

```bash
# Terminal 1 — start rag (auto-starts MongoDB + RabbitMQ + Qdrant)
./local-development/start-unifai-dev.sh --service rag

# Terminal 2 — if you need the Celery worker too
./local-development/start-unifai-dev.sh --service celery-worker
```

### "I'm working on the UI"

```bash
# Terminal 1 — start the UI dev server (no containers needed)
./local-development/start-unifai-dev.sh --service ui

# The Vite proxy forwards API calls to backends — start whichever backends
# you need in other terminals:
# Terminal 2: ./local-development/start-unifai-dev.sh --service backend
# Terminal 3: ./local-development/start-unifai-dev.sh --service rag
```

### "I'm working on Multi-Agent"

```bash
# Terminal 1 — start multi-agent (auto-starts MongoDB + Redis + Temporal)
./local-development/start-unifai-dev.sh --service multi-agent

# Terminal 2 — if you need the Temporal worker
./local-development/start-unifai-dev.sh --service temporal-worker
```

### "Brand new clone — set up everything from scratch"

```bash
# 1. Generate .env files and apply source patches
python3 local-development/apply-local-dev-changes.py

# 2. Edit shared-resources/sso-backend/.env — fill in client_id and client_secret
#    (see "SSO Client Credentials" in Prerequisites)

# 3. Launch (--setup-venv creates venvs; your .env files are preserved automatically)
./local-development/start-unifai-dev.sh --setup-venv

# — or single-service:
./local-development/start-unifai-dev.sh --service backend --setup-venv
```

---

## 6. Comparison: Single-Service vs Full-Stack


|                      | `--service <name>`           | No flags (full-stack)      |
| -------------------- | ---------------------------- | -------------------------- |
| **Use case**         | Working on one service       | Integration testing, demos |
| **Services started** | Just the one you pick        | All 5 services + 2 workers |
| **Containers**       | Only what's needed           | All 5                      |
| **Terminal**         | Foreground in your shell     | tmux session               |
| **Auto-reload**      | Yes (Flask debug / Vite HMR) | Yes                        |
| **Venv check**       | Checks the one service       | Checks all 4 Python venvs  |
| `**.env` sourced**   | Yes (before `exec`)          | Yes (in each tmux pane)    |


---

## 7. Port Reference


| Service     | Port  | URL                                              |
| ----------- | ----- | ------------------------------------------------ |
| Backend     | 8005  | [http://127.0.0.1:8005](http://127.0.0.1:8005)   |
| RAG         | 13457 | [http://127.0.0.1:13457](http://127.0.0.1:13457) |
| Multi-Agent | 8002  | [http://127.0.0.1:8002](http://127.0.0.1:8002)   |
| SSO Backend | 13456 | [http://127.0.0.1:13456](http://127.0.0.1:13456) |
| UI (Vite)   | 5000  | [http://127.0.0.1:5000](http://127.0.0.1:5000)   |



| Infrastructure | Port(s)                     |
| -------------- | --------------------------- |
| MongoDB        | 27017                       |
| RabbitMQ       | 5672, 15672 (management UI) |
| Qdrant         | 6333 (HTTP), 6334 (gRPC)    |
| Redis          | 6379                        |
| Temporal       | 7233 (gRPC), 8233 (web UI)  |


---

## 8. Known Issues

### Python & Virtual Environments

#### No suitable Python found

The startup script auto-detects Python by trying `python3.11`, `python3.12`, `python3.13`, and `python3` in order. It requires a version between 3.11 and 3.13 (3.14+ is not supported). If no suitable version is found, install one:

```bash
# Fedora / RHEL
sudo dnf install python3.11

# macOS (Homebrew)
brew install python@3.11

# Ubuntu / Debian
sudo apt install python3.11 python3.11-venv
```

Make sure `python3` (or `python3.11` / `python3.12` / `python3.13`) is on your `PATH`. Do **not** use Python 3.14+.

#### Python version mismatch between venvs

The startup script now **enforces** that every venv's Python minor version matches the detected interpreter. If you see a "Python version mismatch" error, you have two options:

1. **Recreate the venvs** to match the detected interpreter:

```bash
./local-development/start-unifai-dev.sh --setup-venv
```

2. **Override the detected interpreter** to match your existing venvs:

```bash
export UNIFAI_PYTHON=python3.12   # ← match your venv version
./local-development/start-unifai-dev.sh
```

#### `venv/bin/activate: No such file or directory`

The startup script assumes each service already has a `venv/` directory. If you see this error you skipped the venv setup in [Section 3](#3-setting-up-virtual-environments). Go back and create the venv for the failing service, or use `--setup-venv`.

#### `ModuleNotFoundError: No module named 'global_utils'`

You forgot to install `global_utils` into that service's venv. Activate the venv and run:

```bash
pip install -e /path/to/UnifAI/global_utils
```

---

### Containers & Infrastructure

#### Podman machine not running

On macOS/remote Linux, Podman requires a running machine. If containers fail to start:

```bash
podman machine init    # first time only
podman machine start
```

Alternatively, install Docker and the script will auto-detect it as a fallback.

> [!TIP]
> Container startup errors are captured in the error log file (`/tmp/unifai-dev-*.log`) rather than printed to the terminal. Check the log if containers silently fail to start.

#### Celery worker fails to connect

If the Celery worker crashes with a connection error, RabbitMQ is likely not running. Verify:

```bash
podman ps | grep rabbitmq   # or: docker ps | grep rabbitmq
```

If missing, start it manually:

```bash
podman run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Or use the helper script:

```bash
./local-development/start-infra.sh rabbitmq
```

#### Temporal worker fails to connect

Similarly, if the Temporal worker crashes, ensure the Temporal container is running:

```bash
podman ps | grep temporal
```

If missing:

```bash
./local-development/start-infra.sh temporal
```

---

### Networking & Ports

#### Port already in use

If a service fails to start with `Address already in use`, kill the process occupying the port:

```bash
lsof -ti :PORT_NUMBER | xargs kill -9
```

The startup script does this automatically, but a race condition can occasionally leave a stale process behind.

If a **container** fails to bind a port (e.g. `pasta failed ... Address already in use`), the error details are written to the error log file — check `/tmp/unifai-dev-*.log` (see [4.2 Error logging](#42-error-logging)). A common cause is a previously created container or a system-installed service (e.g. `mongod`) still holding the port. Stop it before re-running:

```bash
./local-development/start-infra.sh --stop     # stop all infra containers
sudo systemctl stop mongod                     # if system MongoDB is running
```

#### Firewall blocking container ports

On Fedora/RHEL, `firewalld` may silently block connections to container-exposed ports (27017, 6333, 5672, etc.). If a service can't reach a container despite it running, check your firewall:

```bash
sudo firewall-cmd --list-ports
```

To temporarily open a port:

```bash
sudo firewall-cmd --add-port=27017/tcp    # MongoDB example
```

Or allow the entire Podman/Docker bridge interface:

```bash
sudo firewall-cmd --zone=trusted --add-interface=podman0   # Podman
sudo firewall-cmd --zone=trusted --add-interface=docker0   # Docker
```

If SELinux is blocking container access (check with `ausearch -m avc -ts recent`), you can temporarily set it to permissive mode:

```bash
sudo setenforce 0
```

To make it persistent across reboots, edit `/etc/selinux/config` and set `SELINUX=permissive`.

#### Vite proxy returns `502 Bad Gateway`

If the UI loads but API calls fail with `502`, the backend service that Vite is trying to proxy to is not running (or hasn't finished starting yet). Check the corresponding tmux pane for errors. The proxy target mapping is:


| UI Path   | Expected Backend         |
| --------- | ------------------------ |
| `/api1/*` | RAG (port 13457)         |
| `/api2/*` | Multi-Agent (port 8002)  |
| `/api3/*` | SSO Backend (port 13456) |
| `/api4/*` | Backend (port 8005)      |


Also verify you are connected to the **Red Hat SSO** — authentication-related requests will fail without it.

---

### UI & Frontend

#### `pnpm: command not found`

Install pnpm globally:

```bash
npm install -g pnpm
```

Or enable Corepack (ships with Node.js 16+):

```bash
corepack enable
```

