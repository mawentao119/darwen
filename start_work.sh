#!/usr/bin/env bash

echo "*** Source py3env/bin/activate ... "

source py3env/bin/activate

here=`pwd`

cd work/workspace/Admin/uniRobot

    python uniRobot.py runserver -h 0.0.0.0 -p 8082

cd ${here}

