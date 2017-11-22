import csv
from LCI_util import *
from LCI_settings import COMPANY_NAME

_GROUP_OBJECT_CLASSES = []

def parse_distribution_group_file(dg_file):
    """
    return a dict with distribution groups, their mail addresses and proxyaliases parsed
    """
    lists = {}
    with open(dg_file) as f:
        dgreader = csv.reader(f)
        headers = dgreader.next()
    
        for line in dgreader:
            data = dict(zip(headers, line))
            list_name = data["Distribution Group"]
            mail = data["Distribution Group Primary Smtp"]
            mail_s = mail.split("@")
            if list_name not in lists:
                lists[list_name] = {"mail": mail, "proxyaddress": [], "member_addresses": []}
                for a in ["0","1","2"]:
                    if len(data[a]) > 0:
                        alias = data[a].split("@")
                        if alias[0] == mail_s[0] and COMPANY_NAME in alias[1]:
                           continue
                        lists[list_name]["proxyaddress"].append(data[a].lower())
            member_email = data["Primary SMTP address"]

            if len(member_email) > 0:
                lists[list_name]["member_addresses"].append(data["Primary SMTP address"].lower())

    logging.debug("DG list size %d" % len(lists))
    return lists

def preprocess_groups(dgroups, existing_dgroups):
    """
    Some groups will exist, and can be modified, others will not and 
    need to be created.

    returns a tuple of lists (those to be created, those to be modified)
    """
    
    create, modify = ([], [])

    for group in dgroups:
        if group in existing_dgroups.keys():
            #dgroups[group]['operation'] = 'modify'
            modify.append(group)
        else:
            #dgroups[group]['operation'] = 'create'
            create.append(group)
    logging.info("Distribution group preprocessing thinks we should modify : %d and create: %d groups." % (len(modify),len(create)))
    logging.info("Create: %s" % create)
    logging.info("Modify: %s" % modify)
    return (create, modify);

def get_free_gidNumber(gidlist):
    """
    Return a free gid, almost straight from FUM.
    """
    gidNumber_range = [0, 3000]
    
    nbrs = [int(gid) for gid in gidlist]
    gidNumber = max(nbrs) + 1
    if gidNumber >= gidNumber_range[0] and gidNumber < gidNumber_range[1]:
        logging.debug("Assigning new gidNumber: %d." % gidNumber)
        return gidNumber
    else:
        logging.critical('No gidNumber left in range %s' % gidNumber_range)
        sys.exit(1)


def emails_to_dns(dgroups, mail_to_dn_mapping, gidlist):
    """
    The function name is a bit misleading this does other stuff as well.
    Convert the member email addresses to user DNs, add sambaSID, gidNumber etc
    return a dgroup dict
    """ 
    for dgroup, dgroupval in dgroups.iteritems():
        dgroups[dgroup]['uniqueMember'] = []
        
        # Gid number geenrated here. We only fech used gids once,
        # so take care of updating your list as you go.
        gid = get_free_gidNumber(gidlist)
        dgroups[dgroup]['gidNumber'] = [str(gid)]
        gidlist.append(gid)

        # Description is expected by fum
        dgroups[dgroup]['description'] = [str(dgroup)]

        # Sambagroup type
        dgroups[dgroup]['sambaGroupType'] = [str(2)]
        
        # Sambagroup SID
        sambaSID = 'S-1-5-21-1049098856-3271850987-3507249052-%s' % (gid * 2 + 1001)
        dgroups[dgroup]['sambaSID'] = sambaSID

        for maddress in dgroupval['member_addresses']:
            if maddress in mail_to_dn_mapping.keys():
                dgroups[dgroup]['uniqueMember'].append(mail_to_dn_mapping[maddress])
            else:
                logging.error("Could not look up '%s' from mail to DN mapping for group '%s'." % (maddress, dgroup))
        # WARNING: Should we have the proxyaddresses in "aliases" as the mails?
        #dgroups[dgroup].pop('aliases', None)
        dgroups[dgroup].pop('member_addresses', None)
        
    return dgroups

