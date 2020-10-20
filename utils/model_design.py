# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""
Model based test design
"""
import os
import time
import json
from utils.mylogger import getlogger

log = getlogger('Utils.Model_Design')


def walk_model(mod, method, output_file):

    startnode = None
    for node in mod["nodeDataArray"]:
        if node["id"] == -1:
            startnode = node
            break

    if (not startnode):
        log.error("找不到Start节点（id为-1）")
        return None

    links = []
    casenum = 1

    def find_paths(node):
        nonlocal links
        nonlocal casenum
        if node["outlinks"] == []:
            output_path(links, casenum, method, output_file)
            casenum += 1
            links.remove(links[-1]) if len(links) > 0 else None
            return
        for l in node["outlinks"]:
            links.append(l)
            find_paths(l["end"])
        links.remove(links[-1]) if len(links) > 0 else None

    return find_paths(startnode)


def output_path(ps, casenum, method, output_file):

    if len(ps) == 0:
        log.error("路径为空，请检查模型文件")
        return

    casename = ''
    line = ''

    for p in ps:
        casename += '_' + str(p.get("key"))
        line += '>' + p.get("text") + ":" + p.get("end").get("text")

    with open(output_file, 'a') as ff:
        ff.write("T" + str(casenum) + casename + '\n')

        if method == 'casetemplate':
            ff.write("    [用例描述]{} \n".format(line))
        else:
            ff.write("    [Documentation]    {}\n".format(line))

        if method == 'casetemplate':
            for p in ps:
                ff.write("    Do:{}[{}] {}\n".format(p.get("text"), p.get(
                    "parameters"), "#"+p.get("description") if p.get("description") else ''))
                ff.write("    Chk:{}[{}] {}\n".format(p.get("end").get("text"), p.get("end").get(
                    "properties"), "#"+p.get("end").get("description") if p.get("end").get("description") else ''))
        elif method == 'handcase':
            ff.write("    [Tags]    Hand\n")
            for p in ps:
                ff.write("    {}    [{}] {}\n".format(p.get("text"), p.get(
                    "parameters"), "#"+p.get("description") if p.get("description") else ''))
                ff.write("    检查结果    {}[{}] {}\n".format(p.get("end").get("text"), p.get("end").get(
                    "properties"), "#"+p.get("end").get("description") if p.get("end").get("description") else ''))
        else:   # 'autocase'
            ff.write("    [Tags]    Auto\n")
            for p in ps:
                ff.write("    {}    [{}] {}\n".format(p.get("text"), p.get(
                    "parameters"), "#"+p.get("description") if p.get("description") else ''))
                ff.write("    检查结果    {}[{}] {}\n".format(p.get("end").get("text"), p.get("end").get(
                    "properties"), "#"+p.get("end").get("description") if p.get("end").get("description") else ''))

        ff.write("\n")

    return


def gen_modelgraph(jsonfile):

    mod = json.load(open(jsonfile, encoding='utf-8'))

    # 让 link 的 end 指向 具体 node
    for link in mod["linkDataArray"]:
        link["end"] = None
        for node in mod["nodeDataArray"]:
            if link["to"] == node["id"]:
                link["end"] = node

    # 让 node 具有 outlinks
    for node in mod["nodeDataArray"]:
        node["outlinks"] = []
        for link in mod["linkDataArray"]:
            if link["from"] == node["id"]:
                node["outlinks"].append(link)

    log.info("完成模型数据图形化：{}".format(jsonfile))

    return mod


def gen_casefile(model_file, method, output_file):

    os.remove(output_file) if os.path.exists(output_file) else None

    mod = gen_modelgraph(model_file)

    with open(output_file, 'w') as ff:
        ff.write("# Generate time: {}\n".format(time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
        ff.write("\n*** Settings ***\n")
        ff.write("\n*** Varialbes ***\n")
        for v in mod["modelData"]["variable"]:
            ff.write("${"+v["name"]+"}    "+v["value"]+" # "+v["rule"]+"\n")
        ff.write("\n*** Test Cases ***\n")

    walk_model(mod, method, output_file)

    return {"status": "success", "msg": "生成文件：{}.".format(output_file)}


if __name__ == '__main__':
    mod = gen_modelgraph(
        "/Users/tester/PycharmProjects/darwen/work/workspace/Admin/Demo_Project/TestDesign/UserManagement.tmd")
    # print(mod)
