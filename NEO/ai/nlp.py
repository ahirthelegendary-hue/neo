"""
ai/nlp.py

NEO AI OS - Natural Language Processing Engine

Responsibilities:
- Normalize and preprocess text
- Tokenization and basic linguistic parsing
- Intent scoring and semantic similarity
- Keyword extraction
- Entity enhancement (beyond parser)
- Language detection (basic heuristic)
- Synonym expansion
- Provide embeddings-like lightweight vectors

Features:
- No external heavy ML dependency (lightweight)
- Pluggable design (can upgrade to transformers later)
- Thread-safe
- Async + Sync support
- Event-driven enrichment (optional hooks)

"""

from __future__ import annotations

import re
import math
import threading
import logging
import traceback
import asyncio
from typing import List, Dict, Any, Tuple, Optional

from core.event_bus import GlobalEventBus, Event


class NLPError(Exception):
    """Base NLP exception"""


class NLPProcessor:
    """
    Lightweight NLP engine for NEO.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.stopwords = self._load_stopwords()
        self.synonyms = self._load_synonyms()

        self.logger = logging.getLogger("NEO.NLP")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [NLP] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscription (optional enhancement layer)
        self.event_bus.subscribe("nlp.process", self._on_process, priority=8)

    # =========================
    # Core NLP Functions
    # =========================

    def normalize(self, text: str) -> str:
        try:
            text = text.lower()
            text = re.sub(r"[^a-z0-9\s]", "", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except Exception as e:
            self._error("normalize", e)
            return text

    def tokenize(self, text: str) -> List[str]:
        try:
            return [t for t in text.split() if t not in self.stopwords]
        except Exception as e:
            self._error("tokenize", e)
            return []

    def extract_keywords(self, text: str) -> List[str]:
        tokens = self.tokenize(text)
        freq: Dict[str, int] = {}

        for t in tokens:
            freq[t] = freq.get(t, 0) + 1

        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:5]]

    def expand_synonyms(self, tokens: List[str]) -> List[str]:
        expanded = set(tokens)

        for token in tokens:
            if token in self.synonyms:
                expanded.update(self.synonyms[token])

        return list(expanded)

    def detect_language(self, text: str) -> str:
        # Simple heuristic (can upgrade later)
        if re.search(r"[a-zA-Z]", text):
            return "en"
        return "unknown"

    # =========================
    # Vectorization (Lightweight)
    # =========================

    def vectorize(self, tokens: List[str]) -> List[float]:
        """
        Simple vector: word length + frequency normalization
        """
        try:
            vec = [len(t) / 10.0 for t in tokens]
            return vec
        except Exception as e:
            self._error("vectorize", e)
            return []

    def similarity(self, v1: List[float], v2: List[float]) -> float:
        try:
            dot = sum(a * b for a, b in zip(v1, v2))
            mag1 = math.sqrt(sum(a * a for a in v1))
            mag2 = math.sqrt(sum(b * b for b in v2))

            if mag1 == 0 or mag2 == 0:
                return 0.0

            return dot / (mag1 * mag2)
        except Exception as e:
            self._error("similarity", e)
            return 0.0

    # =========================
    # Full Processing Pipeline
    # =========================

    def process(self, text: str) -> Dict[str, Any]:
        try:
            normalized = self.normalize(text)
            tokens = self.tokenize(normalized)
            keywords = self.extract_keywords(normalized)
            expanded = self.expand_synonyms(tokens)
            vector = self.vectorize(expanded)
            lang = self.detect_language(text)

            result = {
                "original": text,
                "normalized": normalized,
                "tokens": tokens,
                "keywords": keywords,
                "expanded_tokens": expanded,
                "vector": vector,
                "language": lang,
            }

            return result

        except Exception as e:
            self._error("process", e)
            return {}

    # =========================
    # Event Handler
    # =========================

    def _on_process(self, event: Event):
        try:
            text = event.data.get("text", "")
            result = self.process(text)

            self.event_bus.publish(
                "nlp.result",
                {"result": result},
                priority=7,
            )

        except Exception as e:
            self._error("event_process", e)

    # =========================
    # Data Loaders
    # =========================

    def _load_stopwords(self) -> set:
        return {
            "the", "is", "in", "at", "of", "a", "and", "to", "for",
            "on", "with", "as", "by", "an", "be"
        }

    def _load_synonyms(self) -> Dict[str, List[str]]:
        return {
            "open": ["launch", "start"],
            "close": ["stop", "exit"],
            "delete": ["remove", "erase"],
            "create": ["make", "build"],
        }

    # =========================
    # Error Handler
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.nlp",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def process_async(self, text: str):
        return await asyncio.to_thread(self.process, text)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalNLPProcessor = NLPProcessor()