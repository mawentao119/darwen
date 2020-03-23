# logging_example.py

import os
from utils.file import remove_dir, copy_file, get_projectdirfromkey, get_projectnamefromkey
from utils.mylogger import getlogger

log = getlogger("Clear")

def clear_projectres(project, key=''):

    prj = project
    if not key == '':
        prj = get_projectnamefromkey(key)


    log.info("Clear keyword of project:"+prj)
    cwd = os.getcwd() + "/keyword/" + prj
    try:
        remove_dir(cwd)
    except FileNotFoundError:
        log.warning("Remove dir for project Failed:"+cwd)

    jsd = os.getcwd() + "/auto/www/static/js/" + prj
    log.info("Clear js file of project:"+prj)
    try:
        remove_dir(jsd)
    except FileNotFoundError:
        log.warning("Remove dir for project Failed:" + jsd)

if __name__ == "__main__":
    project = "RobotNew"
    clear_projectres(project)

