# -*- coding: utf-8 -*-

__author__ = "mawentao119@gmail.com"

"""
This module is not be used for now.
But translate it still.
"""

# coding=utf-8
import os
import time
basedir = os.getcwd()
filelists = []

# accumulated file types.
whitelist = ['py', 'js']

filelists = []


# find all files.
def get_file(base_dir):
    for parent, dirnames, filenames in os.walk(basedir):
        for filename in filenames:
            if filename in ("AutoStats.py", "commonLibrary.py"):
                continue

            ext = filename.split('.')[-1]
            if ext == "js" and filename != "auto.js":
                continue

            # only for specific file types.
            if ext in whitelist:
                filelists.append(os.path.join(parent, filename))


# Count lines of a file.
def count_line(fname):
    count = 0
    for file_line in open(fname).readlines():
        # omit NULL lines
        if file_line != '' and file_line != '\n':
            count += 1
    print('%s ---- %s' % (fname, count))
    return count


if __name__ == '__main__' :
    startTime = time.clock()
    get_file(basedir)
    totalline = 0
    for filelist in filelists:
        totalline = totalline + count_line(filelist)

    print('total lines: %s' % totalline)
    print('Done! Cost Time: %0.2f second' % (time.clock() - startTime))