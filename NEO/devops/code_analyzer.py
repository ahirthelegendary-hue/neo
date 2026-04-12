"""
devops/code_analyzer.py

NEO AI OS - Code Analyzer & DevOps Assistant

Responsibilities:
- Analyze source code for errors, smells, and complexity
- Provide refactoring suggestions
- Detect security issues (secrets, unsafe patterns)
- Generate documentation stubs
- Basic dependency insights
- Emit analysis results via EventBus

Features:
- AST-based static analysis (Python)
- Regex-based multi-language heuristics
- Cyclomatic complexity estimation
- Secret scanning (API keys, tokens)
- Thread-safe
- Async + Sync support
- Event-driven integration

No external dependencies required.
"""

from __future__ import annotations

import ast
import os
import re
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, List, Optional

from core.event_bus import GlobalEventBus, Event


class CodeAnalyzerError(Exception):
    """Code Analyzer exception"""


class CodeAnalyzer:
    """
    Static code analyzer for multiple languages (focus: Python).
    """

    SECRET_PATTERNS = [
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS
        re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API
        re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),  # Stripe
        re.compile(r"-----BEGIN PRIVATE KEY-----"),
        re.compile(r"(?i)password\s*=\s*['\"].+?['\"]"),
        re.compile(r"(?i)api[_-]?key\s*=\s*['\"].+?['\"]"),
        re.compile(r"(?i)token\s*=\s*['\"].+?['\"]"),
    ]

    BAD_PATTERNS = [
        (re.compile(r"eval\("), "Avoid eval() for security reasons."),
        (re.compile(r"exec\("), "Avoid exec() for security reasons."),
        (re.compile(r"subprocess\.Popen\(.*shell=True"), "shell=True can be dangerous."),
    ]

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.CodeAnalyzer")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [CodeAnalyzer] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Events
        self.event_bus.subscribe("devops.analyze.execute", self._on_analyze, priority=9)
        self.event_bus.subscribe("devops.analyze.file", self._on_analyze_file, priority=9)
        self.event_bus.subscribe("devops.analyze.dir", self._on_analyze_dir, priority=9)

    # =========================
    # Public APIs
    # =========================

    def analyze_code(self, code: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze raw code string.
        """
        with self._lock:
            try:
                result: Dict[str, Any] = {
                    "filename": filename,
                    "issues": [],
                    "secrets": [],
                    "complexity": 0,
                    "functions": [],
                    "lines": len(code.splitlines()),
                }

                # Python AST analysis
                if self._is_python(filename, code):
                    result.update(self._analyze_python_ast(code))

                # Heuristics (any language)
                result["issues"].extend(self._scan_bad_patterns(code))
                result["secrets"].extend(self._scan_secrets(code))

                # Suggestions
                result["suggestions"] = self._suggest(result)

                return result

            except Exception as e:
                self._error("analyze_code", e)
                return {}

    def analyze_file(self, path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                raise CodeAnalyzerError(f"File not found: {path}")

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()

            return self.analyze_code(code, filename=path)

        except Exception as e:
            self._error("analyze_file", e)
            return {}

    def analyze_directory(self, directory: str) -> Dict[str, Any]:
        summary = {
            "files": 0,
            "issues": 0,
            "secrets": 0,
            "details": [],
        }

        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith((".py", ".js", ".ts", ".json", ".env", ".yml", ".yaml")):
                        path = os.path.join(root, file)
                        res = self.analyze_file(path)
                        if not res:
                            continue

                        summary["files"] += 1
                        summary["issues"] += len(res.get("issues", []))
                        summary["secrets"] += len(res.get("secrets", []))
                        summary["details"].append(res)

            return summary

        except Exception as e:
            self._error("analyze_directory", e)
            return summary

    # =========================
    # Python AST Analysis
    # =========================

    def _analyze_python_ast(self, code: str) -> Dict[str, Any]:
        result = {
            "functions": [],
            "complexity": 0,
            "ast_issues": [],
        }

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "lineno": node.lineno,
                        "args": len(node.args.args),
                        "complexity": self._calc_complexity(node),
                    }
                    result["functions"].append(func_info)
                    result["complexity"] += func_info["complexity"]

                if isinstance(node, ast.Try):
                    result["ast_issues"].append({
                        "type": "try_block",
                        "message": "Check exception handling granularity.",
                        "lineno": node.lineno,
                    })

        except Exception as e:
            self._error("analyze_python_ast", e)

        return result

    def _calc_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                complexity += 1
        return complexity

    # =========================
    # Heuristics
    # =========================

    def _scan_secrets(self, code: str) -> List[str]:
        findings = []
        for pattern in self.SECRET_PATTERNS:
            for match in pattern.findall(code):
                findings.append(match)
        return findings

    def _scan_bad_patterns(self, code: str) -> List[Dict[str, Any]]:
        issues = []
        for pattern, msg in self.BAD_PATTERNS:
            for m in pattern.finditer(code):
                issues.append({
                    "type": "pattern",
                    "message": msg,
                    "position": m.start(),
                })
        return issues

    def _is_python(self, filename: Optional[str], code: str) -> bool:
        if filename and filename.endswith(".py"):
            return True
        # Heuristic: presence of def/class/import
        return any(k in code for k in ["def ", "class ", "import "])

    # =========================
    # Suggestions
    # =========================

    def _suggest(self, result: Dict[str, Any]) -> List[str]:
        suggestions = []

        if result.get("complexity", 0) > 20:
            suggestions.append("Reduce complexity by splitting functions.")

        if result.get("secrets"):
            suggestions.append("Remove hardcoded secrets and use environment variables.")

        if result.get("issues"):
            suggestions.append("Review flagged patterns for security risks.")

        if not suggestions:
            suggestions.append("Code looks clean. Consider adding tests and documentation.")

        return suggestions

    # =========================
    # Event Handlers
    # =========================

    def _on_analyze(self, event: Event):
        try:
            code = event.data.get("code", "")
            result = self.analyze_code(code)

            self.event_bus.publish(
                "devops.analyze.result",
                {"result": result},
                priority=8,
            )
        except Exception as e:
            self._error("event_analyze", e)

    def _on_analyze_file(self, event: Event):
        try:
            path = event.data.get("path")
            result = self.analyze_file(path)

            self.event_bus.publish(
                "devops.analyze.file.result",
                {"result": result},
                priority=8,
            )
        except Exception as e:
            self._error("event_analyze_file", e)

    def _on_analyze_dir(self, event: Event):
        try:
            path = event.data.get("path")
            result = self.analyze_directory(path)

            self.event_bus.publish(
                "devops.analyze.dir.result",
                {"result": result},
                priority=8,
            )
        except Exception as e:
            self._error("event_analyze_dir", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())
        try:
            self.event_bus.publish(
                "system.error.code_analyzer",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def analyze_code_async(self, code: str):
        return await asyncio.to_thread(self.analyze_code, code)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalCodeAnalyzer = CodeAnalyzer()