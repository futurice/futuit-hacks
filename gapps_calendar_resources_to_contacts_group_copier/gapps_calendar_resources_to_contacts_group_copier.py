#!/usr/bin/env python
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
from operator import attrgetter as get, itemgetter as iget
from contextlib import closing

DEFAULT_REL = WORK_REL

from shared.google_apis import calendar_resource, contacts, admin, exhaust, Batch
from shared.dots import compare_object_values, err, dotset, dotget
from shared.fn import flatmap, filtermap
from shared.futurice import get_optout_set
from shared.implementation import get_magic_group, get_group_members, create_magic_group, is_script_contact, is_script_group, undo

os.environ.setdefault('PARSER', 'gapps_calendar_resources_to_contacts_group_copier.options')
os.environ.setdefault('ROOTDIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
from shared.options import options

def resources_to_contacts():
    # Get Calendar Resources
    calendars = calendar_resource(options=options()).get_resource_feed(uri=options().calendar_resource_feed).entry

    # Select Calendars by options
    filtered_calendars = filter(lambda cal: \
        fnmatch(cal.resource_email, options().select_pattern), calendars)
    filtered_calendar_by_email_dict = dict(zip(map(get('resource_email'), filtered_calendars), filtered_calendars))

    # Fetch all domain users
    all_users = exhaust(admin(options=options()).users().list, dict(domain=options().domain, maxResults=500), 'users')

    # Get opt-out lists
    # TODO: opt-out data should NOT be used (stale emails); move service to FUM
    optout_emails_set = set() if not options().undo else get_optout_set(options().optout_uri)

    # Select domain users by options
    filtered_users = filtermap(lambda user: fnmatch(user['primaryEmail'], options().user_pattern) and \
                unicode(user['primaryEmail']).lower() not in optout_emails_set,
                iget('primaryEmail'), all_users)

    logging.info('Starting Calendar Resource to Contacts Group copy operation. Selection is "%s" (%d calendar(s)) and target is "%s" (%d user(s))',
        options().select_pattern, len(filtered_calendars), options().user_pattern, len(filtered_users))

    for target_user in filtered_users:
        contacts_client = contacts(email=target_user, options=options())

        if options().undo:
            undo(contacts_client, target_user, ContactsFeed)
            continue

        # Get Contacts Groups for user
        groups = contacts_client.get_groups().entry

        # Find Contact Group by extended property
        magic_group = get_magic_group(groups) or create_magic_group(contacts_client)
        magic_group_members = get_group_members(contacts_client, magic_group)
        magic_group_emails_set = map(get('address'), flatmap(get('email'), magic_group_members))

        # Find "My Contacts" group in Contacts
        my_contacts_group = next(iter(
            filter(lambda group: group.system_group and group.system_group.id == options().my_contacts_id, groups)), None)

        logging.info('%s: Using group called "%s" with %d members and ID %s',
            target_user, magic_group.title.text, len(magic_group_members),
            magic_group.id.text)

        # Add new Calendar Resources as Contacts
        with closing(Batch(contacts_client, ContactsFeed)) as batch:
            for cal in filter(lambda x: \
                    x.resource_email not in magic_group_emails_set, filtered_calendars):
                new_contact = calendar_resource_to_contact(cal)

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
                batch.put('add_insert', new_contact)

        # Sync data for existing Calendar Resources that were added by the script. Remove those that have been deleted
        with closing(Batch(contacts_client, ContactsFeed)) as batch:
            for existing_contact in filter(is_script_contact, magic_group_members):
                calendar_resource_to_copy = get_value_by_contact_email(filtered_calendar_by_email_dict, existing_contact)

                if calendar_resource_to_copy:
                    calendar_contact = calendar_resource_to_contact(calendar_resource_to_copy)
                    if sync_contact(calendar_contact, existing_contact):
                        logging.info('%s: Modifying contact "%s" with ID %s',
                            target_user, existing_contact.name.full_name.text, existing_contact.id.text)
                        batch.put('add_update', existing_contact)
                elif options().delete_old:
                    logging.info('%s: Removing surplus auto-generated contact "%s" with ID %s',
                        target_user, existing_contact.name.full_name.text, existing_contact.id.text)
                    batch.put('add_delete', existing_contact)


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

def calendar_resource_to_contact(calendar):
    """Converts a Calendar Resource to a Contact."""
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
    """Resolve Contact to email key in email_dict and return the first matching value."""

    matching_emails = filter(
        lambda email: email.address and email.address.lower() in email_dict,
        contact.email)

    if not matching_emails:
        return None

    contact_emails = filter(
        lambda email: email.primary == 'true' and email.rel == DEFAULT_REL,
        matching_emails)

    if not contact_emails:
        contact_emails = matching_emails

    return email_dict[contact_emails[0].address.lower()]

def main():
    resources_to_contacts()
    
if __name__ == "__main__":
    main()

