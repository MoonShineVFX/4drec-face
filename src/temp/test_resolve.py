from resolve.launch import launch
from resolve.define import ResolveStage
from pathlib import Path


yaml_path = r'G:\jobs\4cdd8d\02e2e0\564bf8\job.yml'


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
resolve_frame(0)
