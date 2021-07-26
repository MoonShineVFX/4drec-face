import argparse
from typing import Optional
import json

from define import ResolveStage


def launch(current_frame: int,
           resolve_stage: ResolveStage,
           yaml_path: Optional[str] = None,
           extra_settings: Optional[dict] = None):
    from settings import SETTINGS
    from project import ResolveProject

    SETTINGS.initialize(
        current_frame, resolve_stage, yaml_path, extra_settings
    )
    project = ResolveProject()
    project.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Frame
    parser.add_argument(
        '-f', '--frame', type=int,
        help='Frame number to resolve',
        default=-1
    )
    # Stage
    parser.add_argument(
        '-s', '--resolve_stage', type=ResolveStage,
        help='Resolve steps to process',
        choices=list(ResolveStage),
        required=True
    )
    # Yaml
    parser.add_argument(
        '-l', '--yaml_path', type=str,
        help='Yaml setting path'
    )
    # Extra
    parser.add_argument(
        '-e', '--extra_settings', type=json.loads,
        help='Extra settings, json string format'
    )

    options = parser.parse_args()

    # launch
    launch(
        options.frame,
        options.resolve_stage,
        options.yaml_path,
        options.extra_settings
    )
