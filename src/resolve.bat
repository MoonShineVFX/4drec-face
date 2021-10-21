@echo off
set PYTHONPATH=%~dp0;%PYTHONPATH%
set PATH=%~dp0;%PATH%
set agisoft_LICENSE=G:\app
cd /d %~dp0\resolve
%~dp0\.python\python -u %~dp0\resolve\launch.py %*
