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
from utils.gitit import remote_clone


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

        result = {"status": "success", "msg": "创建成功" +
                  ":"+os.path.basename(user_path)+":"+user_path}
        if not exists_path(user_path):
            make_nod(user_path)
            mod = '''
            { "class": "GraphLinksModel",
            "modelData": {"test":true, "hello":"world", "version":42},
  "nodeKeyProperty": "id",
  "nodeDataArray": [ 
{"id":-1, "loc":"155 -138", "category":"Start"},
{"id":0, "loc":"190 15", "text":"Shopping页"},
{"id":1, "loc":"353 32", "text":"商品详情"},
{"id":2, "loc":"353 166", "text":"商品列表"},
{"id":3, "loc":"512 12", "text":"款式信息"},
{"id":4, "loc":"536.0500000000001 -88", "text":"购物车信息"},
{"id":6, "loc":"666.6499999999999 25.650000000000034", "text":"付款方式"},
{"id":-2, "loc":"508.1562358276643 114.63253968253969", "category":"End"}
 ],
  "linkDataArray": [ 
{"from":-1, "to":0, "text":"打开网站", "points":[200.9629729076036,-63.96743795509042,207.28009415140457,-36.69798710088425,206.78172806502616,-10.695691829847046,196.16932689972282,15]},
{"from":0, "to":1, "progress":"true", "text":"点击商品", "points":[232.2781219482422,24.379717115974557,261.3190602651592,20.997646396489007,288.48056705179744,24.54227174050714,316.6800231933594,34.22325211124115]},
{"from":0, "to":2, "progress":"true", "text":"搜索商品", "points":[214.19571045593858,44.875448608398436,260.5816761145265,73.5127877703892,304.1651239662507,113.88763823425634,342.1203433525658,166]},
{"from":1, "to":2, "progress":"true", "text":"搜索相似", "points":[357.8141649132298,61.875448608398436,369,96.58363240559896,369,131.29181620279948,357.8141649132298,166]},
{"from":2, "to":3, "progress":"true", "text":"点击结果", "points":[363.3562716443014,166,400.00934698668675,113.13217718010841,442.7275367513289,71.75732671624122,488.9124913610701,41.875448608398436]},
{"from":1, "to":3, "progress":"true", "text":"点击详情", "points":[389.3199768066406,34.196859203045165,420.7588034398072,23.377420028365243,447.32185369604207,19.777038941640292,476.0403823852539,22.75408251185555]},
{"from":3, "to":0, "text":"返回首页", "curviness":-100, "points":[493.78291884633757,12,391.41132758690804,-71.94311876401206,307.7139093740174,-71.16332915333295,207.39228093935913,15]},
{"from":3, "to":4, "progress":"true", "text":"加入购物车", "points":[511.3166322041318,12,510.5793221149014,-13.179999309667988,516.1867968994235,-36.523186699336996,527.6771018645919,-58.12455139160157]},
{"from":4, "to":0, "text":"继续购物", "curviness":-150, "points":[492.4000289916993,-83.15086093012349,343.34999999999997,-117.59999999999997,290.85,-110.24999999999997,200.74608710253074,15]},
{"from":4, "to":6, "progress":"true", "text":"结账", "points":[579.6999710083008,-66.15499465371636,639.45,-56.69999999999999,655.2,-16.799999999999955,663.6696249222838,25.650000000000034]},
{"from":6, "to":4, "text":"修改订单", "points":[630.3300231933592,30.004187191844576,567.0000000000001,11.550000000000011,563.9253403825494,-35.06864885461613,547.1002815277606,-58.12455139160157]},
{"from":6, "to":-2, "progress":"true", "text":"微信支付", "points":[657.6369751605379,55.52544860839847,637.9069841576112,88.61403886082026,610.8030334013039,113.25679381829944,577.7328981834986,132.70735674621173]}
 ]}
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
