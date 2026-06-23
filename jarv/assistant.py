

import logging
import sys
import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # python-dotenv optional

from config import VOICE_ENABLED, JARVIS_NAME, LOG_LEVEL, LOG_FILE

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("jarvis")


class Assistant:
    """JARVIS — Just A Rather Very Intelligent System."""

    def __init__(self):
        logger.info("Initialising %s...", JARVIS_NAME)

        #memory
        from brain.memory import Memory
        from brain.ai import Brain
        self.memory = Memory()
        self.brain  = Brain(self.memory)

    
        self.tts = None
        self.stt = None
        if VOICE_ENABLED:
            try:
                from voice.tts import TextToSpeech
                from voice.stt import SpeechToText
                self.tts = TextToSpeech()
                self.stt = SpeechToText()
            except Exception as e:
                logger.warning("Voice modules failed to load: %s", e)

    
        from tools.apps     import AppTools
        from tools.browser  import BrowserTools
        from tools.system   import SystemTools
        from tools.weather  import WeatherTools
        from tools.files    import FileTools
        from tools.reminders import ReminderTools

        self.apps      = AppTools()
        self.browser   = BrowserTools()
        self.system    = SystemTools()
        self.weather   = WeatherTools()
        self.files     = FileTools()
        self.reminders = ReminderTools(speak_fn=self._say)

        logger.info("%s online and ready.", JARVIS_NAME)
        self._say("Good day, Sir. All systems are operational. How may I assist you?")



    def chat(self, user_input: str, session_id: str = "default") -> str:
        """Process a text command and return JARVIS's response."""
        if not user_input.strip():
            return ""

    
        lower = user_input.lower().strip()
        if lower in ("what time is it", "time", "current time"):
            resp = f"It is currently {self.system.get_time()}, Sir."
            self._say(resp)
            return resp
        if lower in ("what's the date", "date", "today's date"):
            resp = f"Today is {self.system.get_date()}, Sir."
            self._say(resp)
            return resp

        logger.info("USER: %s", user_input)
        response_text, actions = self.brain.think(user_input, session_id)

        for action in actions:
            action_result = self._execute_action(action)
            if action_result:
                # Inject tool results back into the response if AI left a placeholder
                response_text = response_text.replace("{{result}}", action_result, 1)

        logger.info("JARVIS: %s", response_text)
        self._say(response_text)
        return response_text

    def listen_and_respond(self) -> str | None:
        """One cycle of listen → think → speak (voice mode)."""
        if not self.stt or not self.stt.available:
            logger.warning("STT not available. Use chat() for text input.")
            return None
        text = self.stt.listen_command()
        if text:
            return self.chat(text)
        return None

    def run_voice_loop(self):
        """
        Continuous voice-assistant loop.
        Waits for the wake word, then listens for a full command.
        """
        if not self.stt or not self.stt.available:
            logger.error("Cannot run voice loop: STT not available.")
            return

        import config
        wake = config.WAKE_WORD
        self._say(f"Voice mode active. Say '{wake}' to activate.")
        print(f"  JARVIS Voice Mode — say '{wake}' to begin\n")

        while True:
            try:
                if self.stt.listen_for_wake_word():
                    self._say("Yes, Sir?")
                    command = self.stt.listen_command()
                    if command:
                        if any(x in command.lower() for x in
                               ["goodbye", "shut down jarvis", "exit jarvis", "power down"]):
                            self._say("Goodbye, Sir. It has been a privilege.")
                            break
                        self.chat(command)
            except KeyboardInterrupt:
                self._say("Standing by.")
                break



    def _execute_action(self, action: dict) -> str | None:
        """
        Execute a structured action returned by the AI brain.
        Returns an optional result string to fold back into the response.
        """
        atype = action.get("type", "")
        logger.info("Action  %s", action)

        try:
        
            if atype == "open_app":
                return self.apps.open(action.get("app", ""))

            elif atype == "close_app":
                return self.apps.close(action.get("app", ""))

            elif atype == "open_file":
                return self.apps.open_file(action.get("path", ""))

        
            elif atype == "web_search":
                self.browser.search(action.get("query", ""))

            elif atype == "open_url":
                self.browser.open_url(action.get("url", ""))

            elif atype == "youtube":
                self.browser.youtube_search(action.get("query", ""))

            elif atype == "maps":
                self.browser.open_maps(action.get("location", ""))

            elif atype == "wikipedia":
                self.browser.open_wikipedia(action.get("topic", ""))

            elif atype == "translate":
                self.browser.translate(
                    action.get("text", ""),
                    action.get("target_lang", "en")
                )

            elif atype == "github":
                self.browser.open_github(action.get("repo", ""))

            
            elif atype == "system":
                cmd = action.get("command", "")
                handler = {
                    "volume_up":    self.system.volume_up,
                    "volume_down":  self.system.volume_down,
                    "mute":         self.system.mute,
                    "unmute":       self.system.unmute,
                    "sleep":        self.system.sleep,
                    "lock":         self.system.lock_screen,
                    "shutdown":     self.system.shutdown,
                    "restart":      self.system.restart,
                    "screenshot":   self.system.screenshot,
                }.get(cmd)
                if handler:
                    result = handler()
                    return str(result) if result else None

            elif atype == "shell":
                return self.system.execute(action.get("command", ""))

            elif atype == "battery":
                return self.system.get_battery()

            elif atype == "system_stats":
                stats = self.system.get_system_stats()
                if "error" not in stats:
                    return (
                        f"CPU: {stats['cpu_percent']}%  |  "
                        f"RAM: {stats['ram_percent']}%  |  "
                        f"Disk free: {stats['disk_free_gb']} GB / {stats['disk_total_gb']} GB"
                    )
                return stats.get("error", "Unknown error")

            elif atype == "kill_process":
                return self.system.kill_process(action.get("name", ""))

            elif atype == "open_folder":
                return self.system.open_folder(action.get("path", "~"))

            elif atype == "clipboard_get":
                return self.system.get_clipboard() or "(clipboard is empty)"

            elif atype == "clipboard_set":
                self.system.set_clipboard(action.get("text", ""))
                return "Copied to clipboard."

        
            elif atype == "weather":
                return self.weather.get_weather(action.get("location", ""))

            elif atype == "forecast":
                return self.weather.get_forecast(
                    action.get("location", ""),
                    int(action.get("days", 3))
                )


            elif atype == "file_read":
                return self.files.read(action.get("path", ""))

            elif atype == "file_write":
                return self.files.write(
                    action.get("path", ""),
                    action.get("content", ""),
                    action.get("overwrite", False)
                )

            elif atype == "file_append":
                return self.files.append(action.get("path", ""), action.get("content", ""))

            elif atype == "file_list":
                return self.files.list_dir(action.get("path", "~"))

            elif atype == "file_search":
                matches = self.files.search(
                    action.get("pattern", "*"),
                    action.get("directory", "~")
                )
                if matches:
                    return "\n".join(matches[:20])
                return "No matching files found."

            elif atype == "file_delete":
                return self.files.delete(action.get("path", ""))

            elif atype == "file_copy":
                return self.files.copy(action.get("src", ""), action.get("dst", ""))

            elif atype == "file_move":
                return self.files.move(action.get("src", ""), action.get("dst", ""))

            elif atype == "file_info":
                return self.files.info(action.get("path", ""))

    
            elif atype == "remind_in":
                return self.reminders.remind_in(
                    action.get("message", "Reminder"),
                    float(action.get("minutes", 5)),
                    action.get("label")
                )

            elif atype == "remind_at":
                return self.reminders.remind_at(
                    action.get("message", "Reminder"),
                    int(action.get("hour", 9)),
                    int(action.get("minute", 0)),
                    action.get("label")
                )

            elif atype == "reminder_cancel":
                return self.reminders.cancel(action.get("label", ""))

            elif atype == "reminder_list":
                items = self.reminders.list_reminders()
                return "Active reminders: " + (", ".join(items) if items else "none") + "."

        
            elif atype == "remember":
                self.memory.remember(action.get("key", ""), action.get("value", ""))
                return f"Noted: {action.get('key')} = {action.get('value')}"

            elif atype == "forget":
                # Not exposed on Memory yet — delete from facts table directly
                self.memory.conn.execute(
                    "DELETE FROM facts WHERE key = ?", (action.get("key", "").lower(),)
                )
                self.memory.conn.commit()
                return f"Forgotten: {action.get('key')}"

            elif atype == "task_add":
                tid = self.memory.add_task(action.get("description", ""))
                return f"Task #{tid} added."

            elif atype == "task_complete":
                self.memory.complete_task(int(action.get("id", 0)))
                return f"Task #{action.get('id')} marked complete."

            elif atype == "task_list":
                tasks = self.memory.get_pending_tasks()
                if not tasks:
                    return "No pending tasks, Sir."
                return "\n".join(f"  [{t['id']}] {t['description']}" for t in tasks)

            else:
                logger.warning("Unknown action type: %s", atype)

        except Exception as e:
            logger.error("Action execution failed (%s): %s", atype, e, exc_info=True)
            return f"(Action '{atype}' failed: {e})"

        return None


    def _say(self, text: str):
        """Speak text aloud (if TTS available) — always also prints to console."""

        if self.tts:
            self.tts.speak(text, block=False)
