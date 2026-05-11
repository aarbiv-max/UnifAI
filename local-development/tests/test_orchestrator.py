"""Tests for devtool.services.orchestrator validation and layout logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devtool.domain.models import (
    ContainerStatus,
    InfraComponent,
    Service,
    ServiceType,
    VenvConfig,
    VenvStrategy,
    WindowLayout,
)
from devtool.services.orchestrator import Orchestrator


def _make_service(
    name: str,
    *,
    is_primary: bool = True,
    port: int | None = 8000,
    svc_type: ServiceType = ServiceType.PYTHON,
    env_file: str | None = None,
    env_entries: dict[str, str] | None = None,
    directory: str = "test",
) -> Service:
    return Service(
        name=name,
        directory=Path(directory),
        type=svc_type,
        launch="echo ok",
        venv=VenvConfig(strategy=VenvStrategy.NONE),
        port=port,
        is_primary=is_primary,
        env_file=env_file,
        env_entries=env_entries or {},
    )


def _make_orchestrator(
    services: list[Service],
    groups: dict[str, list[str]] | None = None,
    *,
    infra: list[InfraComponent] | None = None,
):
    """Build an Orchestrator with a mock registry wired to the given services.

    Returns the orchestrator.  Access mocks via ``orch._registry``,
    ``orch._runtime``, ``orch._session``, ``orch._venv``.
    """
    registry = MagicMock()
    by_name = {s.name: s for s in services}

    registry.get_service.side_effect = lambda n: by_name[n]
    registry.all_services.return_value = services
    registry.primary_services.return_value = [s for s in services if s.is_primary]
    registry.log_dir = Path("/tmp/unifai-dev-test/logs")

    infra_list = infra or []
    infra_by_name = {c.name: c for c in infra_list}
    registry.all_infra.return_value = infra_list
    registry.get_infra.side_effect = lambda n: infra_by_name[n]
    registry.infra_for_services.return_value = infra_list

    def resolve(targets):
        seen: set[str] = set()
        result: list[Service] = []
        for t in targets:
            if groups and t in groups:
                for sn in groups[t]:
                    if sn not in seen:
                        seen.add(sn)
                        result.append(by_name[sn])
            else:
                if t not in seen:
                    seen.add(t)
                    result.append(by_name[t])
        return result

    registry.resolve_services.side_effect = resolve

    return Orchestrator(
        registry=registry,
        root=Path("/fake"),
        container_runtime=MagicMock(),
        session_manager=MagicMock(),
        venv_manager=MagicMock(),
        process_manager=MagicMock(),
    )


class TestValidateStart:
    def test_primary_only_passes(self) -> None:
        services = [_make_service("a"), _make_service("b")]
        Orchestrator._validate_start(services, fg=False)

    def test_non_primary_alone_rejected(self) -> None:
        services = [_make_service("w", is_primary=False)]
        with pytest.raises(SystemExit, match="non-primary"):
            Orchestrator._validate_start(services, fg=False)

    def test_non_primary_with_primary_passes(self) -> None:
        services = [
            _make_service("a"),
            _make_service("w", is_primary=False),
        ]
        Orchestrator._validate_start(services, fg=False)

    def test_fg_single_primary_passes(self) -> None:
        services = [_make_service("a")]
        Orchestrator._validate_start(services, fg=True)

    def test_fg_multiple_services_rejected(self) -> None:
        services = [_make_service("a"), _make_service("b")]
        with pytest.raises(SystemExit, match="exactly one"):
            Orchestrator._validate_start(services, fg=True)

    def test_fg_non_primary_rejected(self) -> None:
        services = [_make_service("w", is_primary=False)]
        with pytest.raises(SystemExit, match="non-primary"):
            Orchestrator._validate_start(services, fg=True)


class TestBuildDefaultLayout:
    def test_primary_only(self) -> None:
        svcs = [_make_service("a"), _make_service("b")]
        layout = Orchestrator._build_default_layout(svcs)
        assert len(layout) == 1
        assert layout[0].name == "services"
        assert [s.name for s in layout[0].services] == ["a", "b"]

    def test_primary_and_workers(self) -> None:
        svcs = [
            _make_service("a"),
            _make_service("b"),
            _make_service("w1", is_primary=False),
            _make_service("w2", is_primary=False),
        ]
        layout = Orchestrator._build_default_layout(svcs)
        assert len(layout) == 2
        assert layout[0].name == "services"
        assert [s.name for s in layout[0].services] == ["a", "b"]
        assert layout[1].name == "workers"
        assert [s.name for s in layout[1].services] == ["w1", "w2"]

    def test_workers_only(self) -> None:
        svcs = [_make_service("w", is_primary=False)]
        layout = Orchestrator._build_default_layout(svcs)
        assert len(layout) == 1
        assert layout[0].name == "workers"

    def test_empty(self) -> None:
        layout = Orchestrator._build_default_layout([])
        assert layout == []


class TestBuildCustomLayout:
    def test_named_windows(self) -> None:
        svc_a = _make_service("a")
        svc_b = _make_service("b")
        svc_c = _make_service("c")
        orch = _make_orchestrator([svc_a, svc_b, svc_c])

        layout = orch._build_custom_layout(
            window_specs=[("win1", ["a", "b"]), ("win2", ["c"])],
            bare_targets=[],
            all_services=[svc_a, svc_b, svc_c],
        )
        assert len(layout) == 2
        assert layout[0].name == "win1"
        assert [s.name for s in layout[0].services] == ["a", "b"]
        assert layout[1].name == "win2"
        assert [s.name for s in layout[1].services] == ["c"]

    def test_auto_named_single_service(self) -> None:
        svc_a = _make_service("a")
        orch = _make_orchestrator([svc_a])

        layout = orch._build_custom_layout(
            window_specs=[(None, ["a"])],
            bare_targets=[],
            all_services=[svc_a],
        )
        assert layout[0].name == "a"

    def test_auto_named_multi_service(self) -> None:
        svc_a = _make_service("a")
        svc_b = _make_service("b")
        orch = _make_orchestrator([svc_a, svc_b])

        layout = orch._build_custom_layout(
            window_specs=[(None, ["a", "b"])],
            bare_targets=[],
            all_services=[svc_a, svc_b],
        )
        assert layout[0].name == "window-0"

    def test_bare_targets_in_services_window(self) -> None:
        svc_a = _make_service("a")
        svc_b = _make_service("b")
        svc_w = _make_service("w", is_primary=False)
        orch = _make_orchestrator([svc_a, svc_b, svc_w])

        layout = orch._build_custom_layout(
            window_specs=[("workers", ["w"])],
            bare_targets=["a", "b"],
            all_services=[svc_a, svc_b, svc_w],
        )
        assert len(layout) == 2
        assert layout[0].name == "services"
        assert [s.name for s in layout[0].services] == ["a", "b"]
        assert layout[1].name == "workers"
        assert [s.name for s in layout[1].services] == ["w"]

    def test_remaining_services_in_other_window(self) -> None:
        svc_a = _make_service("a")
        svc_b = _make_service("b")
        svc_c = _make_service("c")
        orch = _make_orchestrator([svc_a, svc_b, svc_c])

        layout = orch._build_custom_layout(
            window_specs=[("mywin", ["a"])],
            bare_targets=[],
            all_services=[svc_a, svc_b, svc_c],
        )
        assert len(layout) == 2
        assert layout[0].name == "mywin"
        assert layout[1].name == "other"
        assert [s.name for s in layout[1].services] == ["b", "c"]

    def test_dedup_across_bare_and_window(self) -> None:
        svc_a = _make_service("a")
        orch = _make_orchestrator([svc_a])

        layout = orch._build_custom_layout(
            window_specs=[(None, ["a"])],
            bare_targets=["a"],
            all_services=[svc_a],
        )
        assert len(layout) == 1
        assert layout[0].name == "services"
        assert [s.name for s in layout[0].services] == ["a"]

    def test_group_expansion(self) -> None:
        svc_a = _make_service("a")
        svc_w = _make_service("w", is_primary=False)
        orch = _make_orchestrator(
            [svc_a, svc_w],
            groups={"mygroup": ["a", "w"]},
        )

        layout = orch._build_custom_layout(
            window_specs=[("grp", ["mygroup"])],
            bare_targets=[],
            all_services=[svc_a, svc_w],
        )
        assert len(layout) == 1
        assert layout[0].name == "grp"
        assert [s.name for s in layout[0].services] == ["a", "w"]


# ---------------------------------------------------------------------------
# _build_context_command
# ---------------------------------------------------------------------------

class TestBuildContextCommand:
    def test_python_service_includes_activate(self) -> None:
        svc = _make_service("backend", env_file=".env")
        orch = _make_orchestrator([svc])
        ctx = orch._build_context_command(svc, "3.12")
        assert "cd /fake/test" in ctx
        assert "source venv/bin/activate" in ctx
        assert "source /fake/test/.env" in ctx

    def test_node_service_skips_activate(self) -> None:
        svc = _make_service("ui", svc_type=ServiceType.NODE, env_file=".env.local")
        orch = _make_orchestrator([svc])
        ctx = orch._build_context_command(svc, "3.12")
        assert "source venv/bin/activate" not in ctx
        assert ".env.local" in ctx

    def test_no_env_file(self) -> None:
        svc = _make_service("svc")
        orch = _make_orchestrator([svc])
        ctx = orch._build_context_command(svc, "3.12")
        assert "source" in ctx  # venv activate
        assert "set -a" not in ctx


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------

class TestShell:
    @patch("devtool.services.shell_utils.resolve_bash", return_value="/usr/bin/bash")
    @patch("os.execvp")
    def test_shell_calls_execvp_with_bash(self, mock_execvp, mock_bash) -> None:
        svc = _make_service("backend", env_file=".env")
        orch = _make_orchestrator([svc])
        orch._detect_python = MagicMock(return_value=("/usr/bin/python3.12", "3.12"))

        orch.shell("backend")

        mock_execvp.assert_called_once()
        args = mock_execvp.call_args
        assert args[0][0] == "/usr/bin/bash"
        shell_cmd = args[0][1][2]
        assert "exec bash" in shell_cmd
        assert "source venv/bin/activate" in shell_cmd
        assert "echo ok" not in shell_cmd


# ---------------------------------------------------------------------------
# exec_in_context
# ---------------------------------------------------------------------------

class TestExecInContext:
    @patch("os.execvp")
    def test_exec_runs_user_command(self, mock_execvp) -> None:
        svc = _make_service("backend")
        orch = _make_orchestrator([svc])
        orch._detect_python = MagicMock(return_value=("/usr/bin/python3.12", "3.12"))

        orch.exec_in_context("backend", ["pytest", "-x"])

        mock_execvp.assert_called_once()
        shell_cmd = mock_execvp.call_args[0][1][2]
        assert "pytest -x" in shell_cmd
        assert "cd /fake/test" in shell_cmd

    @patch("os.execvp")
    def test_exec_single_command(self, mock_execvp) -> None:
        svc = _make_service("backend")
        orch = _make_orchestrator([svc])
        orch._detect_python = MagicMock(return_value=("/usr/bin/python3.12", "3.12"))

        orch.exec_in_context("backend", ["pip", "list"])

        shell_cmd = mock_execvp.call_args[0][1][2]
        assert "pip list" in shell_cmd


# ---------------------------------------------------------------------------
# attach
# ---------------------------------------------------------------------------

class TestAttach:
    def test_attach_no_session(self, capsys) -> None:
        svc = _make_service("backend")
        orch = _make_orchestrator([svc])
        orch._session.is_running.return_value = False

        orch.attach("backend")

        captured = capsys.readouterr()
        assert "No session" in captured.out

    @patch("subprocess.run")
    def test_attach_finds_pane(self, mock_run) -> None:
        svc = _make_service("backend", directory="backend")
        orch = _make_orchestrator([svc])
        orch._session.is_running.return_value = True
        orch._session.pane_contents.return_value = {
            "0.0": "cd /fake/backend && echo ok",
        }

        orch.attach("backend")

        orch._session.attach.assert_called_once()

    def test_attach_no_pane_found(self, capsys) -> None:
        svc = _make_service("backend", directory="backend")
        orch = _make_orchestrator([svc])
        orch._session.is_running.return_value = True
        orch._session.pane_contents.return_value = {
            "0.0": "something unrelated",
        }

        orch.attach("backend")

        captured = capsys.readouterr()
        assert "Could not find" in captured.out


# ---------------------------------------------------------------------------
# infra_logs
# ---------------------------------------------------------------------------

class TestInfraLogs:
    def test_calls_runtime_logs(self) -> None:
        comp = InfraComponent(
            name="mongo", image="mongo:latest", ports=["27017:27017"], label="MongoDB",
        )
        orch = _make_orchestrator([], infra=[comp])

        orch.infra_logs("mongo", follow=True)

        orch._runtime.logs.assert_called_once_with(comp, follow=True)

    def test_logs_without_follow(self) -> None:
        comp = InfraComponent(
            name="redis", image="redis:latest", ports=["6379:6379"], label="Redis",
        )
        orch = _make_orchestrator([], infra=[comp])

        orch.infra_logs("redis")

        orch._runtime.logs.assert_called_once_with(comp, follow=False)


# ---------------------------------------------------------------------------
# infra_reset
# ---------------------------------------------------------------------------

class TestInfraReset:
    def test_resets_specific_component(self) -> None:
        comp = InfraComponent(
            name="mongo", image="mongo:latest", ports=["27017:27017"], label="MongoDB",
        )
        orch = _make_orchestrator([], infra=[comp])

        orch.infra_reset(targets=["mongo"])

        orch._runtime.reset.assert_called_once_with(comp)

    def test_resets_all_when_no_target(self) -> None:
        comp_a = InfraComponent(
            name="mongo", image="mongo:latest", ports=["27017:27017"], label="MongoDB",
        )
        comp_b = InfraComponent(
            name="redis", image="redis:latest", ports=["6379:6379"], label="Redis",
        )
        orch = _make_orchestrator([], infra=[comp_a, comp_b])

        orch.infra_reset()

        assert orch._runtime.reset.call_count == 2


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------

class TestClean:
    def test_clean_logs(self, tmp_path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "backend.log").write_text("log data")
        (log_dir / "rag.log").write_text("log data")

        svc = _make_service("backend")
        orch = _make_orchestrator([svc])
        orch._registry.log_dir = log_dir
        orch._runtime.status.return_value = ContainerStatus.RUNNING

        orch.clean(clean_logs=True, clean_containers=False)

        assert list(log_dir.iterdir()) == []

    def test_clean_dry_run_does_not_delete(self, tmp_path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "backend.log").write_text("log data")

        svc = _make_service("backend")
        orch = _make_orchestrator([svc])
        orch._registry.log_dir = log_dir

        orch.clean(dry_run=True, clean_logs=True, clean_containers=False)

        assert (log_dir / "backend.log").exists()

    def test_clean_stopped_containers(self) -> None:
        comp = InfraComponent(
            name="mongo", image="mongo:latest", ports=["27017:27017"], label="MongoDB",
        )
        svc = _make_service("backend")
        orch = _make_orchestrator([svc], infra=[comp])
        orch._registry.log_dir = Path("/tmp/unifai-dev-test/logs")
        orch._runtime.status.return_value = ContainerStatus.STOPPED

        orch.clean(clean_logs=False, clean_containers=True)

        orch._runtime.remove.assert_called_once_with(comp)

    def test_clean_skips_running_containers(self) -> None:
        comp = InfraComponent(
            name="mongo", image="mongo:latest", ports=["27017:27017"], label="MongoDB",
        )
        svc = _make_service("backend")
        orch = _make_orchestrator([svc], infra=[comp])
        orch._registry.log_dir = Path("/tmp/unifai-dev-test/logs")
        orch._runtime.status.return_value = ContainerStatus.RUNNING

        orch.clean(clean_logs=False, clean_containers=True)

        orch._runtime.remove.assert_not_called()


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

class TestInit:
    def test_init_calls_all_steps(self) -> None:
        svc = _make_service("backend")
        orch = _make_orchestrator([svc])
        orch._detect_python = MagicMock(return_value=("/usr/bin/python3.12", "3.12"))
        orch.infra_start = MagicMock()
        orch.venv_setup = MagicMock()
        orch.env_generate = MagicMock()

        orch.init(non_interactive=True)

        orch.infra_start.assert_called_once()
        orch.venv_setup.assert_called_once()
        orch.env_generate.assert_called_once()

    def test_init_non_interactive_warns_placeholders(self, capsys) -> None:
        svc = _make_service(
            "identity", env_file=".env",
            env_entries={"client_id": "<REPLACE_WITH_YOUR_CLIENT_ID>"},
        )
        orch = _make_orchestrator([svc])
        orch._detect_python = MagicMock(return_value=("/usr/bin/python3.12", "3.12"))
        orch.infra_start = MagicMock()
        orch.venv_setup = MagicMock()
        orch.env_generate = MagicMock()

        with patch(
            "devtool.services.env_generator.check_unresolved",
            return_value=({"client_id"}, set()),
        ):
            orch.init(non_interactive=True)

        captured = capsys.readouterr()
        assert "client_id" in captured.out
        assert "placeholder" in captured.out


# ---------------------------------------------------------------------------
# _replace_placeholder
# ---------------------------------------------------------------------------

from devtool.services.env_generator import replace_env_value

class TestReplacePlaceholder:
    def test_replaces_placeholder_value(self, tmp_path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("key1=value1\nclient_id=<REPLACE>\nkey2=value2\n")

        replace_env_value(env_file, "client_id", "my-secret")

        content = env_file.read_text()
        assert "client_id=my-secret" in content
        assert "key1=value1" in content
        assert "key2=value2" in content
        assert "<REPLACE>" not in content

    def test_leaves_other_keys_untouched(self, tmp_path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("a=1\nb=2\nc=3\n")

        replace_env_value(env_file, "b", "new")

        lines = env_file.read_text().splitlines()
        assert lines == ["a=1", "b=new", "c=3"]
