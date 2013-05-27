#!/usr/bin/env python

"""A script that copies select Calendar Resources as contacts under a set group for selected organization's members."""
__author__ = "vsin"
__version__ = "1.0.0"

import gdata.apps.client
import atom.data
import gdata.contacts.data
import gdata.contacts.client
import gdata.calendar_resource.client

import interactive_gapps_auth

import sys
import os.path
import os
import logging
import logging.config
import ConfigParser
import optparse
from fnmatch import fnmatch
import urllib
import json

options = None
config = None

APP_CONFIG_SECTION = "application"
PARAM_CONFIG_SECTION = "default_params"
FEED_URI = "https://apps-apis.google.com/a/feeds/calendar/resource/2.0/%s/"
DOMAIN = None
DEFAULT_REL = gdata.data.WORK_REL
OPTOUT_URI = "https://intra.futurice.com/u/contacts/api/get_opted_out"
OPTOUT_SETTING = "optout_rooms"
EXTPROP_CONTACT_NAME = None
EXTPROP_CONTACT_VALUE = None
EXTPROP_GROUP_NAME = None
EXTPROP_GROUP_VALUE = None
MY_CONTACTS_ID = "Contacts"

contacts_client = None
apps_client = None
calendar_resource_client = None
domain_token = None
request_feed = None

def parse_options():
    global options

    parser = optparse.OptionParser()

    parser.add_option(
        "-S", "--select-pattern",
        dest="select_pattern",
        help="select calendars to copy by pattern GLOB against Calendar Resource's email address",
        metavar="GLOB")

    parser.add_option(
        "-U", "--user-pattern",
        dest="user_pattern",
        help="copy contacts to all users whose email address matches GLOB",
        metavar="GLOB")

    parser.add_option(
        "-G", "--group",
        dest="group",
        help="when creating a new contacts group use NAME",
        metavar="NAME")

    parser.add_option(
        "-M", "--my-contacts",
        dest="my_contacts",
        action="store_true",
        default=False,
        help="add contacts to My Contacts as well")

    parser.add_option(
        "-F", "--family-name",
        dest="family_name",
        help="set the compulsory family name of added contacts to NAME",
        metavar="NAME")

    parser.add_option(
        "-D", "--delete-old",
        dest="delete_old",
        action="store_true",
        default=False,
        help="also check the target group for old calendar contacts added by this script and delete those")

    parser.add_option(
        "--undo",
        dest="undo",
        action="store_true",
        default=False,
        help="remove all groups and contacts added by this script")
        
    
    parser.add_option(
        "-r", "--reauth",
        dest="reauth",
        action="store_true",
        default=False,
        help="reauthorize Google Account")

    parser.add_option(
        "-b", "--batch",
        dest="batch",
        action="store_true",
        default=False,
        help="batch operation (consider interactive reauthorization an error)")

    parser.add_option(
        "-t", "--token",
        dest="token_file",
        help="use OAuth2 token FILE [default: %default]",
        metavar="FILE",
        default="token.conf")

    parser.add_option(
        "-d", "--domain-token",
        dest="domain_file",
        help="use domain token FILE [default: %default]",
        metavar="FILE",
        default="token_domain.conf")

    parser.add_option(
        "-c", "--config",
        dest="config",
        help="read application configuration from FILE [default: %default]",
        metavar="FILE",
        default="config.conf")

    parser.add_option(
        "-l", "--log-config",
        dest="log_config",
        help="read logging configuration from FILE [default: %default]",
        metavar="FILE",
        default="logging.conf")

    options = parser.parse_args()[0]

def read_config():
    global config, DOMAIN, EXTPROP_CONTACT_NAME, EXTPROP_CONTACT_VALUE, EXTPROP_GROUP_NAME, EXTPROP_GROUP_VALUE

    config = ConfigParser.RawConfigParser()
    config.read(options.config)

    # Set default params
    if config.has_section(PARAM_CONFIG_SECTION):
        for param in config.options(PARAM_CONFIG_SECTION):
            if not hasattr(options, param) or getattr(options, param) is None:
                setattr(options, param, config.get(PARAM_CONFIG_SECTION, param))

    # Set globals
    DOMAIN = config.get(APP_CONFIG_SECTION, "domain")
    EXTPROP_CONTACT_NAME = config.get(APP_CONFIG_SECTION, "contact_extended_property_name")
    EXTPROP_CONTACT_VALUE = config.get(APP_CONFIG_SECTION, "contact_extended_property_value")
    EXTPROP_GROUP_NAME = config.get(APP_CONFIG_SECTION, "group_extended_property_name")
    EXTPROP_GROUP_VALUE = config.get(APP_CONFIG_SECTION, "group_extended_property_value")

def get_optout_set():
    """Returns a set of user-names who wish to opt-out from synchronization."""

    optout_json = json.load(urllib.urlopen(OPTOUT_URI))
    if u'settings' in optout_json and \
        unicode(OPTOUT_SETTING) in optout_json[u'settings']:
        return set(map(lambda user_email: user_email.lower(), optout_json[u'settings'][u'optout_employees']))

    logging.error("Could not understand opt-out data format")
    sys.exit(1)

def init_clients():
    global contacts_client, apps_client, calendar_resource_client, domain_token, request_feed
    
    # Get tokens
    domain_token = interactive_gapps_auth.obtain_domain_token(
        token_file=options.domain_file)

    try:
        admin_token = interactive_gapps_auth.obtain_oauth2_token(
            token_file=options.token_file,
            scopes=config.get(APP_CONFIG_SECTION, "oauth_scopes"),
            client_id=config.get(APP_CONFIG_SECTION, "client_id"),
            client_secret=config.get(APP_CONFIG_SECTION, "client_secret"),
            user_agent=config.get(APP_CONFIG_SECTION, "user_agent"),
            reauth=options.reauth,
            batch=options.batch)
    except interactive_gapps_auth.ReAuthRequiredError:
        logging.error("Re-authorization required but --batch was specified.")
        sys.exit(1)

    calendar_resource_client = gdata.calendar_resource.client.CalendarResourceClient(DOMAIN)
    admin_token.authorize(calendar_resource_client)
    contacts_client = gdata.contacts.client.ContactsClient(DOMAIN, auth_token=domain_token)

    apps_client = gdata.apps.client.AppsClient(DOMAIN, auth_token=domain_token)
    apps_client.ssl = True

    request_feed = gdata.contacts.data.ContactsFeed()

def ACTING_AS(email):
    """Sets domain token user."""
    logging.info('Domain token now acting as %s', email)
    domain_token.requestor_id = email

def get_current_user():
    """Gets domain token user."""
    return domain_token.requestor_id

def get_magic_group(groups, create=True):
    for group in groups:
        if is_script_group(group):
            # Found group, get members
            contacts_query = gdata.contacts.client.ContactsQuery()
            contacts_query.group = group.id.text
            contacts_query.max_results = config.getint(APP_CONFIG_SECTION, "max_contacts")
            return (group, contacts_client.get_contacts(q=contacts_query).entry)

    if not create:
        return (None, [])
    
    # No group found, create
    logging.info('%s: No room group found, creating..', get_current_user())
    new_group = gdata.contacts.data.GroupEntry()
    new_group.title = atom.data.Title(options.group)

    # Set extended property
    extprop = gdata.data.ExtendedProperty()
    extprop.name = EXTPROP_GROUP_NAME
    extprop.value = EXTPROP_GROUP_VALUE
    new_group.extended_property.append(extprop)

    return (contacts_client.create_group(new_group=new_group), [])

def submit_batch(force=False):
    global request_feed
    
    if not force and len(request_feed.entry) < config.getint(APP_CONFIG_SECTION, "batch_max"):
        return # Wait for more requests

    result_feed = contacts_client.execute_batch(request_feed)
    for result in result_feed.entry:
        try: status_code = int(result.batch_status.code)
        except ValueError: status_code = -1
        if status_code < 200 or status_code >= 400:
            logging.warn("%s: Error %d (%s) while %s'ing batch ID %s = %s (%s)",
                get_current_user(),
                status_code,
                result.batch_status.reason,
                result.batch_operation.type,
                result.batch_id.text,
                result.id and result.id.text or result.get_id(),
                result.name and result.name.full_name and result.name.full_name or "name unknown")

    # Start new feed
    request_feed = gdata.contacts.data.ContactsFeed()

submit_batch_final = lambda: submit_batch(force=True)

# Return if contact was added by the script
is_script_contact = lambda contact: len(filter(
    lambda extprop: extprop.name == EXTPROP_CONTACT_NAME and extprop.value == EXTPROP_CONTACT_VALUE,
    contact.extended_property)) > 0

# Return if contact group was added by the script
is_script_group = lambda group: len(filter(
    lambda extprop: extprop.name == EXTPROP_GROUP_NAME and extprop.value == EXTPROP_GROUP_VALUE,
    group.extended_property)) > 0

def resource_to_contact(calendar):
    """Converts a calendar resource object to a contact object."""
    
    contact = gdata.contacts.data.ContactEntry()

    # Set the contact name.
    contact.name = gdata.data.Name(
        given_name=gdata.data.GivenName(text=calendar.GetResourceCommonName()),
        family_name=gdata.data.FamilyName(text=options.family_name),
        full_name=gdata.data.FullName(text=calendar.GetResourceCommonName()))
    contact.content = atom.data.Content(text=calendar.GetResourceDescription())
    # Set the contact email address
    contact.email.append(gdata.data.Email(address=calendar.GetResourceEmail(),
        primary='true', display_name=calendar.GetResourceCommonName(), rel=DEFAULT_REL))

    return contact

def sync_contact(source, target):
    """Copies data from source contact to target contact and returns True if target was modified."""
    
    modified = False

    # Notes
    if source.content and source.content.text:
        if not target.content or target.content.text != source.content.text:
            modified = True
            target.content = source.content

    # Name
    if source.name:
        if not target.name:
            modified = True
            target.name = gdata.data.Name()

        if not target.name.given_name or target.name.given_name.text != source.name.given_name.text:
            modified = True
            target.name.given_name = source.name.given_name

        if not target.name.family_name or target.name.family_name.text != source.name.family_name.text:
            modified = True
            target.name.family_name = source.name.family_name

        if not target.name.full_name or target.name.full_name.text != source.name.full_name.text:
            modified = True
            target.name.full_name = source.name.full_name

    return modified

def undo(target_user):
    # Let's delete users by global list and group list on the off chance the global list
    # is not comprehensive due to its size exceeding query limits.
    removed_ids = set()

    contacts = contacts_client.get_contacts().entry
    for contact in contacts:
        if is_script_contact(contact):
            logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                get_current_user(), contact.name.full_name.text, contact.id.text)
            removed_ids.add(contact.id.text)
            request_feed.add_delete(entry=contact)
            submit_batch()
    
    # Get users' groups
    groups = contacts_client.get_groups().entry

    # Find group by extended property
    (magic_group, magic_group_members) = get_magic_group(groups, create=False)
    if magic_group is not None:
        for group_member in magic_group_members:
            if group_member.id.text not in removed_ids and is_script_contact(group_member):
                logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                    get_current_user(), group_member.name.full_name.text, group_member.id.text)
                request_feed.add_delete(entry=group_member)
                submit_batch()

        # Remove group
        contacts_client.delete_group(magic_group)
        logging.info('%s: Removing auto-generated group "%s" with ID %s',
            get_current_user(), magic_group.title.text, magic_group.id.text)

def get_value_by_contact_email(email_dict, contact):
    """Resolve contact object to email key in email_dict and return the first matching value."""

    # Get all emails with a match in dictionary
    matching_emails = filter(
        lambda email: email.address and email.address.lower() in email_dict,
        contact.email
    )

    if len(matching_emails) == 0: return None

    # Get primary work emails
    contact_emails = filter(
        lambda email: email.primary == 'true' and email.rel == DEFAULT_REL,
        matching_emails
    )

    if len(contact_emails) == 0:
        # No primary work email? Get non-primary work emails
        contact_emails = filter(
            lambda email: email.rel == DEFAULT_REL,
            matching_emails
        )

    if len(contact_emails) == 0:
        # No work email? Get primary emails
        contact_emails = filter(
            lambda email: email.primary == 'true',
            matching_emails
        )

    if len(contact_emails) == 0:
        # No primary email? Get all matching emails
        contact_emails = matching_emails

    if len(contact_emails) > 1: logging.warn('%s: Several matching emails (%s) for contact "%s" with ID %s',
        get_current_user(),
        map(lambda email: email.address, contact_emails),
        contact.name and contact.name.full_name and contact.name.full_name.text or "(unknown)",
        contact.id and contact.id.text)

    return email_dict[contact_emails[0].address.lower()]

def main():
    # Set-up
    os.chdir(os.path.dirname(sys.argv[0]))
    parse_options()
    logging.config.fileConfig(options.log_config)

    try: main_logging()
    except Exception, err:
        logging.exception("Caught exception:")
        sys.exit(1)

def main_logging():
    read_config()
    init_clients()
    
    # Get calendar resources
    calendars = calendar_resource_client.get_resource_feed(uri=FEED_URI%urllib.quote(DOMAIN))
    # Select calendars by options
    filtered_calendars = [ \
        calendar for calendar in calendars.entry if \
        calendar.GetResourceEmail() is not None and fnmatch(calendar.GetResourceEmail(), options.select_pattern) ]
    filtered_calendar_emails_set = set([calendar.GetResourceEmail() for calendar in filtered_calendars])
    filtered_calendar_by_email_dict = dict(zip([calendar.GetResourceEmail() for calendar in filtered_calendars], filtered_calendars))

    if len(filtered_calendars) == 0:
        logging.warn("No calendars matched %s, aborting", options.select_pattern)
        sys.exit(0)

    # Fetch all domain users
    ACTING_AS(config.get(APP_CONFIG_SECTION, "admin_user"))
    all_users = apps_client.RetrieveAllUsers().entry

    # Get opt-out lists
    if not options.undo: optout_emails_set = get_optout_set()
    else: optout_emails_set = set()

    # Select domain users by options
    filtered_users = [ \
        email for email in \
        [ "%s@%s"%(user.login.user_name, DOMAIN) for user in all_users ] if \
        fnmatch(email, options.user_pattern) and \
        unicode(email).lower() not in optout_emails_set ]

    if len(filtered_users) == 0:
        logging.warn("Zero target users found, aborting")
        sys.exit(0)

    logging.info('Starting Calendar Resource to Contacts Group copy operation. Selection is "%s" (%d calendar(s)) and target is "%s" (%d user(s))',
        options.select_pattern, len(filtered_calendars), options.user_pattern, len(filtered_users))

    for target_user in filtered_users:
        ACTING_AS(target_user)

        if options.undo:
            undo(target_user)
            continue

        # Get users' groups
        groups = contacts_client.get_groups().entry

        # Find group by extended property
        (magic_group, magic_group_members) = get_magic_group(groups)
        magic_group_emails_set = set([ email.address for contact in magic_group_members for email in contact.email ])

        # Find My Contacts group
        my_contacts_group = filter(lambda group: group.system_group and group.system_group.id == MY_CONTACTS_ID, groups)
        if my_contacts_group: my_contacts_group = my_contacts_group[0]

        logging.info('%s: Using group called "%s" with %d members and ID %s',
            get_current_user(), magic_group.title.text,
            len(magic_group_members), magic_group.id.text)

        # Add new calendars (not already in the group) as contacts
        for calendar in filtered_calendars:
            if calendar.GetResourceEmail() not in magic_group_emails_set:
                new_contact = resource_to_contact(calendar)
                
                # Add the relevant groups
                new_contact.group_membership_info.append(gdata.contacts.data.GroupMembershipInfo(href=magic_group.id.text))
                if options.my_contacts and my_contacts_group:
                    new_contact.group_membership_info.append(gdata.contacts.data.GroupMembershipInfo(href=my_contacts_group.id.text))
                    
                # Set extended property
                extprop = gdata.data.ExtendedProperty()
                extprop.name = EXTPROP_CONTACT_NAME
                extprop.value = EXTPROP_CONTACT_VALUE
                new_contact.extended_property.append(extprop)
                
                logging.debug('%s: Creating contact "%s"',
                    get_current_user(), new_contact.name.full_name.text)
                request_feed.add_insert(new_contact)
                submit_batch()

        # Sync data for existing calendars that were added by the script and remove those that have been deleted
        for existing_contact in magic_group_members:
            if is_script_contact(existing_contact):
                calendar_to_copy = get_value_by_contact_email(filtered_calendar_by_email_dict, existing_contact)
                
                if calendar_to_copy:
                    # Sync data
                    calendar_contact = resource_to_contact(calendar_to_copy)
                    if sync_contact(calendar_contact, existing_contact):
                        logging.info('%s: Modifying contact "%s" with ID %s',
                            get_current_user(), existing_contact.name.full_name.text, existing_contact.id.text)
                        request_feed.add_update(existing_contact)
                        submit_batch()

                elif options.delete_old: # Surplus, delete?
                    logging.info('%s: Removing surplus auto-generated contact "%s" with ID %s',
                        get_current_user(), existing_contact.name.full_name.text, existing_contact.id.text)
                    request_feed.add_delete(entry=existing_contact)
                    submit_batch()


        submit_batch_final()
    
if __name__ == "__main__":
    main()
