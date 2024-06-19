import logging
import sys

class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass



class LoggingSetup:
    @staticmethod
    def setup_logging():
        logging.basicConfig(level=logging.ERROR,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=[
                                # logging.StreamHandler(sys.stdout), # Output to console
                                logging.FileHandler("debug.log", mode='w')  # Output to file
                            ])

        logger = logging.getLogger(__name__)
        sys.stdout = StreamToLogger(logger, logging.INFO)
        sys.stderr = StreamToLogger(logger, logging.ERROR)
        return logger
