# -*- coding: utf-8 -*-

__author__ = "苦叶子"
__modifier__ = "mawentao119@gmail.com"

"""

"""

import os
from flask import current_app, session, request, send_file, make_response
from flask_restful import Resource, reqparse
import werkzeug
from robot.api import ExecutionResult

from urllib.parse import quote
from utils.parsing import update_resource
from utils.file import exists_path, rename_file, make_nod, remove_file, write_file, read_file, copy_file, get_splitext, get_projectnamefromkey
from utils.testcaseunite import export_casexlsx, export_casezip, do_importfromxlsx ,do_importfromzip
from utils.mylogger import getlogger

class Case(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('new_name', type=str)
        self.parser.add_argument('project_name', type=str)
        self.parser.add_argument('suite_name', type=str)
        self.parser.add_argument('category', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('new_category', type=str)
        self.parser.add_argument('path', type=str)
        self.parser.add_argument('data', type=str)
        self.app = current_app._get_current_object()
        self.log = getlogger("Case")

    def get(self):
        args = self.parser.parse_args()
        #charis added TODO 应该没有传path的地方了，考虑删除掉
        '''if args["path"]:
            args["path"] = args["path"].replace("--","/")
        if args["key"]:
            args["key"] = args["key"].replace("--","/")'''

        key = args["key"].replace("--","/") if args["key"] else args["path"].replace("--","/")

        self.log.debug("Get args:{}".format(args))
        result = {"status": "success", "msg": "Read file success."}

        ext = get_splitext(key)
        result["ext"] = ext[1]

        #path = self.app.config["AUTO_HOME"] + "/workspace/%s%s" % (session["username"], args["path"])
        #path = args["key"]
        data = read_file(key)
        if not data["status"]:
            result["status"] = "fail"
            result["msg"] = "Read file failed."

        result["data"] = data["data"]
        return result, 201

    def post(self):
        args = self.parser.parse_args()
        #if args["path"]:
        #    args["path"] = args["path"].replace("--", "/")
        if args["key"]:
            args["key"] = args["key"].replace("--", "/")
        self.log.debug("Post args:{}".format(args))
        method = args["method"].lower()
        if method == "create":
            result = self.__create(args)
        elif method == "edit":
            result = self.__edit(args)
        elif method == "delete":
            result = self.__delete(args)
        elif method == "save":
            result = self.__save(args)
        elif method == "copy":
            result = self.__copy(args)
        elif method == "handpass":
            result = self.__handpass(args)
        elif method == "handfail":
            result = self.__handfail(args)
        elif method == "handunknown":
            result = self.__handunknown(args)
        elif method == "recordbug":
            result = self.__recordbug(args)
        else:
            print(request.files["files"])

        return result, 201

    def __create(self, args):

        if args['name'].endswith(args['category']):
            args['name'] = args['name'].split('.')[0]
        if args['category'] == '.oth':
            user_path = args["key"] + '/' + args['name']
        else:
            user_path = args["key"] + '/' + args['name'] + args['category']

        result = {"status": "success", "msg": "Create success"+":"+os.path.basename(user_path)+":"+user_path}
        if not exists_path(user_path):
            make_nod(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Create Fail: File exists !"

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'create', user_path, result['status'])

        return result

    def __edit(self, args):

        # TODO: 参数太复杂了，需要简化
        old_name = args["key"]
        fpre = os.path.dirname(old_name)

        if args['new_name'].endswith(args['new_category']):
            args['new_name'] = args['new_name'].split('.')[0]
        if args['new_category'] == '.oth':
            new_name = fpre + '/' + args["new_name"]
        else:
            new_name = fpre + '/' + args["new_name"] + args["new_category"]

        result = {"status": "success", "msg": "Rename success:"+new_name}
        if not rename_file(old_name, new_name):
            result["status"] = "fail"
            result["msg"] = "Rename Failed , filename exists."
            return result

        if old_name.endswith('.robot'):
            self.app.config['DB'].delete_suite(old_name)
        if new_name.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(new_name)

        if old_name.endswith('.resource'):   # delete keywords or update highlight
            update_resource(old_name)
            update_resource(new_name)

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'rename', old_name, result['status'])

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "Delete success:"+args['key']}

        user_path = args["key"]
        if exists_path(user_path):
            remove_file(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "Delete Failed, File not exists!"
            return result

        if user_path.endswith('.robot'):
            self.app.config['DB'].delete_suite(user_path)
        if user_path.endswith('.resource'):   # delete keywords or update highlight
            update_resource(user_path)

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'delete', user_path, result['status'])

        return result

    def __save(self, args):
        result = {"status": "success", "msg": "Save success."}
        user_path = args["key"]

        if not write_file(user_path, args["data"]):
            result["status"] = "fail"
            result["msg"] = "Save Failed"

        if user_path.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(user_path, 'force')
            self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'edit', user_path, result['status'])

        if user_path.endswith('.resource'):   # delete keywords or update highlight
            update_resource(user_path)

        return result

    def __copy(self, args):
        old_name = args["key"]
        fpre = os.path.dirname(old_name)
        new_name = 'copy_' + os.path.basename(old_name)

        new_file = fpre + '/' + new_name

        result = {"status": "success", "msg": "File copy success"+":"+new_name +":" + new_file}
        if not copy_file(old_name, new_file):
            result["status"] = "fail"
            result["msg"] = "File copy Failed，new name exists!"

        self.app.config['DB'].insert_loginfo(session['username'], 'suite', 'copy', old_name, result['status'])

        return result

    def __handpass(self, args):
        return self.__set_casestatus(args,'PASS')
    def __handfail(self, args):
        return self.__set_casestatus(args,'FAIL')
    def __handunknown(self, args):
        return self.__set_casestatus(args,'unknown')

    def __set_casestatus(self, args, status):
        info_key = args['key']
        info_name = args['name']
        status = status
        runuser = session['username']

        is_suite = False

        if info_name.endswith('.robot'):      # robot file
            is_suite = True

        try:

            if is_suite :
                res = self.app.config['DB'].set_suitestatus(info_key, status, runuser)
            else:
                res = self.app.config['DB'].set_casestatus(info_key, info_name, status, runuser)

            if res.rowcount > 0:
                result = {"status": "success", "msg": "Set status OK :" + info_name}
            else:
                result = {"status": "fail",
                          "msg": "Cannot find case: " + info_name + ", you can try Refresh Dir."}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'hand', info_key, info_name+':'+status)
        except Exception as e:
            self.log.error("handpass Exception:{}".format(e))
            result = {"status": "fail", "msg": "Update DB Failed! See log file."}

        return result

    def __recordbug(self, args):
        result = {"status": "success", "msg": "This is TODO"}
        return result

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
        elif method == "upload":
            file = request.files.to_dict()['files']
            return self.__upload(file, args['key']), 201
        elif method == "download":
            return self.__download(args)
        elif method == "downcaseinfox":
            return self.__downcaseinfox(args)
        elif method == "downcaseinfoz":
            return self.__downcaseinfoz(args)
        elif method == "downruninfo":
            return self.__downruninfo(args)

    def __uploadcase(self, file, path):

        temp_file = self.app.config['AUTO_TEMP'] + '/' + file.filename
        os.remove(temp_file) if os.path.exists(temp_file) else None
        file.save(temp_file)


        f_ext = os.path.basename(temp_file).split('.')[-1]

        if f_ext == 'xlsx':
            (status, msg) = do_importfromxlsx(temp_file, path)
            result = {"status": status, "msg": msg}
        elif f_ext == 'zip':
            (status, msg) = do_importfromzip(temp_file, path)
            result = {"status": status, "msg": msg}
        else:
            result = {"status": "fail", "msg": "Unexpected file ext:{}".format(f_ext)}

        self.app.config['DB'].insert_loginfo(session['username'], 'file', 'uploadcase', path, file.filename)

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
