import Metashape
import numpy as np
import logging

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
            camera.label = camera.label[:-5]

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
        frame = chunk.frames[SETTINGS.current_frame]

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

    def __normalize_chunk_transform(self):
        chunk = self.__doc.chunk
        cameras: [Metashape.Camera] = chunk.cameras

        cameras_up: [Metashape.Camera] = []
        cameras_origin: [Metashape.Camera] = []
        cameras_horizon: [Metashape.Camera] = []
        cameras_distance: [Metashape.Camera] = []

        # Get groups
        for cam in cameras:
            # Get camera number
            camera_number = int(cam.label.split('_')[1])
            if camera_number in SETTINGS.nct_group_up:
                cameras_up.append(cam)
            elif camera_number in SETTINGS.nct_group_origin:
                cameras_origin.append(cam)
            elif camera_number in SETTINGS.nct_group_horizon:
                cameras_horizon.append(cam)
            if camera_number in SETTINGS.nct_group_measure:
                cameras_distance.append(cam)

        # Get scale ratio
        scale_vector = \
            cameras_distance[0].transform.translation() \
            - cameras_distance[1].transform.translation()
        camera_distance = scale_vector.norm()
        scale_ratio = SETTINGS.nct_group_measure_distance / camera_distance

        # Get positions
        position_up = self.get_average_position(cameras_up)
        position_origin = self.get_average_position(cameras_origin)
        position_left = self.get_average_position(cameras_horizon)

        # Get vectors for rotation matrix
        vector_up: Metashape.Vector = (position_up - position_origin).normalized()
        vector_horizon: Metashape.Vector = (
                position_left - position_origin
        ).normalized()
        vector_forward = Metashape.Vector.cross(vector_horizon, vector_up)

        # Get pivot_center
        pivot_center = position_left + (position_origin - position_left) / 2
        pivot_offset = Metashape.Vector(SETTINGS.nct_center_offset)

        # Create matrix_target
        vector_horizon.size = 4
        vector_horizon.w = 0
        vector_up.size = 4
        vector_up.w = 0
        vector_forward.size = 4
        vector_forward.w = 0
        matrix_target = Metashape.Matrix((
            vector_horizon, vector_up, vector_forward, (0.0, 0.0, 0.0, 1.0)
        ))

        # Apply Chunk transform
        chunk.transform.matrix = matrix_target
        chunk.transform.scale = scale_ratio
        chunk.transform.translation = -matrix_target.mulp(
            pivot_center * scale_ratio
        )
        chunk.transform.translation += pivot_offset

        # Apply Region transform
        region = chunk.region
        region.center = pivot_center - matrix_target.inv().mulp(
            pivot_offset / scale_ratio
        )
        region.rot = matrix_target.rotation().inv()
        region.size = Metashape.Vector(SETTINGS.region_size) / scale_ratio

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
