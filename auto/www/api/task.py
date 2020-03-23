# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""

"""

from flask import current_app, session, url_for
from flask_restful import Resource, reqparse
from utils.file import get_projectdirfromkey
import json
import os
import time
import codecs
import threading
import multiprocessing
from dateutil import tz

from robot.api import ExecutionResult

from utils.file import exists_path, remove_dir, get_splitext, get_projectnamefromkey
from utils.run import robot_run, is_run, is_full, remove_robot, stop_robot, robot_job, robot_debugrun, py_debugrun,bzt_debugrun
from ..app import scheduler
from utils.mylogger import getlogger

class Task(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('category', type=str)
        self.parser.add_argument('project', type=str)
        self.parser.add_argument('suite', type=str)
        self.parser.add_argument('case', type=str)
        self.parser.add_argument('tags', type=str)
        self.parser.add_argument('conffile', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('task_no', type=str)
        self.log = getlogger("Task")
        self.app = current_app._get_current_object()

    def post(self):
        args = self.parser.parse_args()

        if args["method"] == "run" or args["method"] == "editor_run":
            return self.runall(args)
        elif args["method"] == "debug_run":
            return self.debug_run(args)
        elif args["method"] == "runpass":
            return self.runpassfail(args,True)
        elif args["method"] == "runfail":
            return self.runpassfail(args,False)
        elif args["method"] == "runtags":
            return self.runtags(args)
        elif args["method"] == "runfile":
            return self.runfile(args)

        elif args["method"] == "rerun":
            return self.rerun_task(args)
        elif args["method"] == "rerunfail":
            return self.rerunfail_task(args)

        elif args["method"] == "stop":
            return stop_robot(self.app, args)

        elif args["method"] == "delete":
            delete_task_record(self.app, args)
            return {"status": "success", "msg": "Record is deleted."}
        else:
            return {"status": "fail", "msg": "Parameter method Error:{}".format(args['method'])}

    def runall(self, args):
        cases = args['key']
        if not os.path.isdir(cases):
            fext = get_splitext(cases)[1]
            if not fext in (".robot"):
                return {"status": "fail", "msg": "Fail：Do not support Run this type of file now :" + fext}

        case_name = os.path.basename(cases)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, cases))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "Please wait for the former task finished."}

        return {"status": "success", "msg": "Start run:" + case_name}

    def runpassfail(self, args, passed=True):

        suites = []
        retry = 0
        if passed:
            sql = ''' SELECT distinct(info_key) FROM testcase WHERE info_key like '{}%' and run_status='PASS' ;
                  '''.format(args['key'])
        else:
            sql = ''' SELECT distinct(info_key) FROM testcase WHERE info_key like '{}%' and run_status='FAIL' ;
                  '''.format(args['key'])

        res = self.app.config['DB'].runsql(sql)
        for r in res:
            (s,) = r
            suites.append(s)

        self.log.info("runpassfail: total suites is :{}".format(len(suites)))

        for key in suites:
            case_name = os.path.basename(key)
            if is_full(self.app):
                return {"status": "fail", "msg": "Exceed Max processes:{},Try later.".format(self.app.config['MAX_PROCS'])}
            if not is_run(self.app, case_name):
                p = multiprocessing.Process(target=robot_run,
                                            args=(self.app, key))
                p.start()
                self.app.config["AUTO_ROBOT"].append(
                    {"name": "%s" % case_name, "process": p})

                time.sleep(0.2)

            else:
                retry += 1
        if retry > 0 :
            return {"status": "success", "msg": "Start Run:{} cases conflict，Need retry.".format(retry)}
        else:
            return {"status": "success", "msg": "Start Run:" + args['key']}

    def runtags(self, args):
        arg_tags = args['tags']
        key = args['key']

        tags = arg_tags.replace('，',',').split(',')

        includ = []
        exclud = []

        for t in tags:
            if t.strip().startswith('-'):
                exclud.append(t.strip().replace('-',''))
            else:
                includ.append(t.strip().replace('+',''))

        includ_arg = ' -i '+ ' -i '.join(includ) if len(includ) > 0 else ''
        exclud_arg = ' -e '+ ' -e '.join(exclud) if len(exclud) > 0 else ''

        case_name = os.path.basename(key)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, key, includ_arg + exclud_arg))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "Please wait for the former task finished"}

        return {"status": "success", "msg": "Start Run:" + case_name}

    def runfile(self, args):
        conffile = args['conffile'].strip()
        key = args['key']

        projectdir = get_projectdirfromkey(key)
        conffile = conffile.replace('${ROBOT_DIR}',projectdir)
        conffile = conffile.replace('${PROJECT_DIR}', projectdir)
        conffile = conffile.replace('%{ROBOT_DIR}', projectdir)
        conffile = conffile.replace('%{PROJECT_DIR}', projectdir)

        if not conffile.strip().startswith('/'):
            conffile = os.path.join( key, conffile )

        if not os.path.isfile(conffile):
            return {"status": "fail", "msg": "Cannot find config file:{}".format(conffile)}

        case_name = os.path.basename(key)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, key, ' -A '+conffile))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "Please wait for the former task finished"}

        return {"status": "success", "msg": "Start Run:{}".format(conffile)}

    def debug_run(self, args):
        fext = os.path.splitext(args['key'])[1]
        if fext == ".robot":
            result = robot_debugrun(self.app, args['key'])
            return {"data": decorate_robotout(result)}
        if fext == ".py":
            result = py_debugrun(self.app, args['key'])
            return {"data": decorate_pyout(result)}
        if fext == ".yaml":
            result = bzt_debugrun(self.app, args['key'])
            return {"data": decorate_pyout(result)}
        return {"data": "Do not support DegugRun <{}> this type of file.".format(fext)}

    def rerun_task(self, args):
        project = args['project']
        task_no = args['task_no']
        cmdfile = self.app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/cmd.txt" % (session['username'], project,str(task_no))
        if not os.path.isfile(cmdfile):
            return {"status": "fail", "msg": "Cannot find command file，file may be deleted:{}".format(cmdfile)}

        cmdline = ''
        with open(cmdfile,'r') as f:
            cmdline = f.readline()

        cmdline = cmdline.strip()
        if cmdline == '':
            return {"status": "fail", "msg": "Command file content is Null."}

        self.log.info("rerun_task CMD:"+cmdline)

        cases = cmdline.split('|')[-1]    # robot|args|output=xxx|cases
        args = cmdline.split('|')[1]
        case_name = os.path.basename(cases)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, cases, args))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "Please wait for the former task finished."}

        return {"status": "success", "msg": "Start Run {}:{}".format(project,task_no)}

    def rerunfail_task(self, args):
        """
        重新执行失败suite ：-S --rerunfailedsuites output ，而不是 -R --rerunfailed output tests
        Rerun failed suite: See robot user guide : -S  not -R
        :param args:
        :return:
        """
        project = args['project']
        task_no = args['task_no']
        cmdfile = self.app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/cmd.txt" % (session['username'], project,str(task_no))
        outfile = self.app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/output.xml" % (session['username'], project,str(task_no))
        if not os.path.isfile(cmdfile):
            return {"status": "fail", "msg": "Cannot find command file，file may be deleted:{}".format(cmdfile)}
        if not os.path.isfile(outfile):
            return {"status": "fail", "msg": "Cannot find output file，file may be deleted:{}".format(outfile)}

        cmdline = ''
        with open(cmdfile,'r') as f:
            cmdline = f.readline()

        cmdline = cmdline.strip()
        if cmdline == '':
            return {"status": "fail", "msg": "Command file content is Null."}

        cases = cmdline.split('|')[-1]    # robot|args|output=xxx|cases
        args = cmdline.split('|')[1] + ' -S ' + outfile
        case_name = os.path.basename(cases)

        self.log.info("rerunfail_task args:" + args)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, cases, args))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "Please wait for the former task finished"}

        return {"status": "success", "msg": "Rerun failed suite{}:{}".format(project,task_no)}

class TaskList(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('cron', type=str)
        self.log = getlogger("TaskList")
        self.app = current_app._get_current_object()

    def get(self):
        args = self.parser.parse_args()
        project = args["name"]

        return get_task_list(self.app, session['username'], project)

    def post(self):
        args = self.parser.parse_args()
        job_id = "%s_%s" % (session["username"], args["name"])
        if args["method"] == "query":
            return get_all_task(self.app)
        elif args["method"] == "start":
            result = {"status": "success", "msg": "Scheduler start success."}
            lock = threading.Lock()
            lock.acquire()
            job = scheduler.get_job(job_id)
            if job:
                scheduler.remove_job(job_id)
            cron = args["cron"].replace("\n", "").strip().split(" ")
            if args["cron"] != "* * * * * *" and len(cron) == 6:
                scheduler.add_job(id=job_id,
                                  name=args["name"],
                                  func=robot_job,
                                  args=(self.app, args["name"], session["username"]),
                                  trigger="cron",
                                  second=cron[0],
                                  minute=cron[1],
                                  hour=cron[2],
                                  day=cron[3],
                                  month=cron[4],
                                  day_of_week=cron[5])
            else:
                result["msg"] = "cron default * * * * * *, <br><br>Cannot start scheduler，Please modify cron setting."
            lock.release()
            return result

        elif args["method"] == "stop":
            lock = threading.Lock()
            lock.acquire()
            job = scheduler.get_job(job_id)
            if job:
                scheduler.remove_job(id=job_id)
            lock.release()
            return {"status": "success", "msg": "Stop task OK"}
        elif args["method"] == "edit":

            result = edit_cron(self.app, args["name"], args["cron"])
            if result:
                # job_id = "%s_%s" % (session["username"], args["name"])
                lock = threading.Lock()
                lock.acquire()
                job = scheduler.get_job(job_id)
                if job:
                    scheduler.remove_job(job_id)

                cron = args["cron"].replace("\n", "").strip().split(" ")
                if args["cron"] != "* * * * * *" and len(cron) == 6:
                    scheduler.add_job(id=job_id,
                                      name=args["name"],
                                      func=robot_job,
                                      args=(self.app, args["name"], session["username"]),
                                      trigger="cron",
                                      second=cron[0],
                                      minute=cron[1],
                                      hour=cron[2],
                                      day=cron[3],
                                      month=cron[4],
                                      day_of_week=cron[5])
                lock.release()

            return {"status": "success", "msg": "Edit cron info OK."}


def get_task_list(app, username, project):
    job_path = app.config["AUTO_HOME"] + "/jobs/%s/%s" % (username, project)
    next_build = 0
    task = []
    if exists_path(job_path):
        next_build = get_next_build_number(job_path)
        if next_build != 0:
            # 遍历所有任务结果
            # 判断最近一个任务状态
            icons = {
                "running": url_for('static', filename='img/running.gif'),
                "success": url_for('static', filename='img/success.png'),
                "fail": url_for('static', filename='img/fail.png'),
                "exception": url_for('static', filename='img/exception.png')}

            #if exists_path(job_path + "/%s" % (next_build - 1)):
            running = False
            lock = threading.Lock()
            lock.acquire()
            remove_robot(app)
            for p in app.config["AUTO_ROBOT"]:
                if p["name"] == project:
                    running = True
                    break
            lock.release()
            if running:
                task.append(
                   {
                       "status": icons["running"],
                       "name": "%s_#%s" % (project, next_build-1),
                       "success": "",
                       "fail": ""
                   }
                )
            last = 1
            if running:
                last = 2
            for i in range(next_build-last, -1, -1):
                if exists_path(job_path + "/%s" % i):
                    try:
                        suite = ExecutionResult(job_path + "/%s/output.xml" % i).suite
                        stat = suite.statistics.critical
                        name = suite.name
                        if stat.failed != 0:
                            status = icons["fail"]
                        else:
                            status = icons['success']
                        task.append({
                            "task_no": i,
                            "status": status,
                            "name": "<a href='/view_report/%s/%s_log' target='_blank'>%s_#%s_log</a>" % (project, i, name, i),
                            "success": stat.passed,
                            "fail": stat.failed,
                            "starttime": suite.starttime,
                            "endtime": suite.endtime,
                            "elapsedtime": suite.elapsedtime,
                            "note": "<a href='/view_report/%s/%s_report' target='_blank'>%s_#%s_report</a>" % (project, i, name, i)
                        })
                    except:
                        status = icons["exception"]
                        if i == next_build-last:
                            status = icons["running"]
                        task.append({
                            "task_no": i,
                            "status": status,
                            "name": "%s_#%s" % (project, i),
                            "success": "-",
                            "fail": "-",
                            "starttime": "-",
                            "endtime": "-",
                            "elapsedtime": "-",
                            "note": "Abnormal"
                        })

    return {"total": next_build-1, "rows": task}


def get_last_task(app, username, project):
    icons = {
        "running": url_for('static', filename='img/running.gif'),
        "success": url_for('static', filename='img/success.png'),
        "fail": url_for('static', filename='img/fail.png'),
        "exception": url_for('static', filename='img/exception.png')}
    job_path = app.config["AUTO_HOME"] + "/jobs/%s/%s" % (username, project)
    status = icons["running"]
    if exists_path(job_path):
        next_build = get_next_build_number(job_path)
        last_job = next_build-1
        if exists_path(job_path + "/%s" % last_job):
            try:
                suite = ExecutionResult(job_path + "/%s/output.xml" % last_job).suite
                stat = suite.statistics.critical
                if stat.failed != 0:
                    status = icons["fail"]
                else:
                    status = icons['success']
            except:
                status = icons["running"]
        else:
            status = icons["exception"]
    else:
        status = icons['success']

    return status


def get_all_task(app):
    projects = app.config['DB'].get_allproject(session["username"])
    task_list = {"total": len(projects), "rows": []}
    for op in projects:
        p = op.split(':')[1]     # projects = ["owner:project","o:p"]
        task = {
            # "status": status,
            "name": p,
            # "last_success": get_last_pass(job_path + "/lastPassed"),
            # "last_fail": get_last_fail(job_path + "/lastFail"),
            "enable": "Enalble",
            "next_time": get_next_time(app, p),
            "cron": "* * * * * *",
            "status": get_last_task(app, session["username"], p)
        }

        task_list["rows"].append(task)
    return task_list

def get_last_pass(job_path):
    passed = "无"
    passed_path = job_path + "lastPassed"
    if exists_path(passed_path):
        f = codecs.open(passed_path, "r", "utf-8")

        passed = f.read()

        f.close()

    return passed


def get_last_fail(job_path):
    fail = "无"
    fail_path = job_path + "lastFail"
    if exists_path(fail_path):
        f = codecs.open(fail_path, "r", "utf-8")

        fail = f.read()

        f.close()

    return fail


def get_next_build_number(job_path):
    next_build_number = 1
    next_path = job_path + "/nextBuildNumber"
    if exists_path(next_path):
        f = codecs.open(next_path, "r", "utf-8")

        next_build_number = int(f.read())

        f.close()

    return next_build_number


def get_next_time(app, name):
    job = scheduler.get_job("%s_%s" % (session["username"], name))
    if job:
        to_zone = tz.gettz("CST")
        return job.next_run_time.astimezone(to_zone).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return "-"


def edit_cron(app, name, cron):
    user_path = app.config["AUTO_HOME"] + "/users/" + session["username"]
    if os.path.exists(user_path):
        config = json.load(codecs.open(user_path + '/config.json', 'r', 'utf-8'))
        index = 0
        for p in config["data"]:
            if p["name"] == name:
                config["data"][index]["cron"] = cron
                break
            index += 1

        json.dump(config, codecs.open(user_path + '/config.json', 'w', 'utf-8'))

        return True

    return False


def delete_task_record(app, args):
    project = args['project']
    task_no = args['task_no']
    task_path = app.config["AUTO_HOME"] + "/jobs/%s/%s/%s" % (session['username'], project, str(task_no))

    if os.path.exists(task_path):
        remove_dir(task_path)

def get_projecttaskdir(app, project):
    #TODO : 适配多用户公用project
    projecttaskdir = app.config["AUTO_HOME"] + "/jobs/" + session["username"] + "/%s" % (project)
    return projecttaskdir

# For debug out, it is shown as html ,so we can decorate it for more readable.
def decorate_robotout(out):
    o = out.replace(' PASS ', '<b><font color="#00FF00">PASS</font></b>')
    o = o.replace(' ERROR ', '<b><font color="#FF0000">ERROR</font></b>')
    o = o.replace(' FAIL ', '<b><font color="#FF0000">FAIL</font></b>')
    o = o.replace('\n', '<BR>')
    return o
def decorate_pyout(out):
    o = out.replace('TypeError', '<b><font color="#FF0000">TypeError</font></b>')
    o = o.replace('\n', '<BR>')
    return o
