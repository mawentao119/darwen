#!/usr/bin/env bash

## Description: Online install Python-3 and uniRobot platform
## Author: charisma 20191130
## Important: This installation will install system to ${uniHome}=/data/uniRobot . NO NEED RUN OnlineInstallRobots.sh

echo "### Stage 0 : Copy file ..."

echo "*** Delete tmp dir and  work dir ...... "

tmpdir="/tmp/uniRobot1234"
workdir="/data/uniRobot"

rm -rf ${tmpdir}
mkdir  ${tmpdir}
rm -rf ${workdir}
mkdir  ${workdir}

echo "*** Copy offlinePackages to ${workdir} "
cp -R * ${tmpdir}/
mv ${tmpdir}/offlinePackages ${workdir}/
mv ${tmpdir}/start_work.sh ${workdir}/

cd ${workdir}

### Stage 1 : install python3
##Just for TBDS TEST:
if [ -f "/etc/yum.repos.d/TBDS.repo" ];then
    cp /etc/yum.repos.d/TBDS.repo /etc/yum.repos.d/backup
    cp /etc/yum.repos.d/backup/*.repo /etc/yum.repos.d/
fi
##
echo "**$0** Check Python version ..."
ver=`python3 -V|awk '{print $2}' `
if [[ "x$ver" < "x3.7.5" ]];then
    echo "Python is < 3.7.5 , Will install Python3.8.0 ..."
    yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel libffi-devel gcc make

    # wget https://www.python.org/ftp/python/3.7.5/Python-3.7.5.tgz
    # wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz

    tar -zxvf offlinePackages/Python-3.8.0.tgz
    cd Python-3.8.0
       ./configure
       make&&make install
    cd ../
    rm -rf Python-3.8.0
    echo "**$0** Finished install Python3.8.0 "
fi
##Just for TBDS TEST:
if [ -f "/etc/yum.repos.d/TBDS.repo" ];then
    mv /etc/yum.repos.d/*.repo /etc/yum.repos.d/backup/
    cp /etc/yum.repos.d/backup/TBDS.repo /etc/yum.repos.d/
fi
##

cd ${workdir}
echo "### Stage 2 : install python module virtualenv"
echo "**$0** Install virtualenv ..."
python3 -m pip install virtualenv
isok=`python3 -m virtualenv --help `
if [ $? -ne 0 ]
then
   echo "**$0**ERROR: Install virtualenv FAILED !! EXIT !"
   exit 1
fi
echo "**$0** Install virtualenv OK !"

echo "### Stage 3 : Install Robot* test system"

pyenv="py3env"

echo "*** python3 -m virtualenv --no-site-packages /data/uniRobot/py3env"
python3 -m virtualenv --no-site-packages ${pyenv}
echo "export PYENV=${pyenv}">>${pyenv}/bin/activate;
echo "export uniHome=${uniHome}">>${pyenv}/bin/activate;
echo "export LANG=zh_CN.UTF8">>${pyenv}/bin/activate;
source ${pyenv}/bin/activate

echo "### Stage 4 : install requirments "

cd ${workdir}

srcdir="work/workspace/Admin/uniRobot"
mkdir -p ${srcdir}
mkdir -p work/DBs
mkdir -p work/jobs
mkdir -p work/logs
mkdir -p work/runtime
echo "*** Copy ${tmpdir} files to ${srcdir} ..."
cp -R ${tmpdir}/* ${srcdir}/

echo "*** Install requirements ..."
pip install -r ${srcdir}/requirements.txt

    cd offlinePackages
        unzip taurus.zip
        cd taurus
        echo "*** Install taurus ..."
        python setup.py install
    cd ${workdir}

echo "### Install Finished , Starting ... "
chmod +x *.sh
nohup ./start_work.sh   &

echo "******* Please Try : http://${PORTAL}:8082/... \n"
####### IF NEEDED: Nginx proxy ###################################
##nginxconf='/etc/nginx/conf.d/default.conf'
##echo "*** Check nginx default config ..."
##if [ ! -f ${nginxconf} ]; then
##    echo "*** ERROR: Cannot Find nginx default config file ${nginxconf}!"
##    exit 1
##fi
##added=`grep 'uniRobot' ${nginxconf} `
##if [ "x$added" = "x" ];then
##    echo "cat nginxsub.conf to ${nginxconf}"
##    cat ${uniHome}/uniWeb/nginxsub.conf >> ${nginxconf}
##    echo "### uniRobot added ###" >> ${nginxconf}
##fi
##
##echo "*** reload nginx config ...."
##nginx -s reload
##cd ${uniHome}/uniWeb
##    ./start_uwsgi.sh
##
##echo "******* Please Try : http://${PORTAL}/tbdstest ... \n"
############### IF NEEDED: TODO #####################
##echo "*** Try to install Google-chrome For UI test ..."
##
## rpm -ivh offlinePackages/google-chrome/liberation-fonts-common-1.07.2-16.el7.noarch.rpm
## rpm -ivh offlinePackages/google-chrome/liberation-narrow-fonts-1.07.2-16.el7.noarch.rpm
## rpm -ivh offlinePackages/google-chrome/liberation-sans-fonts-1.07.2-16.el7.noarch.rpm
## rpm -ivh offlinePackages/google-chrome/liberation-serif-fonts-1.07.2-16.el7.noarch.rpm
## rpm -ivh offlinePackages/google-chrome/liberation-mono-fonts-1.07.2-16.el7.noarch.rpm
## rpm -ivh offlinePackages/google-chrome/liberation-fonts-1.07.2-16.el7.noarch.rpm
##
##chmod +x offlinePackages/google-chrome/install-google-chrome.sh
##bash offlinePackages/google-chrome/install-google-chrome.sh
##
##echo "*** Test google-chrome ....."
##google-chrome-stable --no-sandbox --headless --disable-gpu --screenshot https://www.baidu.com/
##if [ ! -f "screenshot.png" ];then
##    echo "*** Maybe: google-chrome-stable install Failed, You may check it by yourself ...."
##    sleep 3
##fi

