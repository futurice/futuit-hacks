# -*- coding: utf-8 -*-

import datetime

import CES_db
import CES_group

from apiclient.errors import HttpError
from CES_util import *
from CES_main import CMD_OPTIONS
from local_settings import *

class cesEvent:
    def __init__(self, google_event):
        logging.debug("Creating event object from: %s" % google_event)
        self.content = google_event
        self.target_groups = self._parse_description_tag("#groups:")
        # Just the group@domain.com - full group id versions.
        # Would make sense to only use these to avoid confusion.
        self.target_groups_full = ["%s@%s" % (grp.lower(), CES_SETTINGS['domain']) for grp in self.target_groups]

        self.master_id = self.content['id']
        self.content['extendedProperties'] = { "private" : 
                {
                    # Store the id of the master event to extendedProperties
                    "CES_master_id" : self.master_id,
                    # Also store the time of the run
                    "CES_runtime_tz_isostring"  : datetime_to_tz_isostring(datetime.datetime.utcnow())
                }
            }
        
        # Clean up some of the master event ids from content,
        # so it can be applied as a new event
        self.content.pop("id", None)
        self.content.pop("iCalUID", None)
        self.content.pop("etag", None)
        
        if CES_SETTINGS['forceTransparency']:
            self.content['transparency'] = u'transparent'
            
        # Strip comment and control rows (rows starting with #) from desc
        self.content['description'] = "\n".join([row for row in self.content['description'].split("\n") if not row.startswith("#")])
 
    def apply_to_calendars(self, calendar_service, directory_service):
        """ 
        Apply the cesEvent to the calendars of all members of
        groups defined in self.groups
        """
        logging.info("Applying master event '%s' to groups '%s'." % (self.master_id, self.target_groups_full))
        
        if not self.target_groups or self.target_groups == []:
            logging.warning("No groups for master event id '%s', skipping." % self.master_id)
            return

        target_emails = CES_group.merge_recipients(directory_service, self.target_groups_full)
        logging.info("CES event master ID '%s' has recipientlist: %s" % (self.master_id, target_emails))

        added, not_added = (0, 0)
        
        for target_email in target_emails:
            if self._apply_to_calendar(calendar_service, target_email):
                added += 1
            else:
                not_added += 1
        
        logging.info("Apply to calendars for event '%s' done. Events added: %d, Not added: %d." % (self.master_id, added, not_added))
        return

        
    def _apply_to_calendar(self, calendar_service, calendar_id):
        """ Add the event to a calendar. Return "added" boolean. """
        logging.debug("Will try and apply event '%s' to calendar '%s'." % (self.master_id, calendar_id))

        if CES_db.event_already_added_to_calendar(calendar_id, self.master_id):
            logging.info("Not adding event '%s' to calendar '%s'. (Already added)" % (self.master_id, calendar_id))
            return False

        insert_request = calendar_service.events().insert(calendarId=calendar_id, body=self.content)
        created_id = None
        
        pp.pprint(CMD_OPTIONS)
        
        if CMD_OPTIONS.simulate_only:
            logging.info("Simulate switch enabled. Not adding event '%s' to calendar '%s'" % (self.master_id, calendar_id))
        else:
            logging.info("Adding event '%s' to calendar '%s'" % (self.master_id, calendar_id))
            try:
                result = insert_request.execute()
                logging.debug("Event insert result: %s" % result)
                created_id = result['id']
                logging.debug("Added master event '%s' to calendar '%s' as created event '%s'" % (self.master_id, calendar_id, created_id))
            except HttpError, e:
                logging.critical(("Calendar insert call failed for event id '%s', "
                    "calendar '%s', request '%s'. Error: %s") % (self.master_id, calendar_id, insert_request, e))
                return False
            except:
                logging.critical(("Unexpected error, calendar insert call failed for event id '%s', "
                    "calendar '%s', request '%s'. Error: %s") % (self.master_id, calendar_id, insert_request, sys.exc_info()[0]))
                return False
            else:
                CES_db.add_event_to_db(calendar_id, self.master_id, created_id)
                return True
            
    
    def _parse_description_tag(self, control_tag):
        """ 
        Extract control tag values from the description. The control row could be eg.:
        #groups: berlin, helsinki
        "#groups:" would be the control tag and "berlin, helsinki" the values
        @return list of tag values (eg. [u"berlin", u"helsinki"])
        """
        desc = self.content['description'].lower()

        try:
           # Explode string by linebreaks, filter out rows that don't start with our tag
           value_row = [row for row in desc.split("\n") if row.startswith(control_tag)][0]
        except IndexError:
            logging.warning("No values could be parsed with tag '%s' from description: %s" % (control_tag, desc))
            return []
        
        # Explode the comma separated string and strip whitespace
        result = [stripped.strip() for stripped in value_row[len(control_tag):].split(",")]
        logging.debug("Parsed values '%s' for tag '%s' from description '%s'." % (result, control_tag, desc))
        
        # Strip empty elements
        result = [item for item in result if item not in (None, '')]
        
        # If allowed groups is defined in settings, reduce to those
        if control_tag == "#groups:":
            if CES_SETTINGS['allowedGroups']:
                result = list(set(CES_SETTINGS['allowedGroups']) & set(result))
                logging.debug("allowedGroups defined in settings, groups reduced to: %s" % result)
        
        return result

def get_master_events(service, pageToken=None):
    """
    Get a list of events from the master calendar.
    @returns a list of events
    """
    logging.debug("Entered get_master_events")
    result = []

    events = service.events().list(
        calendarId = CES_SETTINGS['masterCalendarId'],
        singleEvents = True,
        maxResults = 1000,
        orderBy ='startTime',
        timeMin = datetime_to_tz_isostring(datetime.datetime.utcnow(), timedelta = datetime.timedelta(days = CES_SETTINGS['startRangeDays'])),
        timeMax = datetime_to_tz_isostring(datetime.datetime.utcnow(), timedelta = datetime.timedelta(days = CES_SETTINGS['endRangeDays'])),
        pageToken = pageToken,
        ).execute()

    for event in events['items']:
        logging.debug("Event: %s" % pp.pformat(event))
        result.append(event)

    logging.debug("Result: %s" % result)
    page_token = events.get('nextPageToken')

    if page_token:
        result += get_master_events(service, group_email, page_token)
        return result
    else:
        return result
