#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A tool for importing exchange exported flatfiles to
LDAP.
"""

__author__ = 'Markus Koskinen (markus.koskinen@futurice.com)'
__copyright__ = 'Copyright (c) 2013 Futurice Oy'
__license__ = 'MIT'

import sys

from optparse import OptionParser

import LCI_aliases
import LCI_contacts
import LCI_distributiongroups
import LCI_ldap

from LCI_util import *

def main():
    init_logging()
    logging.info("Starting Flatfile->LDAP import script ...")
    parser = OptionParser(usage="Usage: %prog [options] filename")
    parser.add_option("-a", "--aliases",
                      action="store_true",
                      dest="aliases_file",
                      default=False,
                      help="User alias file to parse")
    parser.add_option("-d", "--distributiongroups",
                      action="store_true",
                      dest="dg_file",
                      default=False,
                      help="Distribution group file to parse")
    parser.add_option("-r", "--removedistributiongroups",
                      action="store_true",
                      dest="remove_dg_file",
                      default=False,
                      help="Remove a list of distribution groups")
    parser.add_option("-m", "--mailcontacts",
                      action="store_true",
                      dest="mc_file",
                      default=False,
                      help="Parse mailcontact -type file")
    parser.add_option("-p", "--parseonly",
                      action="store_true",
                      dest="parseonly",
                      default=False,
                      help="Just attempt to parse the file")
    parser.add_option("-s", "--simulate",
                      action="store_true",
                      dest="simulateonly",
                      default=False,
                      help="Just simulate, no writes to LDAP")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("You need to specify either a distribution group or aliases -file to parse.")
    
    if options.dg_file == options.aliases_file == options.mc_file == options.remove_dg_file:
        parser.error("Please choose one mode of operation.")
    
    if len(args) != 1:
       parser.error("Please specify a target file.")

    logging.debug("Options: %s", options)
    logging.debug("Args: %s", args)
    
    if options.aliases_file:
        # ALIASES
        logging.info("Starting to parse 'aliases' -type file '%s'." % args[0])
       
        # This alias dict will contain what changes we will make
        alias_dict = LCI_aliases.read_aliases(args[0])
       
        logging.debug("=== Alias dict: ===")
        logging.debug(LCI_pp.pformat(alias_dict))

        if options.parseonly:
            logging.info("'--parseonly' - switch given. Exiting now.")
            sys.exit(0)
       
        conn = LCI_ldap.bind()
       
        # This dict will be a mapping from "email" to "dn value"
        mail_to_dn_mapping = LCI_ldap.fetch_email_to_dn_mapping(conn)
       
        logging.debug("=== Mail to DN mapping: ===")
        logging.debug(LCI_pp.pformat(mail_to_dn_mapping))

        # Simulate and log all email to DN mapping misses
        dn_aliases = LCI_aliases.dn_to_new_aliases(mail_to_dn_mapping, alias_dict)

        logging.debug("=== DN to aliases mapping: ===")
        logging.debug(LCI_pp.pformat(dn_aliases))

        # Write the new proxyaddress attributes to LDAP
        if options.simulateonly:
            logging.info("'--simulate' - switch given. Exiting now.")
            sys.exit(0)
       
        logging.info("Starting writes to aliases...")
       
        LCI_ldap.add_proxy_attributes(dn_aliases)
       
        logging.info("All done.")
        sys.exit(0)

    elif options.mc_file:
        # MAILCONTACTS
        logging.info("Starting to parse 'mailcontact' -type file '%s'." % args[0])

        conn = LCI_ldap.bind()
       
        uidnumlist = LCI_ldap.get_used_uidnumbers(conn)

        logging.debug("=== Used uid numbers: ===")
        logging.debug(uidnumlist)

        uidlist = LCI_ldap.get_used_uids(conn)

        logging.debug("=== Used uids: ===")
        logging.debug(uidlist)

        # This alias dict will contain what changes we will make
        contact_dict = LCI_contacts.read_contacts(args[0], uidnumlist, uidlist)
       
        logging.debug("=== Contacts dict: ===")
        logging.debug(LCI_pp.pformat(contact_dict))

        if options.parseonly:
            logging.info("'--parseonly' - switch given. Exiting now.")
            sys.exit(0)
       
        # Start creating our new groups
        if options.simulateonly:
            logging.info("'--simulate' - switch given. Exiting now.")
            sys.exit(0)

        LCI_ldap.create_mailcontacts(contact_dict)
        logging.info("All done.")
        sys.exit(0)

    elif options.dg_file:
        # DISTRIBUTION GROUPS
        logging.info("Starting to parse 'distribution group' -type file '%s'." % args[0])

        # dgroups will contain the data parsed from the CSV
        dgroups = LCI_distributiongroups.parse_distribution_group_file(args[0])

        #logging.debug("=== Distribution group dict: ===")
        #logging.debug(LCI_pp.pformat(dgroups))

        if options.parseonly:
            logging.info("'--parseonly' - switch given. Exiting now.")
            sys.exit(0)

        conn = LCI_ldap.bind()
       
        # Get the existing groups. Groups that don't exist will be created (later)
        existing_dgroups = LCI_ldap.fetch_dg_dn_mapping(conn)

        logging.debug("=== Distribution group -> DN dict: ===")
        logging.debug(LCI_pp.pformat(existing_dgroups))

        # We'll ned to know the DNs of the email addresses of the members of our DGs
        mail_to_dn_mapping = LCI_ldap.fetch_email_to_dn_mapping(conn)
       
        logging.debug("=== Mail to DN mapping: ===")
        logging.debug(LCI_pp.pformat(mail_to_dn_mapping))
       
        # Fetch used gids
        gidlist = LCI_ldap.get_group_used_gidnumbers(conn)

        logging.debug("=== gidlist: ===")
        logging.debug(LCI_pp.pformat(gidlist))

        # Convert emails to user DNs, also insert group gids
        dgroups_email_as_user_dn = LCI_distributiongroups.emails_to_dns(dgroups, mail_to_dn_mapping, gidlist)

        # Create a dict for the new nodes we'll be creating
        dgcreate, dgmodify = LCI_distributiongroups.preprocess_groups(dgroups, existing_dgroups)
       
        # Start creating our new groups
        if options.simulateonly:
            logging.info("'--simulate' - switch given. Exiting now.")
            sys.exit(0)

        logging.info("Trying to create groups: %s" % dgcreate)

        # Leave only the "create" groups in the dgroups_email_as_user dict
        create_groups_email_as_user_dn = dict((key, value) for key, value in dgroups_email_as_user_dn.iteritems() if key in dgcreate)
       
        LCI_ldap.create_dgroups(create_groups_email_as_user_dn)

        sys.exit(0)
    elif options.remove_dg_file:
        # WARNING: This is a quick kludge, but worked for me
        logging.info("Will attempt to remove distribution groups, based on values parsed from '%s'." % args[0])

        # dgroups will contain the data parsed from the CSV
        dgroups = LCI_distributiongroups.parse_distribution_group_file(args[0])

        #logging.debug("=== Distribution group dict: ===")
        #logging.debug(LCI_pp.pformat(dgroups))

        if options.parseonly:
            logging.info("'--parseonly' - switch given. Exiting now.")
            sys.exit(0)

        conn = LCI_ldap.bind()
       
        # Get the existing groups. Groups that don't exist will be created (later)
        existing_dgroups = LCI_ldap.fetch_dg_dn_mapping(conn)

        logging.debug("=== Distribution group -> DN dict: ===")
        logging.debug(LCI_pp.pformat(existing_dgroups))

        # We'll ned to know the DNs of the email addresses of the members of our DGs
        mail_to_dn_mapping = LCI_ldap.fetch_email_to_dn_mapping(conn)
       
        logging.debug("=== Mail to DN mapping: ===")
        logging.debug(LCI_pp.pformat(mail_to_dn_mapping))
       
        # Fetch used gids
        gidlist = LCI_ldap.get_group_used_gidnumbers(conn)

        logging.debug("=== gidlist: ===")
        logging.debug(LCI_pp.pformat(gidlist))

        # Convert emails to user DNs, also insert group gids
        dgroups_email_as_user_dn = LCI_distributiongroups.emails_to_dns(dgroups, mail_to_dn_mapping, gidlist)

        # Create a dict for the new nodes we'll be creating
        dgcreate, dgmodify = LCI_distributiongroups.preprocess_groups(dgroups, existing_dgroups)
       
        # Start creating our new groups
        if options.simulateonly:
            logging.info("'--simulate' - switch given. Exiting now.")
            sys.exit(0)

        logging.info("Trying to remove groups: %s" % dgmodify)
        raw_input("This will try and remove the groups from LDAP. Press Enter to continue.")

        # This is dodgy, will fix later, might want to alter this a bit more       
        create_groups_email_as_user_dn = dict((key, value) for key, value in dgroups_email_as_user_dn.iteritems() if key in dgmodify + dgcreate)
       
        LCI_ldap.remove_dgroups(create_groups_email_as_user_dn)

        sys.exit(0)
    else:
        logging.info("Nothing to do.")


if __name__ == "__main__":
    main()
