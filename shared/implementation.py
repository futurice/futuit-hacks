from contextlib import closing
import logging

from shared.options import options
from shared.google_apis import Batch

from atom.data import Title
from gdata.data import ExtendedProperty
from gdata.contacts.data import GroupEntry
from gdata.contacts.client import ContactsQuery

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

def undo(contacts_client, target_user, feed):
    # Let's delete users by global list and group list on the off chance the global list
    # is not comprehensive due to its size exceeding query limits.
    removed_ids = set()

    contacts = contacts_client.get_contacts().entry

    with closing(Batch(contacts_client, feed)) as batch:
        for contact in filter(is_script_contact, contacts):
            logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                    target_user, contact.name.full_name.text, contact.id.text)
            removed_ids.add(contact.id.text)
            batch.put('add_delete', contact)
    
    # Get Contact groups
    groups = contacts_client.get_groups().entry
    magic_group = get_magic_group(groups)
    if magic_group:
        with closing(Batch(contacts_client, feed)) as batch:
            for group_member in filter(is_script_contact, get_group_members(contacts_client, magic_group)):
                if group_member.id.text not in removed_ids:
                    logging.info('%s: Removing auto-generated contact "%s" with ID %s',
                        target_user, group_member.name.full_name.text, group_member.id.text)
                    batch.put('add_delete', group_member)

        # Remove group
        contacts_client.delete_group(magic_group)
        logging.info('%s: Removing auto-generated group "%s" with ID %s',
                target_user, magic_group.title.text, magic_group.id.text)
