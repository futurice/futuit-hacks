import os

def fileloc(path):
    if path.startswith('/'):
        return path
    elif path.startswith('./'):
        return os.path.join(os.getenv('ROOTDIR'), path[2:])
    else:
        return os.path.normpath(os.path.join(os.getenv('ROOTDIR'), path))
