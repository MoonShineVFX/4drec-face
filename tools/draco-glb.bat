if not exist "..\gltf_mini_drc" mkdir ..\gltf_mini_drc
for /r %%i in (*) do draco_transcoder -i %%i -o ..\gltf_mini_drc\%%~ni.glb
