# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""

"""

import json
import codecs
from flask import current_app, session, request, send_file
from flask_restful import Resource, reqparse
from werkzeug.security import generate_password_hash, check_password_hash

from utils.mylogger import getlogger
from utils.do_report import get_caseinfo, get_excuteinfo, get_userexcinfo, get_caselist, get_comparedata

class Report(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('username', type=str)
        self.parser.add_argument('dir', type=str)
        self.parser.add_argument('request', type=str)
        self.log = getlogger("Report")
        self.app = current_app._get_current_object()


    def get(self):
        args = self.parser.parse_args()
        if args['request'] == 'caseinfo':
            return self.rpt_caseinfo(args)
        if args['request'] == 'excuteinfo':
            return self.rpt_excuteinfo(args)
        if args['request'] == 'userexcinfo':
            return self.rpt_userexcinfo(args)
        if args['request'] == 'caselist':
            return self.rpt_caselist(args)
        if args['request'] == 'compare':
            return self.rpt_compare(args)

    def post(self):
        args = self.parser.parse_args()
        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        else:
            print(request.files["files"])

        return result, 201

    def rpt_caselist(self, args):
        key = args['key']
        method = args['method']

        return get_caselist(key, method)

    def rpt_compare(self, args):
        key = args['key']
        method = args['method']

        return get_comparedata(key, method)

    def rpt_caseinfo(self, args):

        key = args['key']
        method = args['method']   # day| week| total

        return get_caseinfo(key,method)

    def rpt_excuteinfo(self, args):
        key = args['key']
        method = args['method']  # day| week| total

        return get_excuteinfo(key, method)
    def rpt_userexcinfo(self,args):
        key = args['key']
        method = args['method']

        return get_userexcinfo(key, method)