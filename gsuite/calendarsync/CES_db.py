# -*- coding: utf-8 -*-

import sys
import sqlite3

from local_settings import *
from CES_util import *

def init_db():
    """ 
    Initialize the SQLite DB connection, create an empty db
    if it doesn't exist.
    """
    logging.debug("Entered init_sqlite")
    
    conn = sqlite3.connect(CES_SETTINGS['sqliteDb'])

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SQLITE_VERSION()")
            logging.info("SQLite OK. Version: %s" % cursor.fetchone())

            # If an added_events table doesn't exist, we create it (first run)
            create_sql = ("CREATE TABLE IF NOT EXISTS added_events "
                          "  (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                          "   calendar_id TEXT, "
                          "   master_event_id TEXT, "
                          "   created_event_id TEXT, "
                          "   date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP "
                          "  )")
            cursor.execute(create_sql)
    except sqlite3.Error, e:
        logging.critical("SQLite initialization error: %s" % e.args[0])
        sys.exit(1)


def add_event_to_db(calendar_id, master_event_id, created_event_id):
    """ Mark a calendar-event tuple as processed. """ 
    conn = sqlite3.connect(CES_SETTINGS['sqliteDb'])
    add_event_sql = "INSERT INTO added_events VALUES (NULL, ?, ?, ?, current_timestamp);"
    
    with conn:
        logging.info("Adding calendar-event entry to DB. Calendar: %s, MasterEventID: %s, CreatedEventID: %s" % (calendar_id, master_event_id, created_event_id))
        cursor = conn.cursor()
        cursor.execute(add_event_sql, (calendar_id, master_event_id, created_event_id))


def event_already_added_to_calendar(calendar_id, event_id):
    """ 
    We keep track of what events we've added to calendars in
    our small database and don't insert it again if we have already
    inserted it. (So that people can delete them)
    @returns boolean
    """
    conn = sqlite3.connect(CES_SETTINGS['sqliteDb'])
    check_calendar_event_sql = ("SELECT COUNT(*) FROM added_events "
        "WHERE calendar_id = ? and master_event_id = ?;")

    with conn:
        logging.debug("Looking up calendar entry event from DB. Calendar: %s, MasterEventID: %s from DB." % (calendar_id, event_id))
        cursor = conn.cursor()
        cursor.execute(check_calendar_event_sql, (calendar_id, event_id))
        count = cursor.fetchone()[0]
        logging.debug("Lookup result for calendar-event '%s-%s': %d" % (calendar_id, event_id, count))
        if count == 0:
           return False
        else:
           return True
