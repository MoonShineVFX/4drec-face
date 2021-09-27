import os
import yaml
import logging
from pathlib import Path
from typing import Optional

from define import ResolveStage


# Default license path
if 'agisoft_LICENSE' not in os.environ:
    logging.info('Env "agisoft_LICENSE" not found, using default install path instead')
    os.environ['agisoft_LICENSE'] = 'C:\\Program Files\\Agisoft\\Metashape Pro\\'


class ResolveSettings:
    def __init__(self):
        self.is_initialized = False
        self.current_frame = -1
        self.resolve_stage: Optional[ResolveStage] = None

        # Names
        self.metashape_project_name = 'metashape_project'
        self.output_folder_name = 'output'
        self.chunk_name = 'MainChunk'
        self.timelog_name = 'timelog'

        # Camera
        self.sensor_pixel_width = 0.00345
        self.sensor_focal_length = 12

        # Parameters
        self.match_photos_interval = 5
        self.mesh_clean_faces_threshold = 10000
        self.smooth_model = 1.0
        self.texture_size = 8192
        self.region_size = [0.5, 0.5, 0.5]

        # Normalize chunk transform
        self.nct_marker_locations = {}
        self.nct_center_offset = [0.0, -0.2, 0.3]

        # Job
        self.offset_frame = 0
        self.start_frame = 0
        self.end_frame = 0
        self.current_frame_real = -1
        self.current_frame_at_chunk = -1
        self.cali_path = Path('')
        self.shot_path = Path('')
        self.job_path = Path('')

        # More Paths
        self.project_path = ''
        self.files_path = ''
        self.export_path = ''
        self.timelog_path = ''

    def initialize(self,
                   current_frame: int,
                   resolve_stage: ResolveStage,
                   yaml_path: Optional[str] = None,
                   extra_settings: Optional[dict] = None):
        logging.debug('Initialize')

        self.current_frame = current_frame
        self.resolve_stage = resolve_stage

        import_settings = {}
        # Import yaml
        if yaml_path is not None:
            logging.debug(f'Load yaml file: {yaml_path}')
            with open(yaml_path, 'r') as f:
                import_settings.update(yaml.load(f, Loader=yaml.FullLoader))

        # Import extra settings
        if extra_settings is not None:
            logging.debug(f'Load extra settings')
            import_settings.update(extra_settings)

        # Override properties
        for key, value in import_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logging.debug(f'Apply setting [{key}]: {value}')
            else:
                logging.warning(f'No match setting: [{key}]')

        # Format properties
        self.current_frame_real = self.current_frame + self.offset_frame
        self.current_frame_at_chunk = self.current_frame - self.start_frame + 1
        self.shot_path = Path(self.shot_path)
        self.job_path = Path(self.job_path)
        self.cali_path = Path(self.cali_path)

        # Expand Path
        self.project_path = self.job_path / f'{self.metashape_project_name}.psx'
        self.files_path = self.job_path / f'{self.metashape_project_name}.files'
        self.export_path = self.job_path / f'{self.output_folder_name}'
        self.timelog_path = self.job_path / f'{self.timelog_name}.txt'

        self.is_initialized = True

    def get_import_camera_and_images(self) -> dict:
        camera_folders = self.shot_path.glob('*')
        import_data = {}
        for camera_folder in camera_folders:
            camera_id = camera_folder.stem
            camera_photos = []

            cali_image = self.cali_path / f'{camera_id}.jpg'
            camera_photos.append(str(cali_image))
            for f in range(self.start_frame, self.end_frame + 1):
                real_frame = f + self.offset_frame
                camera_photos.append(
                    str(camera_folder / f'{camera_id}_{real_frame:06d}.jpg')
                )

            import_data[camera_id] = camera_photos

        return import_data


SETTINGS = ResolveSettings()
