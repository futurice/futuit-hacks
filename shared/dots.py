from functools import wraps
import operator

def err(f):
    @wraps(f)
    def wrapper(*a,**kw):
        try:
            return f(*a,**kw)
        except Exception as e:
            return DotDict()
    return wrapper

class DotDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __init__(self, dct={}):
        for key, value in dct.items():
            if hasattr(value, 'keys'):
                value = DotDict(value)
            self[key] = value
    def __missing__(self, key):
        self[key] = DotDict()
        return self[key]

def dotset(obj, keys, value):
    attrs = keys.split('.')
    target = obj
    if '.' in attrs:
        target = dotget(obj, '.'.join(attrs[:-1]))
    setattr(target, attrs[-1], value)

def dotget(obj, attr):
    return reduce(getattr, attr.split('.'), obj)

def compare_object_values(a, b, attrs, cmp=lambda x,y: x==y, cmp_value=lambda x: x, flat=True, allow_empty_values=False):
    ac = DotDict()
    bc = DotDict()
    changes = DotDict()
    for key in attrs:
        setattr(ac, key, dotget(a, key))
        setattr(bc, key, dotget(b, key))
    for key in attrs:
        if not cmp(dotget(ac, key), dotget(bc, key)):
            value = dotget(ac, cmp_value(key))
            if not allow_empty_values and not value:
                continue
            if flat:
                setattr(changes, key, dotget(ac, key))
            else:
                dotset(changes, key, dotget(ac, key))
    return changes
