from resolve.launch import launch
from resolve.define import ResolveStage


yaml_path = r'G:/jobs/9e9802/1ab2a5/f2fc8b/job.yml'


def initial():
    launch(
        -1,
        ResolveStage.INITIALIZE,
        str(yaml_path),
        debug=True
    )


def resolve_frame(frame: int):
    launch(
        frame,
        ResolveStage.RESOLVE,
        str(yaml_path),
        debug=True
    )


# initial()
resolve_frame(2)

