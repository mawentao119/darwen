# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""
Model based test design
"""

import json
from utils.mylogger import getlogger

log = getlogger('Utils.Model_Design')


def walk_model(startnode):
    links = []
    casenum = 1

    def find_paths(node):
        nonlocal links
        nonlocal casenum
        if node["outlinks"] == []:
            output_path(links, casenum)
            casenum += 1
            links.remove(links[-1]) if len(links) > 0 else None
            return
        for l in node["outlinks"]:
            links.append(l)
            find_paths(l["end"])
        links.remove(links[-1]) if len(links) > 0 else None

    return find_paths(startnode)


def output_path(ps, casenum):

    if len(ps) == 0:
        log.error("路径为空，请检查模型文件")
        return

    casename = ''
    line = ''

    for p in ps:
        casename += '_' + str(p.get("key"))
        line += '>' + p.get("text") + ":" + p.get("end").get("text")

    print("T" + str(casenum) + casename)
    print("    [用例描述]{}".format(line))

    for p in ps:
        print("    Act:{}[{}] {}".format(p.get("text"), p.get(
            "parameters"), "#"+p.get("description") if p.get("description") else ''))
        print("    Chk:{}[{}] {}".format(p.get("end").get("text"), p.get("end").get(
            "properties"), "#"+p.get("end").get("description") if p.get("end").get("description") else ''))
    print("\n")


def gen_modelpath(jsonfile):

    mod = json.load(open(jsonfile, encoding='utf-8'))

    startnode = None

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

        if node["id"] == -1:
            startnode = node

    walk_model(startnode) if startnode else log.error(
        "找不到Start节点（id为-1）,文件：{}".format(jsonfile))

    return mod


def gen_casetemplate(model_file, output_file):
    return {"status": "success", "msg": "生成用例模版成功：."}


if __name__ == '__main__':
    mod = gen_modelpath(
        "/Users/tester/PycharmProjects/darwen/work/workspace/Admin/Demo_Project/TestDesign/UserManagement.tmd")
    # print(mod)
