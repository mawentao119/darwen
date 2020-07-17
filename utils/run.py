# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""

"""
import sys
import os
import codecs
from flask import current_app, session, url_for
from flask_mail import Mail, Message
import threading
from subprocess import run as subRun, PIPE ,STDOUT
import multiprocessing
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import json
from utils.file import get_projectnamefromkey

from robot.api import TestSuiteBuilder, ResultWriter, ExecutionResult

from utils.file import exists_path, make_nod, write_file, read_file, mk_dirs, get_projectdirfromkey
from utils.mylogger import getlogger

log = getlogger('Utils.RUN')

def robot_job(app, name, username):
    with app.app_context():
        project = app.config["AUTO_HOME"] + "/workspace/%s/%s" % (username, name)
        output = app.config["AUTO_HOME"] + "/jobs/%s/%s" % (username, name)
        if not is_run(app, project):
            p = multiprocessing.Process(target=robot_run, args=(username, name, project, output))
            p.start()
            app.config["AUTO_ROBOT"].append({"name": project, "process": p})
            print("-+" * 15)
            print(app.config["AUTO_ROBOT"])
            print("-+" * 15)

# This fun is for debug the test case, result is temporliy in /runtime dir
def robot_debugrun(app, cases):

    projectdir = get_projectdirfromkey(cases)

    os.environ["ROBOT_DIR"] = projectdir
    os.environ["PROJECT_DIR"] = projectdir
    out = app.config['AUTO_TEMP']
    if not exists_path(out):
        mk_dirs(out)

    cmd = 'robot --outputdir='+out+' '+cases
    cp = subRun(cmd, shell=True, stdout=PIPE,stderr=STDOUT, text=True, timeout=60)  # timeout: sec

    app.config['DB'].insert_loginfo(session['username'], 'case', 'debug', cases, 'OK')

    return cp.stdout

# This fun is for standard Run, Result will be recorded in Scheduler output.
def robot_run(app, case_key, args=''):

    username = session['username']
    project = get_projectnamefromkey(case_key)
    output = app.config["AUTO_HOME"] + "/jobs/%s/%s" % (session['username'], project)

    if not exists_path(output):
        mk_dirs(output)

    (out, index) = reset_next_build_numb(output)

    projectdir = get_projectdirfromkey(case_key)

    os.environ["ROBOT_DIR"] = projectdir
    os.environ["PROJECT_DIR"] = projectdir

    mk_dirs(out) if not exists_path(out) else None

    cmd = 'robot ' + args + ' --outputdir=' + out + ' ' + case_key

    log.info("Robot_run CMD:{}".format(cmd))
    with open(out + "/cmd.txt", 'w') as f:
        f.write("robot|{}|--outputdir={}|{}\n".format(args,out,case_key))

    cp = subRun(cmd, shell=True, stdout=PIPE, stderr=STDOUT, text=True, timeout=7200)  # timeout: sec 2hrs

    with open(out + "/debug.txt", 'w') as f:
        f.write(cp.stdout)

    app.config['DB'].insert_loginfo(session['username'], 'task', 'run', case_key, 'OK')

    # Report and xUnit files can be generated based on the result object.
    # ResultWriter(result).write_results(report=out + '/report.html', log=out + '/log.html')
    try:

        detail_result = ExecutionResult(out + "/output.xml")

    except Exception as e:
        log.error("Open output.xml Exception:{},\n May robot run fail, console:{}".format(e,cp.stdout))
        return

    # detail_result.save(out + "/output_new.xml")
    reset_last_status(detail_result, output, index)

    # Report and xUnit files can be generated based on the result object.
    ResultWriter(detail_result).write_results(report=out + '/report.html', log=out + '/log.html')

    s = detail_result.suite
    dealwith_source(app, username, s)

    #send_robot_report(username, project, index, detail_result, out)

def robot_runOLD(app, username, project, case_key, output):
    if not exists_path(output):
        mk_dirs(output)

    suite = TestSuiteBuilder().build(case_key)

    (out, index) = reset_next_build_numb(output)

    result = suite.run(output_directory=out,
                       output=out + "/output.xml",
                       debugfile=out + "/debug.txt",
                       loglevel="TRACE")

    try:
        totalcases = result.statistics.total.all.total
        passed = result.statistics.total.all.passed
        failed = result.statistics.total.all.failed
        elapsedtime = result.suite.elapsedtime
        logres = "total:{},pass:{},fail:{},elapsedtime:{}".format(totalcases,passed,failed,elapsedtime)
        app.config['DB'].insert_loginfo(username,'task','run', case_key, logres)
    except Exception as e:
        log.error("robot_run Exception: {}".format(e))

    # Report and xUnit files can be generated based on the result object.
    # ResultWriter(result).write_results(report=out + '/report.html', log=out + '/log.html')
    detail_result = ExecutionResult(out + "/output.xml")

    # detail_result.save(out + "/output_new.xml")
    reset_last_status(detail_result, output, index)

    # Report and xUnit files can be generated based on the result object.
    ResultWriter(detail_result).write_results(report=out + '/report.html', log=out + '/log.html')

    s = detail_result.suite
    dealwith_source(app, username, s)

    send_robot_report(username, project, index, detail_result, out)

def dealwith_source(app, username ,s):

    source = s.source
    if os.path.isfile(s.source):

        app.config['DB'].insert_loginfo(username,'suite','run',s.source,'OK')

        for t in s.tests._items:
            if 'HAND' in t.tags or 'Hand' in t.tags or 'hand' in t.tags:
                log.info("Do not record Hand case status:"+t.name)
                continue
            tags = ",".join(t.tags)
            success = 1 if t.status == 'PASS' else 0
            fail = 1 if t.status == 'FAIL' else 0
            sql = '''UPDATE testcase set ontime=datetime('now','localtime'),
                                       run_elapsedtime='{}',
                                       run_status='{}', 
                                       run_starttime='{}', 
                                       run_endtime='{}', 
                                       info_doc='{}', 
                                       info_tags='{}',
                                       run_user='{}',
                                       rcd_runtimes=rcd_runtimes+1,
                                       rcd_successtimes=rcd_successtimes+{},
                                       rcd_failtimes=rcd_failtimes+{}
                            where info_key='{}' and info_name='{}' ;
            '''.format(t.elapsedtime,t.status,t.starttime,t.endtime,t.doc,tags,username,success,fail,source,t.name)
            res = app.config['DB'].runsql(sql)

            app.config['DB'].insert_loginfo(username, 'case', 'run', source, t.status)

            if res.rowcount < 1 :
                log.warning("Cannot find case:{}:{}, Insert it ...".format(source,t.name))
                sql = '''INSERT INTO testcase(run_elapsedtime,
                                              run_status, 
                                              run_starttime, 
                                              run_endtime, 
                                              info_doc, 
                                              info_tags,
                                              run_user,
                                              rcd_runtimes,
                                              rcd_successtimes,
                                              rcd_failtimes,
                                              info_key,
                                              info_name) 
                         VALUES({},'{}','{}','{}','{}','{}','{}',{},{},{},'{}','{}');
                            '''.format(t.elapsedtime, t.status, t.starttime, t.endtime, t.doc, tags, username, 1,success,fail, source, t.name)
                res = app.config['DB'].runsql(sql)
                if res.rowcount < 1 :
                    log.error("Add New Case:{}:{} Failed".format(source,t.name))

                app.config['DB'].insert_loginfo(username,'case','create',source,'robot_run:'+t.name)
    else:
        for t in s.suites._items:
            dealwith_source(app, username, t)

def reset_next_build_numb(output):
    next_build_number = output + "/nextBuildNumber"
    index = 1
    data = "%d" % (index + 1)
    if not exists_path(next_build_number):
        make_nod(next_build_number)
    else:
        index = int(read_file(next_build_number)["data"])
        data = "%d" % (index + 1)
    write_file(next_build_number, data)

    out = output + "/%d" % index
    if not exists_path(output):
        mk_dirs(output)

    return (out, index)


def reset_last_status(result, output, index):
    stats = result.statistics
    fail = stats.total.critical.failed

    last_fail = output + "/lastFail"
    last_passed = output + "/lastPassed"
    data = "%d" % index

    if fail != 0:
        if not exists_path(last_fail):
            make_nod(last_fail)

        write_file(last_fail, data)
    else:
        if not exists_path(last_passed):
            make_nod(last_passed)
        write_file(last_passed, data)


def remove_robot(app):
    lock = threading.Lock()
    lock.acquire()
    for p in app.config["AUTO_ROBOT"]:
        if not p["process"].is_alive():
            app.config["AUTO_ROBOT"].remove(p)
            break
    lock.release()


def stop_robot(app, args):
    lock = threading.Lock()
    lock.acquire()
    project = args['project']
    task_no = args['task_no']
    cmdfile = app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/cmd.txt" % (session['username'], project, str(task_no))
    if not os.path.isfile(cmdfile):
        return {"status": "fail", "msg": "Cannot find command，Command File maybe deleted:{}".format(cmdfile)}

    cmdline = ''
    with open(cmdfile, 'r') as f:
        cmdline = f.readline()

    cmdline = cmdline.strip()
    if cmdline == '':
        return {"status": "fail", "msg": "Containt of Command file is null. "}

    log.info("stop_task CMD:" + cmdline)

    cases = cmdline.split('|')[-1]  # robot|args|output=xxx|cases
    args = cmdline.split('|')[1]
    name = os.path.basename(cases)

    for p in app.config["AUTO_ROBOT"]:
        if name == p["name"]:
            if p["process"].is_alive():
                p["process"].terminate()
                time.sleep(0.2)
                app.config["AUTO_ROBOT"].remove(p)
                break

    lock.release()

    return {"status": "success", "msg": "Stoped!"}


def is_run(app, name):
    remove_robot(app)
    for p in app.config["AUTO_ROBOT"]:
        if name == p["name"]:
            return True

    return False

def is_full(app):
    remove_robot(app)
    max = app.config['DB'].get_setting('MAX_PROCS')
    if max == 'unknown' or max == '' or (not max):
        max_procs = 20
    else:
        max_procs = int(max)
    return len(app.config["AUTO_ROBOT"]) > max_procs


def send_robot_report(username, name, task_no, result, output):
    app = current_app._get_current_object()
    build_msg = "<font color='green'>Success</font>"
    if result.statistics.total.critical.failed != 0:
        build_msg = "<font color='red'>Failure</font>"

    report_url = url_for("routes.q_view_report",
                         _external=True,
                         username=username,
                         project=name,
                         task=task_no)
    msg = MIMEText("""Hello, %s<hr>
                Projct：%s<hr>
                No.: %s<hr>
                Status: %s<hr>
                Duration: %s毫秒<hr>
                ReportDetail: <a href='%s'>%s</a><hr>
                Log: <br>%s<hr><br><br>
                (This Mail is Auto-sent by System，Please do not response ！)""" %
                   (username,
                    result.statistics.suite.stat.name,
                    task_no,
                    build_msg,
                    result.suite.elapsedtime,
                    report_url, report_url,
                    codecs.open(output + "/debug.txt", "r", "utf-8").read().replace("\n", "<br>")
                    ),
                   "html", "utf-8")

    msg["Subject"] = Header("uniRobot Execution Report", "utf-8")

    try:
        user_path = app.config["AUTO_HOME"] + "/users/%s/config.json" % session["username"]
        user_conf = json.load(codecs.open(user_path, 'r', 'utf-8'))
        for p in user_conf["data"]:
            if p["name"] == name:
                if result.statistics.total.critical.failed != 0:
                    msg["To"] = p["fail_list"]
                else:
                    msg["To"] = p["success_list"]
                break

        conf_path = app.config["AUTO_HOME"] + "/auto.json"
        config = json.load(codecs.open(conf_path, 'r', 'utf-8'))
        msg["From"] = config["smtp"]["username"]
        if config["smtp"]["ssl"]:
            smtp = smtplib.SMTP_SSL()
        else:
            smtp = smtplib.SMTP()

        # 连接至服务器
        smtp.connect(config["smtp"]["server"], int(config["smtp"]["port"]))
        # 登录
        smtp.login(config["smtp"]["username"], config["smtp"]["password"])
        # 发送邮件
        smtp.sendmail(msg["From"], msg["To"].split(","), msg.as_string().encode("utf8"))
        # 断开连接
        smtp.quit()
    except Exception as e:
        print("Send Mail Failed: %s" % e)


class RobotRun(threading.Thread):
    def __init__(self, name, output, lock, executor="auto"):
        threading.Thread.__init__(self)
        self.lock = lock
        self.project = name
        self.output = output
        self.executor = executor
        self.suite = None
        self.result = None

    def run(self):
        #lock = threading.Lock()

        # self.lock.acquire()
        if not exists_path(self.output):
            mk_dirs(self.output)

        self.suite = TestSuiteBuilder().build(self.project)

        (output, index) = self.reset_next_build_numb()

        self.setName(output)

        self.result = self.suite.run(output_directory=output,
                                     output=output + "/output.xml",
                                     debugfile=output + "/debug.txt",
                                     loglevel="TRACE")

        # self.reset_last_status(index)

        # Report and xUnit files can be generated based on the result object.
        # ResultWriter(self.result).write_results(report=output + '/report.html', log=output + '/log.html')

        # self.lock.release()

        # Generating log files requires processing the earlier generated output XML.
        # ResultWriter(self.output + '/output.xml').write_results()

        self.result = ExecutionResult(output + "/output.xml")

        self.reset_last_status(self.result, output, index)

        # Report and xUnit files can be generated based on the result object.
        ResultWriter(self.result).write_results(report=output + '/report.html', log=output + '/log.html')

    def reset_next_build_numb(self):

        next_build_number = self.output + "/nextBuildNumber"
        index = 1
        data = "%d" % (index + 1)
        if not exists_path(next_build_number):
            make_nod(next_build_number)
        else:
            index = int(read_file(next_build_number)["data"])
            data = "%d" % (index + 1)
        write_file(next_build_number, data)

        output = self.output + "/%d" % index
        if not exists_path(output):
            mk_dirs(output)

        return (output, index)

    def reset_last_status(self, index):
        stats = self.result.statistics
        fail = stats.total.critical.failed

        lock = threading.Lock()

        lock.acquire()
        last_fail = self.output + "/lastFail"
        last_passed = self.output + "/lastPassed"
        data = "%d" % index

        if fail != 0:
            if not exists_path(last_fail):
                make_nod(last_fail)

            write_file(last_fail, data)
        else:
            if not exists_path(last_passed):
                make_nod(last_passed)
            write_file(last_passed, data)

        lock.release()

def py_debugrun(app, pyfile):
    projectdir = get_projectdirfromkey(pyfile)

    os.environ["ROBOT_DIR"] = projectdir
    os.environ["PROJECT_DIR"] = projectdir

    cmd = 'python ' + pyfile
    cp = subRun(cmd, shell=True, stdout=PIPE, stderr=STDOUT, text=True, timeout=120)  # timeout: sec

    app.config['DB'].insert_loginfo(session['username'], 'lib', 'debug', pyfile, 'OK')

    return cp.stdout

def bzt_debugrun(app, yamlfile):
    projectdir = get_projectdirfromkey(yamlfile)

    os.environ["ROBOT_DIR"] = projectdir
    os.environ["PROJECT_DIR"] = projectdir

    cmd = 'bzt ' + yamlfile
    cp = subRun(cmd, shell=True, stdout=PIPE, stderr=STDOUT, text=True, timeout=180)  # timeout: sec

    app.config['DB'].insert_loginfo(session['username'], 'case', 'debug', yamlfile, 'OK')

    return cp.stdout