#!/usr/bin/env bash

echo "*** Source py3env/bin/activate ... "

source py3env/bin/activate

here=`pwd`

cd work/workspace/Admin/darwen

  nohup   python darwen.py runserver -h 0.0.0.0 -p 8082  &

cd ${here}

echo "*** Start finished ... "
