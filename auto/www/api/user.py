# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = 'charisma'

"""

用户管理接口

"""

import os
from flask import current_app, session, request, send_file
from flask_restful import Resource, reqparse
from werkzeug.security import generate_password_hash, check_password_hash
from utils.mylogger import getlogger
from utils.file import remove_dir


class User(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('username', type=str)
        self.parser.add_argument('password', type=str)
        self.parser.add_argument('new_password', type=str, default="")
        self.parser.add_argument('email', type=str)
        self.parser.add_argument('fullname', type=str)
        self.log = getlogger("User")
        self.app = current_app._get_current_object()

    def get(self):
        user_list = {"total": 0, "rows": []}
        res = self.app.config['DB'].runsql(
            "Select username,fullname,email,category,main_project from user;")
        for r in res:
            (username, fullname, email, category, main_project) = r
            user_list["rows"].append(
                {"name": username, "fullname": fullname, "email": email, "category": category, "main_project": main_project})
        return user_list

    def post(self):
        args = self.parser.parse_args()

        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "edit":
            result = self.__edit(args)
        elif method == "delete":
            result = self.__delete(args)
        else:
            print(request.files["files"])

        return result, 201

    def __create(self, args):
        result = {"status": "success", "msg": "成功：创建用户."}

        main_project = self.app.config['DB'].get_user_main_project(
            session['username'])
        owner = self.app.config['DB'].get_projectowner(main_project)
        if not (session['username'] == owner):
            result["status"] = "fail"
            result["msg"] = "失败：你无权操作，请联系项目管理员{}.".format(owner)
            return result

        fullname = args["fullname"]
        username = args["username"]

        if username in ['myself', 'Admin', 'admin', 'all', 'All']:
            result["status"] = "fail"
            result["msg"] = "失败:非法用户名 "+username
            return result

        passwordHash = generate_password_hash(args["password"])
        email = args["email"]

        if not self.app.config['DB'].add_user(username, fullname, passwordHash, email, 'User', main_project):
            result["status"] = "fail"
            result["msg"] = "失败：用户名已存在."

        self.log.info("创建用户: 增加用户到项目 project:{} users:{}".format(
            main_project, username))
        self.app.config['DB'].add_projectuser(main_project, username)

        self.save_user(main_project)
        self.app.config['DB'].insert_loginfo(
            session['username'], 'user', 'create', username, result['status'])

        return result

    def __edit(self, args):
        result = {"status": "success", "msg": "成功：编辑用户信息."}

        username = args['username']
        owner = self.app.config['DB'].get_projectowner(
            self.app.config['DB'].get_user_main_project(session['username']))

        if not (session['username'] == username or session['username'] == owner):
            result["status"] = "fail"
            result["msg"] = "失败：你无权操作，请联系项目管理员{}.".format(owner)

            self.app.config['DB'].insert_loginfo(session['username'], 'user', 'edit', username,
                                                 result['status'])
            return result

        org_passwd = self.app.config['DB'].get_password(
            username) if self.app.config['DB'].get_password(username) else ''
        if check_password_hash(org_passwd, args["password"]):
            fullname = args["fullname"]
            passwordHash = generate_password_hash(args["new_password"])
            email = args["email"]
            main_project = self.app.config['DB'].get_user_main_project(
                session['username'])
            self.app.config['DB'].del_user(username)
            if not self.app.config['DB'].add_user(username, fullname, passwordHash, email, 'User', main_project):
                result["status"] = "fail"
                result["msg"] = "失败：DB操作失败，见日志."
        else:
            result["status"] = "fail"
            result["msg"] = "失败：原密码错误或用户不存在!"

        try:
            res = self.app.config['DB'].insert_loginfo(
                session['username'], 'user', 'edit', username, result['status'])
        except Exception as e:
            self.log.error("编辑用户异常 {} Exception:{}".format(username, e))

        self.save_user(
            self.app.config['DB'].get_user_main_project(session['username']))

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "成功：删除用户."}

        del_user_mainproject = self.app.config['DB'].get_user_main_project(
            args["username"])
        owner = self.app.config['DB'].get_projectowner(del_user_mainproject)

        if not (session['username'] == owner):
            result["status"] = "fail"
            result["msg"] = "失败：非项目管理员，请联系管理员{}.".format(owner)

            self.app.config['DB'].insert_loginfo(session['username'], 'user', 'delete', args["username"],
                                                 result['status'])
            return result

        if (session['username'] == args['username']):
            result["status"] = "fail"
            result["msg"] = "失败：请联系Admin删除项目及所有用户."
            return result

        if args["username"] == "Admin" or args["username"] == "admin":
            result["status"] = "fail"
            result["msg"] = "失败：Cannot delete Admin."
            return result

        projects = self.app.config['DB'].get_ownproject(args["username"])
        if len(projects) > 0:
            result["status"] = "fail"
            result["msg"] = "失败：该用户有多个项目!"
        else:
            self.app.config['DB'].del_user(args["username"])
            work_path = os.path.join(
                self.app.config['AUTO_HOME'], 'workspace', args['username'])
            job_path = os.path.join(
                self.app.config['AUTO_HOME'], 'jobs', args['username'])

            remove_dir(work_path) if os.path.exists(work_path) else None
            remove_dir(job_path) if os.path.exists(job_path) else None

        self.save_user(
            self.app.config['DB'].get_user_main_project(session['username']))
        self.app.config['DB'].insert_loginfo(
            session['username'], 'user', 'delete', args["username"], result['status'])

        return result

    def save_user(self, project):
        owner = self.app.config['DB'].get_projectowner(project)

        if owner == 'unknown':
            return

        userfile = os.path.join(
            self.app.config['AUTO_HOME'], 'workspace', owner, project, 'platforminterface/user.conf')
        self.log.info("保存用户信息到文件:{}".format(userfile))
        with open(userfile, 'w') as f:
            f.write("# username|fullname|passworkdHash|email|category|main_project\n")
            cur_project = self.app.config['DB'].get_user_main_project(
                session['username'])
            res = self.app.config['DB'].runsql(
                "select * from user where main_project='{}' ;".format(cur_project))
            for i in res:
                (username, fullname, passworkdHash,
                 email, category, main_project) = i
                f.write("{}|{}|{}|{}|{}|{}\n".format(username, fullname, passworkdHash,
                                                     email, category, main_project))
