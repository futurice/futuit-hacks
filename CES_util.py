# -*- coding: utf-8 -*-

import datetime    
import os
import sys
import logging
import logging.handlers
import pprint

from local_settings import *
from dateutil import tz

DEBUG = True

_LOG_FORMATTER_STRING = "%(asctime)s %(module)s [%(levelname)s] %(message)s"

pp = pprint.PrettyPrinter(indent=4)

def init_logging():
    """ Initialize logging """
    logger = logging.getLogger("")

    # Make sure the logging path exists, create if not
    logdir = os.path.dirname(CES_SETTINGS['logFile'])
    if logdir and not os.path.exists(logdir):
        print "Logging directory '%s' doesn't exist, creating." % logdir
        os.makedirs(logdir)

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    filehandler = logging.handlers.RotatingFileHandler(filename=CES_SETTINGS['logFile'], 
        maxBytes=(5 * 1024 * 1024), backupCount=10)

    handler.setLevel(logging.INFO)
    filehandler.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMATTER_STRING)
    handler.setFormatter(formatter)
    filehandler.setFormatter(formatter)

    if DEBUG:
        debugfilehandler = logging.handlers.RotatingFileHandler(filename=CES_SETTINGS['logFile'] + ".debug", 
                               maxBytes=(5 * 1024 * 1024), backupCount=10)
        debugfilehandler.setLevel(logging.DEBUG)
        debugfilehandler.setFormatter(formatter)
        logger.addHandler(debugfilehandler)

    logger.addHandler(handler)
    logger.addHandler(filehandler)

    logger.debug("Logging started.")

def datetime_to_tz_isostring(utc_dt, timezone_str = CES_SETTINGS['timeZoneLocal'], timedelta = datetime.timedelta(days = 0)):
    """ Gets an UTC datetime object as a parameter.
        Optional parameters are a timezone offset and a timedelta.
    """
    logging.debug("UTC datetime: %s, Timezone: %s, Timedelta: %s" % 
        (utc_dt.isoformat(), timezone_str, timedelta))
    
    # Apply the delta change (defaults to no delta)
    utc_dt = utc_dt + timedelta

    # Strip microseconds
    logging.debug("utc_dt.microsecond = %s" % utc_dt.microsecond)
    utc_dt = utc_dt - datetime.timedelta(microseconds = utc_dt.microsecond)
    
    # Explicitely set utc_dt to UTC and create a local time variant
    utc_dt = utc_dt.replace(tzinfo = tz.gettz('UTC'))
    local_timezone_dt = utc_dt.astimezone(tz.gettz(timezone_str)) 
    
    result = local_timezone_dt.isoformat()
    logging.debug("datetime_to_tz_isostring result: %s" % result)
    
    return result
