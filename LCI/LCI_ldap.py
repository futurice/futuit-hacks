
import ldap
import ldap.modlist as modlist

from LCI_util import *
from LCI_settings import *

_LDAP_WRITE_DELAY = 0.0

_GROUP_OBJECTCLASSES = ['groupOfUniqueNames', 'top', 'posixGroup', \
    'sambaGroupMapping', 'mailrecipient', 'google']

_CUSTOMER_OBJECTCLASSES = ['inetOrgPerson', 'ntUser', 'account', 'hostObject',\
    'posixAccount', 'shadowAccount', 'sambaSamAccount', 'organizationalPerson',\
    'top', 'person', 'google']

def bind():
    """
    try:
        conn = ldap.open(LDAP_CONNECTION['host'])
        conn.protocol_version = ldap.VERSION3
        conn.simple_bind_s(LDAP_CONNECTION['bind_dn'], LDAP_CONNECTION['bind_pwd'])
        return conn;
    except ldap.LDAPError, e:
        logging.critical("LDAP error in bind: %s", e)
        sys.exit(1)
    """
    try:
        ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, 60)
        ldapurl = LDAP_CONNECTION['protocol'] + \
            "://" + LDAP_CONNECTION['host'] + \
            ":" + str(LDAP_CONNECTION['port'])
        conn = ldap.initialize( ldapurl )
        ldap.protocol_version = ldap.VERSION3        
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
        conn.simple_bind_s(LDAP_CONNECTION['bind_dn'], LDAP_CONNECTION['bind_pwd'])
        return conn;
    except ldap.LDAPError, e:
        logging.critical("LDAP error in bind: %s", e)
        sys.exit(1)
    
def fetch_email_to_dn_mapping(conn, baseDN=LDAP_CONNECTION['base_dn']):
    """
    Return a dict of "email address" -> "dn value" for all people
    """
    ## The next lines will also need to be changed to support your search requirements and directory
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["mail"]

    baseDN = "ou=People," + LDAP_CONNECTION['base_dn']
    searchFilter = "uid=*"
    l = conn

    mail_dn_mapping = {}

    try:
	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
	#result_set = []
	while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    if len(result_data[0]) != 2:
                        logging.warning("Unexpected result_data in mail mapping creation: '%s'." % result_data)
                        LCI_pp.pprint(result_data)
                    elif 'mail' in result_data[0][1].keys():
                        user_mail = result_data[0][1]['mail'][0].lower()
                        #LCI_pp.pprint(result_data[0][1]['mail'][0].lower())
                        user_dn = result_data[0][0]
                        mail_dn_mapping[user_mail] = user_dn
                    else:
                        logging.debug("Missing mail attribute value or unexpected result data when creating mail-to-dn -mapping in: %s" % result_data)
                    
                    #result_set.append(result_data)
        
	logging.info("Email lookup mapping result size: %s" % len(mail_dn_mapping))
        return mail_dn_mapping

    except ldap.LDAPError, e:
	logging.critical("LDAP error when creating mail mapping: %s" % e)

def get_group_used_gidnumbers(conn):
    """
    Get all used gidnumbers.
    returns list
    """
    retrieveAttributes = ["gidNumber"]
    #searchScope = ldap.SCOPE_SUBTREE
    searchScope = ldap.SCOPE_ONELEVEL
    baseDN = "ou=Groups," + LDAP_CONNECTION['base_dn']
    searchFilter = "cn=*"
    l = conn
    
    gidlist = []

    try:
	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
	#result_set = []
	while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    if len(result_data[0]) != 2:
                        logging.warning("Unexpected result_data in existing gidlist creation: '%s'." % result_data)
                        LCI_pp.pprint(result_data)
                    elif 'gidNumber' in result_data[0][1].keys():
                        gidlist.append(result_data[0][1]['gidNumber'][0])
                    else:
                        logging.debug("Missing gidNumber attribute value or unexpected result data when creating gidlist in: %s" % result_data)
                    
                    #result_set.append(result_data)
        
	logging.info("Used gidlist result size: %s" % len(gidlist))
        return gidlist

    except ldap.LDAPError, e:
	logging.critical("LDAP error when creating gID list: %s" % e)

def get_used_uidnumbers(conn):
    """
    Get all used gidnumbers.
    returns list
    """
    retrieveAttributes = ["uidNumber"]
    #searchScope = ldap.SCOPE_SUBTREE
    searchScope = ldap.SCOPE_ONELEVEL
    baseDN = "ou=People," + LDAP_CONNECTION['base_dn']
    searchFilter = "cn=*"
    l = conn
    
    uidlist = []

    try:
	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
	#result_set = []
	while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    if len(result_data[0]) != 2:
                        logging.warning("Unexpected result_data in existing uidlist creation: '%s'." % result_data)
                        LCI_pp.pprint(result_data)
                    elif 'uidNumber' in result_data[0][1].keys():
                        uidlist.append(result_data[0][1]['uidNumber'][0])
                    else:
                        logging.debug("Missing uidNumber attribute value or unexpected result data when creating uidlist in: %s" % result_data)
                    
                    #result_set.append(result_data)
        
	logging.info("Used uidnumber list result size: %s" % len(uidlist))
        return uidlist

    except ldap.LDAPError, e:
	logging.critical("LDAP error when creating uID list: %s" % e)

def get_used_uids(conn):
    """
    Get all used uids.
    returns list
    """
    retrieveAttributes = ["uid"]
    #searchScope = ldap.SCOPE_SUBTREE
    searchScope = ldap.SCOPE_ONELEVEL
    baseDN = "ou=People," + LDAP_CONNECTION['base_dn']
    searchFilter = "cn=*"
    l = conn
    
    uidlist = []

    try:
	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
	#result_set = []
	while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    if len(result_data[0]) != 2:
                        logging.warning("Unexpected result_data in existing uidlist creation: '%s'." % result_data)
                        LCI_pp.pprint(result_data)
                    elif 'uid' in result_data[0][1].keys():
                        uidlist.append(result_data[0][1]['uid'][0])
                    else:
                        logging.debug("Missing uid attribute value or unexpected result data when creating uidlist in: %s" % result_data)
                    
                    #result_set.append(result_data)
        
	logging.info("Used uidlist result size: %s" % len(uidlist))
        return uidlist

    except ldap.LDAPError, e:
	logging.critical("LDAP error when creating uID list: %s" % e)
    

def fetch_dg_dn_mapping(conn, baseDN=LDAP_CONNECTION['base_dn']):
    """
    Return a dict of existing groups, that contain their DN value
    """
    ## The next lines will also need to be changed to support your search requirements and directory
    searchScope = ldap.SCOPE_ONELEVEL
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["cn"]

    baseDN = "ou=Groups," + LDAP_CONNECTION['base_dn']
    searchFilter = "cn=*"
    l = conn

    group_dn_mapping = {}

    try:
	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
	#result_set = []
	while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    if len(result_data[0]) != 2:
                        logging.warning("Unexpected result_data in existing DG list creation: '%s'." % result_data)
                        LCI_pp.pprint(result_data)
                    elif 'cn' in result_data[0][1].keys():
                        dg_cn = result_data[0][1]['cn'][0].lower()
                        dg_dn = result_data[0][0]
                        group_dn_mapping[dg_cn] = dg_dn
                    else:
                        logging.debug("Missing CN attribute value or unexpected result data when creating  in: %s" % result_data)
                    
                    #result_set.append(result_data)
        
	logging.info("DG-DN lookup mapping result size: %s" % len(group_dn_mapping))
        return group_dn_mapping

    except ldap.LDAPError, e:
	logging.critical("LDAP error when creating DG-DN mapping: %s" % e)


def add_proxy_attributes(dn_aliases=None):
    """
    This will push the new proxyAddresses (aliases) to LDAP.
    Should log ERROR for every failed modification.
    """
    if not dn_aliases:
        logging.critical("No values to push.")
        sys.exit(1)

    successes, errors = (0,0)
    
    for dn_alias,aliaslist in dn_aliases.iteritems():
        # Debugging, should be OK at 0.0
        from time import sleep
        sleep(_LDAP_WRITE_DELAY)

        conn = bind()
        mod_tuple = [(ldap.MOD_REPLACE, "proxyaddress", aliaslist)]
        logging.info("Trying modify, dn_alias: %s, mod-three-tuple: %s." % (dn_alias, mod_tuple))
        try:
            conn.modify_s(dn_alias, mod_tuple)
            successes += 1
        except ldap.LDAPError, e:
            logging.error("FAILED MODIFY, dn_alias: %s, mod-three-tuple: %s. Error: %s" % (dn_alias, mod_tuple, e))
            errors += 1
        
        conn.unbind_s()

    logging.info("Create proxyaddresses done. Successes: %d, errors: %d." % (successes, errors))


def create_dgroups(create_groups_email_as_user_dn):
    """
    Create distribution groups with values in them.
    We've checked that these don't exist.
    """
    successes, errors = (0,0)
    
    logging.info("Pushing groups to LDAP, please wait ...")
    
    for group, groupval in create_groups_email_as_user_dn.iteritems():
        dn = "cn="+ group +",ou=Groups," + LDAP_CONNECTION['base_dn']
        groupval['objectclass'] = _GROUP_OBJECTCLASSES      
        logging.info("Trying to create group with DN '%s'." % (dn))
        logging.debug("Group DN '%s' content: '%s'." % (dn, LCI_pp.pformat(groupval)))
        
        conn = bind()
        ldif = modlist.addModlist(groupval)
        
        # Debugging, should be OK at 0.0
        from time import sleep
        sleep(_LDAP_WRITE_DELAY)
        #raw_input("Press Enter to continue...")
        
        try:
            conn.add_s(dn, ldif)
            successes += 1
        except ldap.LDAPError, e:
            errors += 1
            logging.error("FAILED CREATE, dn: %s, ldif: %s. Error: %s" % (dn, ldif, e))
        
        conn.unbind_s()
    
    logging.info("Create distribution groups done. Successes: %d, errors: %d." % (successes, errors))

def remove_dgroups(remove_groups_email_as_user_dn):
    """
    Create distribution groups with values in them.
    We've checked that these don't exist.
    """
    successes, errors = (0,0)
    
    logging.info("Removing groups to LDAP, please wait ...")
    
    for group, groupval in remove_groups_email_as_user_dn.iteritems():
        dn = "cn="+ group +",ou=Groups," + LDAP_CONNECTION['base_dn']
        groupval['objectclass'] = _GROUP_OBJECTCLASSES      
        logging.info("Trying to remove group with DN '%s'." % (dn))
        
        conn = bind()
        
        # Debugging, should be OK at 0.0
        from time import sleep
        sleep(_LDAP_WRITE_DELAY)
        #raw_input("Press Enter to continue...")
        
        try:
            conn.delete_s(dn)
            successes += 1
        except ldap.LDAPError, e:
            errors += 1
            logging.error("FAILED DELETE, dn: %s. Error: %s" % (dn, e))
        
        conn.unbind_s()
    
    logging.info("Delete distribution groups done. Successes: %d, errors: %d." % (successes, errors))

def create_mailcontacts(customerdict):
    """
    Create customercontacts
    """
    successes, errors = (0,0)
    
    logging.info("Pushing contacts to LDAP, please wait ...")

    for customer, customerval in customerdict.iteritems():
        dn = "uid="+ customer +",ou=People," + LDAP_CONNECTION['base_dn']
        customerval['objectclass'] = _CUSTOMER_OBJECTCLASSES      
        logging.debug("Trying to create group with DN '%s' and content '%s'." % (dn, LCI_pp.pformat(customerval)))
        
        conn = bind()
        ldif = modlist.addModlist(customerval)
        
        from time import sleep
        sleep(_LDAP_WRITE_DELAY)
        
        try:
            conn.add_s(dn, ldif)
            successes += 1
        except ldap.LDAPError, e:
            errors += 1
            logging.error("FAILED CREATE, dn: %s, ldif: %s. Error: %s" % (dn, ldif, e))
        
        conn.unbind_s()
    
    logging.info("Create customer entries groups done. Successes: %d, errors: %d." % (successes, errors))
