@echo off
setlocal

REM Check if a parameter is passed (i.e., if a folder is dragged and dropped)
if "%~1"=="" (
    echo Please drag and drop a folder onto this batch file.
    pause
    exit /b
)

REM Get the path of the dragged and dropped folder
set "SourceDir=%~1"

REM Get the parent path of the source folder
for %%I in ("%SourceDir%") do set "ParentDir=%%~dpI"

REM Target folder name
set "TargetDirName=drc"

REM Target folder path
set "TargetDir=%ParentDir%%TargetDirName%"

REM Create the target folder if it doesn't exist
if not exist "%TargetDir%" mkdir "%TargetDir%"

REM Iterate through all files in the source folder and convert them
for /r "%SourceDir%" %%i in (*) do (
    if "%%~dpi" neq "%TargetDir%\" (
        draco_encoder -i "%%i" -o "%TargetDir%\%%~ni.drc"
    )
)

echo Conversion completed!
pause
endlocal
