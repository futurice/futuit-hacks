import itertools

def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))

def filtermap(cond, match, *iter):
    return map(match, filter(cond, *iter))
