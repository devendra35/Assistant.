class Memory:

    def __init__(self):
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info("Memory module online.")
