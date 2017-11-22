
LDAP_CONNECTION = {
    'protocol': 'ldaps',
    'host': 'ldap-server-host.futurice.com',
    'port': 636,
    'bind_dn': "",
    'bind_pwd': "",
    'base_dn': "dc=futurice,dc=com",
}

DOMAIN = "futurice.com"
COMPANY_NAME = "futurice"
EXTENDED_DOMAIN_LIST = [u"@futurice.fi", u"@futurice.eu"]

from local_LCI_settings import *
