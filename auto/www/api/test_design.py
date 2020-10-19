# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""

"""

import os
from flask import current_app, session, request
from flask_restful import Resource, reqparse

from utils.parsing import update_resource
from utils.file import exists_path, rename_file, make_nod, remove_file, mk_dirs, remove_dir, write_file, read_file, copy_file, get_splitext
from utils.mylogger import getlogger
from utils.model_design import gen_casetemplate


class TestDesign(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('project_name', type=str)
        self.parser.add_argument('suite_name', type=str)
        self.parser.add_argument('category', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('data', type=str)

        self.app = current_app._get_current_object()
        self.log = getlogger("TestDesign")

    def get(self):
        # TODO
        result = {"status": "success", "msg": "读取文件成功."}
        return result, 201

    def post(self):
        args = self.parser.parse_args()
        if args["key"]:
            args["key"] = args["key"].replace("--", "/")
        self.log.debug("Post args:{}".format(args))
        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "save":
            result = self.__save(args)
        elif method == "gen_casetemplate":
            result = self.__gen_casetemplate(args)
        else:
            print(request.files["files"])

        return result, 201

    def __create(self, args):

        self.log.info(
            "***create***name:{} **cat:{}".format(args['name'], args['category']))
        if args['name'].endswith(args['category']):
            args['name'] = args['name'].split('.')[0]
        if args['category'] == '.oth':
            user_path = args["key"] + '/' + args['name']
        else:
            user_path = args["key"] + '/' + args['name'] + args['category']

        result = {"status": "success", "msg": "创建测试模型成功" +
                  ":"+os.path.basename(user_path)+":"+user_path}
        if not exists_path(user_path):
            make_nod(user_path)
            mod = '''
{ "class": "GraphLinksModel",
  "nodeKeyProperty": "id",
  "linkKeyProperty": "key",
  "nodeDataArray": [ 
    {"id":-1, "loc":"-256 -210", "category":"Start", "text":"开始节点", "description":"这里也可以定义变量", "outputvariable":"产品列表", "disabled":false, "properties":""},
    {"id":0, "loc":"-113 -126", "text":"Shopping页", "description":"", "outputvariable":"", "disabled":false, "properties":"产品列表=产品列表"},
    {"id":2, "loc":"82 -127", "text":"购买", "description":"", "outputvariable":"", "disabled":false, "properties":"购物列表=手表"},
    {"text":"页面关闭", "id":-5, "loc":"71.0 -74.0"}
  ],
  "linkDataArray": [ 
    {"key":-1, "from":-1, "to":0, "text":"打开网站", "points":[-187,-166,-161,-159,-140,-146,-124,-126], "description":"", "parameters":"", "mainpath":true},
    {"key":0, "from":0, "to":2, "progress":"true", "text":"买手表", "points":[-70,-122,-30,-131,13,-131,60,-118], "description":"", "parameters":"手表", "weight":"2.0", "mainpath":true, "action":"buy"},
    {"key":1, "from":0, "to":-5, "points":[-70,-111,-27,-111,13,-98,49,-74], "text":"关闭", "description":"", "action":"close", "parameters":"window", "mainpath":false}
  ],
  "modelData": {"version":1, "nodes":4, "links":3, "actions":3, "variables":5, "variable":[], "init_actions":"模块的初始化条件"}
}
            '''
            with open(user_path, 'w') as f:
                f.write(mod)
        else:
            result["status"] = "fail"
            result["msg"] = "失败: 文件已存在 !"

        self.app.config['DB'].insert_loginfo(
            session['username'], 'model', 'create', user_path, result['status'])

        return result

    def __save(self, args):
        result = {"status": "success", "msg": "成功：保存成功."}
        user_path = args["key"]

        self.log.info(
            "***save path:{} \n***json:{}".format(user_path, args["data"]))

        if not write_file(user_path, args["data"]):
            result["status"] = "fail"
            result["msg"] = "失败：保存失败"

        if user_path.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(user_path, 'force')
            self.app.config['DB'].insert_loginfo(
                session['username'], 'suite', 'edit', user_path, result['status'])

        # delete keywords or update highlight
        if user_path.endswith('.resource'):
            update_resource(user_path)

        return result

    def __gen_casetemplate(self, args):
        modle_file = args["key"]
        output_file = os.path.splitext(modle_file)[0] + '.tplt'
        self.log.info("开始生成用例模版，模型：{}, 输出模版：{}".format(
            modle_file, output_file))
        #result = {"status": "success", "msg": "成功：保存成功."}
        result = gen_casetemplate(modle_file, output_file)

        return result
