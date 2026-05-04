# UnifAI — Local Development Guide

A step-by-step guide for running UnifAI locally — launch the **full stack** in tmux, a **group of services**, or a **single service** in your terminal.

## Quick Start

0. **[Prerequisites](#2-prerequisites)** — make sure you have Python 3.11–3.13, Node.js 22+, pnpm, tmux, and Podman/Docker installed
1. **[Install the CLI](#install-the-cli)**:
   ```bash
   pipx install -e local-development/
   ```
2. **[Run first-time setup](#410-first-time-setup)** — creates venvs, generates `.env` files, starts infra, and prompts for Keycloak credentials:
   ```bash
   unifai-dev init
   ```
3. **[Run](#4-running-the-development-environment)** — start the dev environment:
   ```bash
   unifai-dev start              # full-stack
   unifai-dev start backend --fg # or single service
   ```

> Steps 0–2 are one-time setup. On subsequent runs, just use step 3.
>
> If you prefer manual control over each step, skip `init` and follow these instead:
> - `unifai-dev env generate` — generate `.env` files
> - Edit `shared-resources/identity/.env` — fill in `client_id` and `client_secret`
> - `unifai-dev start --setup-venv` — create venvs and start services

---

## 1. Overview

UnifAI is composed of five services that run side-by-side during local development:


| Service         | Directory                       | Port  | Language   |
| --------------- | ------------------------------- | ----- | ---------- |
| RAG Backend     | `rag/`                          | 13457 | Python     |
| Identity        | `shared-resources/identity/`    | 13456 | Python     |
| Multi-Agent API | `multi-agent/`                  | 8002  | Python     |
| Backend         | `backend/`                      | 8005  | Python     |
| UI (Vite)       | `ui/`                           | 5000  | TypeScript |


In addition, two background workers run alongside the services:


| Worker          | Directory      | Purpose                                       |
| --------------- | -------------- | --------------------------------------------- |
| Celery Worker   | `rag/`         | Async RAG pipelines (document & Slack queues) |
| Temporal Worker | `multi-agent/` | Distributed agent workflow execution          |


### Architecture

The `local-development/` directory is a hexagonal-architecture Python package driven by a single `services.yaml` source of truth:

```
local-development/
├── services.yaml            # Single source of truth (services, infra, groups)
├── pyproject.toml           # Package definition (pipx install -e local-development/)
├── unifai-dev               # Fallback entry point (thin CLI script)
├── LOCAL_DEV_GUIDE.md       # This file
│
├── devtool/                 # Python package
│   ├── domain/              # Core models + YAML registry
│   │   ├── models.py        # Service, InfraComponent, ServiceGroup
│   │   └── registry.py      # Loads services.yaml → typed lookups
│   ├── ports/               # Interfaces (ABCs)
│   │   ├── container_runtime.py
│   │   ├── session_manager.py
│   │   ├── process_manager.py
│   │   └── venv_manager.py
│   ├── adapters/            # Implementations
│   │   ├── container_base.py   # Runtime auto-detection (Podman/Docker)
│   │   ├── podman.py / docker.py
│   │   ├── tmux.py / foreground.py
│   │   └── venv.py
│   ├── services/            # Application services
│   │   ├── orchestrator.py  # Composes ports for start/stop flows
│   │   ├── env_generator.py
│   │   ├── patcher.py
│   │   ├── python_detector.py
│   │   ├── health_checker.py
│   │   └── recovery.py
│   └── cli.py               # Argparse CLI → orchestrator
│
└── tests/
```

All service definitions, infrastructure containers, port assignments, and service groups are declared in `services.yaml` — there is no per-service Python class or hardcoded bash logic.

---

## 2. Prerequisites

### Required

- **Red Hat SSO connection** — you must be connected to the Red Hat SSO (VPN / internal network) for authentication to work
- **Python 3.11 – 3.13** (3.11 or 3.12 recommended; 3.14+ is **not** supported because PyO3's maximum supported version is 3.13)
- **pipx** — used to install the `unifai-dev` CLI. [Install pipx](https://pipx.pypa.io/stable/installation/) if you don't have it
- **Node.js 22+** and **pnpm** (the UI's `package.json` pins `pnpm` via `packageManager`)
- **MongoDB** — used by all Python backends for persistence
- **Qdrant** — vector database for RAG embeddings
- **Redis** — used by Identity (session/cache) and Multi-Agent (streaming)
- **tmux** — used for multi-service mode (auto-created session with panes)

### Install the CLI

From the **repo root**, run:

```bash
pipx install -e local-development/
```

This installs the `unifai-dev` command globally in an isolated environment. You only need to do this once.

### SSO Client Credentials *(Required)*

The Identity service requires a `client_id` and `client_secret` for Keycloak authentication.

1. **Request credentials** from the team — we will provide the values. (See Slack channel #forum-unifai)
2. **Generate `.env` files** (including placeholders for the credentials):

   ```bash
   unifai-dev env generate
   ```

3. **Edit** `shared-resources/identity/.env` — replace the placeholders with the actual values:

   ```
   client_id=<your-client-id>
   client_secret=<your-client-secret>
   ```

4. **Start the dev environment** — your `.env` files are preserved automatically on subsequent runs:

   ```bash
   unifai-dev start --setup-venv
   ```

> [!NOTE]
> The env generator **never overwrites** existing `.env` files — your credentials are safe across restarts. To regenerate from scratch (e.g. after a config change), use `unifai-dev env generate --force` and then re-edit the SSO credentials.


### Optional

- **Temporal** — distributed workflow execution (multi-agent)
- **RabbitMQ** — async RAG pipelines (Celery broker)
- **Keycloak** — OAuth 2.0 / OIDC authentication

### Infrastructure via containers

The tool auto-creates containers for infrastructure services using **Podman** or **Docker**. Make sure at least one is installed and running.


| Container | Ports       | Notes                          |
| --------- | ----------- | ------------------------------ |
| MongoDB   | 27017       |                                |
| RabbitMQ  | 5672, 15672 | 15672 = management UI          |
| Qdrant    | 6333, 6334  | 6333 = HTTP API, 6334 = gRPC   |
| Redis     | 6379        |                                |
| Temporal  | 7233, 8233  | 7233 = gRPC API, 8233 = web UI |


Not every service needs every container. The tool starts only the required ones based on which services you launch:


| Service           | MongoDB | RabbitMQ | Qdrant | Redis | Temporal |
| ----------------- | ------- | -------- | ------ | ----- | -------- |
| `backend`         | x       |          |        |       |          |
| `rag`             | x       | x        | x      |       |          |
| `multi-agent`     | x       |          |        | x     | x        |
| `identity`        |         |          |        | x     |          |
| `ui`              |         |          |        |       |          |
| `celery-worker`   | x       | x        | x      |       |          |
| `temporal-worker` | x       |          |        | x     | x        |


---

## 3. Setting Up Virtual Environments

> [!NOTE]
> **This step is optional.** The `start` command creates virtual environments automatically when you pass `--setup-venv`.
>
> You have three choices:
>
> 1. Run it via the devtool — see [3.1 Automated setup](#31-automated-setup)
> 2. Set up manually — see [3.2 Manual setup](#32-manual-setup)
> 3. **Skip to [Section 4](#4-running-the-development-environment) *(Recommended)*** — the start command handles this for you

### 3.1 Automated setup

Create all venvs at once:

```bash
unifai-dev venv setup
```

Or for a single service:

```bash
unifai-dev venv setup backend
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
| identity    | `shared-resources/identity/`    | `pip install -e .`                | `../../global_utils` |


For the **UI** (React/TypeScript — no Python venv):

```bash
cd ui && pnpm install && cd ..
```

---

## 4. Running the Development Environment

The `unifai-dev` CLI automates local development. Install it once with `pipx install -e local-development/` (see [Install the CLI](#install-the-cli)), then run from the **repo root**.

> ### **WARNING — Do NOT push local dev changes**
>
> The tool patches a few source files for local development. **You MUST revert these changes before pushing to avoid breaking production deployments.** Run from the repo root before any `git add` or `git push`:
>
> ```bash
> unifai-dev patch revert
> ```
>
> Or manually: `git checkout rag/bootstrap/flask_app.py backend/run/dev.py shared-resources/identity/bootstrap/flask_app.py`
>
> The `.env` files (`rag/.env`, `shared-resources/identity/.env`, `ui/.env.local`) are gitignored and safe — they will **not** appear in `git status`.
>
> **Quick check:** run `git diff --name-only` before pushing. If you see any of the files above, revert them first.

### 4.1 CLI reference

```
unifai-dev <command> [options]
```

**Service lifecycle:**

| Command                          | Description                                                                   |
| -------------------------------- | ----------------------------------------------------------------------------- |
| `start [targets...] [flags]`    | Start services (tmux or `--fg` foreground). Defaults to group `all`.          |
| `stop`                           | Stop the tmux session                                                         |
| `restart [targets...] [--failed]`| Dependency-aware restart of one or more services/groups                       |
| `destroy`                        | Kill the tmux session and stop all infrastructure containers                  |

**Start flags:**

| Flag                              | Description                                                                      |
| --------------------------------- | -------------------------------------------------------------------------------- |
| `--fg`                            | Foreground mode — run a single primary service in your terminal                  |
| `--setup-venv`                    | Create virtual environments before starting                                      |
| `--window [name=]svc1,svc2,...`   | Group services into a custom tmux window (repeatable)                            |

**Targets** can be service names, group names, or a mix. When omitted, defaults to the `all` group.

**Context helpers:**

| Command                       | Description                                                        |
| ----------------------------- | ------------------------------------------------------------------ |
| `shell <service>`             | Open an interactive shell with the service's venv and env loaded   |
| `exec <service> <command...>` | Run a command inside the service's context, then exit              |
| `attach <service>`            | Jump to the tmux pane running a specific service                   |

**Monitoring:**

| Command                        | Description                           |
| ------------------------------ | ------------------------------------- |
| `status`                       | Health dashboard (infra + services)   |
| `logs <service>`               | Print log file for a service          |
| `logs <service> --follow`      | Tail log file in real time            |
| `doctor`                       | Full diagnostic (Python, venvs, infra, ports, env files) |

**Infrastructure:**

| Command                              | Description                                         |
| ------------------------------------ | --------------------------------------------------- |
| `infra start [containers...]`        | Start all or named containers                       |
| `infra start --for <service>`        | Start only the containers a service needs           |
| `infra stop`                         | Stop all infrastructure containers                  |
| `infra status`                       | Show status of all containers                       |
| `infra logs <component> [--follow]`  | View (or tail) a container's logs                   |
| `infra reset [components...]`        | Stop, remove, and recreate containers               |

**Virtual environments:**

| Command                       | Description                                          |
| ----------------------------- | ---------------------------------------------------- |
| `venv setup [service]`        | Create venv(s) — all or one service                  |
| `venv setup [service] --force`| Delete and recreate existing venvs                   |
| `venv check`                  | Verify Python versions match                         |

**Environment files:**

| Command                | Description                                    |
| ---------------------- | ---------------------------------------------- |
| `env generate`         | Create .env files (skip existing)              |
| `env generate --force` | Regenerate .env files even if they exist       |
| `env show <service>`   | Print current env config for a service         |

**Source-file patches:**

| Command          | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `patch apply`    | Apply local-dev patches to source files              |
| `patch revert`   | Revert previously applied patches                    |

**Setup and maintenance:**

| Command                  | Description                                              |
| ------------------------ | -------------------------------------------------------- |
| `init [--non-interactive]`| First-time setup (infra, venvs, env, patches)           |
| `clean [--dry-run]`      | Remove stale log files and stopped containers            |
| `clean --logs`           | Only clean log files                                     |
| `clean --venvs`          | Only clean virtual environments                          |
| `clean --containers`     | Only clean stopped containers                            |

### 4.2 Service groups

Services can be launched individually by name or as predefined groups. Groups are defined in `services.yaml`:

| Group          | Services                                                              |
| -------------- | --------------------------------------------------------------------- |
| `all`          | backend, rag, multi-agent, identity, ui, celery-worker, temporal-worker |
| `services`     | backend, rag, multi-agent, identity, ui                                 |
| `workers`      | celery-worker, temporal-worker                                          |
| `agents`       | multi-agent, temporal-worker                                            |
| `rag-stack`    | rag, celery-worker                                                      |
| `backend-only` | backend, identity                                                       |

You can mix service names and group names freely:

```bash
unifai-dev start rag-stack          # rag + celery-worker
unifai-dev start agents backend     # multi-agent + temporal-worker + backend
unifai-dev start backend rag        # just those two
```

> [!NOTE]
> **Non-primary services** (`celery-worker`, `temporal-worker`) cannot be launched alone. They must always be part of a multi-service start — use a group like `rag-stack` or `agents`, or name them alongside their parent service.

### 4.3 Logging

All service output is captured to log files alongside live tmux pane output:

- **Log directory:** `/tmp/unifai-dev/logs/` (configurable in `services.yaml`)
- **Per-service logs:** `/tmp/unifai-dev/logs/<service>.log`
- **Infrastructure logs:** `/tmp/unifai-dev/logs/infra.log`

To view logs:

```bash
unifai-dev logs backend           # print log
unifai-dev logs backend --follow   # tail in real time
```

Log files are truncated on each `start` invocation — they capture the current session only.

> [!TIP]
> If a container fails to start with a "port already in use" error, check `/tmp/unifai-dev/logs/infra.log` for details.

### 4.4 Environment and patches

The `start` command automatically generates `.env` files and applies source patches. You can also run these independently:

```bash
unifai-dev env generate           # create .env files (skip existing)
unifai-dev env generate --force    # overwrite existing .env files
unifai-dev env show identity        # inspect a service's env config
```

**Generated `.env` files (gitignored):**


| File                                | Contents                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------ |
| `rag/.env`                          | `hostname_local=127.0.0.1`, `port=13457`                                             |
| `shared-resources/identity/.env`    | `keycloak_base_url`, `keycloak_realm`, `client_id`, `client_secret` (placeholders), `hostname_local`, `port`, `frontend_url`, `backend_env` |
| `ui/.env.local`                     | `DEV_PORT=5000`, `DEV_HOST=0.0.0.0`, proxy targets for all backends                  |


**Source-file patches (revert with `git checkout`):**


| File                                  | Change                   |
| ------------------------------------- | ------------------------ |
| `rag/bootstrap/flask_app.py`          | Bind host → `0.0.0.0`    |
| `backend/run/dev.py`                  | Bind host → `0.0.0.0`    |
| `shared-resources/identity/bootstrap/flask_app.py` | Bind host → `0.0.0.0`    |


### 4.5 Python version enforcement

The tool auto-detects a Python interpreter (prefers `python3.11` → `python3.12` → `python3.13` → `python3`, and rejects anything outside 3.11–3.13). Before launching, it verifies that each service's venv was built with the **same Python minor version**.

To override auto-detection:

```bash
export UNIFAI_PYTHON=python3.11
unifai-dev start
```

To check your current venv versions:

```bash
unifai-dev venv check
```

---

### 4.6 Single-service foreground mode

Run **one primary service** in your terminal with live auto-reload using `--fg`. Only the infrastructure containers that service needs are started.

```bash
unifai-dev start backend --fg
```

The tool will:

1. Generate `.env` files and apply source patches
2. Verify the service's venv exists and its Python version matches
3. Start only the required infrastructure containers
4. Source the service's `.env` file
5. Launch the service in your foreground terminal with debug/auto-reload

Press `Ctrl+C` to stop.

**Examples:**

```bash
# Standard usage
unifai-dev start rag --fg

# First time — create the venv automatically
unifai-dev start rag --fg --setup-venv
```

> [!NOTE]
> Workers (`celery-worker`, `temporal-worker`) cannot run in foreground mode — they are non-primary services. Use a group instead: `unifai-dev start rag-stack`

---

### 4.7 Multi-service tmux mode (default)

When you start multiple services (or omit `--fg`), the tool creates a tmux session with auto-windowed panes.

**First time** (creates virtual environments before starting):
```bash
unifai-dev start --setup-venv
```

**Subsequent runs** (venvs already exist):
```bash
unifai-dev start
```

**Start a subset:**
```bash
unifai-dev start rag-stack      # rag + celery-worker
unifai-dev start services        # all 5 primary services (no workers)
```

If a previous tmux session is still open, destroy it first:

```bash
unifai-dev destroy
unifai-dev start
```

The tool will:

1. Verify all venvs exist and Python versions match
2. Start required infrastructure containers via Podman/Docker
3. Kill any processes occupying required ports
4. Create a tmux session (`unifai-dev`) with auto-windowed panes:
   - **Window "services"** — one pane per primary service (tiled layout)
   - **Window "workers"** — one pane per worker (if any workers are selected)
5. All output is captured to log files via `tee`

**Useful tmux commands once attached:**


| Action                    | Keys                                                   |
| ------------------------- | ------------------------------------------------------ |
| Switch to next window     | `Ctrl-b n`                                             |
| Switch to previous window | `Ctrl-b p`                                             |
| Navigate between panes    | `Ctrl-b ←/→/↑/↓`                                       |
| Scroll pane output        | `Ctrl-b [` then arrow keys, `q` to exit                |
| Destroy session           | `unifai-dev destroy`               |


---

### 4.8 Managing infrastructure containers

You can manage infrastructure containers independently:

```bash
# Start only what a specific service needs
unifai-dev infra start --for backend       # → mongo
unifai-dev infra start --for rag            # → mongo, rabbitmq, qdrant
unifai-dev infra start --for multi-agent    # → mongo, redis, temporal

# Cherry-pick specific containers
unifai-dev infra start mongo qdrant

# Check what's running
unifai-dev infra status

# View container logs
unifai-dev infra logs mongo
unifai-dev infra logs mongo --follow        # tail in real time

# Reset a misbehaving container (stop → remove → recreate)
unifai-dev infra reset mongo

# Stop all infrastructure
unifai-dev infra stop
```

---

### 4.9 Health checks and diagnostics

Check the health of all running services and infrastructure:

```bash
unifai-dev status
```

This probes each service's port and shows container status.

For a full diagnostic (Python, venvs, containers, ports, env files):

```bash
unifai-dev doctor
```

To restart failed services (checks infra dependencies first):

```bash
unifai-dev restart backend
unifai-dev restart backend rag              # restart multiple services
unifai-dev restart agents                   # restart a group
unifai-dev restart --failed                 # auto-restart all unhealthy services
```

---

### 4.10 First-time setup

The `init` command runs the full first-time setup in one go — checks prerequisites, starts infrastructure, creates venvs, generates `.env` files, prompts for placeholder values, and applies patches:

```bash
unifai-dev init
```

In CI or scripted environments, use `--non-interactive` to skip credential prompts (you'll need to fill in placeholders manually afterwards):

```bash
unifai-dev init --non-interactive
```

---

### 4.11 Context helpers: shell, exec, attach

These commands let you interact with a service's environment without manually activating venvs or sourcing `.env` files.

**`shell`** — drop into an interactive bash session with the service's venv activated and env loaded:

```bash
unifai-dev shell backend
# You're now in backend/ with the venv active — run pytest, manage.py, etc.
```

**`exec`** — run a single command in the service's context:

```bash
unifai-dev exec backend python -m pytest tests/
unifai-dev exec rag pip list
```

**`attach`** — jump directly to a running service's tmux pane:

```bash
unifai-dev attach backend
```

---

### 4.12 Custom tmux window layouts

By default, `start` puts primary services in a "services" window and workers in a "workers" window. Use `--window` to override this layout:

```bash
# Put rag and celery-worker together in a named window
unifai-dev start --window rag=rag,celery-worker --window agents=multi-agent,temporal-worker backend identity ui

# Unnamed windows get auto-generated names
unifai-dev start --window backend,identity --window rag,celery-worker
```

Each `--window` creates a separate tmux window with the listed services as panes. Services named as bare positional arguments go into a default "services" window. Any remaining services go into an "other" window.

---

### 4.13 Cleaning up stale resources

Remove old log files, stopped containers, or virtual environments:

```bash
unifai-dev clean                    # remove logs + stopped containers
unifai-dev clean --dry-run          # preview what would be removed
unifai-dev clean --logs             # only clean log files
unifai-dev clean --venvs            # only clean virtual environments
unifai-dev clean --containers       # only clean stopped containers
```

---

### 4.14 Managing source-file patches

The `start` command automatically applies patches, but you can manage them independently:

```bash
unifai-dev patch apply              # apply local-dev patches
unifai-dev patch revert             # revert to original source files
```

This is especially useful before committing or pushing — run `patch revert` to ensure no local-dev changes leak into your commits.

---

### 4.15 Verifying the setup

Once all services are running, open a browser and navigate to:

```
http://127.0.0.1:5000
```

The Vite dev server proxies API requests to the backends automatically:


| UI Path   | Backend                  |
| --------- | ------------------------ |
| `/api1/*` | RAG (port 13457)         |
| `/api2/*` | Multi-Agent (port 8002)  |
| `/api3/*` | Identity (port 13456)    |
| `/api4/*` | Backend (port 8005)      |


---

## 5. Typical Development Workflows

### "I'm working on the Backend service"

```bash
# Single service in foreground — auto-starts MongoDB
unifai-dev start backend --fg

# Edit code in your IDE → Flask auto-reloads → see changes immediately
# Test: curl http://127.0.0.1:8005/api/health
```

### "I'm working on the RAG service"

```bash
# RAG + Celery worker together (auto-starts MongoDB + RabbitMQ + Qdrant)
unifai-dev start rag-stack

# Or just RAG in foreground
unifai-dev start rag --fg
```

### "I'm working on the UI"

```bash
# UI alone in foreground (no containers needed)
unifai-dev start ui --fg

# Need backends too? Start them alongside:
unifai-dev start ui backend rag
```

### "I'm working on Multi-Agent"

```bash
# Multi-Agent + Temporal worker (auto-starts MongoDB + Redis + Temporal)
unifai-dev start agents

# Or just multi-agent in foreground
unifai-dev start multi-agent --fg
```

### "Brand new clone — set up everything from scratch"

```bash
# 1. Install the CLI (one-time)
pipx install -e local-development/

# 2. Run first-time setup — creates venvs, generates .env, starts infra, prompts for credentials
unifai-dev init

# 3. Launch
unifai-dev start

# — or single-service:
unifai-dev start backend --fg
```

---

## 6. Comparison: Foreground vs Multi-Service


|                      | `start <name> --fg`          | `start` / `start <group>`   |
| -------------------- | ---------------------------- | ---------------------------- |
| **Use case**         | Working on one service       | Integration testing, demos   |
| **Services started** | Just the one you pick        | All selected (group or list) |
| **Containers**       | Only what's needed           | Union of all selected        |
| **Terminal**         | Foreground in your shell     | tmux session                 |
| **Auto-reload**      | Yes (Flask debug / Vite HMR) | Yes                          |
| **Venv check**       | Checks the one service       | Checks all Python venvs      |
| **Log files**        | `/tmp/unifai-dev/logs/`      | `/tmp/unifai-dev/logs/`      |
| **Workers**          | Not allowed alone            | Auto-windowed in "workers"   |


---

## 7. Port Reference


| Service     | Port  | URL                                              |
| ----------- | ----- | ------------------------------------------------ |
| Backend     | 8005  | [http://127.0.0.1:8005](http://127.0.0.1:8005)   |
| RAG         | 13457 | [http://127.0.0.1:13457](http://127.0.0.1:13457) |
| Multi-Agent | 8002  | [http://127.0.0.1:8002](http://127.0.0.1:8002)   |
| Identity    | 13456 | [http://127.0.0.1:13456](http://127.0.0.1:13456) |
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

The tool auto-detects Python by trying `python3.11`, `python3.12`, `python3.13`, and `python3` in order. It requires a version between 3.11 and 3.13 (3.14+ is not supported). If no suitable version is found, install one:

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

The tool **enforces** that every venv's Python minor version matches the detected interpreter. If you see a mismatch error:

1. **Recreate the venvs** to match the detected interpreter:

```bash
unifai-dev venv setup
```

2. **Override the detected interpreter** to match your existing venvs:

```bash
export UNIFAI_PYTHON=python3.12   # ← match your venv version
unifai-dev start
```

3. **Check all venvs at once:**

```bash
unifai-dev venv check
```

#### `venv/bin/activate: No such file or directory`

You skipped the venv setup in [Section 3](#3-setting-up-virtual-environments). Create the venv for the failing service:

```bash
unifai-dev venv setup backend
```

Or use `--setup-venv` with start.

#### `ModuleNotFoundError: No module named 'global_utils'`

You forgot to install `global_utils` into that service's venv. Activate the venv and run:

```bash
pip install -e /path/to/UnifAI/global_utils
```

#### `PyYAML is required`

If you installed via `pipx`, PyYAML is handled automatically. If you see this error, reinstall the CLI:

```bash
pipx install -e local-development/ --force
```

---

### Containers & Infrastructure

#### Podman machine not running

On macOS/remote Linux, Podman requires a running machine. If containers fail to start:

```bash
podman machine init    # first time only
podman machine start
```

Alternatively, install Docker and the tool will auto-detect it as a fallback.

> [!TIP]
> Container startup errors are captured in `/tmp/unifai-dev/logs/infra.log`. Check that file if containers silently fail to start.

#### Celery worker fails to connect

If the Celery worker crashes with a connection error, RabbitMQ is likely not running. Verify:

```bash
unifai-dev infra status
```

If RabbitMQ is missing, start it:

```bash
unifai-dev infra start rabbitmq
```

#### Temporal worker fails to connect

Similarly, if the Temporal worker crashes, ensure the Temporal container is running:

```bash
unifai-dev infra status
unifai-dev infra start temporal
```

---

### Networking & Ports

#### Port already in use

If a service fails to start with `Address already in use`, kill the process occupying the port:

```bash
lsof -ti :PORT_NUMBER | xargs kill -9
```

The tool does this automatically during start, but a race condition can occasionally leave a stale process behind.

If a **container** fails to bind a port (e.g. `pasta failed ... Address already in use`), check `/tmp/unifai-dev/logs/infra.log`. A common cause is a previously created container or a system-installed service (e.g. `mongod`) still holding the port:

```bash
unifai-dev infra stop             # stop all infra containers
sudo systemctl stop mongod                             # if system MongoDB is running
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

If the UI loads but API calls fail with `502`, the backend service that Vite is trying to proxy to is not running. Run the health check:

```bash
unifai-dev status
```

The proxy target mapping is:


| UI Path   | Expected Backend         |
| --------- | ------------------------ |
| `/api1/*` | RAG (port 13457)         |
| `/api2/*` | Multi-Agent (port 8002)  |
| `/api3/*` | Identity (port 13456)    |
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
