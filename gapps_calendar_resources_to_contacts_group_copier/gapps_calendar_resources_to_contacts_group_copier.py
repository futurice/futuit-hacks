#!/usr/bin/env python
"""A script that copies select Calendar Resources as Contacts under a set group for selected organization's members."""

from atom.data import (Title, Content)
from gdata.data import (ExtendedProperty, Name, GivenName, FullName, FamilyName, Email, WORK_REL)
from gdata.contacts.data import (ContactsFeed, GroupMembershipInfo, GroupEntry, ContactEntry)
from gdata.contacts.client import ContactsQuery

import sys
import copy
import os.path
import logging
import logging.config
from fnmatch import fnmatch
import urllib
import json

DEFAULT_REL = WORK_REL

from google_apis import calendar, calendar_resource, contacts, admin, patched_batch
from options import options
from dots import compare_object_values, err, dotset, dotget

from operator import attrgetter as get, itemgetter as iget
import itertools

def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))

def filtermap(cond, match, *iter):
    return map(match, filter(cond, *iter))

def exhaust(resource):
    # TODO: paginate to get all results
    return resource

def resources_to_contacts():
    # Get calendar resources
    calendars = calendar_resource().get_resource_feed(uri=options().calendar_resource_feed).entry

    # Select calendars by options
    filtered_calendars = filter(lambda cal: \
        fnmatch(cal.resource_email, options().select_pattern), calendars)
    filtered_calendar_by_email_dict = dict(zip([cal.resource_email for cal in filtered_calendars], filtered_calendars))

    # Fetch all domain users
    all_users = admin().users().list(domain=options().domain, maxResults=500).execute()
    all_users = all_users.get('users', [])

    # Get opt-out lists
    # TODO: opt-out data should NOT be used (stale emails); move service to FUM
    optout_emails_set = set() if not options().undo else get_optout_set()

    # Select domain users by options
    filtered_users = filtermap(lambda user: fnmatch(user['primaryEmail'], options().user_pattern) and \
                unicode(user['primaryEmail']).lower() not in optout_emails_set,
                iget('primaryEmail'), all_users)

    logging.info('Starting Calendar Resource to Contacts Group copy operation. Selection is "%s" (%d calendar(s)) and target is "%s" (%d user(s))',
        options().select_pattern, len(filtered_calendars), options().user_pattern, len(filtered_users))

    for target_user in filtered_users:
        contacts_client = contacts(email=target_user)

        if options().undo:
            undo(contacts_client, target_user)
            continue

        # Get users Contacts groups
        groups = contacts_client.get_groups().entry

        # Find Contact group by extended property
        magic_group = get_magic_group(groups) or create_magic_group(contacts_client)
        magic_group_members = get_group_members(contacts_client, magic_group)
        magic_group_emails_set = map(get('address'), flatmap(get('email'), magic_group_members))

        # Find My Contacts group
        my_contacts_group = next(iter(
            filter(lambda group: group.system_group and group.system_group.id == options().my_contacts_id, groups)), None)

        logging.info('%s: Using group called "%s" with %d members and ID %s',
            target_user, magic_group.title.text, len(magic_group_members),
            magic_group.id.text)

        # Add new resources as contacts
        request_feed = ContactsFeed()
        for cal in filter(lambda x: \
                x.resource_email not in magic_group_emails_set, filtered_calendars):
            new_contact = resource_to_contact(cal)

            # Add Contact to the relevant groups
            new_contact.group_membership_info.append(GroupMembershipInfo(href=magic_group.id.text))
            if options().my_contacts and my_contacts_group:
                new_contact.group_membership_info.append(GroupMembershipInfo(href=my_contacts_group.id.text))

            # Set Contact extended property
            extprop = ExtendedProperty()
            extprop.name = options().contact_extended_property_name
            extprop.value = options().contact_extended_property_value
            new_contact.extended_property.append(extprop)

            logging.debug('%s: Creating contact "%s"', target_user,
                    new_contact.name.full_name.text)
            request_feed.add_insert(new_contact)
            submit_batch(contacts_client, request_feed)
        submit_batch(contacts_client, request_feed, force=True)

        # Sync data for existing calendars that were added by the script and remove those that have been deleted
        request_feed = ContactsFeed()
        for existing_contact in filter(is_script_contact, magic_group_members):
            calendar_to_copy = get_value_by_contact_email(filtered_calendar_by_email_dict, existing_contact)

            if calendar_to_copy:
                # Sync data
                calendar_contact = resource_to_contact(calendar_to_copy)
                if sync_contact(calendar_contact, existing_contact):
                    logging.info('%s: Modifying contact "%s" with ID %s',
                        target_user, existing_contact.name.full_name.text, existing_contact.id.text)
                    request_feed.add_update(existing_contact)
            elif options().delete_old: # Surplus, delete?
                logging.info('%s: Removing surplus auto-generated contact "%s" with ID %s',
                    target_user, existing_contact.name.full_name.text, existing_contact.id.text)
                request_feed.add_delete(existing_contact)
            submit_batch(contacts_client, request_feed)
        submit_batch(contacts_client, request_feed, force=True)

def submit_batch(contacts_client, feed, force=False):
    if not force and len(feed.entry) < int(options().batch_max):
        return # Wait for more requests

    result_feed = patched_batch(contacts_client, feed)
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

def get_magic_group(groups):
    return next(iter(filter(is_script_group, groups)), None)

def get_group_members(contacts_client, group):
    if not group:
        return []
    contacts_query = ContactsQuery()
    contacts_query.group = group.id.text
    contacts_query.max_results = options().max_contacts
    return contacts_client.get_contacts(q=contacts_query).entry

def create_magic_group(contacts_client):
    logging.info('Creating magic group: {}'.format(options().group))

    new_group = GroupEntry()
    new_group.title = Title(options().group)

    extprop = ExtendedProperty()
    extprop.name = options().group_extended_property_name
    extprop.value = options().group_extended_property_value
    new_group.extended_property.append(extprop)

    return contacts_client.create_group(new_group=new_group)

def is_script_contact(contact):
    return any(filter(
        lambda prop: prop.name == options().contact_extended_property_name \
                and prop.value == options().contact_extended_property_value,
            contact.extended_property))

def is_script_group(group):
    return any(filter(
        lambda prop: prop.name == options().group_extended_property_name \
                and prop.value == options().group_extended_property_value,
        group.extended_property))

def undo(contacts_client, target_user):
    # Let's delete users by global list and group list on the off chance the global list
    # is not comprehensive due to its size exceeding query limits.
    removed_ids = set()

    contacts = contacts_client.get_contacts().entry
    request_feed = ContactsFeed()
    for contact in filter(is_script_contact, contacts):
        logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                target_user, contact.name.full_name.text, contact.id.text)
        removed_ids.add(contact.id.text)
        request_feed.add_delete(entry=contact)
        submit_batch(contacts_client, request_feed)
    submit_batch(contacts_client, request_feed, force=True)
    
    # Get Contact groups
    groups = contacts_client.get_groups().entry
    magic_group = get_magic_group(groups)
    if magic_group:
        request_feed = ContactsFeed()
        for group_member in filter(is_script_contact, get_group_members(contacts_client, magic_group)):
            if group_member.id.text not in removed_ids:
                logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                    target_user, group_member.name.full_name.text, group_member.id.text)
                request_feed.add_delete(entry=group_member)
                submit_batch(contacts_client, request_feed)
        submit_batch(contacts_client, request_feed, force=True)

        # Remove group
        contacts_client.delete_group(magic_group)
        logging.info('%s: Removing auto-generated group "%s" with ID %s',
                target_user, magic_group.title.text, magic_group.id.text)

def get_optout_set():
    """Returns a set of user-names who wish to opt-out from synchronization."""
    return []

    optout_json = json.load(urllib.urlopen(config().optout_uri))
    if u'settings' in optout_json and \
        unicode('optout_rooms') in optout_json[u'settings']:
        return set(map(lambda user_email: user_email.lower(), optout_json[u'settings'][u'optout_employees']))

    raise Exception("Could not understand opt-out data format")


def sync_contact(source, target):
    """Copies data from source contact to target contact and returns changes, if target was modified."""
    keys = ['content','name','name.given_name','name.family_name','name.full_name']
    changes = compare_object_values(source, target, keys,
            cmp=err(lambda x,y: x.text==y.text),
            cmp_value=lambda x: '{}.text'.format(x),
            flat=True,
            allow_empty_values=False)
    for k, v in changes.iteritems():
        dotset(target, k, dotget(source, k))
    return changes

def resource_to_contact(calendar):
    """Converts a Calendar Resource object to a Contact object."""
    contact = ContactEntry()
    contact.name = Name(
        given_name=GivenName(text=calendar.resource_common_name),
        family_name=FamilyName(text=options().family_name),
        full_name=FullName(text=calendar.resource_common_name))
    contact.content = Content(text=calendar.resource_description)
    contact.email.append(Email(address=calendar.resource_email,
        primary='true', display_name=calendar.resource_common_name, rel=DEFAULT_REL))
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
        contact,
        map(lambda email: email.address, contact_emails),
        contact.name and contact.name.full_name and contact.name.full_name.text or "(unknown)",
        contact.id and contact.id.text)

    return email_dict[contact_emails[0].address.lower()]

def main():
    resources_to_contacts()
    
if __name__ == "__main__":
    main()

