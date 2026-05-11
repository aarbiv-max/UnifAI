"""Application-layer orchestration of sandbox lifecycle.

Coordinates PVC provisioning, per-agent pod creation, teardown,
and health checks.  Depends only on ``SandboxManagerPort``.
"""
import logging
import re
from typing import Dict, List, Optional

from .config import SandboxExecToolConfig
from .models import SandboxPodInfo, SandboxState
from .ports import SandboxManagerPort

logger = logging.getLogger(__name__)


def k8s_safe_name(raw: str) -> str:
    """Sanitize a string for use in Kubernetes resource names (RFC 1123)."""
    s = raw.lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9\-.]", "-", s)
    return s.strip("-.")


class SandboxLifecycleService:
    """Manages the full lifecycle of sandbox pods for a workflow session."""

    def __init__(self, sandbox_manager: SandboxManagerPort) -> None:
        self._manager = sandbox_manager

    def provision_for_session(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
        existing_pvc_name: Optional[str] = None,
    ) -> SandboxState:
        """Provision PVC + one pod per agent.  Idempotent.

        Args:
            run_id: Session/workflow identifier.
            agent_ids: Graph node UIDs that need sandbox pods.
            config: Cluster credentials and git repo from the tool resource.
            existing_pvc_name: If set (re-trigger), reuse this PVC instead
                of generating a new name.

        Returns:
            Populated ``SandboxState`` with all pod info.
        """
        pvc_name = existing_pvc_name or f"sandbox-pvc-{run_id[:8]}"

        self._manager.provision_pvc(
            pvc_name=pvc_name,
            namespace=config.namespace,
            cluster_api=config.cluster_api,
            token=config.cluster_token,
            storage_class=config.storage_class,
            skip_tls_verify=config.skip_tls_verify,
        )

        self._cleanup_orphan_pods(run_id, agent_ids, config)

        pods: Dict[str, SandboxPodInfo] = {}
        for agent_id in agent_ids:
            safe_id = k8s_safe_name(agent_id)
            pod_name = f"sandbox-{run_id[:8]}-{safe_id}"
            worktree_path = f"/workspace/worktree-{safe_id}"
            branch_name = f"sandbox/{safe_id}"

            self._manager.provision_pod(
                pod_name=pod_name,
                pvc_name=pvc_name,
                namespace=config.namespace,
                cluster_api=config.cluster_api,
                token=config.cluster_token,
                git_repo_url=config.git_repo_url,
                worktree_path=worktree_path,
                branch_name=branch_name,
                git_token=config.git_token,
                skip_tls_verify=config.skip_tls_verify,
            )

            pods[agent_id] = SandboxPodInfo(
                agent_id=agent_id,
                pod_name=pod_name,
                namespace=config.namespace,
                worktree_path=worktree_path,
                branch_name=branch_name,
                status="ready",
            )

        return SandboxState(
            session_id=run_id,
            pvc_name=pvc_name,
            cluster_api=config.cluster_api,
            namespace=config.namespace,
            git_repo_url=config.git_repo_url,
            pods=pods,
        )

    def teardown_for_session(
        self,
        sandbox_state: SandboxState,
        config: SandboxExecToolConfig,
    ) -> None:
        """Delete all pods tracked in *sandbox_state*.  Does NOT delete PVC."""
        for pod_info in sandbox_state.pods.values():
            try:
                self._manager.teardown_pod(
                    pod_name=pod_info.pod_name,
                    namespace=config.namespace,
                    cluster_api=config.cluster_api,
                    token=config.cluster_token,
                    skip_tls_verify=config.skip_tls_verify,
                )
            except Exception:
                logger.exception("Failed to tear down pod %s", pod_info.pod_name)

    def teardown_by_naming(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
    ) -> None:
        """Fallback teardown using deterministic naming (crash recovery)."""
        for agent_id in agent_ids:
            pod_name = f"sandbox-{run_id[:8]}-{k8s_safe_name(agent_id)}"
            try:
                self._manager.teardown_pod(
                    pod_name=pod_name,
                    namespace=config.namespace,
                    cluster_api=config.cluster_api,
                    token=config.cluster_token,
                    skip_tls_verify=config.skip_tls_verify,
                )
            except Exception:
                logger.exception("Failed to tear down pod %s (naming fallback)", pod_name)

    def health_check(
        self,
        sandbox_state: SandboxState,
        config: SandboxExecToolConfig,
    ) -> Dict[str, bool]:
        """Per-agent pod health check."""
        results: Dict[str, bool] = {}
        for agent_id, pod_info in sandbox_state.pods.items():
            try:
                results[agent_id] = self._manager.is_pod_alive(
                    pod_name=pod_info.pod_name,
                    namespace=config.namespace,
                    cluster_api=config.cluster_api,
                    token=config.cluster_token,
                    skip_tls_verify=config.skip_tls_verify,
                )
            except Exception:
                logger.exception("Health check failed for pod %s", pod_info.pod_name)
                results[agent_id] = False
        return results

    def _cleanup_orphan_pods(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
    ) -> None:
        """Delete any pods from a prior crashed run that share our deterministic names."""
        for agent_id in agent_ids:
            pod_name = f"sandbox-{run_id[:8]}-{k8s_safe_name(agent_id)}"
            try:
                self._manager.teardown_pod(
                    pod_name=pod_name,
                    namespace=config.namespace,
                    cluster_api=config.cluster_api,
                    token=config.cluster_token,
                    skip_tls_verify=config.skip_tls_verify,
                )
            except Exception:
                pass
