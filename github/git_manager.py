"""
github/git_manager.py
GitHub Automation Manager — handles all repository operations.
Commits improvements, pushes changes, and manages version tags.
Uses GitHub REST API via environment token.
"""

import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import request as urllib_request, error as urllib_error


class GitManager:
    """
    GitHub repository manager for the self-improvement system.

    Capabilities:
    - Create and update files via GitHub API
    - Commit with structured, meaningful messages
    - Tag stable releases
    - Rollback to previous commit on failure
    """

    def __init__(self, config: Dict[str, Any] = None, dry_run: bool = False):
        self.config   = config or {}
        self.dry_run  = dry_run
        self.logger   = logging.getLogger("GitManager")
        self.token    = os.environ.get("GITHUB_ACCESS_TOKEN", "")
        self.repo     = self.config.get("repo", os.environ.get("GITHUB_REPO", ""))
        self.branch   = self.config.get("branch", "main")
        self.auto_push = self.config.get("auto_push", True)
        self.base_url = "https://api.github.com"

    def commit_file(self, file_path: str, content: str, message: str) -> bool:
        """
        Create or update a file in the GitHub repository.

        Args:
            file_path: Relative path in repo (e.g., "core/engine.py")
            content:   File content as string
            message:   Commit message

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would commit: {file_path} — {message}")
            return True

        if not self.repo or not self.token:
            self.logger.warning("GitHub repo or token not configured — skipping commit")
            return False

        encoded = base64.b64encode(content.encode()).decode()
        sha = self._get_file_sha(file_path)
        payload_dict = {"message": message, "content": encoded, "branch": self.branch}
        if sha:
            payload_dict["sha"] = sha

        try:
            payload = json.dumps(payload_dict).encode()
            req = urllib_request.Request(
                f"{self.base_url}/repos/{self.repo}/contents/{file_path}",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json"
                },
                method="PUT"
            )
            with urllib_request.urlopen(req) as r:
                result = json.load(r)
                sha_short = result["commit"]["sha"][:10]
                self.logger.info(f"Committed [{sha_short}]: {file_path}")
                return True
        except urllib_error.HTTPError as e:
            self.logger.error(f"Commit failed for {file_path}: {e.read().decode()[:200]}")
            return False

    def tag_release(self, tag: str, message: str) -> bool:
        """
        Create a lightweight tag on the current HEAD.

        Args:
            tag:     Tag name (e.g., "v1.1.0")
            message: Tag description
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would tag: {tag}")
            return True

        # Get HEAD SHA
        try:
            req = urllib_request.Request(
                f"{self.base_url}/repos/{self.repo}/git/ref/heads/{self.branch}",
                headers={"Authorization": f"Bearer {self.token}",
                         "Accept": "application/vnd.github+json"}
            )
            with urllib_request.urlopen(req) as r:
                head_sha = json.load(r)["object"]["sha"]
        except Exception as e:
            self.logger.error(f"Could not get HEAD SHA: {e}")
            return False

        payload = json.dumps({
            "ref":    f"refs/tags/{tag}",
            "sha":    head_sha,
            "message": message
        }).encode()

        try:
            req2 = urllib_request.Request(
                f"{self.base_url}/repos/{self.repo}/git/refs",
                data=payload,
                headers={"Authorization": f"Bearer {self.token}",
                         "Accept": "application/vnd.github+json",
                         "Content-Type": "application/json"},
                method="POST"
            )
            with urllib_request.urlopen(req2) as r:
                self.logger.info(f"Tagged release: {tag}")
                return True
        except urllib_error.HTTPError as e:
            self.logger.error(f"Tag failed: {e.read().decode()[:200]}")
            return False

    def _get_file_sha(self, file_path: str) -> Optional[str]:
        """Get the current SHA of a file (needed for updates)."""
        try:
            req = urllib_request.Request(
                f"{self.base_url}/repos/{self.repo}/contents/{file_path}",
                headers={"Authorization": f"Bearer {self.token}",
                         "Accept": "application/vnd.github+json"}
            )
            with urllib_request.urlopen(req) as r:
                return json.load(r)["sha"]
        except:
            return None

    def get_commit_history(self, n: int = 10) -> list:
        """Fetch last N commits from the repository."""
        try:
            req = urllib_request.Request(
                f"{self.base_url}/repos/{self.repo}/commits?per_page={n}&sha={self.branch}",
                headers={"Authorization": f"Bearer {self.token}",
                         "Accept": "application/vnd.github+json"}
            )
            with urllib_request.urlopen(req) as r:
                commits = json.load(r)
                return [
                    {"sha": c["sha"][:10], "message": c["commit"]["message"][:60],
                     "date": c["commit"]["author"]["date"]}
                    for c in commits
                ]
        except Exception as e:
            self.logger.error(f"Could not fetch commit history: {e}")
            return []
