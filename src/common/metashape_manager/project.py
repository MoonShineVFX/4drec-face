import Metashape
import os
from pathlib import Path
import numpy as np

from common.fourd_frame import FourdFrameManager


class MetashapeProject:
    _psx_name = 'project'
    _cameras_name = 'cameras'
    _masks_name = 'masks'
    _chunk_prefix_name = 'frame_'
    _export_name = 'export'

    SENSOR_PIXEL_WIDTH = 0.00345
    SENSOR_FOCAL_LENGTH = 12

    COMPONENT_REMOVE_THRESHOLD = 10000
    SMOOTH_MODEL = 1.0
    TEXTURE_SIZE = 8192

    CHUNK_NAME = 'MainChunk'
    GROUP_UP = [2, 3]
    GROUP_ORIGIN = [4, 5]
    GROUP_HORIZON = [12, 13]
    GROUP_DISTANCE = [5, 12]
    CENTER_OFFSET = (0.0, -0.2, 0.3)
    CAMERA_REFERENCE_DISTANCE = 0.5564
    REGION_SIZE = (0.5, 0.5, 0.5)
    FEATURE_INTERVAL = 5

    def __init__(self):
        self._start_frame = int(os.environ['start_frame'])
        self._end_frame = int(os.environ['end_frame'])
        self._current_frame = int(os.environ['current_frame'])

        self._shot_path = Path(os.environ['shot_path'])
        self._job_path = Path(os.environ['job_path'])

        self._project_path = self._job_path / f'{self._psx_name}.psx'
        self._files_path = self._job_path / f'{self._psx_name}.files'
        self._cameras_path = self._job_path / f'{self._cameras_name}.out'
        self._masks_path = self._shot_path / self._masks_name
        self._export_path = self._job_path / f'{self._export_name}'

        self._doc = self._initial_doc()

    def _initial_doc(self):
        doc = Metashape.Document()
        if self._project_path.exists():
            doc.open(
                self._project_path.__str__(),
                ignore_lock=True,
                read_only=False
            )
        else:
            self._project_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(self._project_path.__str__())
        return doc

    def _export_4df(self, chunk):
        # Get model
        model = chunk.model

        # Geo
        vtx_idxs = []
        uv_idxs = []
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
        self._export_path.mkdir(parents=True, exist_ok=True)
        export_4df_path = self._export_path / f'{self._current_frame:06d}.4df'

        FourdFrameManager.save_from_metashape(
            geo_arr, tex_arr, export_4df_path.__str__(), self._current_frame
        )

    def initial(self):
        chunk = self._doc.addChunk()
        chunk.label = self.CHUNK_NAME

        # Import images
        camera_folders = self._shot_path.glob('*')
        for camera_folder in camera_folders:
            photos = [str(p) for p in camera_folder.glob('*.jpg')]
            chunk.addPhotos(photos, layout=Metashape.MultiframeLayout)

        # Camera labels
        for camera in chunk.cameras:
            camera.label = camera.label[:-5]

        # Camera calibration sensor
        ref_sensor = chunk.sensors[0]
        ref_sensor.focal_length = self.SENSOR_FOCAL_LENGTH
        ref_sensor.pixel_width = self.SENSOR_PIXEL_WIDTH
        ref_sensor.pixel_height = self.SENSOR_PIXEL_WIDTH

        # Apply sensor data to all cameras
        for camera in chunk.cameras:
            sensor = chunk.addSensor(ref_sensor)
            sensor.label = f'sensor_{camera.label}'
            camera.sensor = sensor
        chunk.remove([ref_sensor])

        self.save()

    def calibrate(self):
        chunk = self._doc.chunk

        # Build points
        interval = self.FEATURE_INTERVAL
        for frame in chunk.frames:
            if interval != self.FEATURE_INTERVAL:
                interval += 1
                continue
            frame.matchPhotos()
            interval = 1

        # Align photos
        chunk.alignCameras()

        # Align chunk
        self._normalize_chunk_transform()

        self.save()

    def resolve(self):
        chunk = self._doc.chunk
        frame = chunk.frames[self._current_frame]

        # Build points
        if frame.point_cloud is None:
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
        frame.model.removeComponents(self.COMPONENT_REMOVE_THRESHOLD)
        frame.smoothModel(self.SMOOTH_MODEL)

        # Build texture
        frame.buildUV()
        frame.buildTexture(texture_size=self.TEXTURE_SIZE)
        self.save()

        # Export 4df
        self._export_4df(frame)

        # Save
        self.save()

    def save(self):
        self._doc.save(str(self._project_path), self._doc.chunks)

    def _normalize_chunk_transform(self):
        chunk = self._doc.chunk
        cameras: [Metashape.Camera] = chunk.cameras

        cameras_up: [Metashape.Camera] = []
        cameras_origin: [Metashape.Camera] = []
        cameras_horizon: [Metashape.Camera] = []
        cameras_distance: [Metashape.Camera] = []

        # Get groups
        for cam in cameras:
            # Get camera number
            camera_number = int(cam.label.split('_')[1])
            if camera_number in self.GROUP_UP:
                cameras_up.append(cam)
            elif camera_number in self.GROUP_ORIGIN:
                cameras_origin.append(cam)
            elif camera_number in self.GROUP_HORIZON:
                cameras_horizon.append(cam)
            if camera_number in self.GROUP_DISTANCE:
                cameras_distance.append(cam)

        # Get scale ratio
        scale_vector = cameras_distance[0].transform.translation() \
                       - cameras_distance[1].transform.translation()
        camera_distance = scale_vector.norm()
        scale_ratio = self.CAMERA_REFERENCE_DISTANCE / camera_distance

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
        pivot_offset = Metashape.Vector(self.CENTER_OFFSET)

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
        region.size = Metashape.Vector(self.REGION_SIZE) / scale_ratio

    @staticmethod
    def get_average_position(camera_list: [Metashape.Camera]) -> Metashape.Vector:
        position = Metashape.Vector((0, 0, 0))
        for camera in camera_list:
            position += camera.transform.translation()
        return position / len(camera_list)
