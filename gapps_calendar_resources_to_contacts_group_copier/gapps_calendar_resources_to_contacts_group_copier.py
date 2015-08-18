#!/usr/bin/env python

"""A script that copies select Calendar Resources as contacts under a set group for selected organization's members."""
__author__ = "vsin"
__version__ = "1.0.0"

import atom.data
import gdata.contacts.data
import gdata.contacts.client
from gdata.contacts.client import ContactsQuery
from gdata.gauth import OAuth2TokenFromCredentials
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage

import hashlib
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

APP_CONFIG_SECTION = "application"
PARAM_CONFIG_SECTION = "default_params"
DEFAULT_REL = gdata.data.WORK_REL
OPTOUT_URI = "https://intra.futurice.com/u/contacts/api/get_opted_out"
OPTOUT_SETTING = "optout_rooms"
MY_CONTACTS_ID = "Contacts"

def ensureOAuthCredentials(secrets_file='client_secrets.json',
        storage_file='a_credentials_file',
        redirect_uri='https://localhost:8000/oauth2callback',
        scopes=[]):
    storage = Storage(storage_file)
    credentials = storage.get()
    if not credentials:
        flow = flow_from_clientsecrets(filename=secrets_file,
                scope=scopes,
                redirect_uri=redirect_uri,)
        # Try to get refresh token in response. Taken from:
        # https://developers.google.com/glass/develop/mirror/authorization
        flow.params['approval_prompt'] = 'force'
        auth_uri = flow.step1_get_authorize_url()
        print auth_uri
        code = raw_input("Auth token: ")
        credentials = flow.step2_exchange(code)
        storage.put(credentials)
    return credentials

import httplib2
import sys
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

SERVICE_ACCOUNT_EMAIL = '573247622343-dm1dkn76ei4jqk4856jo7551ddvp6eke@developer.gserviceaccount.com'
SERVICE_ACCOUNT_PKCS12_FILE_PATH = 'service.p12'
def get_service_account_credentials(scopes=[], user_email=''):
    with file(SERVICE_ACCOUNT_PKCS12_FILE_PATH, 'rb') as f:
        key = f.read()
    return SignedJwtAssertionCredentials(SERVICE_ACCOUNT_EMAIL,
        key,
        scope=scopes,
        sub=user_email)

def get_credentials(scopes, email):
    if email:
        credentials = get_service_account_credentials(scopes=scopes, user_email=email)
    else:
        storage_file = 'credentials_{}'.format(hashlib.md5(json.dumps(scopes)).hexdigest())
        storage_file = 'a_credentials_file'
        credentials = ensureOAuthCredentials(scopes=scopes, storage_file=storage_file)
    return credentials

GDATA_SERVICES = {'contacts': gdata.contacts.client.ContactsClient,}
def get_gdata_api(name, domain='', scopes=[], email=None, extra_kw={}):
    client = GDATA_SERVICES[name](domain=domain, **extra_kw)
    token = OAuth2TokenFromCredentials(get_credentials(scopes=scopes, email=email))
    return token.authorize(client)

def get_discovery_api(name, version, scopes=[], email=None):
    http = httplib2.Http()
    http = get_credentials(scopes=scopes, email=email).authorize(http)
    return build(serviceName=name, version=version, http=http)

from options import parse_options
class Client(object):
    def __init__(self):
        self.read_config()

    def calendar(self, email=None):
        return get_discovery_api(name='calendar',
                version='v3',
                scopes=['https://www.googleapis.com/auth/calendar',
                    'https://apps-apis.google.com/a/feeds/calendar/resource/',],
                email=email)

    def contacts(self, email=None):
        return get_gdata_api(name='contacts',
                domain=self.options.domain,
                scopes=['https://www.google.com/m8/feeds'],
                email=email)

    def admin(self, email=None):
        return get_discovery_api(name='admin',
                version='directory_v1',
                scopes=['https://www.googleapis.com/auth/admin.directory.group',
                    'https://www.googleapis.com/auth/admin.directory.user',],
                email=email)

    def request_feed(self):
        return gdata.contacts.data.ContactsFeed()

    def read_config(self):
        self.options = options = parse_options()
        logging.config.fileConfig(self.options.log_config)
        config = ConfigParser.RawConfigParser()
        config.read(options.config)

        # Set default params
        if config.has_section(PARAM_CONFIG_SECTION):
            for param in config.options(PARAM_CONFIG_SECTION):
                if not hasattr(options, param) or getattr(options, param) is None:
                    setattr(options, param, config.get(PARAM_CONFIG_SECTION, param))

        # Set globals
        if config.has_section(APP_CONFIG_SECTION):
            for param in config.options(APP_CONFIG_SECTION):
                if not hasattr(options, param) or getattr(options, param) is None:
                    setattr(options, param, config.get(APP_CONFIG_SECTION, param))

    def resources_to_contacts(self):
        # Get calendar resources
        calendars = self.calendar().calendarList().list(maxResults=250).execute()
        calendars = calendars.get('items', [])
        # Select calendars by options
        filtered_calendars = [ \
            calendar for calendar in calendars if \
            calendar['id'] is not None and fnmatch(calendar['id'], self.options.select_pattern) ]
        filtered_calendar_emails_set = set([calendar['id'] for calendar in filtered_calendars])
        filtered_calendar_by_email_dict = dict(zip([calendar['id'] for calendar in filtered_calendars], filtered_calendars))

        if len(filtered_calendars) == 0:
            logging.warn("No calendars matched %s, aborting", self.options.select_pattern)
            sys.exit(0)

        # Fetch all domain users
        all_users = self.admin().users().list(domain=self.options.domain, maxResults=500).execute()
        all_users = all_users.get('users', [])

        # Get opt-out lists
        # TODO: opt-out data should NOT be used (stale emails); move service to FUM
        if not self.options.undo:
            optout_emails_set = get_optout_set()
        else:
            optout_emails_set = set()

        # Select domain users by options
        filtered_users = [ \
            email for email in \
            [user['primaryEmail'] for user in all_users] if \
            fnmatch(email, self.options.user_pattern) and \
            unicode(email).lower() not in optout_emails_set ]

        if len(filtered_users) == 0:
            logging.warn("Zero target users found, aborting")
            sys.exit(0)

        logging.info('Starting Calendar Resource to Contacts Group copy operation. Selection is "%s" (%d calendar(s)) and target is "%s" (%d user(s))',
            self.options.select_pattern, len(filtered_calendars), self.options.user_pattern, len(filtered_users))

        for target_user in filtered_users:
            request_feed = gdata.contacts.data.ContactsFeed()
            contacts_client = self.contacts(email=target_user)
            admin_client = self.admin(email=target_user)

            if self.options.undo:
                undo(target_user)
                continue

            # Get users Contacts groups
            groups = contacts_client.get_groups().entry

            # Find Contact group by extended property
            magic_group = self.get_magic_group(groups)
            magic_group_members = self.get_group_members(contacts_client, magic_group)

            if not magic_group:
                magic_group = self.create_magic_group(contacts_client)
                magic_group_members = self.get_group_members(contacts_client, magic_group)

            magic_group_emails_set = set([ email.address for contact in magic_group_members for email in contact.email ])

            # Find My Contacts group
            my_contacts_group = next(iter(
                filter(lambda group: group.system_group and group.system_group.id == MY_CONTACTS_ID, groups)), None)

            logging.info('%s: Using group called "%s" with %d members and ID %s',
                target_user, magic_group.title.text, len(magic_group_members),
                magic_group.id.text)

            # Add new calendars (not already in the group) as contacts
            # batched
            for calendar in filtered_calendars:
                if calendar['id'] not in magic_group_emails_set:
                    new_contact = resource_to_contact(calendar)
                    
                    # Add the relevant groups
                    new_contact.group_membership_info.append(gdata.contacts.data.GroupMembershipInfo(href=magic_group.id.text))
                    if self.options.my_contacts and my_contacts_group:
                        new_contact.group_membership_info.append(gdata.contacts.data.GroupMembershipInfo(href=my_contacts_group.id.text))
                        
                    # Set extended property
                    extprop = gdata.data.ExtendedProperty()
                    extprop.name = self.options.contact_extended_property_name
                    extprop.value = self.options.contact_extended_property_name
                    new_contact.extended_property.append(extprop)
                    
                    logging.debug('%s: Creating contact "%s"', target_user,
                            new_contact.name.full_name.text)
                    request_feed.add_insert(new_contact)
                self.submit_batch(contacts_client, request_feed)
            self.submit_batch(contacts_client, request_feed, force=True)

            # Sync data for existing calendars that were added by the script and remove those that have been deleted
            # non-batch
            for existing_contact in magic_group_members:
                if is_script_contact(existing_contact):
                    calendar_to_copy = get_value_by_contact_email(filtered_calendar_by_email_dict, existing_contact)
                    
                    if calendar_to_copy:
                        # Sync data
                        calendar_contact = resource_to_contact(calendar_to_copy)
                        if sync_contact(calendar_contact, existing_contact):
                            logging.info('%s: Modifying contact "%s" with ID %s',
                                target_user, existing_contact.name.full_name.text, existing_contact.id.text)

                            try:
                                contacts_client.update(existing_contact)
                            except:
                                logging.exception('While updating 1 contact:')

                    elif self.options.delete_old: # Surplus, delete?
                        logging.info('%s: Removing surplus auto-generated contact "%s" with ID %s',
                            target_user, existing_contact.name.full_name.text, existing_contact.id.text)

                        try:
                            contacts_client.delete(existing_contact)
                        except:
                            logging.exception('While deleting 1 contact:')

    def submit_batch(self, contacts_client, feed, force=False):
        if not force and len(feed.entry) < int(self.options.config.batch_max):
            return # Wait for more requests

        result_feed = contacts_client.execute_batch(feed)
        for result in result_feed.entry:
            try: status_code = int(result.batch_status.code)
            except ValueError: status_code = -1
            if status_code < 200 or status_code >= 400:
                logging.warn("Error %d (%s) while %s'ing batch ID %s = %s (%s)",
                    status_code,
                    result.batch_status.reason,
                    result.batch_operation.type,
                    result.batch_id.text,
                    result.id and result.id.text or result.get_id(),
                    result.name and result.name.full_name and result.name.full_name or "name unknown")

    def get_magic_group(self, groups):
        return next(iter(filter(self.is_script_group, groups)), None)

    def get_group_members(self, contacts_client, group):
        if not group: return []
        contacts_query = gdata.contacts.client.ContactsQuery()
        contacts_query.group = group.id.text
        contacts_query.max_results = self.options.max_contacts
        return contacts_client.get_contacts(q=contacts_query).entry

    def create_magic_group(self, contacts_client):
        new_group = gdata.contacts.data.GroupEntry()
        new_group.title = atom.data.Title(self.options.group)

        extprop = gdata.data.ExtendedProperty()
        extprop.name = self.options.group_extended_property_name
        extprop.value = self.options.group_extended_property_value
        new_group.extended_property.append(extprop)

        return contacts_client.create_group(new_group=new_group)

    @property
    def is_script_contact(self):
        # Return if contact was added by the script
        return lambda contact: len(filter(
            lambda extprop: extprop.name == self.options.contact_extended_property_name \
                    and extprop.value == self.options.contact_extended_property_value,
            contact.extended_property)) > 0

    @property
    def is_script_group(self):
        # Return if contact group was added by the script
        return lambda group: len(filter(
            lambda extprop: extprop.name == self.options.group_extended_property_name \
                    and extprop.value == self.options.group_extended_property_value,
            group.extended_property)) > 0

    def undo(self, target_user):
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
        magic_group = get_magic_group(groups)
        if magic_group:
            for group_member in self.get_group_members(magic_group):
                if group_member.id.text not in removed_ids and is_script_contact(group_member):
                    logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                        get_current_user(), group_member.name.full_name.text, group_member.id.text)
                    request_feed.add_delete(entry=group_member)
                    submit_batch()

            # Remove group
            contacts_client.delete_group(magic_group)
            logging.info('%s: Removing auto-generated group "%s" with ID %s',
                get_current_user(), magic_group.title.text, magic_group.id.text)

def get_optout_set():
    """Returns a set of user-names who wish to opt-out from synchronization."""

    optout_json = json.load(urllib.urlopen(OPTOUT_URI))
    if u'settings' in optout_json and \
        unicode(OPTOUT_SETTING) in optout_json[u'settings']:
        return set(map(lambda user_email: user_email.lower(), optout_json[u'settings'][u'optout_employees']))

    raise Exception("Could not understand opt-out data format")


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
    c = Client()
    c.resources_to_contacts()
    
if __name__ == "__main__":
    main()

