import yaml

from launch import launch
from define import ResolveStage

yaml_path = r"G:\submit\0722_wen\shots\shot_4\jobs\resolve_8\job.yml"
with open(yaml_path, "r") as f:
    yaml_settings = yaml.load(f, Loader=yaml.FullLoader)

yaml_settings.update(
    {
        "job_name": "custom",
        "job_path": r"C:\Users\eli.hung\Desktop\test_shot4",
        "no_cloud_sync": True,
        "keep_temp_files": True,
    }
)

launch(
    0,
    ResolveStage.RESOLVE,
    extra_settings=yaml_settings,
    debug=True,
)
