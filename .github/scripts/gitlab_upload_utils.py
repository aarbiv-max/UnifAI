"""
Shared GitLab upload helpers for backup scripts.
All configuration is passed as arguments (no env reads here).
"""
import os
import shutil
import sys
import glob
from git import Repo
from git.remote import RemoteProgress


class GitProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=""):
        print(f"Git progress: {message} {cur_count}/{max_count if max_count else '?'}")


def find_backup_files(search_dir: str, pattern: str) -> list:
    """
    Find files under search_dir matching pattern (e.g. "mongo_backup*" or "postgres_backup_*.sql.gz").
    Returns list of absolute paths.
    """
    try:
        full_pattern = os.path.join(search_dir, pattern)
        return glob.glob(full_pattern)
    except Exception as e:
        print(f"Error finding backup files: {e}")
        return []


def upload_backups_to_gitlab(
    repo_url: str,
    repo_name: str,
    file_sources: list,
    dir_sources: list = None,
    git_user_email: str = "github_actions@users.noreply.gitlab.cee.redhat.com",
    git_user_name: str = "github_actions",
    commit_message: str = "uploading backup files to gitlab",
    cleanup_file_paths: list = None,
    cleanup_dir_paths: list = None,
):
    """
    Clone repo, copy backup files/dirs into it, commit and push.

    Args:
        repo_url: Git clone URL (with token if needed).
        repo_name: Local directory name for the clone.
        file_sources: List of (search_dir, glob_pattern). Files matching pattern in search_dir
                      are copied to repo (existing same-name files in repo are replaced).
        dir_sources: List of (source_path, dest_dirname). source_path is copied into repo as dest_dirname.
                     Existing dest_dirname in repo is removed first.
        git_user_email: Git config user.email for the commit.
        git_user_name: Git config user.name for the commit.
        commit_message: Commit message.
        cleanup_file_paths: Optional list of file paths to remove after push (e.g. /tmp backup files).
        cleanup_dir_paths: Optional list of dir paths to remove after push.
    """
    dir_sources = dir_sources or []
    cleanup_file_paths = cleanup_file_paths or []
    cleanup_dir_paths = cleanup_dir_paths or []

    for val, name in [(repo_url, "repo_url"), (repo_name, "repo_name")]:
        if not (val and str(val).strip()):
            raise ValueError(f"Missing or empty required argument: {name}")

    repo_url = repo_url.strip()
    repo_name = repo_name.strip()
    copied_files = []

    try:
        print("Cloning gitlab repo")
        repo = Repo.clone_from(repo_url, repo_name, depth=1, progress=GitProgress())
        print("Cloned gitlab repo")

        # File sources: (search_dir, glob_pattern)
        for search_dir, glob_pattern in file_sources:
            if not search_dir or not glob_pattern:
                continue
            matches = find_backup_files(search_dir, glob_pattern)
            # Remove old files in repo matching the same pattern
            repo_matches = find_backup_files(repo_name, glob_pattern)
            for old in repo_matches:
                print(f"Deleting older backup file: {old}")
                os.remove(old)
            for path in matches:
                print(f"Copying backup file: {path}")
                shutil.copy(path, repo_name)
                copied_files.append(path)

        # Dir sources: (source_path, dest_dirname)
        for source_path, dest_dirname in dir_sources:
            if not source_path or not dest_dirname:
                continue
            if not os.path.isdir(source_path):
                print(f"Skipping missing dir: {source_path}")
                continue
            dest_path = os.path.join(repo_name, dest_dirname)
            if os.path.exists(dest_path):
                print("Removing old directory in repo:", dest_path)
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)
            print("Copied directory to gitlab repo:", dest_path)

        print("Committing changes to gitlab repo")
        with repo.config_writer() as git_config:
            git_config.set_value("user", "email", git_user_email)
            git_config.set_value("user", "name", git_user_name)

        repo.git.add(A=True)
        repo.index.commit(commit_message)
        print("Committed changes")

        origin = repo.remote(name="origin")
        origin.push(progress=GitProgress())
        print("Pushed changes to gitlab repo")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        print("Cleaning up")
        to_remove_files = set(cleanup_file_paths) | set(copied_files)
        for path in to_remove_files:
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError as e:
                    print(f"Could not remove {path}: {e}")
        for path in cleanup_dir_paths:
            if path and os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except OSError as e:
                    print(f"Could not remove {path}: {e}")
        if repo_name and os.path.isdir(repo_name):
            try:
                shutil.rmtree(repo_name)
            except OSError as e:
                print(f"Could not remove repo dir {repo_name}: {e}")
        print("Upload completed")
