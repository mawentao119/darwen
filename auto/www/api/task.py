# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""

"""

from flask import current_app, session
from flask_restful import Resource, reqparse
from utils.file import get_projectdirfromkey
import os
import time

import multiprocessing

from utils.file import remove_dir, get_splitext
from utils.run import robot_run, is_run, is_full, stop_robot, robot_debugrun, py_debugrun,bzt_debugrun
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
            return {"status": "success", "msg": "删除成功."}
        else:
            return {"status": "fail", "msg": "Parameter 'method' Error:{}".format(args['method'])}

    def runall(self, args):
        cases = args['key']
        if not os.path.isdir(cases):
            fext = get_splitext(cases)[1]
            if not fext in (".robot"):
                return {"status": "fail", "msg": "失败：暂不支持运行此类型的文件 :" + fext}

        case_name = os.path.basename(cases)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, cases, ''))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "失败：超过最大进程数，请等待."}

        return {"status": "success", "msg": "运行:" + case_name}

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
                return {"status": "fail", "msg": "失败：超过最大进程数 MAX_PROCS ,请稍后尝试."}
            if not is_run(self.app, case_name):
                p = multiprocessing.Process(target=robot_run,
                                            args=(self.app, key, ''))
                p.start()
                self.app.config["AUTO_ROBOT"].append(
                    {"name": "%s" % case_name, "process": p})

                time.sleep(0.2)

            else:
                retry += 1
        if retry > 0 :
            return {"status": "success", "msg": "运行:{} 用例冲突，需要重试.".format(retry)}
        else:
            return {"status": "success", "msg": "开始运行:" + args['key']}

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
            return {"status": "fail", "msg": "请等待前面的任务运行完成."}

        return {"status": "success", "msg": "开始运行:" + case_name}

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
            return {"status": "fail", "msg": "无法找到配置文件:{}".format(conffile)}

        case_name = os.path.basename(key)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, key, ' -A '+conffile))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "请等待前面的任务运行完成."}

        return {"status": "success", "msg": "开始运行:{}".format(conffile)}

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
        return {"data": "暂不支持运行此类文件 <{}> .".format(fext)}

    def rerun_task(self, args):
        project = args['project']
        task_no = args['task_no']
        cmdfile = self.app.config["AUTO_HOME"] + "/jobs/%s/%s/%s/cmd.txt" % (session['username'], project,str(task_no))
        if not os.path.isfile(cmdfile):
            return {"status": "fail", "msg": "无法找到命令文件:{}".format(cmdfile)}

        cmdline = ''
        with open(cmdfile,'r') as f:
            cmdline = f.readline()

        cmdline = cmdline.strip()
        if cmdline == '':
            return {"status": "fail", "msg": "命令文件为空."}

        self.log.info("rerun_task CMD:"+cmdline)

        splits = cmdline.split('|')

        cases = splits[-1]    # driver|robot|args|output=xxx|cases
        args = splits[2]
        case_name = os.path.basename(cases)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, cases, args))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "请等待前面的任务运行完成."}

        return {"status": "success", "msg": "重新运行 {}:{}".format(project,task_no)}

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
            return {"status": "fail", "msg": "无法找到命令文件:{}".format(cmdfile)}
        if not os.path.isfile(outfile):
            return {"status": "fail", "msg": "无法找到历史结果文件:{}".format(outfile)}

        cmdline = ''
        with open(cmdfile,'r') as f:
            cmdline = f.readline()

        cmdline = cmdline.strip()
        if cmdline == '':
            return {"status": "fail", "msg": "命令文件为空."}

        splits = cmdline.split('|') # driver|robot|args|output=xxx|cases
        cases = splits[-1]
        args = splits[2] + ' -S ' + outfile
        case_name = os.path.basename(cases)

        self.log.info("rerunfail_task args:" + args)

        if not is_run(self.app, case_name):
            p = multiprocessing.Process(target=robot_run,
                                        args=(self.app, cases, args))
            p.start()
            self.app.config["AUTO_ROBOT"].append(
                {"name": "%s" % case_name, "process": p})
        else:
            return {"status": "fail", "msg": "请等待前面的任务运行完成."}

        return {"status": "success", "msg": "运行场景失败用例 {}:{}".format(project,task_no)}

def delete_task_record(app, args):
    project = args['project']
    task_no = args['task_no']
    task_path = app.config["AUTO_HOME"] + "/jobs/%s/%s/%s" % (session['username'], project, str(task_no))

    if os.path.exists(task_path):
        remove_dir(task_path)

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
