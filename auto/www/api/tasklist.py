# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""

"""

from flask import current_app, session, url_for
from flask_restful import Resource, reqparse
import json
import os
import codecs
import threading
from dateutil import tz
from datetime import datetime

from robot.api import ExecutionResult

from utils.file import exists_path, remove_dir
from utils.run import remove_robot, robot_job, robot_run
from ..app import scheduler
from utils.mylogger import getlogger

class TaskList(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('task_name', type=str)
        self.parser.add_argument('schedule_type', type=str)
        self.parser.add_argument('year', type=str)
        self.parser.add_argument('mon', type=str)
        self.parser.add_argument('day', type=str)
        self.parser.add_argument('hour', type=str)
        self.parser.add_argument('min', type=str)
        self.parser.add_argument('sec', type=str)
        self.parser.add_argument('week', type=str)
        self.parser.add_argument('day_of_week', type=str)
        self.parser.add_argument('start_date', type=str)
        self.parser.add_argument('end_date', type=str)
        self.log = getlogger("TaskList")
        self.app = current_app._get_current_object()

    def get(self):
        args = self.parser.parse_args()
        project = args["name"]

        return get_task_list(self.app, session['username'], project)

    def post(self):
        args = self.parser.parse_args()
        job_id = "%s_%s" % (session["username"], args["name"])
        if args["method"] == "get_projecttask":
            return get_projecttask(self.app)
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

        elif args["method"] == "add_schedulejob":
            user = session["username"]

            self.log.info("add_schedulejob, args:{}".format(args))

            myargs = {'user': user,
                      'method': args['method'],
                      'task_name': args['task_name'],
                      'schedule_type': args['schedule_type'],
                      'year': args['year'],
                      'mon': args['mon'],
                      'day': args['day'],
                      'hour': args['hour'],
                      'min': args['min'],
                      'sec': args['sec'],
                      'week': args['week'],
                      'day_of_week': args['day_of_week'],
                      'start_date': args['start_date'],
                      'end_date': args['end_date']}

            return add_schedulejob(self.app, self.log, myargs)

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
                        driver = get_taskdriver(job_path + "/%s/cmd.txt" % i)
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
                            "driver": driver,
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
                            "driver":driver,
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


def get_projecttask(app):
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

def get_projecttaskdir(app, project):
    #TODO : 适配多用户公用project
    projecttaskdir = app.config["AUTO_HOME"] + "/jobs/" + session["username"] + "/%s" % (project)
    return projecttaskdir

def get_taskdriver(cmdfile):
    if not os.path.exists(cmdfile):
        return 'Unknown'
    else:
        with open(cmdfile, 'r') as f:
            ln = f.readline().strip()
            splits = ln.split('|')
            return splits[0] if len(splits) > 1 else 'Unknown'

def add_schedulejob(app, log, args):

    user = args['user']
    schedule_type = args["schedule_type"]

    if schedule_type not in ["interval","cron","date"] :
        return {"status": "fail", "msg": "暂不支持这种调度:{}".format(schedule_type)}

    splits = args["task_name"].split('_#') #  Project_#03Variables_#36
    if len(splits) != 3:
        return {"status": "fail", "msg": "任务名称的格式错误:{}".format(args["task_name"])}

    (project, task_name, task_no) = splits
    job_id = "%s_%s" % (user, task_name)

    cmdfile = app.config["AUTO_HOME"] + "/jobs/{}/{}/{}/cmd.txt".format(user, project, task_no)
    if not os.path.isfile(cmdfile):
        return {"status": "fail", "msg": "无法找到命令文件:{}".format(cmdfile)}

    cmdline = ''
    with open(cmdfile, 'r') as f:
        cmdline = f.readline()

    cmdline = cmdline.strip()
    if cmdline == '':
        return {"status": "fail", "msg": "命令文件为空."}

    log.info("rerun_task CMD:" + cmdline)

    splits = cmdline.split('|')

    cases = splits[-1]  # driver|robot|args|output=xxx|cases
    jobargs = splits[2]
    case_name = os.path.basename(cases)

    lock = threading.Lock()
    lock.acquire()
    job = scheduler.get_job(job_id)
    if job:
        lock.release()
        return {"status": "fail", "msg": "Error: 该调度任务已存在！"}
    else:
        year = int(args["year"]) if args["year"] !='' else 0
        mon = int(args["mon"]) if args["mon"] !='' else 0
        day = int(args["day"]) if args["day"] !='' else 0
        hour = int(args["hour"]) if args["hour"] !='' else 0
        min = int(args["min"]) if args["min"] !='' else 0
        sec = int(args["sec"]) if args["sec"] !='' else 0

        if schedule_type == 'date':
            log.info("Add date schedulejob:(year,mon,day,hour,min,sec):{},{},{},{},{},{}".format(year,mon,day,hour,min,sec))
            try:
                scheduler.add_job(id=job_id,
                                  name=user,
                                  func=robot_run,
                                  args=(app, cases, jobargs, user, schedule_type),
                                  trigger=schedule_type,
                                  run_date=datetime(year,mon,day,hour,min,sec)
                                  )
            except Exception as e:
                lock.release()
                return {"status": "fail", "msg": "Error: 调度任务添加失败:{}".format(e)}

        elif schedule_type == 'interval':
            weeks = int(args["week"]) if args["week"] else 0
            start_date = args["start_date"]
            end_date = args["end_date"]

            log.info("Add interval schedulejob:weeks,days,hours,minutes,seconds,start_date,end_date:{},{},{},{},{},{},{}".format(weeks,day,hour,min,sec,start_date,end_date))

            try:
                if start_date and end_date:
                    scheduler.add_job(id=job_id,
                                      name=user,
                                      func=robot_run,
                                      args=(app, cases, jobargs, user, schedule_type),
                                      trigger=schedule_type,
                                      weeks = weeks,
                                      days = day,
                                      hours = hour,
                                      minutes = min,
                                      seconds = sec,
                                      start_date = start_date,
                                      end_date = end_date
                                      )
                else:
                    scheduler.add_job(id=job_id,
                                      name=user,
                                      func=robot_run,
                                      args=(app, cases, jobargs, user, schedule_type),
                                      trigger=schedule_type,
                                      weeks=weeks,
                                      days=day,
                                      hours=hour,
                                      minutes=min,
                                      seconds=sec
                                      )
            except Exception as e:
                lock.release()
                return {"status": "fail", "msg": "Error: 调度任务添加失败:{}".format(e)}

        else:   #cron
            year = int(args["year"]) if args["year"] != '' else "*"
            mon = int(args["mon"]) if args["mon"] != '' else "*"
            day = int(args["day"]) if args["day"] != '' else "*"
            hour = int(args["hour"]) if args["hour"] != '' else "*"
            min = int(args["min"]) if args["min"] != '' else "*"
            sec = int(args["sec"]) if args["sec"] != '' else "*"
            week = int(args["week"]) if args["week"] != '' else "*"
            day_of_week = int(args["day_of_week"]) if args["day_of_week"] != '' else "*"

            start_date = args["start_date"]
            end_date = args["end_date"]

            log.info("Add cron schedulejob:year:{},month:{},day:{},week:{},dayofweek:{},hour:{},minute:{},second:{},start_date:{},end_date:{}".format(year,mon,day,week,day_of_week,hour,min,sec,start_date,end_date))

            try:
                if start_date and end_date:
                    scheduler.add_job(id=job_id,
                                      name=user,
                                      func=robot_run,
                                      args=(app, cases, jobargs, user, schedule_type),
                                      trigger=schedule_type,
                                      year = year,
                                      month = mon,
                                      day = day,
                                      week=week,
                                      day_of_week = day_of_week,
                                      hour = hour,
                                      minute = min,
                                      second = sec,
                                      start_date = start_date,
                                      end_date = end_date
                                      )
                else:
                    scheduler.add_job(id=job_id,
                                      name=user,
                                      func=robot_run,
                                      args=(app, cases, jobargs, user, schedule_type),
                                      trigger=schedule_type,
                                      year=year,
                                      month=mon,
                                      day=day,
                                      week=week,
                                      day_of_week=day_of_week,
                                      hour=hour,
                                      minute=min,
                                      second=sec
                                      )
            except Exception as e:
                lock.release()
                return {"status": "fail", "msg": "Error: 调度任务添加失败:{}".format(e)}

    lock.release()
    return {"status": "success", "msg": "新增调度任务成功:{}".format(job_id)}