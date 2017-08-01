import os

def get_path(file_path):
    if file_path[0] == '.':
        return os.path.abspath(file_path)
    elif file_path[0] == '~':
        return os.path.expanduser(file_path)
    else:
        return file_path
