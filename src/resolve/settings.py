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
        self.nct_group_up = [2, 3]
        self.nct_group_origin = [4, 5]
        self.nct_group_horizon = [12, 13]
        self.nct_group_measure = [5, 12]
        self.nct_group_measure_distance = 0.5564
        self.nct_center_offset = [0.0, -0.2, 0.3]

        # Job
        self.start_frame = 0
        self.end_frame = 0
        self.shot_path = Path(r'D"\shot\a1b2c3d4')
        self.job_path = Path(r'D:\jobs\a1b2c3d4')

    def initialize(self,
                   current_frame: int,
                   resolve_stage: ResolveStage,
                   yaml_path: Optional[str] = None,
                   extra_settings: Optional[dict] = None):
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
        self.current_frame = int(self.current_frame)
        self.shot_path = Path(self.shot_path)
        self.job_path = Path(self.job_path)

        # Expand Path
        self.project_path = self.job_path / f'{self.metashape_project_name}.psx'
        self.files_path = self.job_path / f'{self.metashape_project_name}.files'
        self.export_path = self.job_path / f'{self.output_folder_name}'

        self.is_initialized = True


SETTINGS = ResolveSettings()
