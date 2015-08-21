import os, argparse

def parse_options():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-S", "--select-pattern",
        dest="select_pattern",
        help="select calendars to copy by pattern GLOB against Calendar Resource's email address",
        metavar="GLOB")

    parser.add_argument(
        "-U", "--user-pattern",
        dest="user_pattern",
        help="copy contacts to all users whose email address matches GLOB",
        metavar="GLOB")

    parser.add_argument(
        "-G", "--group",
        dest="group",
        help="when creating a new contacts group use NAME",
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
        help="also check the target group for old calendar contacts added by this script and delete those")

    parser.add_argument(
        "--undo",
        dest="undo",
        action="store_true",
        default=False,
        help="remove all groups and contacts added by this script")

    parser.add_argument(
        "-b", "--batch",
        dest="batch",
        action="store_true",
        default=False,
        help="batch operation (consider interactive reauthorization an error)")

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

    return parser

