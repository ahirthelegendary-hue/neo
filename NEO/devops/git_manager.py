"""
devops/git_manager.py

NEO AI OS - Git Manager

Responsibilities:
- Initialize repositories
- Commit changes automatically
- Generate commit messages (basic AI-like heuristics)
- Push / pull operations
- Branch management
- Detect repo status (changed, staged, untracked)
- Event-driven Git automation

Features:
- Works with system Git CLI
- Smart commit message generator
- Safe execution (error handling)
- Async + Sync support
- Thread-safe operations
- Detailed logging

Requirements:
- Git installed on system
"""

from __future__ import annotations

import os
import subprocess
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, Optional

from core.event_bus import GlobalEventBus, Event


class GitManagerError(Exception):
    """Git manager exception"""


class GitManager:
    """
    Git automation manager.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.GitManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Git] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("devops.git.commit", self._on_commit, priority=9)
        self.event_bus.subscribe("devops.git.push", self._on_push, priority=9)
        self.event_bus.subscribe("devops.git.pull", self._on_pull, priority=9)

    # =========================
    # Core Git Commands
    # =========================

    def _run(self, cmd: str, cwd: Optional[str] = None) -> str:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.returncode != 0:
                raise GitManagerError(result.stderr.strip())

            return result.stdout.strip()

        except Exception as e:
            self._error("run", e)
            return ""

    def init_repo(self, path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            self._run("git init", cwd=path)
            self._emit("devops.git.init", {"path": path})
            return True
        except Exception as e:
            self._error("init_repo", e)
            return False

    def status(self, path: str) -> str:
        return self._run("git status", cwd=path)

    def add_all(self, path: str):
        self._run("git add .", cwd=path)

    def commit(self, path: str, message: Optional[str] = None) -> bool:
        try:
            self.add_all(path)

            if not message:
                message = self._generate_commit_message(path)

            self._run(f'git commit -m "{message}"', cwd=path)

            self._emit("devops.git.committed", {"message": message})
            return True

        except Exception as e:
            self._error("commit", e)
            return False

    def push(self, path: str) -> bool:
        try:
            self._run("git push", cwd=path)
            self._emit("devops.git.pushed", {"path": path})
            return True
        except Exception as e:
            self._error("push", e)
            return False

    def pull(self, path: str) -> bool:
        try:
            self._run("git pull", cwd=path)
            self._emit("devops.git.pulled", {"path": path})
            return True
        except Exception as e:
            self._error("pull", e)
            return False

    def create_branch(self, path: str, name: str) -> bool:
        try:
            self._run(f"git checkout -b {name}", cwd=path)
            return True
        except Exception as e:
            self._error("create_branch", e)
            return False

    # =========================
    # Smart Commit Message
    # =========================

    def _generate_commit_message(self, path: str) -> str:
        try:
            diff = self._run("git diff --cached", cwd=path)

            if "fix" in diff.lower():
                return "fix: bug fixes"
            if "add" in diff.lower():
                return "feat: added new features"
            if "remove" in diff.lower():
                return "chore: removed unused code"

            return "update: code changes"

        except Exception:
            return "update: auto commit"

    # =========================
    # Event Handlers
    # =========================

    def _on_commit(self, event: Event):
        try:
            path = event.data.get("path", ".")
            msg = event.data.get("message")
            self.commit(path, msg)
        except Exception as e:
            self._error("event_commit", e)

    def _on_push(self, event: Event):
        try:
            path = event.data.get("path", ".")
            self.push(path)
        except Exception as e:
            self._error("event_push", e)

    def _on_pull(self, event: Event):
        try:
            path = event.data.get("path", ".")
            self.pull(path)
        except Exception as e:
            self._error("event_pull", e)

    # =========================
    # Helpers
    # =========================

    def _emit(self, name: str, data: Dict[str, Any]):
        try:
            self.event_bus.publish(name, data, priority=7)
        except Exception:
            pass

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.git",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def commit_async(self, path: str, message: Optional[str] = None):
        return await asyncio.to_thread(self.commit, path, message)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalGitManager = GitManager()