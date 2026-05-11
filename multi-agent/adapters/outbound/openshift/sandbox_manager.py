"""OpenShift adapter for SandboxManagerPort.

Uses the ``openshift-client`` library (same as OcExecTool) to manage
sandbox pods and PVCs on a user-provided cluster.
"""
import json
import logging
import shlex
import time
from contextlib import contextmanager
from typing import Generator, Optional

import openshift_client as oc

from mas.elements.tools.sandbox_exec.ports import SandboxManagerPort

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "images.paas.redhat.com/unifai/sandbox"
PVC_SIZE = "2Gi"
POD_RESOURCES = {
    "requests": {"cpu": "500m", "memory": "512Mi"},
    "limits": {"cpu": "2", "memory": "2Gi"},
}
_POD_READY_TIMEOUT_S = 120
_POD_POLL_INTERVAL_S = 3


class OpenShiftSandboxManager(SandboxManagerPort):
    """Implements SandboxManagerPort using the openshift-client library."""

    @staticmethod
    @contextmanager
    def _oc_ctx(
        cluster_api: str, token: str, skip_tls_verify: bool = False
    ) -> Generator[None, None, None]:
        with oc.api_server(cluster_api):
            with oc.token(token):
                with oc.tls_verify(enable=not skip_tls_verify):
                    yield

    def provision_pvc(
        self,
        pvc_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool = False,
    ) -> None:
        pvc_manifest = json.dumps({
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": pvc_name, "namespace": namespace},
            "spec": {
                "accessModes": ["ReadWriteMany"],
                "resources": {"requests": {"storage": PVC_SIZE}},
            },
        })
        with self._oc_ctx(cluster_api, token, skip_tls_verify):
            oc.invoke("apply", ["-f", "-", "-n", namespace], cmd_input=pvc_manifest)
        logger.info("PVC %s ensured in namespace %s", pvc_name, namespace)

    def provision_pod(
        self,
        pod_name: str,
        pvc_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        git_repo_url: str,
        worktree_path: str,
        branch_name: str,
        git_token: str = "",
        skip_tls_verify: bool = False,
    ) -> None:
        pod_manifest = json.dumps({
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": pod_name, "namespace": namespace},
            "spec": {
                "containers": [{
                    "name": "sandbox",
                    "image": SANDBOX_IMAGE,
                    "command": ["sleep", "infinity"],
                    "resources": POD_RESOURCES,
                    "volumeMounts": [{"name": "workspace", "mountPath": "/workspace"}],
                    "workingDir": "/workspace",
                }],
                "volumes": [{
                    "name": "workspace",
                    "persistentVolumeClaim": {"claimName": pvc_name},
                }],
                "restartPolicy": "Never",
            },
        })

        with self._oc_ctx(cluster_api, token, skip_tls_verify):
            oc.invoke("apply", ["-f", "-", "-n", namespace], cmd_input=pod_manifest)

        self._wait_for_pod_ready(pod_name, namespace, cluster_api, token, skip_tls_verify)
        self._setup_git_worktree(
            pod_name, namespace, cluster_api, token,
            git_repo_url, worktree_path, branch_name,
            git_token, skip_tls_verify,
        )
        logger.info("Pod %s ready with worktree at %s", pod_name, worktree_path)

    def execute(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        cmd: str,
        workdir: Optional[str] = None,
        skip_tls_verify: bool = False,
    ) -> str:
        exec_args = ["exec", pod_name, "-n", namespace, "--"]
        if workdir:
            exec_args.extend(["bash", "-c", f"cd {shlex.quote(workdir)} && {cmd}"])
        else:
            exec_args.extend(["bash", "-c", cmd])

        with self._oc_ctx(cluster_api, token, skip_tls_verify):
            result = oc.invoke("exec", exec_args[1:])

        stdout = (result.out() or "").strip()
        stderr = (result.err() or "").strip()
        if stdout and stderr:
            return f"{stdout}\nstderr: {stderr}"
        return stdout or stderr or f"(no output, exit code: {result.status()})"

    def teardown_pod(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool = False,
    ) -> None:
        with self._oc_ctx(cluster_api, token, skip_tls_verify):
            oc.invoke("delete", ["pod", pod_name, "-n", namespace, "--ignore-not-found"])
        logger.info("Pod %s deleted (or not found)", pod_name)

    def is_pod_alive(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool = False,
    ) -> bool:
        with self._oc_ctx(cluster_api, token, skip_tls_verify):
            result = oc.invoke(
                "get", ["pod", pod_name, "-n", namespace,
                        "-o", "jsonpath={.status.phase}"]
            )
        return (result.out() or "").strip() == "Running"

    def _wait_for_pod_ready(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool,
    ) -> None:
        deadline = time.monotonic() + _POD_READY_TIMEOUT_S
        while time.monotonic() < deadline:
            if self.is_pod_alive(pod_name, namespace, cluster_api, token, skip_tls_verify):
                return
            time.sleep(_POD_POLL_INTERVAL_S)
        raise TimeoutError(f"Pod {pod_name} not Running after {_POD_READY_TIMEOUT_S}s")

    def _setup_git_worktree(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        git_repo_url: str,
        worktree_path: str,
        branch_name: str,
        git_token: str,
        skip_tls_verify: bool,
    ) -> None:
        """Clone bare repo (if missing) and create a git worktree."""
        if git_token:
            clone_url = git_repo_url.replace("https://", f"https://{git_token}@")
        else:
            clone_url = git_repo_url

        bare_repo = "/workspace/repo.git"
        clone_cmd = (
            f"if [ ! -d {bare_repo} ]; then "
            f"  git clone --bare {shlex.quote(clone_url)} {bare_repo}; "
            f"fi"
        )
        self.execute(pod_name, namespace, cluster_api, token, clone_cmd,
                     skip_tls_verify=skip_tls_verify)

        worktree_cmd = (
            f"if [ ! -d {shlex.quote(worktree_path)} ]; then "
            f"  cd {bare_repo} && "
            f"  git worktree add {shlex.quote(worktree_path)} "
            f"    -b {shlex.quote(branch_name)} HEAD; "
            f"fi"
        )
        self.execute(pod_name, namespace, cluster_api, token, worktree_cmd,
                     skip_tls_verify=skip_tls_verify)
