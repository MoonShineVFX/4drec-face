conda env config vars set CUEBOT_HOSTS=192.168.1.65 &^
conda env config vars set OL_CONFIG=%~dp0capture\utility\opencue_bridge\outline.cfg &^
conda activate %CONDA_PREFIX% &^
conda install -c conda-forge py-lz4framed
pip install -r requirements.txt
