"""
devops/docker_manager.py

NEO AI OS - Docker Manager

Responsibilities:
- Manage Docker containers, images, volumes
- Start/Stop/Restart containers
- Pull/Build images
- Monitor container stats
- Emit events to EventBus

Features:
- Uses Docker CLI via subprocess
- Async + Sync support
- Thread-safe operations
- Retry & timeout handling
- Metrics tracking
"""

from __future__ import annotations

import subprocess
import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, Optional, List

from core.event_bus import GlobalEventBus, Event


class DockerManagerError(Exception):
    """Docker manager exception"""
    pass


class DockerManager:
    """
    Docker control system.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        # Metrics
        self.total_commands: int = 0
        self.total_errors: int = 0

        self.logger = logging.getLogger("NEO.DockerManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Docker] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("devops.docker.run", self._on_run, priority=9)
        self.event_bus.subscribe("devops.docker.stop", self._on_stop, priority=9)
        self.event_bus.subscribe("devops.docker.pull", self._on_pull, priority=9)

    # =========================
    # Core Runner
    # =========================

    def _run(self, cmd: str, timeout: int = 60) -> str:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )

            self._inc_command()

            if result.returncode != 0:
                raise DockerManagerError(result.stderr.strip())

            return result.stdout.strip()

        except Exception as e:
            self._inc_error()
            self._error("run", e)
            return ""

    # =========================
    # Container Operations
    # =========================

    def run_container(self, image: str, name: Optional[str] = None) -> str:
        cmd = f"docker run -d {image}"
        if name:
            cmd = f"docker run -d --name {name} {image}"

        return self._run(cmd)

    def stop_container(self, container: str):
        return self._run(f"docker stop {container}")

    def remove_container(self, container: str):
        return self._run(f"docker rm {container}")

    def list_containers(self) -> str:
        return self._run("docker ps -a")

    # =========================
    # Image Operations
    # =========================

    def pull_image(self, image: str):
        return self._run(f"docker pull {image}")

    def build_image(self, path: str, tag: str):
        return self._run(f"docker build -t {tag} {path}")

    def list_images(self):
        return self._run("docker images")

    # =========================
    # Stats
    # =========================

    def stats(self) -> str:
        return self._run("docker stats --no-stream")

    # =========================
    # Metrics
    # =========================

    def _inc_command(self):
        with self._lock:
            self.total_commands += 1

    def _inc_error(self):
        with self._lock:
            self.total_errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "commands": self.total_commands,
                "errors": self.total_errors,
            }

    # =========================
    # Event Handlers
    # =========================

    def _on_run(self, event: Event):
        try:
            image = event.data.get("image")
            name = event.data.get("name")

            result = self.run_container(image, name)

            self._emit("devops.docker.result", {"result": result})

        except Exception as e:
            self._error("event_run", e)

    def _on_stop(self, event: Event):
        try:
            container = event.data.get("container")
            result = self.stop_container(container)

            self._emit("devops.docker.result", {"result": result})

        except Exception as e:
            self._error("event_stop", e)

    def _on_pull(self, event: Event):
        try:
            image = event.data.get("image")
            result = self.pull_image(image)

            self._emit("devops.docker.result", {"result": result})

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
                "system.error.docker",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def run_container_async(self, image: str, name: Optional[str] = None):
        return await asyncio.to_thread(self.run_container, image, name)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalDockerManager = DockerManager()