import Metashape
import os
from pathlib import Path
import numpy as np

from common.fourd_frame import FourdFrameManager

from .keying import keying_images


class MetashapeProject:
    _psx_name = 'project'
    _cameras_name = 'cameras'
    _masks_name = 'masks'
    _chunk_prefix_name = 'frame_'
    _export_name = 'export'

    _sensor_pixel_width = 0.00345
    _sensor_focal_length = 12
    _region_size_large = (12, 7, 12)
    _region_size_small = (5, 4, 5)

    _marker_reference = {
        'target 1': (0, 0.18, 0),
        'target 2': (0.133, 0.18, 0),
        'target 5': (0, 0.424, 0)
    }

    CHUNK_NAME = 'MainChunk'
    GROUP_UP = [2, 3]
    GROUP_ORIGIN = [4, 5]
    GROUP_HORIZON = [12, 13]
    GROUP_DISTANCE = [5, 12]
    CENTER_OFFSET = (0.0, -0.5, 0.65)
    CAMERA_REFERENCE_DISTANCE = 0.5564
    REGION_SIZE = (1.0, 1.0, 1.0)

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

    def _create_chunk(self, chunk_name) -> Metashape.Chunk:
        new_chunk = self._doc.addChunk()
        new_chunk.label = chunk_name
        return new_chunk

    def _import_images_to_chunk(self, chunk, path, frame):
        photos = [p.__str__() for p in path.glob(f'*_{frame:06d}.jpg')]
        chunk.addPhotos(photos)
        for camera in chunk.cameras:
            camera.label = camera.label.split('_')[0]

    def _log_progress(self, title, progress):
        print(f'{title}: {progress:.2f}%')

    def _get_chunk(self, chunk_name: str) -> Metashape.Chunk:
        for chunk in self._doc.chunks:
            if chunk.label == chunk_name:
                return chunk
        raise ValueError(f'No chunk named {chunk_name}')

    def _export(self, chunk):
        # get model
        model = chunk.model

        # geo
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

        # texture
        image = model.textures[0].image()
        tex_arr = np.fromstring(image.tostring(), dtype=np.uint8)
        tex_arr = tex_arr.reshape((image.width, image.height, 4))
        tex_arr = tex_arr[:, :, :3]

        # make dir
        self._export_path.mkdir(parents=True, exist_ok=True)
        export_4df_path = self._export_path / f'{self._current_frame:06d}.4df'

        FourdFrameManager.save_from_metashape(
            geo_arr, tex_arr, export_4df_path.__str__(), self._current_frame
        )

    def initial(self):
        chunk = self._create_chunk(self.CHUNK_NAME)

        # import images
        camera_folders = self._shot_path.glob('*')
        for camera_folder in camera_folders:
            photos = [str(p) for p in camera_folder.glob('*.jpg')]
            chunk.addPhotos(photos, layout=Metashape.MultiframeLayout)

        # camera labels
        for camera in chunk.cameras:
            camera.label = camera.label[:-5]

        self.save()

    def calibrate(self):
        chunk = self._doc.chunk

        # camera calibration sensor
        ref_sensor = chunk.sensors[0]
        ref_sensor.focal_length = self._sensor_focal_length
        ref_sensor.pixel_width = self._sensor_pixel_width
        ref_sensor.pixel_height = self._sensor_pixel_width

        # camera calibration all
        for camera in chunk.cameras:
            sensor = chunk.addSensor(ref_sensor)
            sensor.label = f'sensor_{camera.label}'
            camera.sensor = sensor
        chunk.remove([ref_sensor])

        # build points
        chunk.matchPhotos(
            reference_preselection=False
        )

        # align photos
        chunk.alignCameras(chunk.cameras)

        # align chunk
        self.calibrate_chunk_transform()

        # save
        self.save()

    def resolve(self):
        # get chunk
        chunk = self._get_chunk(self._current_frame)

        # add photos
        self._import_images_to_chunk(
            chunk, self._shot_path, self._current_frame
        )

        # detect markers
        # chunk.detectMarkers()

        # keying image
        mask_path_list = keying_images(
            self._shot_path,
            self._masks_path,
            self._current_frame
        )

        # import masks
        for camera, mask_path in zip(chunk.cameras, mask_path_list):
            print(camera.label)
            print(mask_path)
            mask = Metashape.Mask()
            mask.load(mask_path)
            camera.mask = mask

        # import cameras
        ref_sensor = self._import_camera_to_chunk(chunk)

        # camera calibration all
        chunk.importCameras(
            self._cameras_path.__str__(),
            format=Metashape.CamerasFormatBundler
        )

        for camera in chunk.cameras:
            sensor = chunk.addSensor(ref_sensor)
            sensor.label = f'sensor_{camera.label}'
            calibration = sensor.calibration.copy()
            calibration.load(
                (self._job_path / f'{camera.label}.xml').__str__()
            )
            sensor.calibration = calibration
            camera.sensor = sensor

        chunk.remove([ref_sensor])

        # # build points
        # chunk.matchPhotos(
        #     filter_mask=True,
        #     reference_preselection=False,
        #     mask_tiepoints=False,
        #     keypoint_limit=0,
        #     tiepoint_limit=0
        # )
        # chunk.triangulatePoints()

        # # optimize cameras
        # chunk.optimizeCameras()
        #

        # build dense
        chunk.resetRegion()
        chunk.region.size = Metashape.Vector(
            self._region_size_large
        )
        chunk.buildDepthMaps(
          downscale=2
        )
        chunk.region.size = Metashape.Vector(
            self._region_size_small
        )
        chunk.buildDenseCloud(
            point_colors=False,
            keep_depth=False
        )

        # build mesh
        chunk.buildModel(
            face_count=Metashape.FaceCount.MediumFaceCount
        )
        chunk.smoothModel()

        # build texture
        chunk.buildUV()
        chunk.buildTexture()
        self.save()

        # align chunk
        # cali_chunk = self._get_chunk(5981)
        # self._doc.alignChunks(
        #     chunks=[cali_chunk.key, chunk.key],
        #     reference=cali_chunk.key,
        #     method=1
        # )

        # export 4df
        self._export(chunk)

        # save
        self.save()

    def save(self):
        self._doc.save(str(self._project_path), self._doc.chunks)

    def calibrate_chunk_transform(self):
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
        chunk.transform.translation += pivot_offset * scale_ratio

        # Apply Region transform
        region = chunk.region
        region.center = pivot_center - matrix_target.inv().mulp(
            pivot_offset
        )
        region.rot = matrix_target.rotation().inv()
        region.size = Metashape.Vector(self.REGION_SIZE) / scale_ratio

    @staticmethod
    def get_average_position(camera_list: [Metashape.Camera]) -> Metashape.Vector:
        position = Metashape.Vector((0, 0, 0))
        for camera in camera_list:
            position += camera.transform.translation()
        return position / len(camera_list)
