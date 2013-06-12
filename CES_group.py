# -*- coding: utf-8 -*-

from local_settings import *
from CES_util import *

# Contains combinations of groups members
AGGREGATE_GROUP_CACHE = {}

ALL_GROUPS = []

def get_groups(service, pageToken = None):
    """ Returns a list of all the groups in the domain. (Emails of the groups) """
    logging.debug("Entered get_groups, token: %s" % pageToken)
    result = []
    groups = service.groups().list(domain = CES_SETTINGS['domain'], pageToken = pageToken).execute()

    if not 'groups' in groups:
       return result;

    for group in groups['groups']:
        #logging.debug("Group: %s" % pp.pformat(group))
        if group['name']:
            result.append(group['email'])

    logging.debug("Result: %s" % result)
    page_token = groups.get('nextPageToken')

    if page_token:
       result += get_groups(service, page_token)
       return result
    else:
       return result

def get_group_members(service, group_email, pageToken = None):
    """ Return a list of emails of the members of group <group_email>  """
    logging.debug("Entered get_group_members, group_email: %s, token: %s" % (group_email, pageToken))
    result = []

    if not group_email or not group_email in ALL_GROUPS:
        return result;
    
    members = service.members().list(groupKey = group_email, pageToken = pageToken).execute()
    
    if not 'members' in members:
       return result;
    
    for member in members['members']:
        logging.debug("Members: %s" % pp.pformat(member))
        result.append(member['email'])
   
    logging.debug("Result: %s" % result)
    page_token = members.get('nextPageToken')

    if page_token:
        result += get_group_members(service, group_email, page_token)
        return result
    else:
        return result

def merge_recipients(service, groups):
    """
    Merge a list of groups to email addresses with no duplicates.
    Maintain a volatile cache as a global.
    Returns an array of emails.
    """
    logging.debug("Entered merge_recipients, groups: %s" % groups)
    
    group_key = groups_to_key(groups)
    
    # If we've already made the merge once we should get a cache hit
    if group_key in AGGREGATE_GROUP_CACHE:
        logging.debug("Recipient merge cache hit for '%s'." % group_key)
        return AGGREGATE_GROUP_CACHE[group_key]
    else:
        logging.info("Cache miss for '%s'." % group_key)
      
    result = []

    for group in groups:
        result += get_group_members(service, group)

    # We discard duplicates here
    AGGREGATE_GROUP_CACHE[group_key] = list(set(result))

    logging.debug("Merged email lookup for groupset '%s' is:\n%s" % (group_key, pp.pformat(result)))
    return AGGREGATE_GROUP_CACHE[group_key]

def groups_to_key(groups):
    """ Convert a list of groups to a key usable in dicts. """
    logging.debug("Entered groups_to_key, groups: %s" % groups)
    
    if not groups or groups == []:
        logger.critical("Can't create a key based on an empty groupset.")
        sys.exit(1)

    groups.sort()
    result = "__".join(groups)
    return result
