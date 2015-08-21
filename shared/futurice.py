import urllib
import json

def get_optout_set(uri):
    """Returns a set of user-names who wish to opt-out from synchronization."""
    return []

    optout_json = json.load(urllib.urlopen(uri))
    if u'settings' in optout_json and \
        unicode('optout_rooms') in optout_json[u'settings']:
        return set(map(lambda user_email: user_email.lower(), optout_json[u'settings'][u'optout_employees']))

    raise Exception("Could not understand opt-out data format")
