
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import STT_ENGINE, STT_LANGUAGE, STT_ENERGY_THRESHOLD, WAKE_WORD

logger = logging.getLogger("astrax.stt")

    def listen_command(self) -> str | None:
        """Listen for a full command after wake word detection."""
        return self.listen(timeout=7, phrase_limit=20)


class SpeechToText:
    def __init__(self):
        self._recognizer = None
        self._microphone = None
        self._init_engine()

    def _init_engine(self):
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = STT_ENERGY_THRESHOLD
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()
            # Calibrate for ambient noise
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("STT engine online. Listening for wake word: '%s'", WAKE_WORD)
        except ImportError:
            logger.warning("speech_recognition not installed. Voice input disabled.")
            logger.warning("Install with: pip install SpeechRecognition pyaudio")
