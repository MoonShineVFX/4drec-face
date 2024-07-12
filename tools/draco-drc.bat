for %%I in (.) do set TargetDirName=%%~nxI__drc
if not exist "..\%TargetDirName%" mkdir ..\%TargetDirName%
for /r %%i in (*) do draco_encoder -i %%i -o ..\%TargetDirName%\%%~ni.drc
