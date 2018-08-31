#!/usr/bin/env python3
# As the name suggests, this script removes certain uids from groups.
# Usage: ./remove_missing_uids_from_groups.py server admin_user filename search_base

import sys
import copy
import getpass
import json
import ldap

if len(sys.argv) != 5:
    print("Incorrect cli arguments. see the source code for instructions!")
    sys.exit(1)

server = sys.argv[1]
username = sys.argv[2]
user_list_filename = sys.argv[3]
search_base = sys.argv[4]
password = getpass.getpass()
# 'ldaps://ldapng1c7.futurice.com'
# 'uid=admin,ou=Administrators,ou=TopologyManagement,o=NetscapeRoot'

# Load user list from file. something like this can be used to get it from
# GoogleCloudDirectorySync loc
# grep AbstractLdapHandler gsync_log.txt | cut -d ' ' -f 11 | sort | uniq
with open(user_list_filename) as f:
    user_list = json.load(f)

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
l = ldap.initialize(server)
l.simple_bind_s(username, password)

for user in user_list:
    print("Processing user: {}".format(user))
    # find groups that have this user dn as a uniqueMember attribute
    ldap_search_string = "(&(objectClass=posixGroup)(uniqueMember={}))".format(user)
    groups = l.search_s(search_base,ldap.SCOPE_SUBTREE,ldap_search_string,['dn', 'uniqueMember'])
    # print("User {} is part of following groups: {}".format(user, groups))
    
    for group in groups:
        print("    Processing group: {}".format(group[0]))
        # new = copy.deepcopy(group)
        # new['uniqueMember'].remove(user)
        # modlist = ldap.modlist.modifyModlist(group,new)

        # Construct modlist that removes the user dn from the uniqueMember attribute
        modlist = [(ldap.MOD_DELETE, 'uniqueMember', bytes(user, 'utf-8'))]
        # print("modlist: {}".format(modlist))

        # execute the modlist against group
        # print("Executing modlist against dn: {}".format(group[0]))
        ret = l.modify_s(group[0], modlist)
        print(ret)

l.unbind_s()
