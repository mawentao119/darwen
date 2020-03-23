# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = 'charisma'

"""

用户管理接口

"""

import json
import codecs
from flask import current_app, session, request, send_file
from flask_restful import Resource, reqparse
from werkzeug.security import generate_password_hash, check_password_hash

from utils.file import list_dir, exists_path, rename_file, make_nod, remove_dir, write_file, read_file, mk_dirs
from utils.mylogger import getlogger

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
        res = self.app.config['DB'].runsql("Select username,fullname,email,category from user;")
        for r in res:
            (username, fullname, email, category) = r
            user_list["rows"].append(
                {"name": username, "fullname": fullname, "email": email, "category": category})
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
        result = {"status": "success", "msg": "Create user success."}

        if not session['username'] == "Admin":
            result["status"] = "fail"
            result["msg"] = "Only Admin can add new user."
            return result

        fullname = args["fullname"]
        username = args["username"]

        if username in ['myself', 'Admin', 'admin', 'all', 'All']:
            result["status"] = "fail"
            result["msg"] = "Illegal username : "+username
            return result

        passwordHash = generate_password_hash(args["password"])
        email = args["email"]
        if not self.app.config['DB'].add_user(username, fullname, passwordHash, email):
            result["status"] = "fail"
            result["msg"] = "Create user Failed : username exists."

        self.app.config['DB'].insert_loginfo(session['username'], 'user', 'create', username, result['status'])

        return result


    def __edit(self, args):
        result = {"status": "success", "msg": "Edit user info success."}

        username = args['username']

        if (not session['username'] == username) and (not session['username'] == 'Admin'):
            result["status"] = "fail"
            result["msg"] = "Only admin can modify user info."

            self.app.config['DB'].insert_loginfo(session['username'], 'user', 'edit', username,
                                                           result['status'])
            return result

        org_passwd = self.app.config['DB'].get_password(username) if self.app.config['DB'].get_password(username) else ''
        if check_password_hash(org_passwd, args["password"]):
            fullname = args["fullname"]
            passwordHash = generate_password_hash(args["new_password"])
            email = args["email"]
            self.app.config['DB'].del_user(username)
            if not self.app.config['DB'].add_user(username, fullname, passwordHash, email):
                result["status"] = "fail"
                result["msg"] = "DB failed，Please see log file."
        else:
            result["status"] = "fail"
            result["msg"] = "Password Wrong or user Not exits!"

        try:
            res = self.app.config['DB'].insert_loginfo(session['username'], 'user', 'edit', username, result['status'])
        except Exception as e:
            self.log.error("Edite user {} Exception:{}".format(username,e))

        return result


    def __delete(self, args):
        result = {"status": "success", "msg": "Delete user success."}

        if not session['username'] == "Admin":
            result["status"] = "fail"
            result["msg"] = "Only Admin can do this."

            self.app.config['DB'].insert_loginfo(session['username'], 'user', 'delete', args["username"],
                                                           result['status'])
            return result

        if args["username"] == "Admin" or args["username"] == "admin":
            result["status"] = "fail"
            result["msg"] = "Cannot delete Admin."
            return result

        projects = self.app.config['DB'].get_ownproject(args["username"])
        if len(projects) > 0:
            result["status"] = "fail"
            result["msg"] = "Please Delete user project first!"
        else:
            self.app.config['DB'].del_user(args["username"])

        self.app.config['DB'].insert_loginfo(session['username'], 'user', 'delete', args["username"], result['status'])

        return result


