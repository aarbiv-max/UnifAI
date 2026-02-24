"""
Backup PostgreSQL database running on a pod in OpenShift/Kubernetes.
Uses k8s_utils for cluster connection and exec; requires kubectl and pg_dump on the target pod.
"""
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Allow importing k8s_utils when run as .github/scripts/backup_postgres.py from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8s_utils

# Kubernetes / cluster (read once, pass into k8s_utils)
POSTGRES_POD = os.getenv("POSTGRES_POD")
NAMESPACE = os.getenv("NAMESPACE")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
API_URL = os.getenv("API_URL")
SKIP_VERIFY_TLS = bool(os.getenv("SKIP_VERIFY_TLS"))
CLUSTER = os.getenv("CLUSTER")

# PostgreSQL connection (used to build pg_dump command run on the pod)
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGDATABASE = os.getenv("PGDATABASE")

# Paths on the pod
POD_BACKUP_FILE = "/tmp/umami_backup.sql"


def _shell_escape(s: str) -> str:
    """Escape a string for safe use inside single-quoted shell literal."""
    if not s:
        return ""
    return s.replace("'", "'\"'\"'")


def remove_old_backup():
    """Remove previous backup file on the pod."""
    print("Removing old backup on pod if it exists")
    k8s_utils.run_cmd_on_pod(POSTGRES_POD, NAMESPACE, ["rm", "-f", POD_BACKUP_FILE])
    print("Old backup removed")


def test_postgres_connection():
    """Test PostgreSQL connectivity using psql on the pod."""
    print("Testing PostgreSQL connection")
    cmd = (
        f"PGPASSWORD='{_shell_escape(PGPASSWORD)}' psql -h {_shell_escape(PGHOST)} "
        f"-p {PGPORT} -U {_shell_escape(PGUSER)} -d {_shell_escape(PGDATABASE)} -c 'SELECT 1'"
    )
    k8s_utils.run_cmd_on_pod(POSTGRES_POD, NAMESPACE, ["sh", "-c", cmd])
    print("PostgreSQL connection test completed")


def backup_postgres():
    """Run pg_dump on the pod and gzip to a single file."""
    print("Running PostgreSQL backup (pg_dump | gzip)")
    cmd = (
        f"PGPASSWORD='{_shell_escape(PGPASSWORD)}' pg_dump -h {_shell_escape(PGHOST)} "
        f"-p {PGPORT} -U {_shell_escape(PGUSER)} -d {_shell_escape(PGDATABASE)} "
        f"--no-owner --no-acl | gzip > {POD_BACKUP_FILE}"
    )
    k8s_utils.run_cmd_on_pod(POSTGRES_POD, NAMESPACE, ["sh", "-c", cmd])
    print("PostgreSQL backup completed")


def copy_backup_from_pod(local_path: str = None):
    """Copy the compressed backup from the pod to the local filesystem."""
    if local_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        local_path = f"/tmp/postgres_backup_{timestamp}.sql.gz"
    print(f"Downloading backup from pod to {local_path}")
    pod_spec = f"{NAMESPACE}/{POSTGRES_POD}:{POD_BACKUP_FILE}"
    result = subprocess.run(
        ["kubectl", "cp", pod_spec, local_path, "-n", NAMESPACE, "--retries", "10"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Failed to copy backup from pod: {result.stderr}")
    print(f"✓ Backup downloaded to {local_path}")


if __name__ == "__main__":
    for var, name in [
        (POSTGRES_POD, "POSTGRES_POD"),
        (NAMESPACE, "NAMESPACE"),
        (API_URL, "API_URL"),
        (ACCESS_TOKEN, "ACCESS_TOKEN"),
        (PGUSER, "PGUSER"),
        (PGPASSWORD, "PGPASSWORD"),
        (PGDATABASE, "PGDATABASE"),
    ]:
        if not var:
            raise SystemExit(f"Missing required env: {name}")

    with k8s_utils.k8s_connection(
         CLUSTER, NAMESPACE, API_URL, ACCESS_TOKEN, SKIP_VERIFY_TLS
    ) as v1:
        k8s_utils.check_k8s_connection(v1, NAMESPACE)

        print("Starting PostgreSQL backup...")
        remove_old_backup()
        test_postgres_connection()
        backup_postgres()
        copy_backup_from_pod()

    print("✓ Backup complete!")
