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

    def post(self):
        args = self.parser.parse_args()

        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "edit":
            result = self.__edit(args)
        elif method == "delete":
            result = self.__delete(args)
        elif method == "adduser":
            result = self.__adduser(args)
        elif method == "deluser":
            result = self.__deluser(args)
        elif method == "gitclone":
            result = self.__gitclone(args)

        return result, 201

    def __create(self, args):
        result = {"status": "success", "msg": "Create Project Success."}
        
        if args["name"] in self.reserved_names :
            result = {"status": "fail", "msg": "Please use other project name."}
            return result

        user_path = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (session["username"], args["name"])
        if not exists_path(user_path):
            mk_dirs(user_path)

        if not self.app.config['DB'].add_project(args["name"],session["username"],'myself'):
            result["status"] = "fail"
            result["msg"] = "Create Failed: Project name exists!"

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'create', user_path, result['status'])

        return result

    def __gitclone(self, args):

        url = args['name']

        user_path = self.app.config["AUTO_HOME"] + "/workspace/%s" % (session["username"])

        (ok, info) = remote_clone(url, user_path)

        if ok:
            projectname = get_projectnamefromkey(info)
            result = {"status": "success", "msg": "Create Project success:"+projectname }
            if not self.app.config['DB'].add_project(projectname, session["username"], 'myself'):
                result["status"] = "fail"
                result["msg"] = "Create Failed: Project name exists!"

            self.app.config['DB'].insert_loginfo(session['username'], 'project', 'gitcreate', info,
                                                           result['status'])
        else:
            result = {"status": "fail", "msg": info}
            self.app.config['DB'].insert_loginfo(session['username'], 'project', 'gitcreate', user_path,
                                                           result['status'])

        return result

    def __edit(self, args):
        result = {"status": "success", "msg": "Rename project success."}
        
        if args["new_name"] in self.reserved_names :
            result = {"status": "fail", "msg": "Please use other name."}
            return result
        
        if args["name"] in self.reserved_names :
            result = {"status": "fail", "msg": "Cannot rename this project."}
            return result

        owner = get_ownerfromkey(args['key'])
        if not session["username"] == owner:
            result["status"] = "fail"
            result["msg"] = "FAIL：Cannot rename shared project."
            return result

        old_name = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (owner, args["name"])
        new_name = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (owner, args["new_name"])

        if not rename_file(old_name, new_name):
            result["status"] = "fail"
            result["msg"] = "Rename Failed, new name exits!"
        if not self.app.config['DB'].edit_project(args["name"], args["new_name"], session["username"]):
            result["status"] = "fail"
            result["msg"] = "Rename Failed, new name exits!"

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'rename', old_name, result['status'])

        # Delete resource is not dangerous, all of that can be auto generated.
        clear_projectres('usepath', old_name)

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "Delete project success."}

        self.log.debug("Delete Project args:{}".format(args))

        owner = get_ownerfromkey(args['key'])
        if not session["username"] == owner:
            result["status"] = "fail"
            result["msg"] = "FAIL：Cannot Delete shared project!"
            return result

        #user_path = self.app.config["AUTO_HOME"] + "/workspace/%s/%s" % (session["username"], args["name"])
        user_path = args['key']
        if exists_path(user_path):
            remove_dir(user_path)

        if not self.app.config['DB'].del_project(args["name"],session["username"]):
            result["status"] = "fail"
            result["msg"] = "Delete Failed, Project not exists."

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'delete', user_path, result['status'])

        #Delete resource is not dangerous, all of that can be auto generated.
        clear_projectres('usepath',user_path)

        return result

    def __adduser(self, args):
        result = {"status": "success", "msg": "Add user to project success."}

        project = get_projectnamefromkey(args['key'])
        owner = get_ownerfromkey(args['key'])
        if not session["username"] == owner:
            result["status"] = "fail"
            result["msg"] = "FAIL：Only the project owner can add new user."
            return result

        new_name = args["new_name"]

        try:
            self.app.config['DB'].add_projectuser(project, new_name)
        except Exception:
            result["status"] = "fail"
            result["msg"] = "DB failed！"

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'adduser', args['key'], new_name)

        return result

    def __deluser(self, args):
        result = {"status": "success", "msg": "Remove user success."}

        project = get_projectnamefromkey(args['key'])
        owner = get_ownerfromkey(args['key'])
        if not session["username"] == owner:
            result["status"] = "fail"
            result["msg"] = "FAIL：Only the project owner can remove user."
            return result

        new_name = args["new_name"]

        try:
            self.app.config['DB'].del_projectuser(project, new_name)
        except Exception:
            result["status"] = "fail"
            result["msg"] = "DB failed！"

        self.app.config['DB'].insert_loginfo(session['username'], 'project', 'deluser', args['key'], new_name)

        return result


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
    print("get_projectlist:user:{},{}".format(username,projects))
    children = []
    for p in projects:
        owner = p.split(':')[0]
        prj = p.split(':')[1]
        key = app.config["AUTO_HOME"] + "/workspace/" + owner + '/' + prj
        ico = "icon-project"
        text_p = prj
        if not owner == username :
            ico = "icon-project_c"
            text_p = owner + ':' + prj
        children.append({
            "text": text_p, "iconCls": ico, "state": "closed",
            "attributes": {
                "name": prj,
                "category": "project",
                "key": key
            },
            "children": []
        })

        if username == "Admin":
            app.config["DB"].init_settings()
            app.config["CUR_PROJECT"] = 'Demo_Project'
        else:
            app.config["DB"].init_project_settings(key)
            app.config["CUR_PROJECT"] = prj

        generate_high_light(key)
        generate_auto_complete(key)

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