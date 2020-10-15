# -*- coding: utf-8 -*-

__author__ = "苦叶子"

"""

"""
import os
import markdown
from flask import Blueprint, render_template, session, redirect, url_for, current_app, send_file, request
from utils.file import get_splitext, exists_path, get_projectnamefromkey, read_file
from utils.parsing import prepare_editorjs
from utils.do_report import get_distinct_suites, rpt_caseratio, rpt_runprogress, rpt_moduleprogress, rpt_moduleinfo
from utils.mylogger import getlogger

log = getlogger("blueprints")
routes = Blueprint('routes', __name__)


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


@routes.route("/editor/<key>")
def editor(key):

    rpkey = key.replace("--", "/")
    t = get_splitext(rpkey)

    log.info("*RPKEY:"+rpkey)
    log.info("*KEY:"+key)
    log.info("*File ext:"+t[1])

    default = "default.html"

    if t[1] in (".html", ".htm"):
        if os.path.exists(rpkey):
            default = rpkey
        return send_file(default)

    if t[1] in (".txt", ".robot", ".resource", ".py", ".js", ".yaml", ".conf", ".ini", ".sh", ".md"):
        default = "editor.html"

        if t[1] == ".yaml":
            mode = 'yaml'
        elif t[1] == '.py':
            mode = 'python'
        elif t[1] == '.md':
            mode = 'textile'
        else:
            mode = 'python'

        return render_template(default, key=rpkey, mode=mode)

    if t[1] in (".bmp", ".jpg", ".jpeg", ".png", ".gif"):
        return send_file(rpkey)

    if t[1] in (".tmd"):
        res = read_file(rpkey)
        return render_template("test_design.html", key=rpkey, value=res["data"])
    return render_template(default)


@routes.route("/task_list/<name>")
def task_list(name):
    if name.find('--') == -1:
        return render_template('task_list.html', project=name)
    else:
        key = name.replace("--", "/")
        project = get_projectnamefromkey(key)
        return render_template('task_list.html', project=name)


@routes.route("/project_task/")
def scheduler():
    return render_template('project_task.html')


@routes.route("/test_design/")
def test_design():
    return render_template('test_design.html')


@routes.route("/test_env/")
def test_env():
    app = current_app._get_current_object()
    test_project = app.config['DB'].get_setting('test_project')
    test_projectversion = app.config['DB'].get_setting('test_projectversion')
    auto_conffile = os.path.expandvars(
        app.config['DB'].get_setting('test_env_conf'))
    if not os.path.exists(auto_conffile):
        with open(app.config['AUTO_TEMP']+'/env_temp.conf', 'w') as f:
            f.write("无法找到配置文件:\n")
            f.write("{}\n".format(auto_conffile))
            f.write("请在'系统配置'中配置'test_env_conf'项.\n")
        auto_conffile = app.config['AUTO_TEMP']+'/env_temp.conf'
    return render_template('test_env.html', test_project=test_project, test_projectversion=test_projectversion, key=auto_conffile)


@routes.route("/schedule_mng/")
def schedule_mng():
    return render_template('schedule_mng.html')


@routes.route("/monitor/")
def monitor():
    return render_template('monitor.html')


@routes.route("/inject/")
def inject():
    return render_template('inject.html')


@routes.route("/performance/")
def performance():
    return render_template('inject.html')


@routes.route("/turning/")
def turning():
    return render_template('inject.html')


@routes.route("/tools/")
def tools():
    return render_template('tools.html')


@routes.route("/test_analyse/")
def test_analyse():
    return render_template('test_analyse.html')


@routes.route("/user/")
def user():
    return render_template('user.html')


@routes.route("/settings/")
def settings():
    return render_template('settings.html')


@routes.route("/project_mng/")
def project_mng():
    return render_template('project_mng.html')


@routes.route("/view_report/<project>/<task>")
def view_report(project, task):
    app = current_app._get_current_object()
    job_path = 'default.html'
    if task.endswith('_log'):
        num = task.split('_')[0]
        job_path = app.config["AUTO_HOME"] + \
            "/jobs/%s/%s/%s/log.html" % (session['username'], project, num)
    if task.endswith('_report'):
        num = task.split('_')[0]
        job_path = app.config["AUTO_HOME"] + \
            "/jobs/%s/%s/%s/report.html" % (session['username'], project, num)

    return send_file(job_path)


@routes.route("/q_view_report/<username>/<project>/<task>")
def q_view_report(username, project, task):
    app = current_app._get_current_object()

    job_path = app.config["AUTO_HOME"] + \
        "/jobs/%s/%s/%s/log.html" % (username, project, task)

    return send_file(job_path)


@routes.route("/view_img")
def view_img():
    args = request.args.to_dict()
    app = current_app._get_current_object()
    img_path = app.config["AUTO_HOME"] + \
        "/workspace/%s" % session['username'] + args["path"]
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

    (total, hand, auto) = rpt_caseratio(rpkey)
    ratio = format((auto/total)*100, '.2f') if total > 0 else '0'
    suites = get_distinct_suites(rpkey)
    autoratio = {'total': total, 'suites': suites,
                 'hand': hand, 'auto': auto, 'ratio': ratio}

    modulesinfo = rpt_moduleinfo(rpkey)
    return render_template("case_report.html", autoratio=autoratio, modulesinfo=modulesinfo, dir=rpkey)


@routes.route("/caselist/<key>")
def caselist(key):
    """
    用例列表页面
    Test Case List Page
    :param key:
    :return:
    """
    rpkey = key.replace("--", "/")

    return render_template("case_list.html", dir=rpkey)


@routes.route("/compare/<key>")
def compare(key):
    """
    用例历史结果对比页面
    :param key:
    :return:
    """
    rpkey = key.replace("--", "/")

    return render_template("compare_caseresult.html", dir=rpkey)


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

    totalratio = format(((runprogress['total'][1]+runprogress['total'][2]) /
                         runprogress['total'][0])*100, '.2f') if runprogress['total'][0] > 0 else '0'
    handratio = format(((runprogress['hand'][1]+runprogress['hand'][2]) /
                        runprogress['hand'][0])*100, '.2f') if runprogress['hand'][0] > 0 else '0'
    autoratio = format(((runprogress['auto'][1]+runprogress['auto'][2]) /
                        runprogress['auto'][0])*100, '.2f') if runprogress['auto'][0] > 0 else '0'

    grossinfo = {'totalratio': totalratio, 'handratio': handratio, 'autoratio': autoratio,
                 'total': runprogress['total'],
                 'hand': runprogress['hand'],
                 'auto': runprogress['auto']}

    moduleinfo = rpt_moduleprogress(rpkey)
    return render_template("excute_report.html", grossinfo=grossinfo, moduleinfo=moduleinfo, dir=rpkey)


@routes.route("/welcome")
def welcome():
    return render_template("welcome.html")


@routes.route("/project_readme")
def project_readme():
    app = current_app._get_current_object()

    try:
        readmefile = app.config['DB'].get_setting('project_readme')
        main_project = app.config['DB'].get_user_main_project(
            session['username'])
        project_path = app.config['DB'].get_project_path(main_project)
        project_ownreadme = os.path.join(project_path, 'ReadMe.md')
        project_darwenreadme = os.path.join(project_path, 'darwen/ReadMe.md')
    except Exception as e:
        log.error("{}".format(e))

    if os.path.exists(readmefile):
        p_file = readmefile
    elif os.path.exists(project_ownreadme):
        p_file = project_ownreadme
    else:
        p_file = project_darwenreadme

    body = "<p>说明文件："+p_file+"</p> \n"
    if os.path.exists(p_file):
        with open(p_file, 'r') as f:
            for l in f:
                body += markdown.markdown(l) + '\n'
    else:
        log.error("找不到ReadMe文件:{}".format(p_file))
        return render_template("welcome.html")
    return render_template("project_readme.html", body=body)
