from resolve.launch import launch
from resolve.define import ResolveStage
from pathlib import Path


yaml_path = Path('test_resolve.yml').absolute()


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

resolve_frame(1)
