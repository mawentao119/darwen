# -*- coding: utf-8 -*-

__author__ = "苦叶子"

"""
Modified by mawentao119@gmail.com
"""

import os
import json
import codecs
from flask import Flask
from flask_login import LoginManager
# from flask_mail import Mail
from flask_apscheduler import APScheduler

from auto.configuration import config
from utils.run import robot_job

# mail = Mail()

scheduler = APScheduler()
login_manager = LoginManager()
login_manager.login_view = 'auto.login'

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    login_manager.init_app(app)

    # mail.init_app(app)

    # app.config["MAIL"] = mail

    scheduler.init_app(app)
    #scheduler._load_config()
    scheduler.start()

    # for blueprints
    from .blueprints import routes as routes_blueprint
    app.register_blueprint(routes_blueprint)

    from .api import api_bp as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    if app.config['SSL_REDIRECT']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    return app
