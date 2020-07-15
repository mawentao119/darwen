# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""

"""

import os
from flask import current_app, session, request
from flask_restful import Resource, reqparse

from utils.parsing import update_resource
from utils.file import exists_path, rename_file, make_nod, remove_file, write_file, read_file, copy_file, get_splitext
from utils.mylogger import getlogger

class Case(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('new_name', type=str)
        self.parser.add_argument('project_name', type=str)
        self.parser.add_argument('suite_name', type=str)
        self.parser.add_argument('category', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('new_category', type=str)
        self.parser.add_argument('path', type=str)
        self.parser.add_argument('data', type=str)
        self.app = current_app._get_current_object()
        self.log = getlogger("Case")

    def get(self):
        args = self.parser.parse_args()
        #charis added TODO 应该没有传path的地方了，考虑删除掉
        '''if args["path"]:
            args["path"] = args["path"].replace("--","/")
        if args["key"]:
            args["key"] = args["key"].replace("--","/")'''

        key = args["key"].replace("--","/") if args["key"] else args["path"].replace("--","/")

        self.log.debug("Get args:{}".format(args))
        result = {"status": "success", "msg": "Read file success."}

        ext = get_splitext(key)
        result["ext"] = ext[1]

        #path = self.app.config["AUTO_HOME"] + "/workspace/%s%s" % (session["username"], args["path"])
        #path = args["key"]
        data = read_file(key)
        if not data["status"]:
            result["status"] = "fail"
            result["msg"] = "Read file failed."

        result["data"] = data["data"]
        return result, 201

    def post(self):
        args = self.parser.parse_args()
        #if args["path"]:
        #    args["path"] = args["path"].replace("--", "/")
        if args["key"]:
            args["key"] = args["key"].replace("--", "/")
        self.log.debug("Post args:{}".format(args))
        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "edit":
            result = self.__edit(args)
        elif method == "delete":
            result = self.__delete(args)
        elif method == "save":
            result = self.__save(args)
        elif method == "copy":
            result = self.__copy(args)
        elif method == "handpass":
            result = self.__handpass(args)
        elif method == "handfail":
            result = self.__handfail(args)
        elif method == "handunknown":
            result = self.__handunknown(args)
        elif method == "save_result":
            result = self.__save_result(args)
        elif method == "delete_caserecord":
            result = self.__delete_caserecord(args)
        elif method == "recordbug":
            result = self.__recordbug(args)
        else:
            print(request.files["files"])

        return result, 201

    def __create(self, args):

        if args['name'].endswith(args['category']):
            args['name'] = args['name'].split('.')[0]
        if args['category'] == '.oth':
            user_path = args["key"] + '/' + args['name']
        else:
            user_path = args["key"] + '/' + args['name'] + args['category']

        result = {"status": "success", "msg": "Create success"+":"+os.path.basename(user_path)+":"+user_path}
        if not exists_path(user_path):
            make_nod(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Create Fail: File exists !"

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'create', user_path, result['status'])

        return result

    def __edit(self, args):

        # TODO: 参数太复杂了，需要简化
        old_name = args["key"]
        fpre = os.path.dirname(old_name)

        if args['new_name'].endswith(args['new_category']):
            args['new_name'] = args['new_name'].split('.')[0]
        if args['new_category'] == '.oth':
            new_name = fpre + '/' + args["new_name"]
        else:
            new_name = fpre + '/' + args["new_name"] + args["new_category"]

        result = {"status": "success", "msg": "Rename success:"+new_name}
        if not rename_file(old_name, new_name):
            result["status"] = "fail"
            result["msg"] = "Rename Failed , filename exists."
            return result

        if old_name.endswith('.robot'):
            self.app.config['DB'].delete_suite(old_name)
        if new_name.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(new_name)

        if old_name.endswith('.resource'):   # delete keywords or update highlight
            update_resource(old_name)
            update_resource(new_name)

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'rename', old_name, result['status'])

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "Delete success:"+args['key']}

        user_path = args["key"]
        if exists_path(user_path):
            remove_file(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Delete Failed, File not exists!"
            return result

        if user_path.endswith('.robot'):
            self.app.config['DB'].delete_suite(user_path)
        if user_path.endswith('.resource'):   # delete keywords or update highlight
            update_resource(user_path)

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'delete', user_path, result['status'])

        return result

    def __delete_caserecord(self, args):
        res = self.app.config['DB'].runsql("DELETE from caserecord;")
        if res:
            result = {"status": "success", "msg": "Delete caserecord success!"}
        else:
            result = {"status": "fail", "msg": "Delete caserecord failed!"}

        self.app.config['DB'].insert_loginfo(session['username'], 'caserecord', 'delete', 'none', result['status'])
        return result

    def __save(self, args):
        result = {"status": "success", "msg": "Save success."}
        user_path = args["key"]

        if not write_file(user_path, args["data"]):
            result["status"] = "fail"
            result["msg"] = "Save Failed"

        if user_path.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(user_path, 'force')
            self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'edit', user_path, result['status'])

        if user_path.endswith('.resource'):   # delete keywords or update highlight
            update_resource(user_path)

        return result

    def __copy(self, args):
        old_name = args["key"]
        fpre = os.path.dirname(old_name)
        new_name = 'copy_' + os.path.basename(old_name)

        new_file = fpre + '/' + new_name

        result = {"status": "success", "msg": "File copy success"+":"+new_name +":" + new_file}
        if not copy_file(old_name, new_file):
            result["status"] = "fail"
            result["msg"] = "File copy Failed，new name exists!"

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'copy', old_name, result['status'])

        return result

    def __handpass(self, args):
        return self.__set_casestatus(args,'PASS')
    def __handfail(self, args):
        return self.__set_casestatus(args,'FAIL')
    def __handunknown(self, args):
        return self.__set_casestatus(args,'unknown')

    def __set_casestatus(self, args, status):
        info_key = args['key']
        info_name = args['name']
        status = status
        runuser = session['username']

        is_suite = False

        if info_name.endswith('.robot'):      # robot file
            is_suite = True

        try:

            if is_suite :
                res = self.app.config['DB'].set_suitestatus(info_key, status, runuser)
            else:
                res = self.app.config['DB'].set_casestatus(info_key, info_name, status, runuser)

            if res.rowcount > 0:
                result = {"status": "success", "msg": "Set status OK :" + info_name}
            else:
                result = {"status": "fail",
                          "msg": "Cannot find case: " + info_name + ", you can try Refresh Dir."}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'hand', info_key, info_name+':'+status)
        except Exception as e:
            self.log.error("handpass Exception:{}".format(e))
            result = {"status": "fail", "msg": "Update DB Failed! See log file."}

        return result

    def __recordbug(self, args):
        result = {"status": "success", "msg": "This is TODO"}
        return result

    def __save_result(self, args):
        info_key = args['key']
        info_name = args['name']

        if info_name == 'save_d_i_r':
            msginfo = 'Dir|Suite: ' + info_key
            res = self.app.config['DB'].save_caserecord_d(info_key)
        else:
            msginfo = 'Case: ' + info_name
            res = self.app.config['DB'].save_caserecord(info_key, info_name)

        if res :
            result = {"status": "success", "msg": "保存用例结果成功! " + msginfo}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'save_result', info_key,
                                                 info_name + ':success')
        else:
            result = {"status": "fail",
                      "msg": "保存用例结果失败: " + info_name + ", 用例结果已存在."}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'save_result', info_key,
                                                 info_name + ':fail')
        return result

