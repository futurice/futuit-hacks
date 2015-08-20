import httplib2
import sys

from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

import gdata.client
import atom.http_core
from gdata.contacts.client import ContactsClient
from gdata.calendar_resource.client import CalendarResourceClient
from gdata.gauth import OAuth2TokenFromCredentials
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage

from options import options

GDATA_SERVICES = {
'contacts': ContactsClient,
'calendar_resource': CalendarResourceClient,}

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

def get_service_account_credentials(scopes=[], user_email=''):
    with file(options().service_account_pkcs12_file_path, 'rb') as f:
        key = f.read()
    return SignedJwtAssertionCredentials(options().service_account_email,
        key,
        scope=scopes,
        sub=user_email)

def get_credentials(scopes, email, storage_file='a_credentials_file'):
    if email:
        credentials = get_service_account_credentials(scopes=scopes, user_email=email)
    else:
        credentials = ensureOAuthCredentials(scopes=scopes, storage_file=storage_file)
    return credentials

def get_gdata_api(name, credentials, domain='', extra_kw={}):
    client = GDATA_SERVICES[name](domain=domain, **extra_kw)
    token = OAuth2TokenFromCredentials(credentials)
    return token.authorize(client)

def get_discovery_api(name, version, credentials):
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build(serviceName=name, version=version, http=http)

def calendar(email=None):
    return get_discovery_api(name='calendar',
            version='v3',
            credentials=get_credentials(scopes=[
                'https://www.googleapis.com/auth/calendar',
                'https://apps-apis.google.com/a/feeds/calendar/resource/',],
                email=email))

def calendar_resource(email=None):
    return get_gdata_api(name='calendar_resource',
            domain=options().domain,
            credentials=get_credentials(scopes=['https://apps-apis.google.com/a/feeds/calendar/resource/',],
            email=email,
            storage_file='gdata_credential_file'))

def contacts(email=None):
    return get_gdata_api(name='contacts',
            domain=options().domain,
            credentials=get_credentials(scopes=['https://www.google.com/m8/feeds',],
            email=email,
            storage_file='gdata_credential_file'))

def admin(email=None):
    return get_discovery_api(name='admin',
            version='directory_v1',
            credentials=get_credentials(scopes=[
                'https://www.googleapis.com/auth/admin.directory.group',
                'https://www.googleapis.com/auth/admin.directory.user',],
                email=email))

# http://stackoverflow.com/questions/23576729/getting-if-match-or-if-none-match-header-or-entry-etag-attribute-required-erro
def patched_post(client, entry, uri, auth_token=None, converter=None, desired_class=None, **kwargs):
    if converter is None and desired_class is None:
        desired_class = entry.__class__
    http_request = atom.http_core.HttpRequest()
    entry_string = entry.to_string(gdata.client.get_xml_version(client.api_version))
    entry_string = entry_string.replace('ns1', 'gd') # where the magic happens
    http_request.add_body_part(entry_string, 'application/atom+xml')
    return client.request(method='POST', uri=uri, auth_token=auth_token,
            http_request=http_request,
            converter=converter,
            desired_class=desired_class, **kwargs)

def patched_batch(client_instance, entry_feed):
    return patched_post(client_instance, entry_feed, 'https://www.google.com/m8/feeds/contacts/default/full/batch')

