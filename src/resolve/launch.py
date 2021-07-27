import argparse
from typing import Optional
import json
import logging

from define import ResolveStage


def launch(current_frame: int,
           resolve_stage: ResolveStage,
           yaml_path: Optional[str] = None,
           extra_settings: Optional[dict] = None,
           debug: bool = False):
    # Set logging
    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging_level
    )

    # launch
    from settings import SETTINGS
    from project import ResolveProject

    SETTINGS.initialize(
        current_frame,
        # Redefined for preventing outside import
        ResolveStage(resolve_stage.value),
        yaml_path,
        extra_settings
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
    # Debug
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Show more detailed log'
    )

    options = parser.parse_args()

    # Call launch
    launch(
        options.frame,
        options.resolve_stage,
        options.yaml_path,
        options.extra_settings,
        options.debug
    )
