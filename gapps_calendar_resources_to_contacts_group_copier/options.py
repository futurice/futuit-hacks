import os, optparse, logging, ConfigParser

from kids.cache import cache

def parse_options():
    parser = optparse.OptionParser()

    parser.add_option(
        "-S", "--select-pattern",
        dest="select_pattern",
        help="select calendars to copy by pattern GLOB against Calendar Resource's email address",
        metavar="GLOB")

    parser.add_option(
        "-U", "--user-pattern",
        dest="user_pattern",
        help="copy contacts to all users whose email address matches GLOB",
        metavar="GLOB")

    parser.add_option(
        "-G", "--group",
        dest="group",
        help="when creating a new contacts group use NAME",
        metavar="NAME")

    parser.add_option(
        "-M", "--my-contacts",
        dest="my_contacts",
        action="store_true",
        default=False,
        help="add contacts to My Contacts as well")

    parser.add_option(
        "-F", "--family-name",
        dest="family_name",
        help="set the compulsory family name of added contacts to NAME",
        metavar="NAME")

    parser.add_option(
        "-D", "--delete-old",
        dest="delete_old",
        action="store_true",
        default=False,
        help="also check the target group for old calendar contacts added by this script and delete those")

    parser.add_option(
        "--undo",
        dest="undo",
        action="store_true",
        default=False,
        help="remove all groups and contacts added by this script")
        
    
    parser.add_option(
        "-r", "--reauth",
        dest="reauth",
        action="store_true",
        default=False,
        help="reauthorize Google Account")

    parser.add_option(
        "-b", "--batch",
        dest="batch",
        action="store_true",
        default=False,
        help="batch operation (consider interactive reauthorization an error)")

    parser.add_option(
        "-t", "--token",
        dest="token_file",
        help="use OAuth2 token FILE [default: %default]",
        metavar="FILE",
        default="token.conf")

    parser.add_option(
        "-d", "--domain-token",
        dest="domain_file",
        help="use domain token FILE [default: %default]",
        metavar="FILE",
        default="token_domain.conf")

    parser.add_option(
        "-c", "--config",
        dest="config",
        help="read application configuration from FILE [default: %default]",
        metavar="FILE",
        default="config.conf")

    parser.add_option(
        "-l", "--log-config",
        dest="log_config",
        help="read logging configuration from FILE [default: %default]",
        metavar="FILE",
        default="logging.conf")

    return parser.parse_args()[0]

@cache
def options():
    o = parse_options()
    logging.config.fileConfig(o.log_config)
    config = ConfigParser.RawConfigParser()
    config.read(o.config)

    # parse config in-order
    keys = []
    for section in config.sections():
        for param in config.options(section):
            keys.append(param)
            setattr(o, param, config.get(section, param))

    # environment variables can be used to override configs
    for key in keys:
        setattr(o, key, os.getenv(key.upper(), getattr(o, key)))
    return o
