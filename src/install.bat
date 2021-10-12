conda env config vars set CUEBOT_HOSTS=192.168.29.10 &^
conda env config vars set OL_CONFIG=%~dp0capture\utility\opencue_bridge\outline.cfg &^
conda activate %CONDA_PREFIX% &^
conda install -c conda-forge py-lz4framed
pip install -r requirements.txt
@REM java -jar e:\cuebot\cuebot-0.14.5-all.jar --datasource.cue-data-source.jdbc-url=jdbc:postgresql://localhost/opencue --datasource.cue-data-source.username=opencue --datasource.cue-data-source.password=opencue_pass --log.frame-log-root="G:/opencue/logs" --history.archive_jobs_cutoff_hours=7200
