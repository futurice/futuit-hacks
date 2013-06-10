#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" 
A tool for synchronizing a master google calendar to several
user calendars. 
"""

__author__ = 'Markus Koskinen (markus.koskinen@futurice.com)'
__copyright__ = 'Copyright (c) 2013 Futurice Oy'
__license__ = 'Apache License 2.0'

import os
import sys

import CES_db
import CES_calendar
import CES_googleservices
import CES_group

from CES_util import *
from local_settings import *

def main(argv):
   init_logging()
   CES_db.init_db()
   calendar_service, directory_service = CES_googleservices.init_googleservices()

   logging.info("Populating list of all groups ...")
   CES_group.ALL_GROUPS = CES_group.get_groups(directory_service)

   logging.info("Fetching all master events ...")
   master_events = CES_calendar.get_master_events(calendar_service)

   logging.debug("Master events:\n%s" % pp.pformat(master_events))

   logging.info("Creating CES events ...")
   ces_events = [CES_calendar.cesEvent(mevent) for mevent in master_events]

   logging.info("Applying CES events to calendars ...")
   for ces_event in ces_events:
       ces_event.apply_to_calendars(calendar_service, directory_service)

   logging.info("All done.")


if __name__ == '__main__':
  main(sys.argv)
