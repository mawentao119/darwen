# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""
charis made a big change of this file
"""
import os
from flask import current_app, session
from flask_restful import Resource, reqparse

from utils.file import mk_dirs, exists_path, rename_file, remove_dir
from utils.mylogger import getlogger
from utils.gitit import remote_clone

class Suite(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('new_name', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('project_name', type=str)
        self.log = getlogger("Suite")
        self.app = current_app._get_current_object()

    def post(self):
        args = self.parser.parse_args()
        self.log.debug("**** suite post args:{}".format(args))
        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "edit":
            result = self.__edit(args)
        elif method == "delete":
            result = self.__delete(args)
        elif method == "refresh":
            result = self.__refreshcases(args)
        elif method == "gitclone":
            result = self.__gitclone(args)

        return result, 201

    def __create(self, args):
        result = {"status": "success", "msg": "Create suite success."}
        user_path = args['key'] + '/' + args['name']
        if not exists_path(user_path):
            mk_dirs(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Create Failed, filename exists!"

        try:
            res = self.app.config['DB'].insert_loginfo(session['username'], 'dir', 'create', user_path, result['status'])
        except Exception as e:
            self.log.error("Create dir {} Execption: {}".format(user_path,e))

        return result

    def __gitclone(self, args):
        url = args['name']
        user_path = args['key']

        (ok, info) = remote_clone(url, user_path)

        if ok:
            result = {"status": "success", "msg": info}
            self.app.config['DB'].insert_loginfo(session['username'], 'dir', 'gitcreate', user_path,
                                                           result['status'])
        else:
            result = {"status": "fail", "msg": info}

        return result

    def __edit(self, args):
        result = {"status": "success", "msg": "Rename suite success."}
        old_name = args['key']
        new_name = os.path.dirname(old_name) + '/' + args["new_name"]

        if not rename_file(old_name, new_name):
            result["status"] = "fail"
            result["msg"] = "Rename Failed , new name exists!"
            return result

        self.app.config['DB'].delete_suite(old_name)
        isok = self.app.config['DB'].refresh_caseinfo(new_name,'force')
        if not isok:
            result["status"] = "fail"
            result["msg"] = "Failed：Rename OK，Refresh case failed！"

        self.app.config['DB'].insert_loginfo(session['username'], 'dir', 'rename', old_name, result['status'])

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "Delete suite success."}
        user_path = args['key']
        if exists_path(user_path):
            remove_dir(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Delete Failed，file not exits!"
            return result

        self.app.config['DB'].delete_suite(user_path)

        self.app.config['DB'].insert_loginfo(session['username'], 'dir', 'delete', user_path, result['status'])

        return result

    def __refreshcases(self, args):
        result = {"status": "success", "msg": "Refresh case info success."}
        info_key = args['key']
        isok = self.app.config['DB'].refresh_caseinfo(info_key)

        if not isok:
            result = {"status": "fail", "msg": "Fail：Refresh too often, Try later."}

        self.app.config['DB'].insert_loginfo(session['username'], 'dir', 'refresh', info_key, result['status'])

        return result
