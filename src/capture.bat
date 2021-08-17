@echo off

set CUEBOT_HOSTS=192.168.29.10
set http_proxy=
set https_proxy=
set LOGURU_LEVEL=DEBUG
set PYTHONPATH=%~dp0;%PYTHONPATH%
set PATH=%~dp0;%PATH%

cd /d %~dp0\capture

:EXEC
%~dp0\.python\python -u %~dp0\capture\main.py %*

if not ["%errorlevel%"]==["4813"] goto LEAVE

:RESTART
echo.
echo.
echo.
echo "============ RESTART in 5 secs ============"
echo.
echo.
echo.
ping 127.0.0.1 -n 5 > nul
goto EXEC

:LEAVE
if NOT ["%errorlevel%"]==["0"] pause
