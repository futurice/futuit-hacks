# -*- coding: utf-8 -*-
# local_settings doesn't contain secrets at this time,
# if you add any - please remember to update .gitignore
# accordingly or separate to a different settings file

CES_SETTINGS = {
    # Master calendar id (You can find the id from Google Calendar settings for the calendar"
    "masterCalendarId" : "futuevents@futurice.com",
    # Markus' test calendar
    #"masterCalendarId" : "futurice.com_5oq1nn5ve93bvpbefu2cucarns@group.calendar.google.com",

    # Force created events to be transparent (user shown as "available")
    "forceTransparency" : True,
    
    # Allowed groups (to allow any, set it to: None)
    "allowedGroups" : None,
    
    # Domain
    "domain" : "futurice.com",

    # Time deltas for master calendar reading (days). This will define how far in the past
    # and how far in the future we will read data from the master calendar from.
    "startRangeDays" : -14,
    "endRangeDays" : 180,

    # Local timezone
    "timeZoneLocal" : "Europe/Helsinki",
    # SQLite db file
    "sqliteDb" : "CES.db",
    # Log file
    "logFile" : "log/CES.log",
    # Identity storage file
    "oauthStorage" : "oauthstore/CES.dat",

    # No reminders is default. Calendar default if set to true
    "no_reminders" : { "useDefault" : False },
    "default_reminders" : { 'useDefault': True }    
}

# Override these with a similar dict in private_settings
CES_PRIVATE_SETTINGS = {
  "SERVICE_ACCOUNT_EMAIL" : "DEFINE-IN-PRIVATE-SETTINGS@developer.gserviceaccount.com",
  "SERVICE_ACCOUNT_PKCS12_FILE_PATH" : "DEFINE-IN-PRIVATE-SETTINGS-privatekey.p12",
  "ADMIN_ACCOUNT_EMAIL" : "admin@domain.com",
}

from private_settings import *
