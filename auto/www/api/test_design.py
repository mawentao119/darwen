# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""

"""

import os
from flask import current_app, session, request
from flask_restful import Resource, reqparse

from utils.parsing import update_resource
from utils.file import exists_path, rename_file, make_nod, remove_file, mk_dirs, remove_dir, write_file, read_file, copy_file, get_splitext
from utils.mylogger import getlogger
from utils.gitit import remote_clone


class TestDesign(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('method', type=str)
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('project_name', type=str)
        self.parser.add_argument('suite_name', type=str)
        self.parser.add_argument('category', type=str)
        self.parser.add_argument('key', type=str)
        self.parser.add_argument('data', type=str)

        self.app = current_app._get_current_object()
        self.log = getlogger("TestDesign")

    def get(self):
        args = self.parser.parse_args()

        key = args["key"].replace(
            "--", "/") if args["key"] else args["path"].replace("--", "/")

        self.log.debug("Get args:{}".format(args))
        result = {"status": "success", "msg": "读取文件成功."}

        ext = get_splitext(key)
        result["ext"] = ext[1]

        #path = self.app.config["AUTO_HOME"] + "/workspace/%s%s" % (session["username"], args["path"])
        #path = args["key"]
        data = read_file(key)
        if not data["status"]:
            result["status"] = "fail"
            result["msg"] = "读取文件失败."

        result["data"] = data["data"]
        return result, 201

    def post(self):
        args = self.parser.parse_args()
        # if args["path"]:
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
        elif method == "save_result":
            result = self.__save_result(args)
        elif method == "gitclone_caserecord":
            result = self.__gitclone_caserecord(args)
        elif method == "delete_caserecord":
            result = self.__delete_caserecord(args)
        elif method == "recordbug":
            result = self.__recordbug(args)
        else:
            print(request.files["files"])

        return result, 201

    def __create(self, args):

        self.log.info(
            "***create***name:{} **cat:{}".format(args['name'], args['category']))
        if args['name'].endswith(args['category']):
            args['name'] = args['name'].split('.')[0]
        if args['category'] == '.oth':
            user_path = args["key"] + '/' + args['name']
        else:
            user_path = args["key"] + '/' + args['name'] + args['category']

        result = {"status": "success", "msg": "创建成功" +
                  ":"+os.path.basename(user_path)+":"+user_path}
        if not exists_path(user_path):
            make_nod(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "失败: 文件已存在 !"

        self.app.config['DB'].insert_loginfo(
            session['username'], 'model', 'create', user_path, result['status'])

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

        result = {"status": "success", "msg": "重命名成功:"+new_name}
        if not rename_file(old_name, new_name):
            result["status"] = "fail"
            result["msg"] = "重命名失败，文件已存在."
            return result

        if old_name.endswith('.robot'):
            self.app.config['DB'].delete_suite(old_name)
        if new_name.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(new_name)

        if old_name.endswith('.resource'):   # delete keywords or update highlight
            update_resource(old_name)
            update_resource(new_name)

        self.app.config['DB'].insert_loginfo(
            session['username'], 'suite', 'rename', old_name, result['status'])

        return result

    def __delete(self, args):
        result = {"status": "success", "msg": "删除成功:"+args['key']}

        user_path = args["key"]
        if exists_path(user_path):
            remove_file(user_path)
        else:
            result["status"] = "fail"
            result["msg"] = "删除失败，文件不存在!"
            return result

        if user_path.endswith('.robot'):
            self.app.config['DB'].delete_suite(user_path)
        # delete keywords or update highlight
        if user_path.endswith('.resource'):
            update_resource(user_path)

        self.app.config['DB'].insert_loginfo(
            session['username'], 'suite', 'delete', user_path, result['status'])

        return result

    def __delete_caserecord(self, args):
        res = self.app.config['DB'].runsql("DELETE from caserecord;")
        if res:
            result = {"status": "success", "msg": "成功：删除用例记录!"}
        else:
            result = {"status": "fail", "msg": "失败：删除用例记录!"}

        self.app.config['DB'].insert_loginfo(
            session['username'], 'caserecord', 'delete', 'none', result['status'])
        return result

    def __save(self, args):
        result = {"status": "success", "msg": "成功：保存成功."}
        user_path = args["key"]

        self.log.info(
            "***save path:{} \n***json:{}".format(user_path, args["data"]))

        if not write_file(user_path, args["data"]):
            result["status"] = "fail"
            result["msg"] = "失败：保存失败"

        if user_path.endswith('.robot'):
            self.app.config['DB'].refresh_caseinfo(user_path, 'force')
            self.app.config['DB'].insert_loginfo(
                session['username'], 'suite', 'edit', user_path, result['status'])

        # delete keywords or update highlight
        if user_path.endswith('.resource'):
            update_resource(user_path)

        return result

    def __copy(self, args):
        old_name = args["key"]
        fpre = os.path.dirname(old_name)
        new_name = 'copy_' + os.path.basename(old_name)

        new_file = fpre + '/' + new_name

        result = {"status": "success", "msg": "文件拷贝成功" +
                  ":"+new_name + ":" + new_file}
        if not copy_file(old_name, new_file):
            result["status"] = "fail"
            result["msg"] = "失败：新文件已存在!"

        self.app.config['DB'].insert_loginfo(
            session['username'], 'suite', 'copy', old_name, result['status'])

        return result

    def __handpass(self, args):
        return self.__set_casestatus(args, 'PASS')

    def __handfail(self, args):
        return self.__set_casestatus(args, 'FAIL')

    def __handunknown(self, args):
        return self.__set_casestatus(args, 'unknown')

    def __set_casestatus(self, args, status):
        info_key = args['key']
        info_name = args['name']
        status = status
        runuser = session['username']

        is_suite = False

        if info_name.endswith('.robot'):      # robot file
            is_suite = True

        try:

            if is_suite:
                res = self.app.config['DB'].set_suitestatus(
                    info_key, status, runuser)
            else:
                res = self.app.config['DB'].set_casestatus(
                    info_key, info_name, status, runuser)

            if res.rowcount > 0:
                result = {"status": "success", "msg": "设置状态 OK :" + info_name}
            else:
                result = {"status": "fail",
                          "msg": "找不到用例: " + info_name + ", you can try Refresh Dir."}
            self.app.config['DB'].insert_loginfo(
                session['username'], 'case', 'hand', info_key, info_name+':'+status)
        except Exception as e:
            self.log.error("handpass Exception:{}".format(e))
            result = {"status": "fail", "msg": "更新DB失败! See log file."}

        return result

    def __recordbug(self, args):
        result = {"status": "success", "msg": "This is TODO"}
        return result

    def __save_result(self, args):
        info_key = args['key']
        info_name = args['name']

        if info_name == 'save_d_i_r':
            msginfo = 'Dir|Suite: ' + info_key
            res = self.app.config['DB'].save_caserecord_d(info_key)
        else:
            msginfo = 'Case: ' + info_name
            res = self.app.config['DB'].save_caserecord(info_key, info_name)

        if res:
            result = {"status": "success", "msg": "保存用例结果成功! " + msginfo}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'save_result', info_key,
                                                 info_name + ':success')
        else:
            result = {"status": "fail",
                      "msg": "保存用例结果失败: " + info_name + ", 用例结果已存在."}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'save_result', info_key,
                                                 info_name + ':fail')
        return result

    def __gitclone_caserecord(self, args):

        url = args['name']
        if len(url) < 4:
            url = self.app.config['DB'].get_setting('history_git')
            if not url.startswith('http'):
                result = {"status": "fail",
                          "msg": "Fail:没有配置历史结果git或配置有误！url:" + url}
                return result

        path = self.app.config['AUTO_TEMP'] + '/caserecordgit'
        remove_dir(path) if os.path.exists(path) else None
        mk_dirs(path)

        (ok, info) = remote_clone(url, path)

        if not ok:
            result = {"status": "fail", "msg": info}
            self.app.config['DB'].insert_loginfo(session['username'], 'case', 'gitclonecaserecord', url,
                                                 result['status'])
            return result

        (gitname, extf) = os.path.splitext(os.path.basename(url))
        gitpath = os.path.join(path, gitname, '.git')
        remove_dir(gitpath) if os.path.exists(gitpath) else None

        total = 0
        success = 0
        formaterror = 0
        exits = 0
        totalfile = 0
        omitfile = 0

        for root, dirs, files in os.walk(os.path.join(path, gitname), topdown=False):
            for name in files:
                ff = os.path.join(root, name)
                (_, f_ext) = os.path.splitext(ff)
                totalfile += 1
                if not f_ext == '.his':
                    self.log.warning("Gitclone caserecord 忽略文件:"+ff)
                    omitfile += 1
                    continue
                with open(ff, 'r') as f:
                    for l in f:
                        l = l.strip()
                        if len(l) != 0:
                            total += 1
                        else:
                            continue
                        splits = l.split('|')
                        if len(splits) != 8:
                            formaterror += 1
                            self.log.error("uploadcaserecord 错误行:" + l)
                            continue
                        (
                            info_key, info_name, info_testproject, info_projectversion, ontime, run_status, run_elapsedtime,
                            run_user) = splits
                        sql = ''' INSERT into caserecord (info_key,info_name,info_testproject,info_projectversion,ontime,run_status,run_elapsedtime,run_user)
                                  VALUES ('{}','{}','{}','{}','{}','{}','{}','{}');
                                  '''.format(info_key, info_name, info_testproject, info_projectversion, ontime,
                                             run_status, run_elapsedtime, run_user)
                        res = self.app.config['DB'].runsql(sql)
                        if res:
                            success += 1
                        else:
                            exits += 1
                            self.log.error("uploadcaserecord 失败，记录存在:" + l)

        remove_dir(path) if os.path.exists(path) else None

        info = 'Finished with totalfile:{}, omitfile:{}, total:{}, sucess:{}, error:{}, exists:{}'.format(
            totalfile, omitfile, total, success, formaterror, exits)
        result = {"status": "success", "msg": info}

        return result
