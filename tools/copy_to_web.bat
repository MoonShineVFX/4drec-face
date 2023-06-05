@ECHO OFF

REM Check if any folders are dragged onto the script
if "%~1"=="" (
    echo Error: No folders dragged onto the script.
    pause
    exit /b 1
)

REM Main
setlocal enabledelayedexpansion
for %%A in (%*) do (
    set "source_folder=%%A"
    set "web_folder=%%A\..\..\web\%%~nxA"

    @ECHO ^>^> Convert %%A

    REM Create web_folder if it doesn't exist
    if not exist "!web_folder!" (
        mkdir "!web_folder!"
    )

    REM Call a subroutine to avoid issues with variable expansion
    call :ProcessFolder "!source_folder!" "!web_folder!"
)
endlocal

@ECHO ^>^> Done
pause
exit /b

:ProcessFolder
setlocal enabledelayedexpansion
set "source_folder=%~1"
set "web_folder=%~2"
set "frameCount=0"

REM Get frame count
for /r "%source_folder%\gltf" %%f in (*) do (
    set /a frameCount+=1
)
set /a frameCount-=1

@ECHO ^>^> Create metadata.yaml
echo.
(
  echo ^{
  echo   "hires": true,
  echo   "endFrame": !frameCount!,
  echo   "meshFrameOffset": -1,
  echo   "modelPositionOffset": [0, 0.05, 0]
  echo ^}
) > "%web_folder%\metadata.json"

@ECHO ^>^> Copy hires
robocopy "%source_folder%\gltf" "%web_folder%\hires" /E /MT /NP /NDL /NJH /NJS /BYTES /XJ /W:1 /ETA

@ECHO ^>^> Copy mesh
robocopy "%source_folder%\gltf_mini_drc" "%web_folder%\mesh" /E /MT /NP /NDL /NJH /NJS /BYTES /XJ /W:1 /ETA

@ECHO ^>^> Copy texture.mp4
copy "%source_folder%\texture.mp4" "%web_folder%\texture.mp4" > nul

endlocal
exit /b