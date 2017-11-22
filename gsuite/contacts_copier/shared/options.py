import os, ConfigParser
import logging.config
from importlib import import_module

from shared.files import fileloc
from kids.cache import cache

def provided_arguments(parser):
    p = vars(parser.parse_args())
    o = []
    for action in parser._actions[1:]:
        if(p.get(action.dest) and p[action.dest] != action.default):
            o.append(action.dest)
    return o

@cache
def options():
    parser = import_module(os.getenv('PARSER')).parse_options()

    o = parser.parse_args()

    logging.config.fileConfig(fileloc(o.log_config))

    config = ConfigParser.SafeConfigParser()
    config.read(fileloc(o.config))

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

