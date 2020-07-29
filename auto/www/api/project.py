# -*- coding: utf-8 -*-

__author__ = "苦叶子" + "mawentao119@gmail.com"

"""

"""

import os
from flask import current_app, session
from flask_restful import Resource, reqparse

from robot.api import TestSuiteBuilder

from utils.file import list_dir, mk_dirs, exists_path, rename_file, remove_dir, get_splitext, get_projectdirfromkey,get_projectnamefromkey, get_ownerfromkey
from utils.resource import ICONS
from utils.clear import clear_projectres
from utils.mylogger import getlogger
from utils.parsing import generate_high_light, generate_auto_complete
from utils.gitit import remote_clone
class Project(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('new_name', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('description', type=str)
        self.parser.add_argument('enable', type=str, default="OFF")
        self.parser.add_argument('cron', type=str, default="* * * * * *")
        self.parser.add_argument('boolean', type=str, default="ON")
        self.log = getlogger("Project")
        self.reserved_names = ["workspace", "project", "uniRobot"]
        self.app = current_app._get_current_object()

    def get(self):
        args = self.parser.parse_args()
        method = args["method"].lower()
        if method == 'project_list':
            return self.__get_projectlist(args)

    def post(self):
        args = self.parser.parse_args()

        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "edit":
            result = self.__edit(args)
        elif method == "delete":
            result = self.__delete(args)
        elif method == "set_main":
            result = self.__set_main(args)
        elif method == "adduser":
            result = self.__adduser(args)
        elif method == "deluser":
            result = self.__deluser(args)
        elif method == "gitclone":
            result = self.__gitclone(args)

        return result, 201

    def __create(self, args):
        result = {"status": "success", "msg": "成功：创建项目."}
        
        if args["name"] in self.reserved_names :
            result = {"status": "fail", "msg": "请换一个用户名."}
            return result

        user_path = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (session["username"], args["name"])
        if not exists_path(user_path):
            mk_dirs(user_path)

        if not self.app.config['DB'].add_project(args["name"],session["username"],'myself'):
            result["status"] = "fail"
            result["msg"] = "失败: 项目名已存在!"

        self.save_project(user_path)
        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'create', user_path, result['status'])

        return result

    def __gitclone(self, args):

        url = args['name']
        (ok, info) = remote_clone(self.app , url)

        if ok:
            projectname = get_projectnamefromkey(info)
            msg = self.app.config['DB'].load_project_from_path(info)
            result = {"status": "success", "msg": "Result: {} project:{}".format(msg,projectname) }
            self.app.config['DB'].insert_loginfo(session['username'], 'project', 'gitcreate', info,
                                                           result['status'])
        else:
            result = {"status": "fail", "msg": info}
            self.app.config['DB'].insert_loginfo(session['username'], 'project', 'gitcreate', url,
                                                           result['status'])

        return result

    def __edit(self, args):
        result = {"status": "success", "msg": "成功：重命名."}
        
        if args["new_name"] in self.reserved_names :
            result = {"status": "fail", "msg": "失败：请用其它名字."}
            return result
        
        if args["name"] in self.reserved_names :
            result = {"status": "fail", "msg": "失败：无法重命名此项目."}
            return result

        owner = get_ownerfromkey(args['key'])
        if not session["username"] == "Admin":
            result["status"] = "fail"
            result["msg"] = "失败：只有Admin可以进行此操作."
            return result

        old_name = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (owner, args["name"])
        new_name = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (owner, args["new_name"])

        if not rename_file(old_name, new_name):
            result["status"] = "fail"
            result["msg"] = "失败：新名字已存在于目录中!"
        if not self.app.config['DB'].edit_project(args["name"], args["new_name"], owner):
            result["status"] = "fail"
            result["msg"] = "失败：新名字已存在于数据库中!"

        self.log.info("更新用户到主项目为 {}".format(args["new_name"]))
        self.app.config['DB'].runsql("UPDATE user set main_project='{}' where main_project='{}';".format(args["new_name"], args["name"]))

        self.save_project(new_name)
        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'rename', old_name, result['status'])

        # Delete resource is not dangerous, all of that can be auto generated.
        clear_projectres('usepath', old_name)

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "删除项目成功."}

        self.log.debug("删除项目 args:{}".format(args))

        project = args["name"]
        owner = get_ownerfromkey(args['key'])

        if not session["username"] == "Admin":
            result["status"] = "fail"
            result["msg"] = "FAIL：只有Admin可以进行此操作!"
            return result

        #user_path = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (session["username"], args["name"])
        user_path = args['key']
        self.log.info("删除项目：开始删除项目目录 {}".format(user_path))
        if exists_path(user_path):
            remove_dir(user_path)

        if not self.app.config['DB'].del_project(args["name"],owner):
            result["status"] = "fail"
            result["msg"] = "删除失败, 项目不存在."

        self.log.info("删除项目的owner：{} 和以 {} 为主项目的成员".format(owner,project))
        self.app.config['DB'].del_user(owner)
        self.app.config['DB'].runsql("Delete from user where main_project='{}' ;".format(project))

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'delete', user_path, result['status'])

        #Delete resource is not dangerous, all of that can be auto generated.
        clear_projectres('usepath',user_path)

        return result

    def __set_main(self, args):

        main_project = self.app.config['DB'].get_user_main_project(session['username'])
        owner = self.app.config['DB'].get_projectowner(main_project)

        if session['username'] == owner:
            return {"status": "Fail", "msg": "失败：项目管理员不能切换主项目."}

        #user_path = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (session["username"], args["name"])
        user_path = args['key']
        if exists_path(user_path):
            info = self.app.config['DB'].init_project_settings(user_path)
            projectname = get_projectnamefromkey(user_path)
            self.app.config['DB'].set_user_main_project(session['username'],projectname)

        result = {"status": "success", "msg": info}

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'set_main', user_path, info)

        return result

    def __adduser(self, args):
        result = {"status": "success", "msg": "成功：增加项目用户."}

        project = get_projectnamefromkey(args['key'])
        owner = get_ownerfromkey(args['key'])
        if not session["username"] == owner:
            result["status"] = "fail"
            result["msg"] = "失败：没有权限操作，请联系{}.".format(owner)
            return result

        new_name = args["new_name"]

        try:
            self.app.config['DB'].add_projectuser(project, new_name)
        except Exception:
            result["status"] = "fail"
            result["msg"] = "数据库操作失败！"

        self.save_project(args['key'])
        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'adduser', args['key'], new_name)

        return result

    def __deluser(self, args):
        result = {"status": "success", "msg": "成功：移除用户."}

        project = get_projectnamefromkey(args['key'])
        owner = get_ownerfromkey(args['key'])
        if not session["username"] == owner:
            result["status"] = "fail"
            result["msg"] = "失败：没有权限操作，请联系{}.".format(owner)
            return result

        new_name = args["new_name"]

        try:
            self.app.config['DB'].del_projectuser(project, new_name)
        except Exception:
            result["status"] = "fail"
            result["msg"] = "DB操作失败！"

        self.save_project(args['key'])
        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'deluser', args['key'], new_name)

        return result

    def __get_projectlist(self, args):
        project_list = {"total": 0, "rows": []}
        res = self.app.config['DB'].runsql("Select projectname,owner,users,cron from project;")
        for r in res:
            (projectname,owner,users,cron) = r
            project_list["rows"].append(
                {"projectname": projectname, "owner": owner, "users": users, "cron": cron})

        return project_list

    def save_project(self, project_path):
        project = get_projectnamefromkey(project_path)
        projectfile = os.path.join(project_path, 'darwen/conf/project.conf')
        self.log.info("保存项目信息到文件:{}".format(projectfile))
        with open(projectfile, 'w') as f:
            f.write("# projectname|owner|users|cron\n")
            res = self.app.config['DB'].runsql("select * from project where projectname='{}';".format(project))
            for i in res:
                (projectname, owner, users, cron) = i
                line = "{}|{}|{}|{}\n".format(projectname, owner, users, cron)
                self.log.info("保存项目信息:{}".format(line))
                f.write(line)

class ProjectList(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('category', type=str, default="root")
        self.parser.add_argument('key', type=str, default="root")
        self.parser.add_argument('project', type=str)
        self.parser.add_argument('suite', type=str)
        self.parser.add_argument('splitext', type=str)
        self.log = getlogger("ProjectList")
        self.app = current_app._get_current_object()

    def get(self):
        args = self.parser.parse_args()

        #log.info("get projectList: args:{}".format(args))
        if args["key"] == "root":
            return get_projects(self.app, session["username"])
        else:
            path = args["key"]

            if os.path.isfile(path):      # 单个文件
                return get_step_by_case(self.app, path)

            files = list_dir(path)
            files = [f for f in files if not f.startswith('.')]  # Omit the hidden file
            if len(files) > 1:
                files.sort()

            children = []
            for d in files:
                ff = path + '/' + d
                if os.path.isdir(ff):     # 目录:Dir
                    icons = "icon-suite-open"
                    stat = "closed"
                    text = d

                    if self.app.config['SHOW_DIR_DETAIL']:    # For performance concern, False.
                        td = self.app.config['DB'].get_testdata(ff)
                        if td[0] > 0:    # [suites,cases,passed,Failed,unknown]
                            icons = "icon-suite-open_case"
                            text = d+':'+ " ".join([str(ss) for ss in td])

                    children.append({
                        "text": text, "iconCls": icons, "state": stat,
                        "attributes": {
                            "name": d,
                            "category": "suite",
                            "key": ff,
                        },
                        "children": []
                    })
                else:                  # 单个文件:single file
                    text = get_splitext(ff)
                    if text[1] in ICONS:
                        icons = ICONS[text[1]]
                    else:
                        icons = "icon-file-default"

                    if text[1] in (".robot"):
                        if self.app.config['SHOW_DIR_DETAIL']:
                            td = self.app.config['DB'].get_testdata(ff)   #[suites,cases,passed,Failed,unknown]
                            if td[1] == td[2]:
                                icons = 'icon-robot_pass'
                            if td[3] > 0:
                                icons = 'icon-robot_fail'
                            lb = d.replace('.robot', ':') + ' '.join([str(ss) for ss in td[1:]])
                        else:
                            suite_status = self.app.config['DB'].get_suitestatus(ff)
                            if suite_status == 'PASS':
                                icons = 'icon-robot_pass'
                            if suite_status == 'FAIL':
                                icons = 'icon-robot_fail'
                            lb = d.replace('.robot', '')

                        children.append({
                            "text": lb, "iconCls": icons, "state": "closed",
                            "attributes": {
                                "name": d,
                                "category": "case",
                                "key": ff,
                                "splitext": text[1]
                            },
                            "children": []
                        })
                    elif text[1] in (".resource"):
                        children.append({
                            "text": d, "iconCls": icons, "state": "closed",
                            "attributes": {
                                "name": d,
                                "category": "case",
                                "key": ff,
                                "splitext": text[1]
                            }
                        })
                    else:
                        children.append({
                            "text": d, "iconCls": icons, "state": "open",
                            "attributes": {
                                "name": d,
                                "category": "case",
                                "key": ff,
                                "splitext": text[1]
                            }
                        })
            return children


def get_project_list(app, username):
    projects = app.config["DB"].get_allproject(username)
    return projects

def get_projects(app, username):
    projects = get_project_list(app, username)
    children = []
    for p in projects:
        owner = p.split(':')[0]
        prj = p.split(':')[1]
        key = app.config["AUTO_HOME"] + "/workspace/" + owner + '/' + prj
        ico = "icon-project_s"
        text_p = prj

        if not owner == username :
            text_p = owner + ':' + prj
        if prj == app.config['DB'].get_user_main_project(session['username']):
            ico = "icon-project_m"
        children.append({
            "text": text_p, "iconCls": ico, "state": "closed",
            "attributes": {
                "name": prj,
                "category": "project",
                "key": key
            },
            "children": []
        })

        generate_high_light(key)
        generate_auto_complete(key)

        project_path = app.config['DB'].get_project_path(app.config['DB'].get_user_main_project(session['username']))
        app.config['DB'].init_project_settings(project_path)

        os.environ["ROBOT_DIR"] = project_path      # 用于解析 settings 中的环境变量
        os.environ["PROJECT_DIR"] = project_path

    return [{
        "text": session['username'], "iconCls": "icon-workspace",
        "attributes": {
            "category": "root",
            "key": "root",
        },
        "children": children}]

# charis  modified
def get_step_by_case(app, path):
    fext = os.path.splitext(path)[1]
    data = []
    if fext == ".robot":
        try:
            data = get_case_data(app, path)
        except Exception as e:
            app.log.warnning("Get_case_data of {} Exception :{}".format(path, e))
            return []

    #TODO: dealwith resource file : cannot use suiteBuilder
    '''if fext == ".resource":
        data = get_resource_data(app,path)'''

    return data


def get_case_data(app, path):

    projectdir = get_projectdirfromkey(path)
    os.environ["ROBOT_DIR"] = projectdir
    os.environ["PROJECT_DIR"] = projectdir

    suite = TestSuiteBuilder().build(path)
    children = []
    if suite:
        # add library , make it can be open if it is a file.
        for i in suite.resource.imports:

            rsfile = i.name
            if rsfile.find("%{ROBOT_DIR}") != -1:
                rsfile = rsfile.replace("%{ROBOT_DIR}", projectdir)
            if rsfile.find("%{PROJECT_DIR}") != -1:
                rsfile = rsfile.replace("%{PROJECT_DIR}", projectdir)

            # do not show System Library or rs file cannot be found.
            if not os.path.exists(rsfile):
                continue

            if os.path.isfile(rsfile):
                fname = os.path.basename(rsfile)
                children.append({
                    "text": fname, "iconCls": "icon-library", "state": "open",
                    "attributes": {
                        "name": fname, "category": "case", "key": rsfile,
                    }
                })
        for t in suite.tests:
            status = app.config['DB'].get_casestatus(path,t.name)
            icons = 'icon-step'
            if status == 'FAIL':
                icons = 'icon-step_fail'
            if status == 'PASS':
                icons = 'icon-step_pass'
            children.append({
                "text": t.name, "iconCls": icons, "state": "open",
                "attributes": {
                    "name": t.name, "category": "step", "key": path,
                },
                "children": []
            })

        ''' for v in suite.resource.variables:
            children.append({
                "text": v.name, "iconCls": "icon-variable", "state": "open",
                "attributes": {
                    "name": v.name, "category": "variable", "key": path,
                }
            }) 

        for t in suite.tests:
            keys = []
            for k in t.keywords:
                keys.append({
                    "text": k.name, "iconCls": "icon-keyword", "state": "open",
                    "attributes": {
                        "name": k.name, "category": "keyword", "key": path,
                    }
                })

            children.append({
                "text": t.name, "iconCls": "icon-step", "state": "closed",
                "attributes": {
                    "name": t.name, "category": "step", "key": path,
                },
                "children": keys
            })
        for v in suite.resource.keywords:
            children.append({
                "text": v.name, "iconCls": "icon-user-keyword", "state": "open",
                "attributes": {
                    "name": v.name, "category": "user_keyword", "key": path,
                }
            }) '''

    return children

def get_resource_data(app,path):
    projectdir = get_projectdirfromkey(path)
    os.environ["ROBOT_DIR"] = projectdir
    os.environ["PROJECT_DIR"] = projectdir

    suite = TestSuiteBuilder().build(path)
    children = []
    if suite:
        # add library , make it can be open if it is a file.
        for i in suite.resource.imports:

            rsfile = i.name
            if rsfile.find("%{ROBOT_DIR}") != -1:
                rsfile = rsfile.replace("%{ROBOT_DIR}", projectdir)
            if rsfile.find("%{PROJECT_DIR}") != -1:
                rsfile = rsfile.replace("%{PROJECT_DIR}", projectdir)

            # do not show System Library or rs file cannot be found.
            if not os.path.exists(rsfile):
                continue

            if os.path.isfile(rsfile):
                fname = os.path.basename(rsfile)
                children.append({
                    "text": fname, "iconCls": "icon-library", "state": "open",
                    "attributes": {
                        "name": fname, "category": "resource", "key": rsfile,
                    }
                })

        for v in suite.resource.variables:
            children.append({
                "text": v.name, "iconCls": "icon-variable", "state": "open",
                "attributes": {
                    "name": v.name, "category": "variable", "key": path,
                }
            })

        for v in suite.resource.keywords:
            children.append({
                "text": v.name, "iconCls": "icon-user-keyword", "state": "open",
                "attributes": {
                    "name": v.name, "category": "user_keyword", "key": path,
                }
            })

    return children