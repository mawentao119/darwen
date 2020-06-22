# -*- coding: utf-8 -*-

__author__ = "苦叶子"

"""

"""
import os
from flask import Blueprint, render_template, session, redirect, url_for, current_app, send_file, request
from utils.file import get_splitext, exists_path, get_projectnamefromkey
from utils.parsing import prepare_editorjs
from utils.do_report import get_distinct_suites,rpt_caseratio,rpt_runprogress,rpt_moduleprogress, rpt_moduleinfo
from utils.mylogger import getlogger

log = getlogger("blueprints")
routes = Blueprint('routes', __name__)


@routes.before_request
def before_routes():
    if 'username' in session:
        pass
    else:
        pass
        # return redirect(url_for('routes.index'))


@routes.route('/')
def index():
    return render_template('login.html')


@routes.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        return render_template('login.html')


@routes.route('/gen_report', methods=['GET'])
def get_report():
    if 'username' in session:
        return render_template('gen_report.html', username=session['username'])
    else:
        return render_template('login.html')

@routes.route("/editor/<project>/<suite>/<case>")
def editor_1(project, suite, case):
    t = get_splitext(case)
    print("********* Case:{}".format(case))
    default = "default.html"
    if t[1] in (".txt", ".robot", ".py", ".js", ".yaml", ".conf", ".ini", ".sh"):
        default = "editor_1.html"
    elif t[1] in (".bmp", ".jpg", ".jpeg", ".png", ".gif"):
        default = "view_img.html"

    return render_template(default, project=project, suite=suite, case=case)

@routes.route("/editor/<key>")
def editor(key):
    rpkey = key.replace("--", "/")
    t = get_splitext(rpkey)
    default = "default.html"
    if t[1] in (".txt", ".robot", ".resource", ".py", ".js", ".yaml", ".conf", ".ini", ".sh"):
        default = "editor.html"
    elif t[1] in (".bmp", ".jpg", ".jpeg", ".png", ".gif"):
        default = "view_img.html"

    mode = 'robot'
    if t[1] == ".yaml":
        mode = 'yaml'
    if t[1] == '.py':
        mode = 'python'

    prepare_editorjs(rpkey)

    return render_template(default, key=rpkey, mode=mode)


@routes.route("/task_list/<name>")
def task_list(name):
    if name.find('--') == -1:
        return render_template('task_list.html', project=name)
    else:
        key = name.replace("--", "/")
        project = get_projectnamefromkey(key)
        return render_template('task_list.html', project=name)

@routes.route("/scheduler/")
def scheduler():
    return render_template('scheduler.html')

@routes.route("/test_env/")
def test_env():
    return render_template('test_env.html')

@routes.route("/user/")
def user():
    return render_template('user.html')


@routes.route("/view_report/<project>/<task>")
def view_report(project, task):
    app = current_app._get_current_object()
    job_path = 'default.html'
    if task.endswith('_log'):
        num = task.split('_')[0]
        job_path = app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/log.html" % (session['username'], project, num)
    if task.endswith('_report'):
        num = task.split('_')[0]
        job_path = app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/report.html" % (session['username'], project, num)

    return send_file(job_path)


@routes.route("/q_view_report/<username>/<project>/<task>")
def q_view_report(username, project, task):
    app = current_app._get_current_object()

    job_path = app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/log.html" % (username, project, task)

    return send_file(job_path)


@routes.route("/view_img")
def view_img():
    args = request.args.to_dict()
    app = current_app._get_current_object()
    img_path = app.config["AUTO_HOME"] + "/workspace/%s" % session['username'] + args["path"]
    img_path.replace("\\", "/")
    if exists_path(img_path):
        return send_file(img_path)

    return False

@routes.route("/casereport/<key>")
def casereport(key):
    """
    用例统计页面
    Test Case Report Page
    :param key:
    :return:
    """
    rpkey = key.replace("--", "/")
    app = current_app._get_current_object()
    (total,hand,auto) = rpt_caseratio(rpkey)
    ratio = format((auto/total)*100 , '.2f') if total > 0 else '0'
    suites = get_distinct_suites(rpkey)
    autoratio = {'total':total, 'suites': suites ,'hand': hand, 'auto': auto, 'ratio': ratio}

    modulesinfo = rpt_moduleinfo(rpkey)
    return render_template("case_report.html", autoratio=autoratio,modulesinfo=modulesinfo, dir=rpkey)

@routes.route("/caselist/<key>")
def caselist(key):
    """
    用例列表页面
    Test Case List Page
    :param key:
    :return:
    """
    rpkey = key.replace("--", "/")
    app = current_app._get_current_object()

    return render_template("case_list.html", dir=rpkey)

@routes.route("/excutereport/<key>")
def excutereport(key):
    """
    执行报告页面
    Test Execution Report Page
    :param key:
    :return:
    """

    '''
    runprogress = {"total":[total,totalpass,totalfail,total-(totalpass + totalfail)],
                   "hand": [hand, handpass, handfail, hand -(handpass +  handfail)],
                   "auto": [auto, autopass, autofail, auto -(autopass +  autofail)]}
    moduleinfo = {'modules':modules, 'passed':passed, 'failed':failed, 'unknown':unknown}
    '''
    rpkey = key.replace("--", "/")
    runprogress = rpt_runprogress(rpkey)

    totalratio = format(((runprogress['total'][1]+runprogress['total'][2])/runprogress['total'][0])*100, '.2f') if runprogress['total'][0]>0 else '0'
    handratio  = format(((runprogress['hand'][1]+runprogress['hand'][2])/runprogress['hand'][0])*100, '.2f') if runprogress['hand'][0]>0 else '0'
    autoratio  = format(((runprogress['auto'][1]+runprogress['auto'][2])/runprogress['auto'][0])*100, '.2f') if runprogress['auto'][0]>0 else '0'

    grossinfo = {'totalratio':totalratio, 'handratio':handratio,'autoratio':autoratio,
                 'total':runprogress['total'],
                 'hand': runprogress['hand'],
                 'auto': runprogress['auto']}

    moduleinfo = rpt_moduleprogress(rpkey)
    return render_template("excute_report.html", grossinfo=grossinfo, moduleinfo=moduleinfo, dir=rpkey)

@routes.route("/welcome")
def welcome():
    return render_template("welcome.html")
