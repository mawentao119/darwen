# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""
Add "key" as argument.
Make KeyWords content link with the editor's content.
"""

import os
from flask_restful import Resource, reqparse
from utils.parsing import parser_robot_keyword_list
from utils.mylogger import getlogger

class Keyword(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('category', type=str)  # Do not use category now ,maybe latter.
        self.parser.add_argument('key', type=str)  # This is the editor's file path.
        self.log = getlogger("keyword")

    def get(self):
        args = self.parser.parse_args()
        fext = os.path.splitext(args['key'])[1]
        self.log.debug("GET args:{}".format(args))
        if fext in ('.robot', '.resource'):
            return parser_robot_keyword_list(args['key'])
        else:
            return {}
