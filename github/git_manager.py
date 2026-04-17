"""
github/git_manager.py

GitHub Automation Engine — production-grade repo management.
- Branch-based updates (never direct main commits)
- Pull request creation with validation proof
- Auto-merge ONLY after validation + benchmark pass
- Semantic commit messages
- Version tagging and changelog generation
- Rollback on failure
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request as urequest, error as uerror

from utils.logger import get_logger


class GitManager:
    """
    Production GitHub automation manager.

    Key design decisions:
    - All improvements go to feature branches, not main
    - PRs are created with validation evidence attached
    - Auto-merge only when: tests pass + no regression + security clear
    - Every operation is logged and idempotent where possible
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, config: Dict[str, Any] = None, dry_run: bool = False):
        self.config    = config or {}
        self.dry_run   = dry_run
        self.logger    = get_logger("GitManager")
        self.token     = os.environ.get("GITHUB_ACCESS_TOKEN", "")
        self.repo      = self.config.get("repo", os.environ.get("GITHUB_REPO", ""))
        self.base_branch = self.config.get("branch", "main")

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept":        "application/vnd.github+json",
            "Content-Type":  "application/json",
        }

    # ── Core File Operations ───────────────────────────────────────

    def commit_file(
        self,
        file_path: str,
        content:   str,
        message:   str,
        branch:    str = None,
    ) -> bool:
        """
        Create or update a file on a specified branch.

        Args:
            file_path: Repo-relative path
            content:   File content as string
            message:   Semantic commit message
            branch:    Target branch (default: base_branch)

        Returns:
            True on success
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] commit_file: {file_path} | {message}")
            return True
        if not self._check_configured():
            return False

        branch    = branch or self.base_branch
        encoded   = base64.b64encode(content.encode()).decode()
        sha       = self._get_file_sha(file_path, branch)
        payload   = {"message": message, "content": encoded, "branch": branch}
        if sha:
            payload["sha"] = sha

        try:
            resp = self._request(
                "PUT",
                f"/repos/{self.repo}/contents/{file_path}",
                payload,
            )
            sha_short = resp["commit"]["sha"][:10]
            self.logger.info(f"Committed [{sha_short}] {file_path} → {branch}")
            return True
        except Exception as exc:
            self.logger.error(f"commit_file failed for {file_path}: {exc}")
            return False

    # ── Branch Management ──────────────────────────────────────────

    def create_branch(self, branch_name: str, from_branch: str = None) -> bool:
        """Create a new branch from the specified base."""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] create_branch: {branch_name}")
            return True

        from_branch = from_branch or self.base_branch
        try:
            ref_data = self._request("GET", f"/repos/{self.repo}/git/ref/heads/{from_branch}")
            sha      = ref_data["object"]["sha"]
            self._request("POST", f"/repos/{self.repo}/git/refs", {
                "ref": f"refs/heads/{branch_name}",
                "sha": sha,
            })
            self.logger.info(f"Branch created: {branch_name} from {from_branch}")
            return True
        except Exception as exc:
            self.logger.error(f"create_branch failed: {exc}")
            return False

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists in the remote repo."""
        try:
            self._request("GET", f"/repos/{self.repo}/git/ref/heads/{branch_name}")
            return True
        except Exception:
            return False

    # ── Pull Requests ──────────────────────────────────────────────

    def create_pull_request(
        self,
        title:      str,
        body:       str,
        head:       str,
        base:       str = None,
        labels:     List[str] = None,
    ) -> Optional[Dict]:
        """
        Create a pull request with validation evidence in the body.

        Args:
            title:  PR title
            body:   PR description (include validation proof)
            head:   Source branch
            base:   Target branch (default: main)
            labels: GitHub labels to apply

        Returns:
            PR data dict or None on failure
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] PR: {title} | {head} → {base or self.base_branch}")
            return {"number": 0, "html_url": "dry_run"}

        base = base or self.base_branch
        try:
            pr = self._request("POST", f"/repos/{self.repo}/pulls", {
                "title": title,
                "body":  body,
                "head":  head,
                "base":  base,
            })
            self.logger.info(f"PR #{pr['number']} created: {pr['html_url']}")
            return pr
        except Exception as exc:
            self.logger.error(f"create_pull_request failed: {exc}")
            return None

    def merge_pull_request(
        self,
        pr_number: int,
        commit_msg: str = None,
        method:     str = "squash",
    ) -> bool:
        """
        Merge a pull request. Only called after full validation pass.

        Args:
            pr_number:  GitHub PR number
            commit_msg: Merge commit message
            method:     merge | squash | rebase (default: squash)
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] merge PR #{pr_number}")
            return True

        try:
            self._request("PUT", f"/repos/{self.repo}/pulls/{pr_number}/merge", {
                "commit_title":   commit_msg or f"merge: PR #{pr_number}",
                "merge_method":   method,
            })
            self.logger.info(f"PR #{pr_number} merged via {method}")
            return True
        except Exception as exc:
            self.logger.error(f"merge_pull_request failed: {exc}")
            return False

    # ── Tags & Releases ────────────────────────────────────────────

    def create_tag(self, tag: str, message: str, branch: str = None) -> bool:
        """Create a release tag on the latest commit of branch."""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] tag: {tag}")
            return True

        branch = branch or self.base_branch
        try:
            ref  = self._request("GET", f"/repos/{self.repo}/git/ref/heads/{branch}")
            sha  = ref["object"]["sha"]
            self._request("POST", f"/repos/{self.repo}/git/refs", {
                "ref": f"refs/tags/{tag}",
                "sha": sha,
            })
            self.logger.info(f"Tag created: {tag} @ {sha[:10]}")
            return True
        except Exception as exc:
            self.logger.error(f"create_tag failed: {exc}")
            return False

    def generate_changelog(self, from_tag: str = None, n_commits: int = 20) -> str:
        """Generate a changelog from recent commits."""
        try:
            url = f"/repos/{self.repo}/commits?per_page={n_commits}&sha={self.base_branch}"
            commits = self._request("GET", url)
            lines   = [f"## Changelog — {datetime.utcnow().strftime('%Y-%m-%d')}\n"]
            for c in commits:
                msg = c["commit"]["message"].split("\n")[0][:80]
                sha = c["sha"][:8]
                lines.append(f"- [{sha}] {msg}")
            return "\n".join(lines)
        except Exception as exc:
            self.logger.error(f"generate_changelog failed: {exc}")
            return ""

    # ── Rollback ───────────────────────────────────────────────────

    def rollback_to_commit(self, sha: str, branch: str = None) -> bool:
        """
        Force-reset a branch to a specific commit (rollback mechanism).

        WARNING: This is a destructive force-push. Use only for emergency rollback.
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] rollback to {sha[:10]}")
            return True

        branch = branch or self.base_branch
        try:
            self._request("PATCH", f"/repos/{self.repo}/git/refs/heads/{branch}", {
                "sha":   sha,
                "force": True,
            })
            self.logger.warning(f"ROLLBACK: {branch} reset to {sha[:10]}")
            return True
        except Exception as exc:
            self.logger.error(f"rollback failed: {exc}")
            return False

    def get_commit_history(self, n: int = 10, branch: str = None) -> List[Dict]:
        """Retrieve last N commits from the repo."""
        branch = branch or self.base_branch
        try:
            commits = self._request(
                "GET", f"/repos/{self.repo}/commits?per_page={n}&sha={branch}"
            )
            return [
                {
                    "sha":     c["sha"][:10],
                    "message": c["commit"]["message"].split("\n")[0][:80],
                    "date":    c["commit"]["author"]["date"],
                    "author":  c["commit"]["author"]["name"],
                }
                for c in commits
            ]
        except Exception as exc:
            self.logger.error(f"get_commit_history failed: {exc}")
            return []

    # ── Low-level HTTP ─────────────────────────────────────────────

    def _request(self, method: str, path: str, body: Dict = None) -> Any:
        """Make an authenticated GitHub API request."""
        url  = self.BASE_URL + path
        data = json.dumps(body).encode() if body else None
        req  = urequest.Request(url, data=data, headers=self._headers, method=method)
        try:
            with urequest.urlopen(req) as r:
                resp_body = r.read()
                return json.loads(resp_body) if resp_body else {}
        except uerror.HTTPError as e:
            raise RuntimeError(f"GitHub API {method} {path} failed [{e.code}]: "
                               f"{e.read().decode()[:200]}")

    def _get_file_sha(self, file_path: str, branch: str) -> Optional[str]:
        """Get current SHA of a file for updates."""
        try:
            data = self._request("GET",
                f"/repos/{self.repo}/contents/{file_path}?ref={branch}")
            return data.get("sha")
        except Exception:
            return None

    def _check_configured(self) -> bool:
        if not self.token or not self.repo:
            self.logger.warning("GITHUB_ACCESS_TOKEN or GITHUB_REPO not set.")
            return False
        return True
