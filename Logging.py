import logging

class LoggingSetup:
    @staticmethod
    def setup_logging():
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=[
                                # logging.StreamHandler(),  # Output to console
                                logging.FileHandler("debug.log", mode='w')  # Output to file
                            ])
        logger = logging.getLogger(__name__)
        return logger
