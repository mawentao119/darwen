# -*- coding: utf-8 -*-

__author__ = "charisma"

"""
这里用来进行系统层面的配置管理，原有的settings 见ORG备份
"""

from flask import current_app, session, request, send_file
from flask_restful import Resource, reqparse
from utils.mylogger import getlogger

class Settings(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('description', type=str)
        self.parser.add_argument('item', type=str)
        self.parser.add_argument('value', type=str, default="")
        self.parser.add_argument('demo', type=str)
        self.parser.add_argument('category', type=str)
        self.log = getlogger("Settings")
        self.app = current_app._get_current_object()

    def get(self):
        args = self.parser.parse_args()
        if args['method'] == 'setting_list':
            return self.__get_settinglist(args)
        if args['method'] == 'machines':
            return self.__get_machines(args)
        if args['method'] == 'modules':
            return self.__get_modules(args)

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
        result = {"status": "success", "msg": "创建配置项成功."}

        ## 暂不考虑权限，所有人都可以修改配置项
        #if not session['username'] == "Admin":
        #    result["status"] = "fail"
        #    result["msg"] = "Only Admin can add new user."
        #    return result

        description = args["description"]
        item = args["item"]
        value = args["value"]
        demo = args["demo"]

        if not self.app.config['DB'].add_setting(description, item, value, demo):
            result["status"] = "fail"
            result["msg"] = "创建失败: 配置项已存在！."

        self.app.config['DB'].insert_loginfo(session['username'], 'settings', 'create', item + ":" + value, result["status"])

        return result


    def __edit(self, args):
        result = {"status": "success", "msg": "编辑配置项信息成功."}

        ## 暂不考虑权限
        #if (not session['username'] == username) and (not session['username'] == 'Admin'):
        #    result["status"] = "fail"
        #    result["msg"] = "Only admin can modify user info."
        #
        #    self.app.config['DB'].insert_loginfo(session['username'], 'user', 'edit', username,
        #                                                   result['status'])
        #    return result

        description = args["description"]
        item = args["item"]
        value = args["value"]
        demo = args["demo"]

        sql = '''UPDATE settings set description='{}',
                                     value='{}',
                                     demo='{}'
                 WHERE item='{}';'''.format(description,value,demo,item)

        res = self.app.config['DB'].runsql(sql)

        if res.rowcount < 1:
            result["status"] = "fail"
            result["msg"] = "编辑失败: 配置项不存在！."

        self.app.config['DB'].insert_loginfo(session['username'], 'setting', 'update', item + ":" + value, result["status"])

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "删除配置项成功."}

        #if not session['username'] == "Admin":
        #    result["status"] = "fail"
        #    result["msg"] = "Only Admin can do this."
        #
        #    self.app.config['DB'].insert_loginfo(session['username'], 'user', 'delete', args["username"],
        #                                                   result['status'])
        #    return result
        #
        #if args["username"] == "Admin" or args["username"] == "admin":
        #    result["status"] = "fail"
        #    result["msg"] = "Cannot delete Admin."
        #    return result

        self.app.config['DB'].del_setting(args["item"])

        self.app.config['DB'].insert_loginfo(session['username'], 'setting', 'delete', args["item"], result['status'])

        return result

    def __get_settinglist(self, args):
        setting_list = {"total": 0, "rows": []}
        res = self.app.config['DB'].runsql("Select description,item,value,demo from settings;")
        for r in res:
            (description, item, value, demo) = r
            setting_list["rows"].append(
                {"description": description, "item": item, "value": value, "demo": demo})
        return setting_list


    def __get_machines(self, args):
        import os  ## ?? why cannot put it on top.
        setting_list = {"total": 0, "rows": []}

        infof = self.app.config['DB'].get_setting('test_env_machines')
        ff = os.path.join(self.app.config['AUTO_HOME'], infof)

        if not os.path.exists(ff):
            self.log.error("Get Machines: Cannot find file:{}".format(ff))
            return setting_list

        with open(ff,'r') as f:
            for l in f:
                splits = l.strip().split('|')
                if len(splits) !=5 :
                    self.log.error("Get Machines: from file:{} found err line:{}".format(ff,l))
                    continue
                (ip, os, cpus , mem, ontime ) = splits
                setting_list["rows"].append(
                    {"ip": ip, "os": os, "cpus": cpus, "mem": mem, "ontime":ontime})

        return setting_list

    def __get_modules(self, args):
        import os  ## ?? why cannot put it on top.
        setting_list = {"total": 0, "rows": []}

        infof = self.app.config['DB'].get_setting('test_env_modules')
        ff = os.path.join(self.app.config['AUTO_HOME'], infof)

        if not os.path.exists(ff):
            self.log.error("Get Modules: Cannot find file:{}".format(ff))
            return setting_list

        with open(ff,'r') as f:
            for l in f:
                splits = l.strip().split('|')
                if len(splits) != 4:
                    self.log.error("Get Module: from file:{} found err line:{}".format(ff,l))
                    continue
                (name, machines, status , ontime ) = splits
                setting_list["rows"].append(
                    {"name": name, "machines": machines, "status": status, "ontime":ontime})

        return setting_list
