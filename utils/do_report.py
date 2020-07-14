# -*- coding: utf-8 -*-

__author__ = "charisma"

"""

"""

import os
from flask import current_app, url_for
from utils.file import get_projectnamefromkey

from utils.mylogger import getlogger

log = getlogger('Utils.Report')

def get_caseinfo(key,method):
    """
    Generate Case and Suite's Add/Delete/Modify/Execution Info
    :param key: Specific dir
    :param method: Time period ：sqlite's time modifier
    :return: All data from case_report-caseinfo tab
    """

    app = current_app._get_current_object()

    log.info("get_caseinfo Key:{} method:{}".format(key,method))
    if method == 'day':
        period = '-24 hours'
        time = "Within 24 Hrs"
    elif method == 'week':
        period = '-7 days'
        time = 'Within 7 Days'
    else:
        period = '-365 days'
        time = 'Within 1 Year'

    user_list = {"total": 0, "rows": []}
    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                      logtime > datetime('now','localtime','{}') 
                                  and target='case' 
                                  and action='create' 
                                  and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum1,) = res.fetchone()

    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                              logtime > datetime('now','localtime','{}') 
                                          and target='suite' 
                                          and (action='create' or action='copy') 
                                          and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum2,) = res.fetchone()

    user_list["rows"].append(
        {"case": 'New Cases', "caseresult": sum1, "nothing": "|", "suite": 'New Suites', "suiteresult": sum2, "time": time})

    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                              logtime > datetime('now','localtime','{}') 
                                          and target='case' 
                                          and action='delete'
                                          and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum1,) = res.fetchone()
    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                                      logtime > datetime('now','localtime','{}') 
                                                  and target='suite' 
                                                  and action='delete'
                                                  and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum2,) = res.fetchone()

    user_list["rows"].append(
        {"case": 'Del Cases', "caseresult": sum1, "nothing": "|", "suite": 'Del Suites', "suiteresult": sum2, "time": time})

    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                                      logtime > datetime('now','localtime','{}') 
                                                  and target='case' 
                                                  and action='debug' 
                                                  and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum1,) = res.fetchone()
    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                                      logtime > datetime('now','localtime','{}') 
                                                  and target='suite' 
                                                  and (action='edit' or action='rename')
                                                  and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum2,) = res.fetchone()

    user_list["rows"].append(
        {"case": 'Debug Cases', "caseresult": sum1, "nothing": "|", "suite": 'Modify Suites', "suiteresult": sum2, "time": time})

    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                                      logtime > datetime('now','localtime','{}') 
                                                  and target='case' 
                                                  and ( action='run' or action='hand') 
                                                  and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum1,) = res.fetchone()
    sql = ''' SELECT count(*) FROM loginfo WHERE 
                                                              logtime > datetime('now','localtime','{}') 
                                                          and target='suite' 
                                                          and action='run'
                                                          and key like '{}%' ; '''.format(period, key)
    res = app.config['DB'].runsql(sql)
    (sum2,) = res.fetchone()

    user_list["rows"].append(
        {"case": 'Run Cases', "caseresult": sum1, "nothing": "|", "suite": 'Run Suites', "suiteresult": sum2, "time": time})

    return user_list

def get_excuteinfo(key, method):
    """
    Get execution info: auto-run passed failed , hand-run passed,failed , and total : day ,week, all
    :param key:
    :param method:
    :return:
    """
    app = current_app._get_current_object()

    log.info("get_excuteinfo Key:{} method:{}".format(key, method))
    if method == 'day':
        time = "Within 24 Hrs"
    elif method == 'week':
        time = 'Within 7 Days'
    else:
        time = 'From Beginning'

    excute_list = {"total": 0, "rows": []}
    progress = rpt_runprogress(key,method)

    percent = format(((progress['auto'][1]+progress['auto'][2])/progress['auto'][0])*100, '.2f') if progress['auto'][0]>0 else '0'
    excute_list["rows"].append(
        {"category":'Auto-Cases', "passed": progress['auto'][1],
                             "failed": progress['auto'][2],
                             "unknown": progress['auto'][3],
                             "percent": percent+'%',
                             "time": time
         }
    )

    percent = format(((progress['hand'][1]+progress['hand'][2]) / progress['hand'][0]) * 100, '.2f') if progress['hand'][0] > 0 else '0'
    excute_list["rows"].append(
        {"category": 'Hand-Cases', "passed": progress['hand'][1],
         "failed": progress['hand'][2],
         "unknown": progress['hand'][3],
         "percent": percent + '%',
         "time": time
         }
    )

    percent = format(((progress['total'][1]+progress['total'][2]) / progress['total'][0]) * 100, '.2f') if progress['total'][0] > 0 else '0'
    excute_list["rows"].append(
        {"category": 'Total', "passed": progress['total'][1],
         "failed": progress['total'][2],
         "unknown": progress['total'][3],
         "percent": percent + '%',
         "time": time
         }
    )

    return excute_list

def get_userexcinfo(key, method):
    """
    Get Users' execution info.
    :param key:
    :param method:
    :return:
    """
    app = current_app._get_current_object()
    pname = get_projectnamefromkey(key)
    users = app.config['DB'].get_projectusers(pname)

    excute_list = {"total": 0, "rows": []}

    for u in users:
        sql = '''SELECT count(*) from loginfo 
                 WHERE user='{}' and target='case' and action='create' 
                 and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (createcase,) = res.fetchone()

        sql = '''SELECT count(*) from loginfo 
                         WHERE user='{}' and target='case' 
                         and (action='run' OR action='hand' OR action='debug') 
                         and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (excutecase,) = res.fetchone()

        sql = '''SELECT count(*) from loginfo 
                                 WHERE user='{}' and target='suite' 
                                 and (action='create' OR action='copy') 
                                 and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (createsuite,) = res.fetchone()

        sql = '''SELECT count(*) from loginfo 
                                         WHERE user='{}' and target='suite' 
                                         and action='run'
                                         and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (excutesuite,) = res.fetchone()

        sql = '''SELECT count(*) from loginfo 
                                         WHERE user='{}' and target='suite' 
                                         and (action='edit' OR action='rename') 
                                         and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (editsuite,) = res.fetchone()

        sql = '''SELECT count(*) from loginfo 
                                         WHERE user='{}' and target='suite' 
                                         and action='delete'
                                         and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (deletesuite,) = res.fetchone()

        sql = '''SELECT min(logtime), max(logtime) from loginfo 
                                         WHERE user='{}' 
                                         and logtime > datetime('now','localtime','-1 day'); '''.format(u)
        res = app.config['DB'].runsql(sql)
        (start,end) = res.fetchone()

        usetime = start + ' - ' + end if (start and end) else "None - None"

        excute_list["rows"].append(
            {
                "createcase": createcase, "excutecase": excutecase,
                "createsuite":createsuite,"excutesuite":excutesuite,
                "editsuite":  editsuite, "deletesuite":deletesuite,
                "usetime": usetime, "username":u
            }
        )

    return excute_list

def get_distinct_suites(key):
    """
    Get num of suites.
    :param key: dir
    :return: files
    """
    app = current_app._get_current_object()
    log.info("Get distinct keys for {}".format(key))
    sql = '''SELECT count( DISTINCT info_key )FROM testcase where info_key like '{}%' ;'''.format(key)
    res = app.config['DB'].runsql(sql)
    (suites,) = res.fetchone()
    return suites


def rpt_caseratio(dir):
    """
    Count cases of total, hand-cases,auto-cases
    :param dir: dir
    :return: （total，hand-cases，auto-cases）
    """

    app = current_app._get_current_object()
    sql = '''SELECT info_tags,info_name FROM testcase where info_key like '{}%'; '''.format(dir)
    res = app.config['DB'].runsql(sql)

    total = 0
    hand = 0
    for t in res:
        (tag, name) = t
        total += 1
        tags = tag.split(',')
        if "HAND" in tags or 'Hand' in tags or 'hand' in tags:
            hand += 1
    return (total, hand, total - hand)

def rpt_runprogress(dir, method=''):
    """
    统计执行进度：总用例数，pass fail，手工用例数，pass fail，自动化用例数 pass fail
    Calculate progress of execution: Total cases, pass and fail, hand-cases, auto-cases ,their pass-fail.
    :param dir: dir
    :return:
    """

    app = current_app._get_current_object()

    if method == 'day':
        period = '-24 hours'
        sql = '''SELECT info_tags,info_name, run_status FROM testcase 
                 WHERE info_key LIKE '{}%' and ontime > datetime('now','localtime', '{}'); '''.format(dir, period)

    elif method == 'week':
        period = '-7 days'
        sql = '''SELECT info_tags,info_name, run_status FROM testcase 
                         WHERE info_key LIKE '{}%' and ontime > datetime('now','localtime', '{}'); '''.format(dir, period)
    else:
        sql = '''SELECT info_tags,info_name, run_status FROM testcase 
                     WHERE info_key LIKE '{}%'; '''.format(dir)


    res = app.config['DB'].runsql(sql)

    total = 0
    hand = 0
    auto = 0

    totalpass = 0
    totalfail = 0
    handpass  = 0
    handfail  = 0
    autopass  = 0
    autofail  = 0
    for t in res:
        (tag, name, status) = t
        total += 1
        tags = tag.split(',')
        if "HAND" in tags or 'Hand' in tags or 'hand' in tags:
            hand += 1
            if status == 'PASS':
                handpass += 1
            if status == 'FAIL':
                handfail += 1
        else:
            auto +=1
            if status == 'PASS':
                autopass += 1
            if status == 'FAIL':
                autofail += 1

        if status == 'PASS':
            totalpass += 1
        if status == 'FAIL':
            totalfail += 1

    runprogress = {"total":[total,totalpass,totalfail,total-(totalpass + totalfail)],
                   "hand": [hand, handpass, handfail, hand -(handpass +  handfail)],
                   "auto": [auto, autopass, autofail, auto -(autopass +  autofail)]}

    return runprogress

def rpt_moduleprogress(dir):
    """
    统计 模块执行进度 自动认为 listdir（dir）为子模块
    Calculate Modules(Subdir)'s execution progress
    :param dir:Dir
    :return:
    """
    app = current_app._get_current_object()
    result = {}

    if not os.path.isdir(dir):
        return result

    modules = []
    passed  = []
    failed  = []
    unknown = []
    for d in os.listdir(dir):
        key = os.path.join(dir,d)
        progress = rpt_runprogress(key)
        if progress['total'][0] == 0:   # Omite dir or file that do not contain cases
            continue
        modules.append(d)
        passed.append(progress['total'][1])
        failed.append(progress['total'][2])
        unknown.append(progress['total'][3])

    result = {'modules':modules, 'passed':passed, 'failed':failed, 'unknown':unknown}

    return result

def rpt_moduleinfo(dir):
    """
    统计 模块用例统计 自动认为 listdir（dir）为子模块
    Calculate modules(subdir)'s cases info
    :param dir:
    :return:
    """
    app = current_app._get_current_object()
    result = {}

    if not os.path.isdir(dir):
        return result

    modules = []
    autocases  = []
    handcases  = []
    for d in os.listdir(dir):
        key = os.path.join(dir,d)
        (total,hand,auto) = rpt_caseratio(key)
        modules.append(d)
        autocases.append(auto)
        handcases.append(hand)


    result = {'modules':modules, 'auto':autocases, 'hand':handcases}

    return result

def get_caselist(key , method=''):
    """
    取得用例列表
    Get Cases List
    :param key:
    :param method:
    :return:
    """
    app = current_app._get_current_object()
    case = []

    icons = {
        "unknown": url_for('static', filename='img/unknown.png'),
        "success": url_for('static', filename='img/success.png'),
        "fail": url_for('static', filename='img/fail.png'),
        "exception": url_for('static', filename='img/exception.png')}

    sql = '''SELECT run_status, 
                    info_name, 
                    info_doc, 
                    info_tags, 
                    rcd_runtimes,
                    run_elapsedtime,
                    run_user,
                    info_key
             FROM testcase where info_key like '{}%' ;'''.format(key)
    res = app.config['DB'].runsql(sql)

    for r in res:
        (run_status,
         info_name,
         info_doc,
         info_tags,
         rcd_runtimes,
         run_elapsedtime,
         run_user,
         info_key) = r

        if run_status == 'PASS':
            status = icons['success']
        elif run_status == 'FAIL':
            status = icons['fail']
        else:
            status = icons['unknown']

        case.append({
            "task_no": info_key+':'+info_name,
            "run_status": status,
            "info_name": info_name,
            "info_doc": info_doc,
            "info_tags": info_tags,
            "rcd_runtimes": rcd_runtimes,
            "run_elapsedtime": run_elapsedtime,
            "run_user": run_user,
            "info_key": info_key
        })

    return {"total": len(case), "rows": case}

def get_comparedata(key , method=''):
    """
    取得用例历史结果记录
    Get Cases List
    :param key:
    :param method:
    :return:
    """
    app = current_app._get_current_object()
    case = []

    icons = {
        "unknown": url_for('static', filename='img/unknown.png'),
        "success": url_for('static', filename='img/success.png'),
        "fail": url_for('static', filename='img/fail.png'),
        "exception": url_for('static', filename='img/exception.png')}

    sql = '''SELECT info_name, info_testproject, info_projectversion, ontime, run_status,run_elapsedtime,run_user,info_key
             FROM caserecord where info_key like '{}%' ORDER by info_name, ontime desc ;'''.format(key)
    res = app.config['DB'].runsql(sql)

    for r in res:
        (info_name, info_testproject, info_projectversion, ontime, run_status,run_elapsedtime,run_user,info_key) = r

        case.append({
            "info_name": info_name,
            "info_testproject": info_testproject,
            "info_projectversion": info_projectversion,
            "ontime": ontime,
            "run_status": run_status,
            "run_elapsedtime": run_elapsedtime,
            "run_user": run_user,
            "info_key": info_key
        })

    return {"total": len(case), "rows": case}