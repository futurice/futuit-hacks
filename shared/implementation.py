from shared.options import options

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
