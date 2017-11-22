import argparse

def parse_options():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-S", "--select-pattern",
        dest="select_pattern",
        help="select users to copy by pattern GLOB against user's email address",
        metavar="GLOB")

    parser.add_argument(
        "-P", "--no-phone",
        dest="phone",
        action="store_false",
        default=True,
        help="copy users who do NOT have a phone number set")

    parser.add_argument(
        "-U", "--user-pattern",
        dest="user_pattern",
        help="copy contacts to all users whose email address matches GLOB",
        metavar="GLOB")

    parser.add_argument(
        "-G", "--group",
        dest="group",
        help="copy contacts under group NAME",
        metavar="NAME")
    
    parser.add_argument(
        "-M", "--my-contacts",
        dest="my_contacts",
        action="store_true",
        default=False,
        help="add contacts to My Contacts as well")
        
    parser.add_argument(
        "-D", "--delete-old",
        dest="delete_old",
        action="store_true",
        default=False,
        help="also check the target group for old contacts added by this script and delete those")

    parser.add_argument(
        "-R", "--rename-old",
        dest="rename_old",
        action="store_true",
        default=False,
        help="also check the target group for old contacts added by this script and rename them with a suffix")
        
    parser.add_argument(
        "--rename-suffix",
        dest="rename_suffix",
        help="suffix string to use in conjunction with --rename-old",
        metavar="SUFFIX")

    parser.add_argument(
        "--add-other-emails",
        dest="add_other_emails",
        action="store_true",
        default=False,
        help="also add all user's other e-mail addresses to contacts [default: only add the primary email]")

    parser.add_argument(
        "--add-aliases",
        dest="add_aliases",
        action="store_true",
        default=False,
        help="also add all user's e-mail aliases to contacts [default: only add the primary email]")
    
    parser.add_argument(
        "-O", "--organization-name",
        dest="organization_name",
        help="organization name to use for contacts when not specified",
        metavar="NAME")
        
    parser.add_argument(
        "--undo",
        dest="undo",
        action="store_true",
        default=False,
        help="remove all groups and contacts added by this script [dangerous]")

    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="read application configuration from FILE [default: %default]",
        metavar="FILE",
        default="config.conf")

    parser.add_argument(
        "-l", "--log-config",
        dest="log_config",
        help="read logging configuration from FILE [default: %default]",
        metavar="FILE",
        default="logging.conf")

    parser.add_argument(
        "--delete-contacts",
        dest="delete_contacts",
        help="delete all matching existing contacts for processed user(s) before starting sync",
        action="store_true",
        default=False)

    return parser
