# -*- utf-8 -*-
import sqlite3 as db
import os
from utils.mylogger import getlogger
from datetime import datetime,date

from robot.api import TestData


log = getlogger('TestDB')

class TestDB():
    def __init__(self, confdir='.'):
        # Init system TestDBID with file TestCaseDB.id if exists, Create new if not exists.
        self.DBID='0'
        self.DBcon = None
        self.DBcor = None

        self.confdir = confdir
        self.dbpath = self.confdir + '/'
        self.exclude_suite = '/work/workspace/Admin/uniRobot'
        self.refresh_interval = 180  # seconds
        self.refresh_time = self.get_timenow()
        self.DBIDFileName = 'TestCaseDB.id'
        self.IsNewDBID = False

        log.info("DB confdir : "+self.confdir)
        log.info("Checking if DBID file exists:" + self.dbpath+ self.DBIDFileName)
        if os.path.exists(self.dbpath + self.DBIDFileName):
            with open(self.dbpath + self.DBIDFileName, 'r') as f:
                self.DBID = f.readline().strip()
                log.info("Reading DBID from " + self.DBIDFileName + ": "+self.DBID)
        else:
            self.DBID = self.get_timenow()
            self.IsNewDBID = True
            with open(self.dbpath + self.DBIDFileName, 'w') as f:
                f.write(self.DBID)
                log.info("Create new File with ID: " + self.DBID)
        
        if not os.path.exists(self.dbpath + self.DBID+'.db'):
            log.warning("Found ID file:" + self.dbpath + self.DBIDFileName + " with DBID:" + self.DBID + " But no .db file found!")
            log.warning("Will create a new DB file ... ")
            self.IsNewDBID = True

        # init DB 
        self.DBcon = db.connect(self.dbpath + self.DBID+'.db', isolation_level=None,check_same_thread=False)
        self.DBcor = self.DBcon.cursor()
    
        # if NewDBID , Create Table 
        if self.IsNewDBID:

            log.info("NewDBID, Start create table testcase ...")
            self.createtb_testcase()
            log.info("NewDBID, Start create table loginfo ...")
            self.createtb_loginfo()

            log.info("NewDBID, Start create table user ...")
            self.createtb_user()
            self.init_user()
            log.info("NewDBID, Start create table project ...")
            self.createtb_project()
            self.init_project()

            log.info("NewDBID, Start create table tasks ...")
            self.createtb_tasks()

            log.info("NewDBID, Start create table settings ...")
            self.createtb_settings()
            self.init_settings()

            log.info("NewDBID, Start create table caserecord ...")
            self.createtb_caserecord()

        # Refresh Cases info Every time of Start ...
        workspace = os.path.dirname(self.confdir) + '/workspace'
        log.info("Force refresh TestCases of dir: "+workspace)
        self.refresh_caseinfo(workspace, "start")

    # datetime like: 20190112091212
    def get_timenow(self):
        return date.strftime(datetime.now(),'%Y%m%d%H%M%S')

    def _reset_refreshtime(self):
        self.refresh_time = self.get_timenow()
        log.info("Reset TestDB refreshtime to :"+self.refresh_time)

    def runsql(self, sql):
        log.info("RUNSQL:"+sql)
        try:
            res = self.DBcor.execute(sql)
            self.DBcon.commit()
        except Exception as e:
            log.error("RUNSQL Exeption:{}".format(e))
            return None
        return res

    def createtb_settings(self):
        self.runsql('''create table settings(
               description TEXT,
               item TEXT UNIQUE,
               value   TEXT DEFAULT '',
               demo    TEXT DEFAULT '',
               category TEXT DEFAULT 'unknown'
               );''')
    def init_settings(self):
        self.runsql('''INSERT INTO settings values('被测系统名称','test_project',"TBDS",'Do not modify twice.','system');''')
        self.runsql('''INSERT INTO settings values('被测系统版本号','test_projectversion',"V5013",'Do not modify twice.','system');''')
        self.runsql(
            '''INSERT INTO settings values('测试用例历史记录git','history_git',"https://www.github.com/abc.git",'','system');''')

        #self.runsql(
        #    '''INSERT INTO settings values('Testee Project Name','test_project',"TBDS",'Do not modify twice.','system');''')
        #self.runsql(
        #    '''INSERT INTO settings values('Testee Project Version','test_projectversion',"V5013",'Do not modify twice.','system');''')
        #self.runsql(
        #    '''INSERT INTO settings values('TestCase history git','history_git',"https://www.github.com/abc.git",'','system');''')

    def add_setting(self, description, item, value, demo):

        return self.runsql("INSERT INTO settings values('{}','{}','{}','{}','system'); ".format(description, item, value, demo))

    def del_setting(self, item):

        return self.runsql("DELETE FROM settings WHERE item='{}'; ".format(item))

    def get_setting(self, item):
        try:
            sql = "SELECT item, value from settings WHERE item='{}'; ".format(item)
            res = self.runsql(sql)
            (item, value) = res.fetchone()
            return value
        except TypeError:
            log.warning("Can not find Setting item: "+item)
            return 'unknown'

    def createtb_user(self):
        self.runsql('''create table user(
               username TEXT UNIQUE,
               fullname TEXT,
               passwordHash   TEXT,
               email    TEXT,
               category TEXT DEFAULT 'user'
               );''')
    def init_user(self):
        self.runsql('''INSERT INTO user values('Admin','admin',"pbkdf2:sha256:50000$fHCEAiyw$768c4f2ba9cabbc77513b9a25ffea1a19a77c23d8dab86e635d5f62f6fb8be6b",'charisma@tencent.com','Admin');''')
        self.runsql('''INSERT INTO user values('tester','tester',"pbkdf2:sha256:50000$kluBmp5X$611e4d66f33fd139b03425f1ad0a21c4009974bd02343bfc69bd4e3d06325d57",'tester@tencent.com','User');''')

    def _case_exists(self, info_key , info_name):
        try:
            sql = "select info_key,info_name from testcase where info_key='{}' and info_name ='{}'; ".format(info_key,info_name)
            res = self.runsql(sql)
            (key, name) = res.fetchone()
            return True
        except TypeError:
            return False

    def set_casestatus(self, info_key,info_name,status , runuser):
        try:
            sql = '''UPDATE testcase SET ontime=datetime('now','localtime'),
                                         run_status='{}',
                                         run_user='{}',
                                         rcd_handtime=datetime('now','localtime')
                     WHERE info_key='{}' and info_name='{}'; 
                     '''.format(status,runuser,info_key,info_name)
            return self.runsql(sql)
        except TypeError:
            return None

    def set_suitestatus(self, info_key, status , runuser):
        try:
            sql = '''UPDATE testcase SET ontime=datetime('now','localtime'),
                                         run_status='{}',
                                         run_user='{}',
                                         rcd_handtime=datetime('now','localtime')
                     WHERE info_key='{}'; 
                     '''.format(status,runuser,info_key)
            return self.runsql(sql)
        except TypeError:
            return None

    def get_casestatus(self, info_key , info_name):
        try:
            sql = "select run_status,info_name from testcase where info_key='{}' and info_name ='{}'; ".format(info_key,info_name)
            res = self.runsql(sql)
            (status, name) = res.fetchone()
            return status
        except TypeError:
            return 'unknown'

    def get_suitestatus(self,info_key):
        try:
            ss = []
            sql = "select run_status,info_name from testcase where info_key='{}'; ".format(info_key)
            res = self.runsql(sql)
            for i in res:
                (status, name) = i
                ss.append(status)

            if 'unknown' in ss or len(ss) == 0 :
                return 'unknown'
            if 'FAIL' in ss:
                return 'FAIL'
            return 'PASS'
        except TypeError:
            return 'unknown'

    def get_password(self,username):
        try:
            res = self.runsql("select username,passwordHash from user where username='{}'; ".format(username))
            (name, passwd) = res.fetchone()
            return passwd
        except TypeError:
            return None

    def del_user(self, username):
        if username == 'Admin' or username == 'admin':
            return True
        self.runsql("Delete from user where username = '{}' ;".format(username))
        return True

    def add_user(self, username, fullname, passwordHash, email):
        if username in ['myself','Admin','admin','all','All']:
            log.error("It is not allowed username:{}".format(username))
            return False
        try:
            self.runsql("INSERT INTO user values('{}','{}','{}','{}','User'); ".format(username, fullname, passwordHash, email))
        except Exception as e:
            log.error("Exception in add_user, User exists.{}".format(e))
            return False
        return True

    def createtb_project(self):
        self.runsql('''create table project(
               projectname TEXT,
               owner TEXT,
               users TEXT DEFAULT 'myself',
               cron  TEXT DEFAULT '* * * * * *',
               primary key (projectname,owner)
               );''')

    def init_project(self):
        self.runsql('''INSERT INTO project(projectname,owner,users) VALUES('Demo_Project','Admin','all');''')
        self.runsql('''INSERT INTO project(projectname,owner,users) VALUES('uniRobot','Admin','Admin');''')
        #self.runsql('''INSERT INTO project(projectname,owner,users) VALUES('RobotTbds3','tester','mwt');''')

    def add_project(self, projectname, owner ,users):
        try:
           self.runsql("INSERT INTO project(projectname,owner,users) VALUES('{}','{}','{}');".format(projectname,owner,users))
        except Exception as e:
            log.error("Exception in add_project:{}".format(e))
            return False
        return True

    def edit_project(self, pname, newname, owner):
        try:
           self.runsql("Update project set projectname = '{}' where projectname = '{}' and owner = '{}' ;".format(newname,pname,owner))
        except Exception as e:
            log.error("Exception in add_project:{}".format(e))
            return False
        return True

    def add_projectuser(self, project, newuser):
        users = []
        user = []
        res = self.runsql("SELECT users FROM project WHERE projectname='{}' ;".format(project))
        for u in res:
            (us,) = u
            users.append(us)
        if len(users) > 0:
            user = users[0].split(',')
        user.append(newuser)
        user = list(set(user))
        user_str = ','.join(user)

        sql = "UPDATE project set users='{}' WHERE projectname='{}' ;".format(user_str,project)
        return self.runsql(sql)

    def del_projectuser(self, project, newuser):
        users = []
        user = []
        res = self.runsql("SELECT users FROM project WHERE projectname='{}' ;".format(project))
        for u in res:
            (us,) = u
            users.append(us)
        if len(users) > 0:
            user = users[0].split(',')
        user.remove(newuser) if newuser in user else None
        user = list(set(user))
        user_str = ','.join(user)

        sql = "UPDATE project set users='{}' WHERE projectname='{}' ;".format(user_str,project)
        return self.runsql(sql)

    def get_ownproject(self,username):

        res = self.runsql("select projectname from project where owner = '{}';".format(username))
        projects = []
        for i in res:
            (p,) = i
            projects.append(p)

        return projects

    def get_othproject(self,username):
        res = self.runsql("select projectname,users from project;")
        projects = []
        for i in res:
            (p,u) = i
            us = u.split(',')
            if username in us:
                projects.append(p)

        return projects

    def get_allproject(self,username):
        all = []
        res = self.runsql("select owner,projectname,users from project ;")
        for i in res:
            (o,p,u) = i
            if o == username:
                all.append("{}:{}".format(o, p))
            us = u.split(',')
            if username in us or 'all' in us:
                all.append("{}:{}".format(o, p))

        all = list(set(all))    # delete the same values
        all.sort()              # order , TODO order by category
        return all

    def get_projectusers(self,project):
        all = []
        isforall = False
        res = self.runsql("select owner,users from project where projectname = '{}' ;".format(project))
        for i in res:
            (o,u) = i
            all.append(o)
            us = u.split(',')
            for uu in us:
                if uu == 'all':
                    isforall = True
                else:
                    all.append(uu)

        if isforall:
            res = self.runsql("select username from user;")
            for r in res:
                (u,) = r
                all.append(u)

        all = list(set(all))    # delete the same values
        all.sort()              # order , TODO order by category
        return all

    def del_project(self, projectname, owner):
        return self.runsql("Delete from project where projectname = '{}' and owner = '{}' ;".format(projectname, owner))

    def createtb_tasks(self):
        '''
        暂时没有用到，后续为定时任务使用
        :return:
        '''
        return self.runsql('''Create Table tasks(user TEXT , taskkey TEXT, cron TEXT );''')

    def createtb_testcase(self):
        '''
        保存测试用例
        :return:
        '''
        return self.runsql('''create table testcase(
                       info_key TEXT,
                       info_name TEXT,
                       info_casecontent TEXT DEFAULT '',
                       info_doc TEXT DEFAULT '',
                       info_tags TEXT DEFAULT '',
                       ontime TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                       run_status TEXT DEFAULT 'unknown',
                       run_user TEXT,
                       run_elapsedtime INTEGER DEFAULT 0,
                       run_starttime TEXT,
                       run_endtime TEXT,
                       rcd_handtime TIMESTAMP DEFAULT 0,
                       rcd_runtimes INTEGER DEFAULT 0,
                       rcd_successtimes INTEGER DEFAULT 0,
                       rcd_failtimes INTEGER DEFAULT 0,
                       rcd_runusers TEXT,
                       primary key (info_key,info_name)                       
                ); ''')

    def createtb_caserecord(self):
        '''
        用于用例的历史结果比对
        :return:
        '''
        return self.runsql('''create table caserecord(
                       info_key TEXT,
                       info_name TEXT,
                       info_testproject TEXT DEFAULT '',
                       info_projectversion TEXT DEFAULT '',
                       ontime TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                       run_status TEXT DEFAULT 'unknown',
                       run_elapsedtime INTEGER DEFAULT 0,
                       run_user TEXT,
                       primary key (info_key,info_name,ontime)                       
                ); ''')

    def save_caserecord(self, info_key, info_name):

        testproject = self.get_setting('test_project')
        projectversion = self.get_setting('test_projectversion')

        try:
            sql = '''INSERT into caserecord (info_key,info_name,info_testproject,info_projectversion,ontime,run_status,run_elapsedtime,run_user)
                     SELECT                  info_key,info_name,'{}',            '{}',               ontime,run_status,run_elapsedtime,run_user
                     FROM        testcase
                     WHERE info_key='{}' and info_name='{}'; 
                     '''.format(testproject, projectversion, info_key,info_name)
            return self.runsql(sql)
        except TypeError:
            return None
    
    def createtb_loginfo(self):
        '''
        保存所有执行日志，用于统计报表和审计
        :return:
        '''
        self.runsql(''' CREATE TABLE loginfo(
                       logtime TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                       user TEXT DEFAULT '',
                       target TEXT DEFAULT '',
                       action  TEXT DEFAULT '',
                       key TEXT DEFAULT '',
                       result  TEXT DEFAULT ''
                );''')
    def insert_loginfo(self,user,target,action,key,result=''):
        sql = ''' INSERT INTO loginfo(user,target,action,key,result) 
                  VALUES('{}','{}','{}','{}','{}');'''.format(user,target,action,key,result)
        try:
            res = self.runsql(sql)
        except Exception as e:
            log.error("loginfo Exception:"+sql)
            return None

        return res

    def get_id(self):
        return self.DBID

    def delete_suite(self, info_key):
        return self.runsql("Delete from testcase where info_key like '{}%' ;".format(info_key))

    def refresh_caseinfo(self, target, mode='normal'):
        if os.path.isdir(target):
            old = self.refresh_time
            now = self.get_timenow()

            if int(now) - int(old) < self.refresh_interval and mode == "normal" :
                log.info("Do not reach the refresh time of {}s : {} ".format(self.refresh_interval,target))
                return False

        log.info("Start refresh cases:"+target)

        if target.find(self.exclude_suite) != -1:
            return True

        suite = TestData(source=target, extensions='robot')
        self._refresh_case(suite, mode)

        if os.path.isdir(target):
            self._reset_refreshtime()

        return True

    def _refresh_case(self, suite, mode='normal'):
        source = suite.source

        if source.find(self.exclude_suite) != -1:
            return

        suite_cases = []

        # update each robot file
        try:
            sql = "select info_key,info_name from testcase where info_key='{}'; ".format(
                source)
            res = self.runsql(sql)
            for i in res:
                (k, n) = i
                suite_cases.append([k, n])
        except Exception:
            suite_cases = []

        # add new case
        for test in suite.testcase_table:
            info_key = source
            info_name = test.name

            tags = ",".join(test.tags)
            doc = test.doc

            if [info_key, info_name] in suite_cases:
                suite_cases.remove([info_key, info_name])
                sql = '''UPDATE testcase set info_tags='{}', 
                                             info_doc='{}' 
                         WHERE info_key='{}' and info_name='{}';'''.format(tags,doc,info_key,info_name)
                self.runsql(sql)
            else:
                try:
                    sql = "insert into testcase(info_key,info_name,info_tags, info_doc) \
                    values('{}','{}','{}','{}');".format(info_key, info_name, tags,doc)
                    self.runsql(sql)
                except Exception as e:
                    log.error("Insert testcase Fail:{}".format(e))

                if not mode == 'start':
                    self.insert_loginfo('unknown', 'case', 'create', info_key, info_name)

        # deleted cases and renamed cases should be deleted
        for i in suite_cases:
            sql = "delete from testcase where info_key ='{}' and info_name='{}';".format(i[0], i[1])
            self.runsql(sql)

            if not mode == 'start':
                self.insert_loginfo('unknown','case','delete',i[0],i[1])

        for child in suite.children:
            self._refresh_case(child, mode)

    def get_testdata(self, target):

        if target.find(self.exclude_suite) != -1:
            return [0, 0, 0, 0, 0]

        suites = 0
        cases = 0
        passed = 0
        failed = 0
        unknown = 0

        sql = '''SELECT count(distinct(info_key)), count(info_name) from testcase where info_key like '{}%' ;'''.format(target)
        res = self.runsql(sql)
        (suites,cases) = res.fetchone()

        sql = '''SELECT count(info_name) from testcase where run_status='PASS' and info_key like '{}%' ;'''.format(target)
        res = self.runsql(sql)
        (passed,) = res.fetchone()

        sql = '''SELECT count(info_name) from testcase where run_status='FAIL' and info_key like '{}%' ;'''.format(
            target)
        res = self.runsql(sql)
        (failed,) = res.fetchone()

        return [suites,cases,passed,failed,cases-(passed + failed)]

    def get_testdataOLD(self, target):

        if target.find(self.exclude_suite) != -1:
            return [0, 0, 0, 0, 0]

        try:
            suite = TestData(source=target, extensions='robot')
        except Exception as e:
            log.error("get_testdata of source {} Exception :{}".format(target,e))
            return [0,0,0,0,0]

        suites = 0
        cases = 0
        passed = 0
        failed = 0
        unknown = 0

        def _getdata(suite=suite):
            ss = suite.source
            nonlocal suites
            nonlocal cases
            nonlocal passed
            nonlocal failed
            nonlocal unknown
            if len(suite.testcase_table) > 0:
                suites += 1
                for t in suite.testcase_table:
                    info_key = ss
                    info_name = t.name
                    status = self.get_casestatus(info_key, info_name)
                    if status == 'PASS':
                        passed += 1
                    elif status == 'FAIL':
                        failed += 1
                    else:
                        unknown += 1
                    cases += 1

            for child in suite.children:
                _getdata(child)

        _getdata(suite)

        return [suites,cases,passed,failed,unknown]
    
if __name__ == '__main__':
    myDB = TestDB('/Users/tester/PycharmProjects/uniRobotDev/work/DBs')
    #res = myDB.runsql("insert into everyday(item,value,demo) values('second','1112222','demo info');")
    #res = myDB.add_user('zhangsan1','zhangsan1','aaabbb','zh@e.com')
    #res = myDB.add_project('proj2','zhangsan','lisi')

    #res = myDB.runsql("select * from user ;")
    #for i in res:
    #    print(i)

    #res = myDB.runsql("select * from project ;")
    #for i in res:
    #    print(i)

    #print(myDB.get_ownproject('tbdsadmin'))
    #print(myDB.get_passwd('Admin'))
    #print(myDB.get_allproject('zhangsan'))
    #all = myDB.get_allproject('AA')
    #for o in all:
    #    print("{}:::{}".format(o.split(':')[0],o.split(':')[1]))

    #myDB.refresh_caseinfo('/Users/tester/PycharmProjects/uniRobotDev/.beats/workspace/Admin/Demo_Project/RobotTestDemo/TestCase/903dir1','force')
    file1 = '/Users/tester/PycharmProjects/uniRobotDev/.beats/workspace/Admin/Demo_Project/RobotTestDemo/TestCase/903dir1/case1.robot'

    dir1 = '/Users/tester/PycharmProjects/uniRobotDev/.beats/workspace/Admin/Demo_Project/RobotTestDemo/TestCase/903dir1'


    #res = myDB.insert_loginfo("admin","case","run case","Jest test")
    #res = myDB.runsql("select * from loginfo  ;".format(file1))
    sql = '''INSERT INTO loginfo(user,target,action,key,result) 
                  VALUES('Admin','case','debug','/Users/tester/PycharmProjects/uniRobotDev/work/workspace/Admin/Demo_Project/RobotTestDemo/TestCase/01Template.robot','OK')'''

    sql2 = ''' SELECT count(*) FROM loginfo WHERE 
                                                  logtime > datetime('now','localtime','-365 days') 
                                              and target='suite' 
                                              and ( action='create' or action='copy' )
                                              and key like '/Users/tester/PycharmProjects/uniRobotDev/work/workspace/Admin/Demo_Project%'; '''



    res = myDB.runsql("select user, target, action ,key from loginfo;")
    for u in res:
        print(u)




