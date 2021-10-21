import argparse
from typing import Optional, Callable, Any
import json
import logging
import sys
from define import ResolveStage, ResolveEvent


OnEventCall = Callable[[ResolveEvent, Optional[Any]], None]


class LoggingEventHandler(logging.StreamHandler):
    def __init__(self, on_event: OnEventCall = None):
        super(LoggingEventHandler, self).__init__()
        self.__on_event = on_event
        self.__stdout = sys.stdout
        sys.stdout = self

    def write(self, message: str):
        if message != '\n':
            self.__on_event(ResolveEvent.LOG_STDOUT, message)
        return

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if hasattr(record, 'resolve_state'):
                if record.resolve_state == 'COMPLETE':
                    self.__on_event(ResolveEvent.COMPLETE)
                    return
                elif record.resolve_state == 'PROGRESS':
                    self.__on_event(ResolveEvent.PROGRESS, record.progress)
            if record.levelname in ('INFO', 'DEBUG'):
                self.__on_event(ResolveEvent.LOG_INFO, record.message)
            elif record.levelname == 'WARNING':
                self.__on_event(ResolveEvent.LOG_WARNING, record.message)
            elif record.levelname in ('CRITICAL', 'ERROR'):
                self.__on_event(ResolveEvent.FAIL, record.message)
        except:
            self.handleError(record)


def launch(current_frame: int,
           resolve_stage: ResolveStage,
           yaml_path: Optional[str] = None,
           extra_settings: Optional[dict] = None,
           debug: bool = False,
           on_event: Optional[OnEventCall] = None):
    # Set logging
    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging_level
    )

    # Add Event if assign
    if on_event is not None:
        event_handler = LoggingEventHandler()
        logging.getLogger().addHandler(event_handler)

    # launch
    from settings import SETTINGS
    from project import ResolveProject

    SETTINGS.initialize(
        current_frame,
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
