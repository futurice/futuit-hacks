"""
* mailcontacts.txt

* Generate uid:
  - Pontus Hellman -> cphel
  - (remove 'ext-' -prefix)
* Add mail - parsed from: "ExternalEmailAddress : SMTP:aarne.asiakas@customer.fi
* password -> "!"
* discard ExternalEmailAddress: endswith futurice.com.test-google-a.com
"""

import codecs

from LCI_util import *

def read_contacts(contacts_file, uidlist, used_uid_names):
   """
   Return a dictionary with "uid" -> "email" mapping.
   """
   # Read in out values to a list
   lines = read_contacts_to_list(contacts_file)

   # Convert our list to dict
   contactsdict = contacts_from_list_to_dict(lines, uidlist, used_uid_names)

   #logging.debug("Aliasdict: %s" %  aliasdict)
   return contactsdict

    
def contacts_from_list_to_dict(lines, uidlist, used_uid_names):
    """
    Quite ugly alias list to mapping conversion.
    """
    contactdict = {}
    
    # Our dict keys are the PrimarySmtpAddresses
    for i in range(len(lines)):
        if i % 2 != 0:
            contact_key_value = extract_contact_key(lines[i-1])
            contact_list_string = lines[i]

            if contact_list_string.endswith("futurice.com.test-google-a.com"):
                #contactdict.pop(contact_key_value)
                continue
            else:
                mail = str(contact_list_string.split("SMTP:")[1]).lower()
                displayname = extract_contact_name(lines[i-1]).encode("ascii", "ignore")
                
                if len(displayname.split()) >= 2:
                    sn = displayname.split()[-1]
                else:
                    sn = displayname
                
                if contact_key_value in used_uid_names:
                    logging.warn("UID '%s' was already taken, check manually if it is a collision or the same person." % contact_key_value)
                    continue
                
                uidNumber = get_free_uidNumber(uidlist)
                uidlist.append(uidNumber)
                
                contactdict[contact_key_value] = {
                    "uid": contact_key_value, 
                    "mail": mail, 
                    "cn": displayname,
                    #rdn_value',  'cn', 'title', 'sn', 'display
                    "displayName" : displayname,
                    "title" : "customer",
                    "sn": sn,
                    "ntUserDomainId" : contact_key_value,
                    "gidNumber" : "2000",
                    "homeDirectory" : "/home/" + contact_key_value[0] + "/" + contact_key_value,
                    "uidNumber" : str(uidNumber),
                    "sambaSID" : 'S-1-5-21-1049098856-3271850987-3507249052-%s' % (uidNumber * 2 + 1000),
                    "shadowLastChange" : "0",
                    #"userPassword" : "!",
                    "googlePassword" : "!"
                    #"shadowMaxChange" : "0"
                    }
    
    return contactdict

def get_free_uidNumber(uidlist):
        """
        Returns:
            str. A uidNumber that is not yet in use in the LDAP.
        """
        nbrs = [int(number) for number in uidlist]
        uidNumber = max(nbrs) + 1
        if uidNumber >= 2000 and uidNumber < 3000:
            return uidNumber
        else :
            raise RuntimeError('No uidNumber left in range %s' % [2000, 3000])

def extract_contact_name(str):
    """
    """
    str_split = [val.strip() for val in str.split(":")]

    if len(str_split) != 2 or str_split[0] != u"DisplayName":
        logging.error("String '%s' doesn't look like a DisplayName value. Split value: %s" % (str, str_split))
        return None
    
    contactname = str_split[1]
    
    # Strip leading "ext-"
    if contactname.startswith("ext-"):
       contactname = contactname[4:]
    
    contactname = contactname.replace(".", "")
    return contactname

            
def extract_contact_key(str):
    """
    """
    contactkey = extract_contact_name(str).lower()
    
    # Try and convert the displayname to an uid
    str_split = contactkey.split()

    if len(str_split) == 3 and len(str_split[1]) <= 2:
        str_split = [str_split[0], str_split[2]]
    
    if len(str_split) == 2:
        contactkey = ("c" + str_split[0][0] + str_split[1][0:3]).encode('ascii','ignore')
        return contactkey
    
    contactkey = contactkey.replace("-", "")
    contactkey = contactkey.replace(".", "")
    return contactkey.encode('ascii', 'ignore')

def read_contacts_to_list(aliases_file):
    f = codecs.open(aliases_file, encoding='utf_16')

    lines = []

    for line in f:
        # Ugly continue
        # Our lines of interest have a ':'
        line = line.strip()
        if not ":" in line: continue
        if "PrimarySmtpAddress" in line or "EmailAddresses" in line: continue
        lines.append(line)
    
    #logging.debug(u"Lines: %s" % lines)
    return lines
