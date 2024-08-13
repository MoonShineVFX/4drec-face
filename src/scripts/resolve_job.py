from launch import launch
from define import ResolveStage

yaml_path = r"G:/submit/hb/shots/shot_27/jobs/resolve_2/job.yml"

launch(
    500,
    ResolveStage.RESOLVE,
    yaml_path,
    debug=True,
)
