# logging_example.py

import logging
import os
from datetime import datetime,date

"""Log Module of Project"""
def getlogger(name='loggerself',dir=''):
 
    starttime = date.strftime(datetime.now(),'%Y%m%d%H')

    path = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))) if dir == '' else dir
    LogFile = path + "/logs/" + "app_"+starttime+".log"

    os.mkdir(path + "/logs/") if not os.path.exists(path + "/logs/") else None

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(LogFile)
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger
