
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import STT_ENGINE, STT_LANGUAGE, STT_ENERGY_THRESHOLD, WAKE_WORD

logger = logging.getLogger("astrax.stt")


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
            
    @property
    def available(self) -> bool:
        return self._recognizer is not None and self._microphone is not None

    def listen(self, timeout: int = 5, phrase_limit: int = 15) -> str | None:
        """
        Listen for speech and return transcribed text, or None on failure.
        timeout: seconds to wait for speech to begin
        phrase_limit: max seconds of phrase to capture
        """
        if not self.available:
            return None

        import speech_recognition as sr
        try:
            with self._microphone as source:
                print("🎙  Listening...")
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )

  if STT_ENGINE == "google":
                text = self._recognizer.recognize_google(audio, language=STT_LANGUAGE)
            elif STT_ENGINE == "sphinx":
                text = self._recognizer.recognize_sphinx(audio)
            else:
                text = self._recognizer.recognize_google(audio)

            logger.debug(f"Heard: {text}")
            return text.strip()
 except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            logger.debug("Could not understand audio.")
            return None
        except sr.RequestError as e:
            logger.error(f"STT API error: {e}")
            return None

    def listen_for_wake_word(self, timeout: int = 3) -> bool:
        """Returns True if wake word is detected in the audio."""
        text = self.listen(timeout=timeout, phrase_limit=3)
        if text and WAKE_WORD.lower() in text.lower():
            return True
        return False
