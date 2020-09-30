# -*- coding: utf-8 -*-

__author__ = "苦叶子"

"""

modified: use DB not json.

"""
from flask import current_app, url_for, redirect, session
from flask_restful import Resource, reqparse
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import codecs
from utils.mylogger import getlogger

class Auth(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('username', type=str)
        self.parser.add_argument('password', type=str)
        self.log = getlogger("auth")

    def get(self):
        args = self.parser.parse_args()
        username = args["username"]

        if username in session:
            session.pop(username, None)

        return {"status": "success", "msg": "登出成功", "url": url_for('routes.index')}, 201

    # chairs added: use DB
    def post(self):
        args = self.parser.parse_args()
        username = args["username"]
        password = args["password"]
        app = current_app._get_current_object()

        passwordHash = app.config["DB"].get_password(username)

        self.log.info("登录请求: user: {} password xxx".format(username))

        if passwordHash:
            if check_password_hash(passwordHash, password):
                session['username'] = username
                return {"status": "success", "msg": "登录成功", "url": url_for('routes.dashboard')}, 201

        self.log.warning("登录失败: user: {} password ******".format(username))

        app.config['DB'].insert_loginfo(username, 'login', username, password)

        return {"status": "fail", "msg": "login fail", "url": url_for('routes.index')}, 201
