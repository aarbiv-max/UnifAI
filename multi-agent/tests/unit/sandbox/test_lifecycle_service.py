"""Tests for SandboxLifecycleService."""
import pytest
from unittest.mock import Mock, call

from mas.elements.tools.sandbox_exec.service import SandboxLifecycleService


class TestProvisionForSession:

    def test_creates_pvc_and_pods(
        self, mock_sandbox_manager, sandbox_config, sample_run_id, sample_agent_ids,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)

        state = service.provision_for_session(
            run_id=sample_run_id,
            agent_ids=sample_agent_ids,
            config=sandbox_config,
        )

        mock_sandbox_manager.provision_pvc.assert_called_once()
        assert mock_sandbox_manager.provision_pod.call_count == len(sample_agent_ids)
        assert len(state.pods) == len(sample_agent_ids)
        assert state.pvc_name == f"sandbox-pvc-{sample_run_id[:8]}"

    def test_reuses_existing_pvc_name(
        self, mock_sandbox_manager, sandbox_config, sample_run_id, sample_agent_ids,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)
        existing = "sandbox-pvc-old12345"

        state = service.provision_for_session(
            run_id=sample_run_id,
            agent_ids=sample_agent_ids,
            config=sandbox_config,
            existing_pvc_name=existing,
        )

        assert state.pvc_name == existing
        pvc_call = mock_sandbox_manager.provision_pvc.call_args
        assert pvc_call.kwargs["pvc_name"] == existing

    def test_pod_names_are_deterministic(
        self, mock_sandbox_manager, sandbox_config, sample_run_id, sample_agent_ids,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)

        state = service.provision_for_session(
            run_id=sample_run_id,
            agent_ids=sample_agent_ids,
            config=sandbox_config,
        )

        for agent_id in sample_agent_ids:
            expected_pod = f"sandbox-{sample_run_id[:8]}-{agent_id}"
            assert state.pods[agent_id].pod_name == expected_pod
            assert state.pods[agent_id].worktree_path == f"/workspace/worktree-{agent_id}"
            assert state.pods[agent_id].branch_name == f"sandbox/{agent_id}"

    def test_passes_git_token_to_provision_pod(
        self, mock_sandbox_manager, sandbox_config, sample_run_id,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)

        service.provision_for_session(
            run_id=sample_run_id,
            agent_ids=["a1"],
            config=sandbox_config,
        )

        pod_call = mock_sandbox_manager.provision_pod.call_args
        assert pod_call.kwargs["git_token"] == sandbox_config.git_token

    def test_cleans_orphan_pods_before_provisioning(
        self, mock_sandbox_manager, sandbox_config, sample_run_id,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)

        service.provision_for_session(
            run_id=sample_run_id,
            agent_ids=["a1"],
            config=sandbox_config,
        )

        teardown_calls = [
            c for c in mock_sandbox_manager.teardown_pod.call_args_list
        ]
        assert len(teardown_calls) == 1
        assert teardown_calls[0].kwargs["pod_name"] == f"sandbox-{sample_run_id[:8]}-a1"


class TestTeardownForSession:

    def test_tears_down_all_pods(
        self, mock_sandbox_manager, sandbox_config, sample_sandbox_state,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)

        service.teardown_for_session(sample_sandbox_state, sandbox_config)

        assert mock_sandbox_manager.teardown_pod.call_count == 2

    def test_continues_on_individual_pod_failure(
        self, mock_sandbox_manager, sandbox_config, sample_sandbox_state,
    ):
        mock_sandbox_manager.teardown_pod.side_effect = [
            RuntimeError("pod stuck"),
            None,
        ]
        service = SandboxLifecycleService(mock_sandbox_manager)

        service.teardown_for_session(sample_sandbox_state, sandbox_config)

        assert mock_sandbox_manager.teardown_pod.call_count == 2


class TestTeardownByNaming:

    def test_reconstructs_pod_names(
        self, mock_sandbox_manager, sandbox_config, sample_run_id, sample_agent_ids,
    ):
        service = SandboxLifecycleService(mock_sandbox_manager)

        service.teardown_by_naming(sample_run_id, sample_agent_ids, sandbox_config)

        assert mock_sandbox_manager.teardown_pod.call_count == 2
        pod_names = [
            c.kwargs["pod_name"]
            for c in mock_sandbox_manager.teardown_pod.call_args_list
        ]
        assert f"sandbox-{sample_run_id[:8]}-agent_1" in pod_names
        assert f"sandbox-{sample_run_id[:8]}-code_reviewer" in pod_names


class TestHealthCheck:

    def test_returns_per_agent_status(
        self, mock_sandbox_manager, sandbox_config, sample_sandbox_state,
    ):
        mock_sandbox_manager.is_pod_alive.side_effect = [True, False]
        service = SandboxLifecycleService(mock_sandbox_manager)

        result = service.health_check(sample_sandbox_state, sandbox_config)

        assert result["agent_1"] is True
        assert result["code_reviewer"] is False

    def test_returns_false_on_exception(
        self, mock_sandbox_manager, sandbox_config, sample_sandbox_state,
    ):
        mock_sandbox_manager.is_pod_alive.side_effect = RuntimeError("timeout")
        service = SandboxLifecycleService(mock_sandbox_manager)

        result = service.health_check(sample_sandbox_state, sandbox_config)

        assert all(v is False for v in result.values())
