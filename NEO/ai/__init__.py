"""
ai/__init__.py

NEO AI OS - AI Module Initializer

Responsibilities:
- Initialize all AI submodules
- Provide unified access to AI components
- Ensure proper module loading order
- Export global AI instances

"""

from __future__ import annotations

import logging

# Import all AI modules
from ai.nlp import GlobalNLPProcessor
from ai.reasoning_engine import GlobalReasoningEngine
from ai.planner import GlobalPlanner
from ai.learning import GlobalLearningEngine
from ai.response_generator import GlobalResponseGenerator


class AIManager:
    """
    Central AI Manager to access all AI modules.
    """

    def __init__(self):
        self.logger = logging.getLogger("NEO.AI")

        self.nlp = GlobalNLPProcessor
        self.reasoning = GlobalReasoningEngine
        self.planner = GlobalPlanner
        self.learning = GlobalLearningEngine
        self.response = GlobalResponseGenerator

        self.logger.info("AI Manager initialized")

    def process(self, text: str):
        """
        Full AI pipeline:
        text -> NLP -> reasoning -> planning -> response
        """
        try:
            nlp_data = self.nlp.process(text)

            reasoning = self.reasoning.analyze(nlp_data)

            plan = self.planner.create_plan(reasoning)

            response = self.response.generate({
                "intent": reasoning.get("intent"),
                "entities": nlp_data.get("entities", {}),
            })

            return {
                "nlp": nlp_data,
                "reasoning": reasoning,
                "plan": plan,
                "response": response,
            }

        except Exception as e:
            self.logger.error(f"AI pipeline error: {e}")
            return {
                "error": str(e)
            }


# =========================
# GLOBAL INSTANCE
# =========================

GlobalAI = AIManager()