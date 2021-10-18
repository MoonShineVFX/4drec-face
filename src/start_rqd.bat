@echo off

REM Add rqd.conf for personal setting
set output_folder=%LOCALAPPDATA%\OpenCue
if not exist "%output_folder%" mkdir %output_folder%
set output_file=%output_folder%\rqd.conf
echo [Override]> %output_file%
echo OVERRIDE_HOSTNAME = %COMPUTERNAME%>> %output_file%

REM Launch rqd
set PYTHONPATH=%~dp0;%PYTHONPATH%
set PATH=%~dp0;%PATH%
SET CUEBOT_HOSTNAME=192.168.29.10
SET http_proxy=
SET https_proxy=
%~dp0\.python\python -c "import sys; sys.argv = []; from rqd.__main__ import main; main()"

if NOT ["%errorlevel%"]==["0"] pause
REM Set thread-mode: cue cueadmin -host 4D-USR -thread all
