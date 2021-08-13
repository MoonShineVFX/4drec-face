@echo off
SET CUEBOT_HOSTS=192.168.29.10
SET http_proxy=
SET https_proxy=
set LOGURU_LEVEL=INFO
set PYTHONPATH=%~dp0;%PYTHONPATH%
set PATH=%~dp0;%PATH%
cd /d %~dp0\capture
%~dp0\.python\python -u %~dp0\capture\main.py %*
if NOT ["%errorlevel%"]==["0"] pause