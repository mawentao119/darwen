# -*- coding: utf-8 -*-

__author__ = "苦叶子"

"""
Basic Operation of OS
"""

import os, stat, codecs
import shutil


def mk_dirs(path, mode=0o777):
    try:
        os.makedirs(path, mode=mode)
    except OSError:
        if not os.path.isdir(path):
            raise
def copy_file(s,d):
    try:
        shutil.copy(s,d)
    except Exception:
        return False
    return True

def walk_dir(path):
    try:
        return os.walk(path)
    except OSError:
        if not os.path.exists(path):
            raise


def list_dir(path):
    try:
        return os.listdir(path)
    except OSError:
        if not os.path.exists(path):
            raise


def exists_path(path):
    if not os.path.exists(path):
        return False

    return True


def rename_file(src, dst):
    if exists_path(src) and not exists_path(dst):
        os.rename(src, dst)

        return True

    return False


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_dir(path):
    shutil.rmtree(path, onerror=remove_readonly)


def remove_file(path):
    os.remove(path)


def get_splitext(path):
    return os.path.splitext(path)


def make_nod(path, mode="w", encoding="utf-8"):
    if exists_path(path):
        return False

    f = codecs.open(path, mode, encoding)

    f.close()

    return True


def write_file(path, data, mode="w", encoding="utf-8"):
    if not exists_path(path):
        return False

    f = codecs.open(path, mode, encoding)

    f.write(data)

    f.close()

    return True


def read_file(path, mode="r", encoding="utf-8"):
    if not exists_path(path):
        return {"status": False, "data": ""}

    f = codecs.open(path, mode, encoding)

    data = f.read()

    f.close()

    return {"status": True, "data": data}


def get_projectnamefromkey(key):
    # "//a/b/c/workspace/user/project/dir1/dir2/abc.robot --> project"
    return key.split("workspace")[1].split('/')[2]


def get_projectdirfromkey(key):
    splitkey = key.split('workspace')
    basedir = splitkey[0]
    project = get_projectnamefromkey(key)
    user = splitkey[1].split(project)[0]
    return basedir + 'workspace' + user + project


def get_ownerfromkey(key):
    return key.split("workspace")[1].split('/')[1]


