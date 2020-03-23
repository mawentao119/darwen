# -*- coding:utf-8 -*-
import os
import git

from utils.file import remove_dir
from utils.mylogger import getlogger
from flask import session


log = getlogger("Git",".")

def remote_clone(url, localpath):
    """
    git.colone_from
    return True/False and info
    """

    newdir = url.split('/')[-1].split('.')[0]
    to_path = os.path.join(localpath,newdir)
    if os.path.exists(to_path):
        errinfo = "path {} already exists ,Please Delete it!".format(newdir)
        log.error("remote_clone:"+to_path+" exits!")
        return (False, errinfo)

    os.mkdir(to_path)

    try:
        repo = git.Repo.clone_from(url, to_path)
    except git.exc.GitError as e:
        log.error("git clone from {} to dir {} Exception:{}".format(url,localpath,e))
        log.info("{}".format(e))
        return (False, "{}".format(e))

    return (True, to_path) if repo else (False,"fail")

def is_gitdir(dir):

    try:
        repo = git.Repo(dir)
    except git.exc.InvalidGitRepositoryError:
        return False

    return True

def commit(dir):
    """
    git.commit
    """
    try:
        repo = git.Repo(dir)
    except git.exc.InvalidGitRepositoryError as e:
        log.error("Dir {} is not a git dir!{}".format(dir.e))
        log.info("{}".format(e))
        return False,"{}".format(e)

    for f in repo.untracked_files:
        repo.index.add([f])
        repo.index.commit("Add file:"+f)
    try:
        repo.commit("master")
    except Exception as e:
        log.error("commit {} changes fail.{}".format(dir,e))
        log.info("{}".format(e))
        return False,"{}".format(e)

    return True

def push(dir):

    log.info("Before Push, commit first ...")

    ok,info = commit(dir)
    if not ok:
        return False,info

    remote = git.Repo(dir).remote()

    try:
        remote.push("origin")
    except Exception as e:
        log.error("Push dir {} failed:{}".format(dir,e))
        log.info("{}".format(e))
        return False,"{}".format(e)

    return True,"success"

if __name__ == '__main__':

    url1 = "https://github.com/mawentao119/robotframework-metrics.git"
    url = "https://mawentao119:mwt\@Github1@github.com/mawentao119/robotframework-metrics.git"

    path = "temp1234"
    remove_dir(path) if os.path.exists(path) else None
    os.mkdir(path)

    remote_clone(url1,path)
    open("temp1234/robotframework-metrics/123.txt", 'w').close()
    commit(path+'/'+"robotframework-metrics")

    print(is_gitdir("temp1234"))
    remove_dir(path)

    #from utils.dbclass import TestDB
    #myDB = TestDB('/Users/tester/PycharmProjects/uniRobotDev/.beats')
