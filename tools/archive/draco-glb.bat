for %%I in (.) do set TargetDirName=%%~nxI_drc
if not exist "..\%TargetDirName%" mkdir ..\%TargetDirName%
for /r %%i in (*) do draco_transcoder -i %%i -o ..\%TargetDirName%\%%~ni.glb
