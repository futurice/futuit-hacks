"""
* aliases.txt
** Match by PrimarySmtpAddress
** Add EmailAddresses to -> proxyaddresses
** If emailAddress not found, log error
** futurice.* -> discard those where firstname.surname@futurice.* (as long as it is the same)
"""

import codecs

from LCI_util import *
from LCI_settings import DOMAIN, EXTENDED_DOMAIN_LIST

def read_aliases(aliases_file):
   """
   Return a dictionary with the sanitized email aliases we want to add,
   based on a textfile.
   """
   # Read in out values to a list
   lines = read_aliases_to_list(aliases_file)

   # Convert our list to dict
   aliasdict = aliases_from_list_to_dict(lines)

   #logging.debug("Aliasdict: %s" %  aliasdict)
   return aliasdict

def dn_to_new_aliases(mail_to_dn_mapping, alias_dict):
    """
    Create a dict with "dn" -> [list of new aliases]
    We discard empty values at this point - the resulting
    dict will be used to push the attributes to LDAP for each dn
    return dict
    """
    misses, hits = (0, 0)
    
    dn_to_alias_dict = {}
    
    for aliaskey, aliasvalue in alias_dict.iteritems():
        if aliasvalue and aliasvalue != [u'']:
            if not aliaskey in mail_to_dn_mapping.keys():
                logging.warning("E-mail to DN mapping miss for mail '%s', aliasvalues '%s'." % (aliaskey, aliasvalue))
                misses += 1
            else:
                dn_to_alias_dict[mail_to_dn_mapping[aliaskey]] = aliasvalue
                hits += 1
    logging.info("Email->DN mapping, hits: %d, misses: %d, total: %d." % (hits, misses, hits+misses))
    return dn_to_alias_dict

    
def aliases_from_list_to_dict(lines):
    """
    Quite ugly alias list to mapping conversion.
    """
    aliasdict = {}
    
    # Our dict keys are the PrimarySmtpAddresses
    for i in range(len(lines)):
        if i % 2 == 0:
            aliasdict[extract_alias_key(lines[i])] = []
        else:
            alias_key_value = extract_alias_key(lines[i-1])
            alias_list_string = lines[i]
            aliasdict[alias_key_value] = extract_mail_aliases(alias_list_string, alias_key_value)
    
    return aliasdict

            
def extract_alias_key(str):
    """
    Attempt to extract the e-mail address part of:
    PrimarySmtpAddress : aarne.bertta@futurice.com
    returns lowercase string
    """
    str_split = [val.strip() for val in str.split(":")]

    if len(str_split) != 2 or str_split[0] != u"PrimarySmtpAddress":
        logging.error("String '%s' doesn't look like a PrimarySmtpAddress value. Split value: %s" % (str, str_split))
        return None
    
    return str_split[1].lower()

def extract_mail_aliases(str, base_value_for_sanitize=None):
    """
    Attempt to extract the e-mail aliases from a line such as:
    EmailAddresses     : {aber@futurice.com, Aarne.Bertta@futurice.eu}
    return list
    """
    str_split = [val.strip() for val in str.split(":")]

    if len(str_split) != 2 or str_split[0] != u"EmailAddresses":
        logging.error("String '%s' doesn't look like a EmailAddresses. Split value: %s" % (str, str_split))
        return None
    
    pseudolist_string = str_split[1].replace("{","").replace("}","")
    
    alias_list = [val.lower().strip() for val in pseudolist_string.split(",")]

    if base_value_for_sanitize:
       alias_list = sanitize_aliases(base_value_for_sanitize, alias_list)

    return alias_list

def sanitize_aliases(base_value_for_sanitize, alias_list):
    """
    Attempt to sanitize out reduntant aliases from the alias_list.
    futurice.* -> discard those where firstname.surname@futurice.* (as long as it is the same)
    """
    _EXTENDED_DOMAIN_LIST = EXTENDED_DOMAIN_LIST
    
    mail_prefix = base_value_for_sanitize.split("@" + DOMAIN)[0]
    
    # Get a sublist with all aliases prefixes ending with "futurice.com" and add the base value
    futucom_sublist = [val.split("@")[0] for val in alias_list if val.endswith("@" + DOMAIN)]
    futucom_sublist.append(mail_prefix)
    
    #logging.debug("futucom_sublist: %s" % futucom_sublist)

    for sublist_val in futucom_sublist:
        for domain_val in _EXTENDED_DOMAIN_LIST:
            alt_alias = sublist_val + domain_val
            if alt_alias in alias_list:
                alias_list.remove(alt_alias)

    return [aitem.encode('ascii','ignore') for aitem in alias_list]
    

def read_aliases_to_list(aliases_file):
    f = codecs.open(aliases_file, encoding='utf_16')

    lines = [] 

    for line in f:
        # Ugly continue
        # Our lines of interest have a ':'
        line = line.strip()
        if not ":" in line: continue
        if "DisplayName" in line: continue
        lines.append(line)
    
    #logging.debug(u"Lines: %s" % lines)
    return lines
