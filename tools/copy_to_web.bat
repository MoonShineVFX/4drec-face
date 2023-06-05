@ECHO OFF
setlocal enabledelayedexpansion

REM Check if any folders are dragged onto the script
if "%~1"=="" (
    echo Error: No folders dragged onto the script.
    pause
    exit /b 1
)

REM Loop through each dragged folder
for %%A in (%*) do (
    REM Main
    set "gltf_folder=%%A\gltf"
    set "web_folder=%%A\..\..\web\%%~nxA"
    set "frameCount=0"

    @ECHO ^>^> Convert %%A

    REM Get frame count
    for /r "%%A\gltf" %%f in (*) do (
        set /a frameCount+=1
    )
    set /a frameCount-=1

    REM Create web_folder if it doesn't exist
    if not exist "!web_folder!" (
        mkdir "!web_folder!"
    )

    @ECHO ^>^> Create metadata.yaml
    echo.
    (
      echo ^{
      echo   "hires": true,
      echo   "endFrame": !frameCount!,
      echo   "meshFrameOffset": -1,
      echo   "modelPositionOffset": [0, 0.05, 0]
      echo ^}
    ) > "!web_folder!\metadata.json"

    @ECHO ^>^> Copy hires
    robocopy "%%A\gltf" "!web_folder!\hires" /E /MT /NP /NDL /NJH /NJS /BYTES /XJ /W:1 /ETA

    @ECHO ^>^> Copy mesh
    robocopy "%%A\gltf_mini_drc" "!web_folder!\mesh" /E /MT /NP /NDL /NJH /NJS /BYTES /XJ /W:1 /ETA

    @ECHO ^>^> Copy texture.mp4
    copy "%%A\texture.mp4" "!web_folder!\texture.mp4" > nul
)

endlocal
@ECHO ^>^> Done
pause