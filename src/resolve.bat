@echo off
set PYTHONPATH=%~dp0;%PYTHONPATH%
set PATH=%~dp0;%PATH%
set agisoft_LICENSE=G:\app
cd /d %~dp0\resolve
%~dp0\.python\python -u %~dp0\resolve\launch.py %*
set python_return_code=%ERRORLEVEL%

@REM If return code is 3221225477(-1073741819), set to 0
if %python_return_code% == -1073741819 (
    @echo on
    echo error level adjust
    @echo off
    EXIT /B 0
)

EXIT /B %python_return_code%
