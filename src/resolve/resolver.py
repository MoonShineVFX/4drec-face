import logging

from define import ResolveStage
from settings import SETTINGS


class Resolver:
    def __init__(self):
        self.__progress = 0.0

        # Check settings
        if not SETTINGS.is_initialized:
            error_message = "Settings didn't initialized"
            logging.critical(error_message)
            raise ValueError(error_message)

    def run(self):
        # Main
        if SETTINGS.resolve_stage is ResolveStage.INITIALIZE:
            logging.info("Project run: INITIAL")
            from processors.metashape import MetashapeResolver

            metashape_resolver = MetashapeResolver(self.__logging_progress)
            metashape_resolver.initialize()
            metashape_resolver.calibrate()
        elif SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            logging.info("Project run: RESOLVE")
            from processors.metashape import MetashapeResolver

            metashape_resolver = MetashapeResolver(self.__logging_progress)
            metashape_resolver.resolve()
        elif SETTINGS.resolve_stage is ResolveStage.CONVERSION:
            logging.info("Project run: CONVERSION")
            from processors.conversion import Conversion

            Conversion.convert_glb()
            Conversion.convert_draco()
            Conversion.convert_texture()
        elif SETTINGS.resolve_stage is ResolveStage.EXPORT:
            logging.info("Project run: EXPORT")
            from processors.conversion import Conversion

            Conversion.convert_audio()
            Conversion.export_fourdrec_roll()
        else:
            error_message = (
                f"ResolveStage {SETTINGS.resolve_stage} not implemented"
            )
            logging.critical(error_message)
            raise ValueError(error_message)

        logging.info("Finish", extra={"resolve_state": "COMPLETE"})

    def __logging_progress(self, progress_step: float, message: str):
        self.__progress += progress_step
        logging.info(
            message,
            extra={"resolve_state": "PROGRESS", "progress": self.__progress},
        )
