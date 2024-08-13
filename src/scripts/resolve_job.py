from launch import launch
from define import ResolveStage

yaml_path = r"G:\submit\hb\shots\shot_10\jobs\resolve_1\job.yml"

launch(
    0,
    ResolveStage.RESOLVE,
    yaml_path,
    debug=True,
)
