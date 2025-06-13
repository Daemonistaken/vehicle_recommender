import logging
import os
import datetime

class LazyFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=True):
        super().__init__(filename, mode, encoding, delay=delay)

def get_file_logger(logger_name: str, log_prefix: str = "logs/") -> logging.Logger:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"{log_prefix}{logger_name}_{timestamp}.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

        # Delay=True ensures file is created only when first log is emitted
        fh = LazyFileHandler(log_path)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    return logger