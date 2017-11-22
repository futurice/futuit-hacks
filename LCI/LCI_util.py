import sys
import logging
import pprint

DEBUG = False

_LOG_FORMATTER_STRING = "%(asctime)s %(module)s [%(levelname)s] %(message)s"

LCI_pp = pprint.PrettyPrinter(indent=4)

def init_logging():
    """ Initialize logging """
    logger = logging.getLogger("")

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    filehandler = logging.FileHandler("LCI.log")
    filehandler.setLevel(logging.DEBUG)

    if DEBUG:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)

    logger.addHandler(handler)
    logger.addHandler(filehandler)

    formatter = logging.Formatter(_LOG_FORMATTER_STRING)
    handler.setFormatter(formatter)
    filehandler.setFormatter(formatter)
    logger.debug("Logging started.")

