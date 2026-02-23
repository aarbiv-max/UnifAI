import os
import subprocess
import json
import tempfile
from datetime import datetime
from kubernetes import client, config
from kubernetes.stream import stream

# Environment variables
MONGO_POD = os.getenv("MONGO_POD")
NAMESPACE = os.getenv("NAMESPACE")
CLUSTER = os.getenv("CLUSTER")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
API_URL = os.getenv("API_URL")
MONGO_URI = os.getenv("MONGO_URI")
VERIFY_TLS = bool(os.getenv("SKIP_VERIFY_TLS"))

def setup_k8s_connection():
    """
    Set up Kubernetes connection using environment variables
    """
    kube_config = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{
            "name": CLUSTER,
            "cluster": {
                "server": API_URL,
                "insecure-skip-tls-verify": VERIFY_TLS
            }
        }],
        "users": [{
            "name": CLUSTER,
            "user": {"token": ACCESS_TOKEN}
        }],
        "contexts": [{
            "name": CLUSTER,
            "context": {
                "cluster": CLUSTER,
                "user": CLUSTER,
                "namespace": NAMESPACE
            }
        }],
        "current-context": CLUSTER
    }
    fd, kubeconfig_path = tempfile.mkstemp(suffix='.kubeconfig')
    with os.fdopen(fd, 'w') as f:
        json.dump(kube_config, f)
    os.environ['KUBECONFIG'] = kubeconfig_path
    config.load_kube_config(kubeconfig_path)
    print(f"✓ Connected to {CLUSTER}")
    return client.CoreV1Api(), kubeconfig_path

def check_k8s_connection(v1: client.CoreV1Api):
    """Verify connection by listing resources"""
    apps_v1 = client.AppsV1Api()
    
    print("Checking pods and deployments...")
    pods = v1.list_namespaced_pod(namespace=NAMESPACE)
    deployments = apps_v1.list_namespaced_deployment(namespace=NAMESPACE)
    
    print(f"Found {len(pods.items)} pods and {len(deployments.items)} deployments")
    return True

def run_cmd_on_pod(pod_name: str, namespace: str, command: list[str]):
    v1 = client.CoreV1Api()
    result = stream(
        v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False
    )
    return result

def copy_backup_from_pod(local_path: str = None):
    """
    Copy the compressed backup file from the pod to local filesystem
    
    Args:
        local_path: Local path to save the backup. If None, generates a timestamped filename

    """
    if local_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        local_path = f"/tmp/mongo_backup_{timestamp}.tar.gz"
    
    print(f"Downloading backup from pod to {local_path}")
    
    # Using kubectl cp command
    pod_spec = f"{NAMESPACE}/{MONGO_POD}:/tmp/backup.tar.gz"
    cmd = ['kubectl', 'cp', pod_spec, local_path, '-n', NAMESPACE, '--retries', '10']
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Failed to copy backup from pod: {result.stderr}")
    
    print(f"✓ Backup downloaded to {local_path}")


def remove_old_backup():
    print("Removing old backup if they exist")
    run_cmd_on_pod(MONGO_POD, NAMESPACE, ["rm", "-rf", "/tmp/backup"])
    run_cmd_on_pod(MONGO_POD, NAMESPACE, ["rm", "-rf", "/tmp/backup.tar.gz"])
    print("Old backup removed")

def test_mongodb_connection():
    print("Testing MongoDB connection")
    run_cmd_on_pod(MONGO_POD, NAMESPACE, ["mongosh", "--eval", "db.version()", "--uri", MONGO_URI])
    print("MongoDB connection test completed")

def backup_mongodb():
    print("Running MongoDB backup")
    run_cmd_on_pod(MONGO_POD, NAMESPACE, ["mongodump", "--uri", MONGO_URI, "--out", "/tmp/backup"])
    print("MongoDB backup completed")

def compress_backup():
    print("Compressing MongoDB backup")
    run_cmd_on_pod(MONGO_POD, NAMESPACE, ["tar", "-czf", "/tmp/backup.tar.gz", "/tmp/backup"])
    print("MongoDB backup compressed")

if __name__ == "__main__":
    # Setup connection
    v1, kubeconfig_path = setup_k8s_connection()
    check_k8s_connection(v1)
    
    # Run backup
    print("Starting MongoDB backup...")
    remove_old_backup()
    test_mongodb_connection()
    backup_mongodb()
    compress_backup()
    copy_backup_from_pod()
    # remove kubeconfig file
    try:
        os.unlink(kubeconfig_path)
    except OSError:
        pass
    print("✓ Backup complete!")