
import anthropic
import logging
import json
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS, TEMPERATURE, JARVIS_PERSONA
)
from brain.memory import Memory

logger = logging.getLogger("jarvis.ai")


class Brain:
    """The cognitive core of JARVIS."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._build_system_prompt()
        logger.info("AI Brain online.")


    def _build_system_prompt(self) -> str:
        facts = self.memory.get_all_facts()
        facts_text = "\n".join(f"- {k}: {v}" for k, v in facts.items()) if facts else "None yet."
        now = datetime.now().strftime("%A, %B %d %Y — %H:%M")

        self.system_prompt = f"""{JARVIS_PERSONA}
