


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
