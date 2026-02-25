"""
Upload backup files to GitLab. Generic entry point for any backup workflow.
All paths, globs, and commit message are driven by env (or could be passed as args).
No references to a specific DB type.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitlab_upload_utils


def _env(key: str, default: str = None):
    v = os.getenv(key, default)
    return v.strip() if isinstance(v, str) else v


def _build_commit_message(base: str = "uploading backup to gitlab", label: str = None) -> str:
    if label:
        return f"{base} ({label})"
    return base


if __name__ == "__main__":
    backup_repo = _env("BACKUP_REPO") or _env("BACKUP_REPO_URL")
    backup_repo_name = _env("BACKUP_REPO_NAME")
    backup_search_dir = _env("BACKUP_SEARCH_DIR") or "/tmp"
    backup_file_glob = _env("BACKUP_FILE_GLOB")
    backup_label = _env("BACKUP_LABEL") or _env("ENVIRONMENT")
    backup_dir_source = _env("BACKUP_DIR_SOURCE")
    backup_dir_dest = _env("BACKUP_DIR_DEST")

    for var, name in [
        (backup_repo, "BACKUP_REPO or BACKUP_REPO_URL"),
        (backup_repo_name, "BACKUP_REPO_NAME"),
    ]:
        if not var:
            raise SystemExit(f"Missing required env: {name}")

    file_sources = []
    if backup_file_glob:
        file_sources = [(backup_search_dir, backup_file_glob)]

    dir_sources = []
    if backup_dir_source and backup_dir_dest:
        dir_sources = [(backup_dir_source, backup_dir_dest)]

    if not file_sources and not dir_sources:
        raise SystemExit(
            "At least one of BACKUP_FILE_GLOB or (BACKUP_DIR_SOURCE + BACKUP_DIR_DEST) is required"
        )

    cleanup_files = []
    if backup_file_glob:
        cleanup_files = gitlab_upload_utils.find_backup_files(backup_search_dir, backup_file_glob)

    commit_message = _build_commit_message(label=backup_label)

    gitlab_upload_utils.upload_backups_to_gitlab(
        repo_url=backup_repo,
        repo_name=backup_repo_name,
        file_sources=file_sources,
        dir_sources=dir_sources,
        commit_message=commit_message,
        cleanup_file_paths=cleanup_files,
        cleanup_dir_paths=[backup_dir_source] if backup_dir_source else [],
    )
