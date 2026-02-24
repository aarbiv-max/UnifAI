"""
Shared Kubernetes/OpenShift helpers for backup scripts.
Callers read env (e.g. CLUSTER, NAMESPACE, API_URL, ACCESS_TOKEN, SKIP_VERIFY_TLS) and pass values as arguments.
"""
import os
import json
import tempfile
from contextlib import contextmanager
from kubernetes import client, config
from kubernetes.stream import stream


def setup_k8s_connection(
    cluster: str,
    namespace: str,
    api_url: str,
    access_token: str,
    skip_verify_tls: bool,
):
    """
    Set up Kubernetes connection from explicit config.
    Returns (CoreV1Api, kubeconfig_path). Caller or k8s_connection() must clean up the temp file.
    """
    kube_config = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{
            "name": cluster,
            "cluster": {
                "server": api_url,
                "insecure-skip-tls-verify": skip_verify_tls
            }
        }],
        "users": [{
            "name": cluster,
            "user": {"token": access_token}
        }],
        "contexts": [{
            "name": cluster,
            "context": {
                "cluster": cluster,
                "user": cluster,
                "namespace": namespace
            }
        }],
        "current-context": cluster
    }
    fd, kubeconfig_path = tempfile.mkstemp(suffix='.kubeconfig')
    with os.fdopen(fd, 'w') as f:
        json.dump(kube_config, f)
    os.environ['KUBECONFIG'] = kubeconfig_path
    config.load_kube_config(kubeconfig_path)
    print(f"✓ Connected to {cluster}")
    return client.CoreV1Api(), kubeconfig_path


def check_k8s_connection(v1: client.CoreV1Api, namespace: str):
    """Verify connection by listing pods and deployments in the given namespace."""
    apps_v1 = client.AppsV1Api()
    print("Checking pods and deployments...")
    pods = v1.list_namespaced_pod(namespace=namespace)
    deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
    print(f"Found {len(pods.items)} pods and {len(deployments.items)} deployments")
    return True


def run_cmd_on_pod(pod_name: str, namespace: str, command: list):
    """Execute a command in the pod via exec. Returns the stream result."""
    v1 = client.CoreV1Api()
    return stream(
        v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False
    )


@contextmanager
def k8s_connection(
    cluster: str,
    namespace: str,
    api_url: str,
    access_token: str,
    skip_verify_tls: bool,
):
    """
    Context manager: sets up K8s connection with the given config, yields CoreV1Api,
    then removes the temp kubeconfig.
    """
    v1, kubeconfig_path = setup_k8s_connection(
        cluster, namespace, api_url, access_token, skip_verify_tls
    )
    try:
        yield v1
    finally:
        try:
            os.unlink(kubeconfig_path)
        except OSError:
            pass
