import os, sys, argparse, logging, ConfigParser
import logging.config

from kids.cache import cache

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

def provided_arguments(parser):
    p = vars(parser.parse_args())
    o = []
    for action in parser._actions[1:]:
        if(p.get(action.dest) and p[action.dest] != action.default):
            o.append(action.dest)
    return o

@cache
def options():
    parser = parse_options()
    o = parser.parse_args()

    logging.config.fileConfig(o.log_config)

    config = ConfigParser.SafeConfigParser()
    config.read(o.config)

    # parse config in-order
    keys = []
    for section in config.sections():
        for param in config.options(section):
            keys.append(param)
            setattr(o, param, config.get(section, param))

    # cli arguments override configs
    for key in provided_arguments(parser):
        setattr(o, key, getattr(parser.parse_args(), key))

    # environment variables override configs
    for key in keys:
        setattr(o, key, os.getenv(key.upper(), getattr(o, key)))
    return o

