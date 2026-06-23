
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
        
Current date/time: {now}

Things I know about the user:
{facts_text}

Available commands I can execute for the user (just describe what to do and I will handle it):
- Open applications (browser, music player, code editor, calculator, etc.)
- Search the web
- Tell the time, date, weather (user's location needed)
- Manage tasks and reminders
- Perform system actions (volume, shutdown, sleep)
- Answer questions using my knowledge
- Remember important facts for future sessions

When the user asks me to DO something, I embed one or more JSON action blocks in my response:

APPS & FILES
<action>{{"type": "open_app",    "app": "spotify"}}</action>
<action>{{"type": "close_app",   "app": "chrome"}}</action>
<action>{{"type": "open_file",   "path": "~/Documents/report.pdf"}}</action>
<action>{{"type": "open_folder", "path": "~/Downloads"}}</action>
<action>{{"type": "file_read",   "path": "~/notes.txt"}}</action>
<action>{{"type": "file_write",  "path": "~/output.txt", "content": "Hello", "overwrite": false}}</action>
<action>{{"type": "file_append", "path": "~/log.txt", "content": "new line"}}</action>
<action>{{"type": "file_list",   "path": "~/Documents"}}</action>
<action>{{"type": "file_search", "pattern": "*.pdf", "directory": "~"}}</action>
<action>{{"type": "file_delete", "path": "~/trash/old.txt"}}</action>
<action>{{"type": "file_copy",   "src": "~/a.txt", "dst": "~/b.txt"}}</action>
<action>{{"type": "file_move",   "src": "~/a.txt", "dst": "~/docs/a.txt"}}</action>
<action>{{"type": "file_info",   "path": "~/report.pdf"}}</action>

BROWSER
<action>{{"type": "web_search",  "query": "latest AI news"}}</action>
<action>{{"type": "open_url",    "url": "https://example.com"}}</action>
<action>{{"type": "youtube",     "query": "lofi hip hop"}}</action>
<action>{{"type": "maps",        "location": "Eiffel Tower"}}</action>
<action>{{"type": "wikipedia",   "topic": "quantum computing"}}</action>
<action>{{"type": "translate",   "text": "Hello", "target_lang": "es"}}</action>
<action>{{"type": "github",      "repo": "anthropics/anthropic-sdk-python"}}</action>

SYSTEM
<action>{{"type": "system",      "command": "volume_up"}}</action>
<action>{{"type": "system",      "command": "volume_down"}}</action>
<action>{{"type": "system",      "command": "mute"}}</action>
<action>{{"type": "system",      "command": "unmute"}}</action>
<action>{{"type": "system",      "command": "screenshot"}}</action>
<action>{{"type": "system",      "command": "lock"}}</action>
<action>{{"type": "system",      "command": "sleep"}}</action>
<action>{{"type": "system",      "command": "shutdown"}}</action>
<action>{{"type": "system",      "command": "restart"}}</action>
<action>{{"type": "battery"}}</action>
<action>{{"type": "system_stats"}}</action>
<action>{{"type": "kill_process","name": "chrome"}}</action>
<action>{{"type": "clipboard_get"}}</action>
<action>{{"type": "clipboard_set","text": "some text"}}</action>
<action>{{"type": "shell",       "command": "ls -la ~"}}</action>

WEATHER
<action>{{"type": "weather",   "location": "London"}}</action>
<action>{{"type": "forecast",  "location": "Tokyo", "days": 3}}</action>

REMINDERS
<action>{{"type": "remind_in", "message": "Take a break", "minutes": 30}}</action>
<action>{{"type": "remind_at", "message": "Meeting", "hour": 14, "minute": 30}}</action>
<action>{{"type": "reminder_cancel", "label": "reminder_xyz"}}</action>
<action>{{"type": "reminder_list"}}</action>

MEMORY & TASKS
<action>{{"type": "remember",      "key": "user_name", "value": "Tony"}}</action>
<action>{{"type": "forget",        "key": "old_fact"}}</action>
<action>{{"type": "task_add",      "description": "Review project specs"}}</action>
<action>{{"type": "task_complete", "id": 3}}</action>
<action>{{"type": "task_list"}}</action>

Multiple actions can appear in one response. Place them inline where natural. After an action that
returns data (weather, file_read, battery, system_stats, etc.), incorporate the result into your
spoken reply — the result will be injected where {{{{result}}}} appears if you use that placeholder.

Otherwise respond conversationally as JARVIS."""
        return self.system_prompt

    def think(self, user_input: str, session_id: str = "default") -> tuple[str, list[dict]]:
        """
        Process user input and return (text_response, list_of_actions).
        Actions are parsed from <action>…</action> tags in the response.
        """
    
        self._build_system_prompt()

    
        messages = self.memory.get_context(session_id)
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                system=self.system_prompt,
                messages=messages,
            )
            raw = response.content[0].text
        except anthropic.AuthenticationError:
            raw = "I'm afraid my neural pathways are misconfigured, Sir. The API key appears to be invalid."
        except anthropic.RateLimitError:
            raw = "My processing cores are momentarily overwhelmed, Sir. Please try again in a moment."
        except Exception as e:
            logger.error(f"API error: {e}")
            raw = f"I've encountered an unexpected error, Sir: {str(e)[:100]}"

    
        actions = self._parse_actions(raw)
        clean_text = self._strip_action_tags(raw)

        # Persist to memory
        self.memory.add_message("user", user_input, session_id)
        self.memory.add_message("assistant", clean_text, session_id)

        return clean_text, actions


    def _parse_actions(self, text: str) -> list[dict]:
        import re
        actions = []
        for match in re.finditer(r"<action>(.*?)</action>", text, re.DOTALL):
            try:
                action = json.loads(match.group(1).strip())
                actions.append(action)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse action: {match.group(1)}")
        return actions

    def _strip_action_tags(self, text: str) -> str:
        import re
        return re.sub(r"\s*<action>.*?</action>\s*", " ", text, flags=re.DOTALL).strip()

