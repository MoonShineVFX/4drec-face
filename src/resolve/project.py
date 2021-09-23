import Metashape
import numpy as np
import logging
from time import perf_counter
from datetime import datetime

from common.fourd_frame import FourdFrameManager

from settings import SETTINGS
from define import ResolveStage


class ResolveProject:
    def __init__(self):
        # Check settings
        if not SETTINGS.is_initialized:
            error_message = "Settings didn't initialized"
            logging.critical(error_message)
            raise ValueError(error_message)

        # Check metashape documents
        self.__doc = Metashape.Document()
        if SETTINGS.project_path.exists():
            logging.info('Project file exists, loading')
            self.__doc.open(
                str(SETTINGS.project_path),
                ignore_lock=True,
                read_only=False
            )
        else:
            logging.info('Project file not found, create one')
            SETTINGS.project_path.parent.mkdir(parents=True, exist_ok=True)
            self.__doc.save(str(SETTINGS.project_path))

    def initialize(self):
        logging.info('Initialize')
        if self.__doc.chunk is not None:
            logging.critical('Project chunk is not empty')
            raise ValueError('Project chunk is not empty')

        # Add Chunk
        chunk = self.__doc.addChunk()
        chunk.label = SETTINGS.chunk_name

        # Import images
        camera_folders = SETTINGS.shot_path.glob('*')
        for camera_folder in camera_folders:
            photos = [str(p) for p in camera_folder.glob('*.jpg')]
            chunk.addPhotos(photos, layout=Metashape.MultiframeLayout)

        # Camera labels
        for camera in chunk.cameras:
            camera.label = camera.label[:-7]

        # Camera calibration sensor
        ref_sensor: Metashape.Sensor = chunk.sensors[0]
        ref_sensor.focal_length = SETTINGS.sensor_focal_length
        ref_sensor.pixel_width = SETTINGS.sensor_pixel_width
        ref_sensor.pixel_height = SETTINGS.sensor_pixel_width

        # Apply sensor data to all cameras
        for camera in chunk.cameras:
            sensor = chunk.addSensor(ref_sensor)
            sensor.label = f'sensor_{camera.label}'
            camera.sensor = sensor
        chunk.remove([ref_sensor])

        self.save()

    def calibrate(self):
        logging.info('Calibrate')
        chunk: Metashape.Chunk = self.__doc.chunk

        # Build points
        interval = SETTINGS.match_photos_interval
        logging.debug(f'Match photos every {interval} frames')
        for frame in chunk.frames:
            if interval != SETTINGS.match_photos_interval:
                interval += 1
                continue
            frame.matchPhotos()
            interval = 1

        # Align photos
        chunk.alignCameras()

        # Align chunk
        self.__normalize_chunk_transform()

        self.save()

    def resolve(self):
        logging.info('Resolve')
        chunk = self.__doc.chunk
        frame = chunk.frames[SETTINGS.offsetted_current_frame]

        # Build points
        if frame.point_cloud is None:
            logging.debug('Point cloud not found, build one')
            frame.matchPhotos()
            frame.triangulatePoints()

        # Build dense
        frame.buildDepthMaps()
        frame.buildDenseCloud(
            point_colors=False,
            keep_depth=False
        )

        # Build mesh
        frame.buildModel()
        frame.model.removeComponents(SETTINGS.mesh_clean_faces_threshold)
        frame.smoothModel(SETTINGS.smooth_model)

        # Build texture
        frame.buildUV()
        frame.buildTexture(texture_size=SETTINGS.texture_size)
        self.save()

        # Export 4df
        self.export_4df(frame)

        self.save()

    def save(self):
        self.__doc.save(str(SETTINGS.project_path), self.__doc.chunks)

    def run(self):
        # Timestamp
        start_time = perf_counter()
        now = datetime.now()

        # Maim
        if SETTINGS.resolve_stage is ResolveStage.INITIALIZE:
            logging.info('Project run: INITIAL')
            self.initialize()
            self.calibrate()
        elif SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            logging.info('Project run: RESOLVE')
            self.resolve()
        else:
            error_message = f'ResolveStage {SETTINGS.resolve_stage} not implemented'
            logging.critical(error_message)
            raise ValueError(error_message)

        logging.info('Finish')
        # Record elapsed time
        duration = perf_counter() - start_time
        time_label = f'[{SETTINGS.resolve_stage}]'
        if SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            time_label += f'({SETTINGS.current_frame})'
        with open(str(SETTINGS.timelog_path), 'a') as f:
            f.write(f'{now:%Y-%m-%d %H:%M:%S} {time_label}: {duration}s\n')

    def __normalize_chunk_transform(self):
        chunk = self.__doc.chunk

        # Define marker locations and update chunk transform
        for marker in chunk.markers:
            marker_num = int(marker.label.split(' ')[-1])
            if marker_num in SETTINGS.nct_marker_locations.keys():
                marker.reference.location = Metashape.Vector(
                    SETTINGS.nct_marker_locations[marker_num]
                )
        chunk.updateTransform()

        # Define region transform
        chunk_transform = chunk.transform
        region = chunk.region
        region.rot = chunk_transform.matrix.rotation().inv()
        region.size = Metashape.Vector(SETTINGS.region_size) / chunk_transform.scale
        region.center = chunk_transform.matrix.inv().mulp(
            Metashape.Vector(SETTINGS.nct_center_offset)
        )

    @staticmethod
    def get_average_position(camera_list: [Metashape.Camera]) -> Metashape.Vector:
        position = Metashape.Vector((0, 0, 0))
        for camera in camera_list:
            position += camera.transform.translation()
        return position / len(camera_list)

    @staticmethod
    def export_4df(chunk: Metashape.Chunk):
        logging.info('Export 4DF')
        # Get model
        model: Metashape.Model = chunk.model

        # Geo
        vtx_idxs: [int] = []
        uv_idxs: [int] = []
        for face in model.faces:
            vtx_idxs += face.vertices
            uv_idxs += face.tex_vertices

        vtx_arr = np.array(
            [list(vtx.coord) for vtx in model.vertices],
            np.float32
        )
        uv_arr = np.array(
            [list(uv.coord) for uv in model.tex_vertices],
            np.float32
        )

        vtx_arr = vtx_arr[vtx_idxs]

        uv_arr = uv_arr[uv_idxs]
        uv_arr *= [1, -1]
        uv_arr += [0, 1.0]

        geo_arr = np.hstack((vtx_arr, uv_arr))

        # Texture
        image = model.textures[0].image()
        tex_arr = np.fromstring(image.tostring(), dtype=np.uint8)
        tex_arr = tex_arr.reshape((image.width, image.height, 4))
        tex_arr = tex_arr[:, :, :3]

        # Make dir
        SETTINGS.export_path.mkdir(parents=True, exist_ok=True)
        export_4df_path = SETTINGS.export_path / f'{SETTINGS.current_frame:06d}.4df'

        FourdFrameManager.save_from_metashape(
            geo_arr, tex_arr, export_4df_path.__str__(), SETTINGS.current_frame
        )
