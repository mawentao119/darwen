# -*- coding:utf-8 -*-
import os
import git

from utils.file import remove_dir, mk_dirs
from utils.mylogger import getlogger
import shutil

log = getlogger("Git", ".")


def remote_clone(app, url):
    """
    git.colone_from
    return True/False and info
    """

    newdir = url.split('/')[-1].split('.')[0]
    to_path = os.path.join(app.config['AUTO_TEMP'], newdir)
    remove_dir(to_path) if os.path.exists(to_path) else None
    mk_dirs(to_path)

    try:
        repo = git.Repo.clone_from(url, to_path)
    except git.exc.GitError as e:
        log.error("Git clone 从 {} 到目录 {} 异常:{}".format(url, to_path, e))
        log.info("{}".format(e))
        return (False, "{}".format(e))

    log.info("Clone 从 {} 到路径:{} 成功".format(url, to_path))

    projectfile = os.path.join(to_path, 'platforminterface/project.conf')
    log.info("读取 Project file: {}".format(projectfile))
    if os.path.exists(projectfile):
        with open(projectfile, 'r') as f:
            for l in f:
                if l.startswith('#'):
                    continue
                if len(l.strip()) == 0:
                    continue
                splits = l.strip().split('|')
                if len(splits) != 4:
                    log.error("错误的 project.conf 行 " + l)
                    return (False, "错误的 project.conf 行 " + l)
                (projectname, owner, users, cron) = splits
                project_path = os.path.join(
                    app.config['AUTO_HOME'], 'workspace', owner, projectname)
                if os.path.exists(project_path):
                    msg = '目标目录存在:{}'.format(project_path)
                    log.error(msg)
                    return (False, msg)
                log.info("复制文件从 {} 到 {} ".format(to_path, project_path))
                try:
                    shutil.copytree(to_path, project_path)
                except Exception as e:
                    return (False, "{}".format(e))
    else:
        msg = "Load Project Fail: 找不到 project.conf:{} ".format(projectfile)
        log.error(msg)
        return (False, msg)

    return (True, project_path) if repo else (False, "Git clone fail!")


def remote_clone_BAK(url, localpath):
    """
    git.colone_from
    return True/False and info
    """

    newdir = url.split('/')[-1].split('.')[0]
    to_path = os.path.join(localpath, newdir)
    if os.path.exists(to_path):
        errinfo = "路径 {} 已存在,请先删除!".format(newdir)
        log.error("remote_clone:"+to_path+" 目录存在!")
        return (False, errinfo)

    os.mkdir(to_path)

    try:
        repo = git.Repo.clone_from(url, to_path)
    except git.exc.GitError as e:
        log.error("Git clone 从 {} 到目录 {} 异常:{}".format(url, localpath, e))
        log.info("{}".format(e))
        return (False, "{}".format(e))

    return (True, to_path) if repo else (False, "fail")


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
        log.error("目录 {} 不是一个git目录!{}".format(dir, e))
        log.info("{}".format(e))
        return False, "{}".format(e)

    for f in repo.untracked_files:
        repo.index.add([f])
        repo.index.commit("Add file:"+f)
    try:
        repo.commit("master")
    except Exception as e:
        log.error("commit {} 失败.{}".format(dir, e))
        log.info("{}".format(e))
        return False, "{}".format(e)

    return True


def push(dir):

    log.info("Push前先commit ...")

    ok, info = commit(dir)
    if not ok:
        return False, info

    remote = git.Repo(dir).remote()

    try:
        remote.push("origin")
    except Exception as e:
        log.error("Push dir {} failed:{}".format(dir, e))
        log.info("{}".format(e))
        return False, "{}".format(e)

    return True, "success"


if __name__ == '__main__':

    url1 = "https://github.com/mawentao119/robotframework-metrics.git"
    url = "https://mawentao119:mwt\@Github1@github.com/mawentao119/robotframework-metrics.git"

    path = "temp1234"
    remove_dir(path) if os.path.exists(path) else None
    os.mkdir(path)

    remote_clone(url1, path)
    open("temp1234/robotframework-metrics/123.txt", 'w').close()
    commit(path+'/'+"robotframework-metrics")

    print(is_gitdir("temp1234"))
    remove_dir(path)

    #from utils.dbclass import TestDB
    #myDB = TestDB('/Users/tester/PycharmProjects/uniRobotDev/.beats')
