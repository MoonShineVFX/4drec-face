import os
import yaml
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from define import ResolveStage


# Default license path
if "agisoft_LICENSE" not in os.environ:
    logging.warning(
        'Env "agisoft_LICENSE" not found, using default install path instead'
    )
    os.environ["agisoft_LICENSE"] = "G:\\app\\"


class ResolveSettings:
    def __init__(self):
        self.is_initialized = False
        self.current_frame = -1
        self.resolve_stage: Optional[ResolveStage] = None

        # Version
        self.version = 1

        # Names
        self.metashape_project_name = "metashape_project"
        self.output_folder_name = "output"
        self.chunk_name = "MainChunk"
        self.archive_name = "cali_archive"
        self.temp_name = "fourd_temp"
        self.masks_name = "masks"
        self.project_name = ""
        self.shot_name = ""
        self.job_name = ""
        self.project_id = ""
        self.shot_id = ""
        self.job_id = ""

        # Camera
        self.sensor_pixel_width = 0.00345
        self.sensor_focal_length = 12

        # Parameters
        self.match_photos_interval = 5
        self.mesh_clean_faces_threshold = 10000
        self.smooth_model = 1.0
        self.texture_size = 8192
        self.region_size = [0.5, 0.5, 0.5]
        self.skip_masks = False

        # Normalize chunk transform
        self.nct_marker_locations = {}
        self.nct_center_offset = [0.0, -0.2, 0.3]

        # Job
        self.offset_frame = 0
        self.start_frame = 0
        self.end_frame = 0
        self.current_frame_real = -1
        self.current_frame_at_chunk = -1
        self.output_frame_number = 0
        self.cali_path = Path("")
        self.shot_path = Path("")
        self.job_path = Path("")
        self.created_at = None

        # More Paths
        self.project_path = Path("")
        self.files_path = Path("")
        self.output_path = Path("")
        self.archive_path = Path("")
        self.temp_path = Path("")
        self.temp_project_path = Path("")
        self.temp_masks_path = Path("")

        # Cloud bridge
        self.thumbnail_camera = "20087901"

    def initialize(
        self,
        current_frame: int,
        resolve_stage: ResolveStage,
        yaml_path: Optional[str] = None,
        extra_settings: Optional[dict] = None,
    ):
        logging.debug("Initialize")

        self.current_frame = current_frame
        self.resolve_stage = resolve_stage

        import_settings = {}
        # Import yaml
        if yaml_path is not None:
            logging.debug(f"Load yaml file: {yaml_path}")
            with open(yaml_path, "r") as f:
                import_settings.update(yaml.load(f, Loader=yaml.FullLoader))

            # Get created_at from yaml file
            self.created_at = datetime.fromtimestamp(
                Path(yaml_path).stat().st_ctime
            )

        # Import extra settings
        if extra_settings is not None:
            logging.debug(f"Load extra settings")
            import_settings.update(extra_settings)

        # Override properties
        for key, value in import_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logging.debug(f"Apply setting [{key}]: {value}")
            else:
                logging.warning(f"No match setting: [{key}]")

        # Format properties
        self.current_frame_real = self.current_frame + self.offset_frame
        self.current_frame_at_chunk = self.current_frame - self.start_frame + 1
        self.output_frame_number = self.current_frame - self.start_frame
        self.shot_path = Path(self.shot_path)
        self.job_path = Path(self.job_path)
        self.cali_path = Path(self.cali_path)

        # Expand Path
        self.project_path = (
            self.job_path / f"{self.metashape_project_name}.psx"
        )
        self.files_path = (
            self.job_path / f"{self.metashape_project_name}.files"
        )
        self.output_path = self.job_path / f"{self.output_folder_name}"
        self.archive_path = self.job_path / f"{self.archive_name}.zip"
        self.temp_path = Path.home() / self.temp_name
        self.temp_project_path = (
            self.temp_path / f"{self.metashape_project_name}.psx"
        )
        self.temp_masks_path = self.temp_path / self.masks_name

        # get names
        names = self.job_path.__str__().split("\\")
        if len(names) >= 5:
            self.project_name = names[2]
            self.shot_name = names[4]
        self.job_name = self.job_path.stem

        self.is_initialized = True

    def get_import_camera_and_images(self) -> dict:
        camera_folders = self.shot_path.glob("*")
        import_data = {}
        for camera_folder in camera_folders:
            if camera_folder.is_file():
                continue

            camera_id = camera_folder.stem
            camera_photos = []

            cali_image = self.cali_path / f"{camera_id}.jpg"
            if not cali_image.exists():
                raise ValueError(f"Calibration image not exists: {cali_image}")
            camera_photos.append(str(cali_image))
            for f in range(self.start_frame, self.end_frame + 1):
                real_frame = f + self.offset_frame
                camera_photos.append(
                    str(camera_folder / f"{camera_id}_{real_frame:06d}.jpg")
                )

            import_data[camera_id] = camera_photos

        return import_data


SETTINGS = ResolveSettings()
