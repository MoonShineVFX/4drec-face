import logging

from define import ResolveStage
from settings import SETTINGS
from common.cloud_bridge import CloudBridge


class Resolver:
    def __init__(self):
        self.__progress = 0.0

        # Check settings
        if not SETTINGS.is_initialized:
            error_message = "Settings didn't initialized"
            logging.critical(error_message)
            raise ValueError(error_message)

    def run(self):
        cloud_bridge = self.__get_cloud_bridge()
        try:
            if SETTINGS.resolve_stage is ResolveStage.INITIALIZE:
                logging.info("Project run: INITIAL")
                cloud_bridge.update_job("RUNNING")
                from processors.metashape import MetashapeResolver

                metashape_resolver = MetashapeResolver(self.__logging_progress)
                metashape_resolver.initialize()
                metashape_resolver.calibrate()
            elif SETTINGS.resolve_stage is ResolveStage.RESOLVE:
                logging.info("Project run: RESOLVE")
                cloud_bridge.update_frame("RUNNING")
                from processors.metashape import MetashapeResolver

                metashape_resolver = MetashapeResolver(self.__logging_progress)
                resolve_file_path = metashape_resolver.resolve()

                cloud_bridge.update_frame("RESOLVED", resolve_file_path)
            elif SETTINGS.resolve_stage is ResolveStage.CONVERSION:
                logging.info("Project run: CONVERSION")
                from processors.conversion import Conversion

                Conversion.convert_glb()
                Conversion.convert_draco()
                Conversion.convert_texture()

                cloud_bridge.update_frame("CONVERTED")
            elif SETTINGS.resolve_stage is ResolveStage.EXPORT:
                logging.info("Project run: EXPORT")
                from processors.conversion import Conversion

                Conversion.convert_audio()
                export_file_path = Conversion.export_fourdrec_roll()

                cloud_bridge.update_job("COMPLETED", export_file_path)
            elif SETTINGS.resolve_stage is ResolveStage.EXPORT_ALEMBIC:
                logging.info("Project run: EXPORT_ALEMBIC")
                from processors.export_abc import AlembicExporter
                import re

                # Get file name
                folder_name = f"{SETTINGS.project_name}_{SETTINGS.shot_name}"
                folder_name = re.sub(r"[^\w\d-]", "_", folder_name)

                AlembicExporter.export(
                    output_path=str(SETTINGS.output_path),
                    start_frame=0,
                    end_frame=SETTINGS.end_frame - SETTINGS.start_frame,
                    export_path=str(SETTINGS.export_path / folder_name),
                    on_progress=self.__logging_progress,
                )
            else:
                raise ValueError(
                    f"ResolveStage {SETTINGS.resolve_stage} not implemented"
                )
        except Exception as e:
            # Cloud sync
            if (
                SETTINGS.resolve_stage is ResolveStage.INITIALIZE
                or SETTINGS.resolve_stage is ResolveStage.EXPORT
            ):
                cloud_bridge.update_job("FAILED")
            elif (
                SETTINGS.resolve_stage is ResolveStage.RESOLVE
                or SETTINGS.resolve_stage is ResolveStage.CONVERSION
            ):
                cloud_bridge.update_frame("FAILED")

            logging.critical(f"Error: {e}", exc_info=True)
            raise e

        logging.info("Finish", extra={"resolve_state": "COMPLETE"})

    @staticmethod
    def __get_cloud_bridge():
        return CloudBridge(
            SETTINGS.project_id,
            SETTINGS.project_name,
            SETTINGS.shot_id,
            SETTINGS.shot_name,
            SETTINGS.job_id,
            SETTINGS.job_name,
            SETTINGS.end_frame - SETTINGS.start_frame + 1,
            SETTINGS.output_frame_number,
            SETTINGS.no_cloud_sync,
        )

    def __logging_progress(self, progress_step: float, message: str):
        self.__progress += progress_step
        logging.info(
            message,
            extra={"resolve_state": "PROGRESS", "progress": self.__progress},
        )
