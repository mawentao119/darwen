# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""

"""

import os
import time
from flask import current_app, session, request, send_file, make_response
from flask_restful import Resource, reqparse
import werkzeug
from robot.api import ExecutionResult

from urllib.parse import quote
from utils.file import exists_path, rename_file, make_nod, remove_file, write_file, read_file, copy_file, get_splitext, get_projectnamefromkey
from utils.testcaseunite import export_casexlsx, export_casezip, do_importfromxlsx ,do_importfromzip, do_uploadcaserecord
from utils.mylogger import getlogger

class ManageFile(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('data', type=str)
        self.parser.add_argument('file', type=werkzeug.datastructures.FileStorage, location='files', action='append')
        self.app = current_app._get_current_object()
        self.log = getlogger("ManageFile")

    def post(self):
        args = request.form.to_dict()
        self.log.debug("Post:args:{}".format(args))
        method = args["method"].lower()
        if method == "uploadcase":
            file = request.files.to_dict()['files']
            return self.__uploadcase(file, args['key']), 201
        elif method == "uploadcaserecord":
            file = request.files.to_dict()['files']
            return self.__uploadcaserecord(file, args['key']), 201
        elif method == "upload":
            file = request.files.to_dict()['files']
            return self.__upload(file, args['key']), 201
        elif method == "download":
            return self.__download(args)
        elif method == "downcaseinfox":
            return self.__downcaseinfox(args)
        elif method == "downcaseinfoz":
            return self.__downcaseinfoz(args)
        elif method == "export_result":
            return self.__export_result(args)
        elif method == "downruninfo":
            return self.__downruninfo(args)

    def __uploadcase(self, file, path):

        temp_file = self.app.config['AUTO_TEMP'] + '/' + file.filename
        os.remove(temp_file) if os.path.exists(temp_file) else None
        file.save(temp_file)

        (_, f_ext) = os.path.splitext(temp_file)

        if f_ext == '.xlsx':
            (status, msg) = do_importfromxlsx(temp_file, path)
            result = {"status": status, "msg": msg}
        elif f_ext == '.zip':
            (status, msg) = do_importfromzip(temp_file, path)
            result = {"status": status, "msg": msg}
        else:
            result = {"status": "fail", "msg": "Unexpected file ext:{}".format(f_ext)}

        self.app.config['DB'].insert_loginfo(session['username'], 'file', 'uploadcase', path, file.filename)

        return result

    def __uploadcaserecord(self, file, key):
        '''
        上传用例历史执行结果，并导入到caserecord表
        :param file:
        :param key:
        :return:
        '''
        temp_file = self.app.config['AUTO_TEMP'] + '/' + file.filename
        os.remove(temp_file) if os.path.exists(temp_file) else None
        file.save(temp_file)

        (_, f_ext) = os.path.splitext(temp_file)

        self.log.error("******* temp_file:{} ; f_ext:{}".format(temp_file,f_ext))

        if f_ext == '.his':
            (status, msg) = do_uploadcaserecord(temp_file)
            result = {"status": status, "msg": msg}
        else:
            msg = "文件后缀不符合要求(.his):{}".format(f_ext)
            result = {"status": "fail", "msg": msg}

        self.app.config['DB'].insert_loginfo(session['username'], 'file', 'uploadcaserecord', msg, file.filename)

        return result

    def __upload(self, file, path):
        result = {"status": "success", "msg": "Upload success."}

        #charis added  TODO: 如果统一菜单的话，可以这里判断path是否为目录或文件
        user_path = path + '/' + file.filename
        #user_path = self.app.config["AUTO_HOME"] + "/workspace/%s" % session['username'] + path + file.filename
        if not exists_path(user_path):
            file.save(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Upload Failed."

        self.app.config['DB'].insert_loginfo(session['username'], 'file', 'upload', user_path)

        return result

    def __download(self, args):
        # charis added :
        user_path = args['key']
        self.log.info("Download casefile request:" + user_path)

        self.app.config['DB'].insert_loginfo(session['username'], 'file', 'download', user_path)

        return self.__sendfile(user_path)

    def __downcaseinfox(self, args):
        # charis added :
        key = args['key']
        self.log.info("Download xlsx caseinfo of dir:"+key)

        (isok, casefile) = export_casexlsx(key, self.app.config['DB'], self.app.config['AUTO_TEMP'])

        self.app.config['DB'].insert_loginfo(session['username'], 'caseinfo', 'download', key,'xlsx')

        if not isok :
            self.log.error("Download case Failed,return is :{}".format(casefile))
            return "Fail:{}".format(casefile)

        return self.__sendfile(casefile)

    def __downcaseinfoz(self, args):
        # charis added :
        key = args['key']
        self.log.info("Download zip caseinfo of dir:"+key)

        (isok, casefile) = export_casezip(key, self.app.config['AUTO_TEMP'])

        self.app.config['DB'].insert_loginfo(session['username'], 'caseinfo', 'download', key,'zip')

        if not isok :
            self.log.error("Download case Failed,return is :{}".format(casefile))
            return "Fail:{}".format(casefile)

        return self.__sendfile(casefile)

    def __export_result(self, args):
        key = args['key']
        name = args['name']

        testproject = self.app.config['DB'].get_setting('test_project')
        projectversion = self.app.config['DB'].get_setting('test_projectversion')

        sql = '''SELECT info_key,info_name,'{}', '{}', ontime,run_status,run_elapsedtime,run_user
                 FROM   testcase
                 WHERE info_key='{}' and info_name='{}'; '''.format(testproject, projectversion, key,name)

        if name == 'export_d_i_r':
            sql = '''SELECT info_key,info_name,'{}', '{}', ontime,run_status,run_elapsedtime,run_user
                             FROM   testcase
                             WHERE info_key like '{}%' ; '''.format(testproject, projectversion, key)

        res = self.app.config['DB'].runsql(sql)
        if res:
            fname = os.path.join(self.app.config['AUTO_TEMP'], 'his_' + str(time.time_ns()) + '.his')
            with open(fname,'w') as myfile:
                for i in res:
                    (key, name, project, version, ontime, run_status, run_elapsedtime, run_user) = i
                    myfile.write("{}|{}|{}|{}|{}|{}|{}|{}\n".format(key, name, project, version, ontime,run_status,run_elapsedtime,run_user))

            self.app.config['DB'].insert_loginfo(session['username'], 'caseinfo', 'export1result', key, name)

            return self.__sendfile(fname)
        else:
            self.log.error("Fail: exportXresult of key:{} ,name:{} ,Cannot find case .".format(key,name))
            return "Cannot find case ."

    def __downruninfo(self, args):
        # charis added :
        user_path = args["key"]
        project = get_projectnamefromkey(user_path)
        self.log.info("Download runinfo request:"+user_path)

        jobpath = self.app.config["AUTO_HOME"] + "/jobs"
        job_path = self.app.config["AUTO_HOME"] + "/jobs/%s/%s" % (session['username'], project)

        for user in os.listdir(job_path):
            if os.path.isdir(user):
                for prj in os.listdir(user):
                    if os.path.isdir(prj) and prj == project:
                        for tasks in prj:
                            if os.path.isdir(tasks):
                                for f in tasks:
                                    if f.endswith('.xml'):
                                        suite = ExecutionResult(f).suite


        user_path = "/Users/tester/PycharmProjects/uniRobotDev/.beats/workspace/Admin/Demo_Project/RobotTestDemo/TestCase/01Template.robot"

        self.app.config['DB'].insert_loginfo(session['username'], 'runinfo', 'download', project)

        return self.__sendfile(user_path)

    def __sendfile(self, f):
        response = make_response(send_file(f))
        basename = os.path.basename(f)
        response.headers["Content-Disposition"] = \
            "attachment;" \
            "filename*=UTF-8''{utf_filename}".format(
                utf_filename=quote(basename.encode('utf-8'))
            )
        return response
