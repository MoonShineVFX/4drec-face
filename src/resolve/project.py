import zipfile
import os
import Metashape
import numpy as np
import logging
from time import perf_counter
import shutil
from typing import Optional
from PIL import Image
from pathlib import Path
import math
import subprocess
import json

from common.fourd_frame import FourdFrameManager

from settings import SETTINGS
from define import ResolveStage


MAX_CALIBRATE_FRAMES = 5
MIN_VALID_MARKERS = 3


class ResolveProject:
    def __init__(self):
        self.__step_timer: Optional[float] = None
        self.__progress = 0.0

        # Check settings
        if not SETTINGS.is_initialized:
            error_message = "Settings didn't initialized"
            logging.critical(error_message)
            raise ValueError(error_message)

        # Check metashape documents
        if SETTINGS.resolve_stage is ResolveStage.INITIALIZE or SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            self.__doc = Metashape.Document()

        # Initial load project file
        if SETTINGS.resolve_stage is ResolveStage.INITIALIZE:
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
                self.__doc.save(str(SETTINGS.project_path), absolute_paths=True)
        # Resolve load archive zip
        elif SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            logging.info('Project file exists, extract to local')
            if not SETTINGS.archive_path.exists():
                raise ValueError(f'Project file {SETTINGS.archive_path} not found!')
            if SETTINGS.temp_path.exists():
                shutil.rmtree(str(SETTINGS.temp_path), ignore_errors=True)
            SETTINGS.temp_path.mkdir(parents=True, exist_ok=True)
            zf = zipfile.ZipFile(str(SETTINGS.archive_path), 'r')
            zf.extractall(str(SETTINGS.temp_path))
            self.__doc.open(
                str(SETTINGS.temp_project_path),
                ignore_lock=True,
                read_only=False
            )

    def initialize(self):
        logging.info('Initialize')
        if self.__doc.chunk is not None:
            logging.critical('Project chunk is not empty')
            raise ValueError('Project chunk is not empty')

        # Add Chunk
        chunk = self.__doc.addChunk()
        chunk.label = SETTINGS.chunk_name

        # Import images
        import_data = SETTINGS.get_import_camera_and_images()
        progress_import_step = 10.0 / len(import_data.keys())
        camera_count = 1
        camera_total_count = len(import_data.keys())
        for camera, photos in import_data.items():
            self.__logging_progress(
                progress_import_step,
                f'Import camera {camera_count}/{camera_total_count}'
            )
            chunk.addPhotos(photos, layout=Metashape.MultiframeLayout)
            camera_count += 1

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

        self.save(chunk)

    def calibrate(self):
        logging.info('Calibrate')
        chunk: Metashape.Chunk = self.__doc.chunk

        # Detect Markers
        chunk.detectMarkers(tolerance=50, inverted=False, frames=[0])

        # Build points
        interval = SETTINGS.match_photos_interval
        frames_count = len(chunk.frames)
        if frames_count < interval:
            interval = 1
        elif frames_count / interval > MAX_CALIBRATE_FRAMES:
            interval = int(frames_count / MAX_CALIBRATE_FRAMES)

        self.__logging_progress(2.0, f'Match photos every {interval} frames')

        progress_point_step = 85.0 / len(chunk.frames)
        for frame_number, frame in enumerate(chunk.frames):
            if frame_number % interval != 0:
                continue
            frame.matchPhotos(tiepoint_limit=8000)
            self.__logging_progress(
                progress_point_step,
                f'Match photos - {frame_number} / {len(chunk.frames)}'
            )

        # Align photos
        chunk.alignCameras()

        # Redetect markers for low parity markers
        chunk.remove(chunk.markers)
        chunk.detectMarkers(tolerance=50, inverted=True, frames=[0])

        # Align chunk
        logging.info('Normalize chunk transform')
        self.__normalize_chunk_transform()

        # Save and archive
        self.save(chunk)
        Metashape.Document()
        self.__archive_project()

    def resolve(self):
        logging.info('Resolve')
        frame = self.get_current_chunk()
        self.__logging_progress(1, 'Resolve Process')

        # Align chunk again if setting changed
        self.__mark_timer('Start')
        self.__align_region()
        self.__mark_timer('Align Region')

        # Build points
        is_cali_frame = frame.point_cloud is not None
        if not is_cali_frame:
            logging.info('Point cloud not found, build one')
            frame.matchPhotos(
                tiepoint_limit=8000,
                filter_stationary_points=False
            )
            self.__mark_timer('Match Photos')

            frame.triangulatePoints()
            self.__mark_timer('Triangulate Points')
        self.__logging_progress(8, 'Match Photos')

        # Apply mask
        if SETTINGS.skip_masks:
            self.__mark_timer('Skip Background Removal')
            self.__logging_progress(11, 'Skip Background Removal')
        else:
            self.__load_image_masks()
            self.__mark_timer('Background Removal')
            self.__logging_progress(11, 'Background Removal')

        # Build dense
        frame.buildDepthMaps()
        self.__mark_timer('Depth Map')
        frame.buildDenseCloud(
            point_colors=False,
            keep_depth=False
        )
        self.__mark_timer('Dense Cloud')
        self.__logging_progress(10, 'Dense Cloud')

        # Build mesh
        frame.buildModel()
        self.__mark_timer('Build Model')
        frame.model.removeComponents(SETTINGS.mesh_clean_faces_threshold)
        self.__mark_timer('Remove Small Parts')
        frame.smoothModel(SETTINGS.smooth_model)
        self.__mark_timer('Smooth Model')
        self.__logging_progress(15, 'Model Process')

        # Build texture
        frame.buildUV()
        self.__mark_timer('Build UV')
        self.__logging_progress(30, 'Build UV')
        frame.buildTexture(texture_size=SETTINGS.texture_size)
        self.__mark_timer('Build Texture')
        self.__logging_progress(15, 'Build Texture')

        # Export 4d data
        self.export_4df(frame)
        self.__mark_timer('Export 4D Data')

        # Clean data
        Metashape.Document()
        shutil.rmtree(str(SETTINGS.temp_path), ignore_errors=True)

    def save(self, chunk: Metashape.Chunk):
        self.__doc.save(str(SETTINGS.project_path), [chunk], absolute_paths=True)

    def run(self):
        # Main
        if SETTINGS.resolve_stage is ResolveStage.INITIALIZE:
            logging.info('Project run: INITIAL')
            self.initialize()
            self.calibrate()
        elif SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            logging.info('Project run: RESOLVE')
            self.resolve()
        elif SETTINGS.resolve_stage is ResolveStage.CONVERSION:
            logging.info('Project run: CONVERSION')
            self.convert_by_houdini()
        elif SETTINGS.resolve_stage is ResolveStage.POSTPROCESS:
            logging.info('Project run: POSTPROCESS')
            self.convert_texture_video()
            self.export_for_web()
        else:
            error_message = f'ResolveStage {SETTINGS.resolve_stage} not implemented'
            logging.critical(error_message)
            raise ValueError(error_message)

        logging.info('Finish', extra={'resolve_state': 'COMPLETE'})

    def get_current_chunk(self):
        return self.__doc.chunk.frames[SETTINGS.current_frame_at_chunk]

    def __logging_progress(self, progress_step: float, message: str):
        self.__progress += progress_step
        logging.info(message,
                     extra={
                         'resolve_state': 'PROGRESS',
                         'progress': self.__progress
                     })

    def __archive_project(self):
        zf = zipfile.ZipFile(str(SETTINGS.archive_path), 'w', zipfile.ZIP_STORED)
        zf.write(
            str(SETTINGS.project_path),
            str(SETTINGS.project_path.name))
        for root, dirs, files in os.walk(str(SETTINGS.files_path)):
            for file in files:
                zf.write(os.path.join(root, file),
                         os.path.relpath(os.path.join(root, file),
                         os.path.join(str(SETTINGS.files_path), '..')))
        zf.close()
        os.remove(str(SETTINGS.project_path))
        shutil.rmtree(str(SETTINGS.files_path), ignore_errors=True)

    def __align_region(self):
        chunk = self.__doc.chunk

        # Define region transform
        chunk_transform = chunk.transform
        region = chunk.region
        region.rot = chunk_transform.matrix.rotation().inv()
        region.size = Metashape.Vector(SETTINGS.region_size) / chunk_transform.scale
        region.center = chunk_transform.matrix.inv().mulp(
            Metashape.Vector(SETTINGS.nct_center_offset)
        )

    def __normalize_chunk_transform(self):
        chunk = self.__doc.chunk

        # Define marker locations and update chunk transform
        markers_ref_count = len(SETTINGS.nct_marker_locations.keys())
        markers_real_count = 0
        for marker in chunk.markers:
            marker_num = marker.label.split(' ')[-1]
            # Find specify markers
            if marker_num in SETTINGS.nct_marker_locations.keys():
                # Get marker error pix
                if not marker.position:
                    logging.warning(f'Marker[{marker_num}] has no position.')
                    continue

                proj_error = []
                proj_sqsum = 0
                for camera in marker.projections.keys():
                    if not camera.transform:
                        continue  # skipping not aligned cameras
                    proj = marker.projections[camera].coord
                    reproj = camera.project(marker.position)
                    error = reproj - proj
                    proj_error.append(error.norm())
                    proj_sqsum += error.norm() ** 2

                if len(proj_error) == 0:
                    logging.warning(f'Marker[{marker_num}] has no valid projections.')
                    continue

                error_pix = math.sqrt(proj_sqsum / len(proj_error))

                # Filter by error_pix
                if error_pix > 1:
                    logging.warning(f'Marker[{marker_num}] error pix is too big ({error_pix}).')
                    continue

                # Apply location data
                marker.reference.location = Metashape.Vector(
                    SETTINGS.nct_marker_locations[marker_num]
                )
                logging.info(f'Marker[{marker_num} apply location with error pix {error_pix}')
                markers_real_count += 1

        if markers_real_count < MIN_VALID_MARKERS:
            error_message = f'Markers valid count not enough: {markers_real_count} ({MIN_VALID_MARKERS})'
            logging.critical(error_message)
            raise ValueError(error_message)

        chunk.updateTransform()

        self.__align_region()

    def __mark_timer(self, text: str):
        if self.__step_timer is None:
            self.__step_timer = perf_counter()
            logging.info(f'[Timer] {text}')
            return
        now = perf_counter()
        duration = now - self.__step_timer
        self.__step_timer = now
        logging.info(f'[Timer] {text}: {duration:.2f}s')

    def __load_image_masks(self):
        from common.bg_remover import detect

        logging.info('Generate Mask')
        # Get images
        frame = self.get_current_chunk()
        image_path_list = []
        for camera in frame.cameras:
            image_path_list.append(camera.photo.path)

        images = [
            (image_path, np.array(Image.open(image_path).convert('RGB')))
            for image_path in image_path_list
        ]
        h, w, c = images[0][1].shape

        # Generate masks
        logging.info('Generating')
        SETTINGS.temp_masks_path.mkdir(parents=True, exist_ok=True)
        detect.generate_mask(images, w, h, str(SETTINGS.temp_masks_path))

        # Apply masks
        for camera in frame.cameras:
            filename = Path(camera.photo.path).stem
            mask_image_path = str(SETTINGS.temp_masks_path / f'{filename}.png')
            mask = Metashape.Mask()
            mask.load(mask_image_path)
            camera.mask = mask

    @staticmethod
    def get_average_position(camera_list: [Metashape.Camera]) -> Metashape.Vector:
        position = Metashape.Vector((0, 0, 0))
        for camera in camera_list:
            position += camera.transform.translation()
        return position / len(camera_list)

    @staticmethod
    def export_4df(chunk: Metashape.Chunk):
        logging.info('Export 4DF')
        # Get transform
        transform = chunk.transform.matrix
        rot_mat = np.array(list(transform.rotation().inv()), np.float32)
        rot_mat = rot_mat.reshape((3, 3))
        scale = transform.scale()
        offset = np.array(list(transform.translation()), np.float32)
        nct_offset = np.array(SETTINGS.nct_center_offset, np.float32)

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
        # Apply transform
        vtx_arr = np.dot(vtx_arr, rot_mat) * scale + offset - nct_offset

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
        export_4df_path = SETTINGS.export_path / f'{SETTINGS.current_frame_real:06d}.4df'

        FourdFrameManager.save_from_metashape(
            geo_arr, tex_arr, export_4df_path.__str__(), SETTINGS.current_frame_real
        )

    @staticmethod
    def __get_houdini_path():
        se_folder = Path('C:\\Program Files\\Side Effects Software')
        if not se_folder.exists() or not se_folder.is_dir():
            return None
        for folder in Path('C:\\Program Files\\Side Effects Software').glob('Houdini 19*'):
            if folder.is_dir():
                return folder
        return None

    @staticmethod
    def __run_process(commands: [str]):
        process = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        for line in process.stdout:
            logging.info(line.strip())
        process.stdout.close()

        return_code = process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, process.args)

    def convert_by_houdini(self):
        # version 2
        # export 4dh
        logging.info('Export 4DH')
        fourdf_path = SETTINGS.export_path / f'{SETTINGS.current_frame_real:06d}.4df'
        fourd_frame = FourdFrameManager.load(fourdf_path.__str__())
        root_path = SETTINGS.export_path.parent

        fourdh_path = root_path / 'geo' / f'{SETTINGS.current_frame:04d}.4dh'
        fourdh_path.parent.mkdir(parents=True, exist_ok=True)
        with open(fourdh_path, 'wb') as f:
            f.write(fourd_frame.get_houdini_data())

        fourdtexture_path = root_path / 'texture' / f'{SETTINGS.current_frame:04d}.jpg'
        fourdtexture_path.parent.mkdir(parents=True, exist_ok=True)
        with open(fourdtexture_path, 'wb') as f:
            f.write(fourd_frame.get_texture_data(raw=True))

        # Run hython
        logging.info('Run Houdini')

        houdini_path = self.__get_houdini_path()
        if houdini_path is None:
            logging.critical('Houdini not found')
            raise ValueError('Houdini not found')

        hython_path = houdini_path / 'bin' / 'hython3.9.exe'
        if not hython_path.exists():
            logging.critical('Hython not found')
            raise ValueError('Hython not found')

        self.__run_process([
            str(hython_path),
            str(Path(__file__).parent / 'conversion.py'),
            '-i',
            str(root_path / 'geo'),
            '-f',
            str(SETTINGS.current_frame)
        ])

    def convert_texture_video(self):
        root_path = SETTINGS.export_path.parent
        self.__run_process([
            'g:\\app\\ffmpeg',
            '-r', '30',
            '-start_number', '0',
            '-i',
            str(root_path / 'texture' / '%04d.jpg'),
            '-i',
            str(SETTINGS.shot_path.parent / 'audio.wav'),
            '-vf', 'scale=2048:-1',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-y',
            str(root_path / 'texture.mp4')
        ])
        self.__logging_progress(40, 'Convert texture video')

    def export_for_web(self):
        web_path = SETTINGS.web_path / f'{SETTINGS.job_name}-{SETTINGS.shot_name}'
        shutil.rmtree(web_path, ignore_errors=True)
        web_path.mkdir(parents=True, exist_ok=True)

        root_path = SETTINGS.export_path.parent

        shutil.copy(root_path / 'texture.mp4', web_path / 'texture.mp4')
        self.__logging_progress(10, 'Copy texture.mp4')

        mesh_path = web_path / 'mesh'
        shutil.copytree(root_path / 'gltf_mini_drc', mesh_path)
        self.__logging_progress(15, 'Copy mesh data')

        hires_path = web_path / 'hires'
        shutil.copytree(root_path / 'gltf', hires_path)
        self.__logging_progress(30, 'Copy hires data')

        with open(web_path / 'metadata.json', 'w', encoding='utf8') as f:
            json.dump({
                'hires': True,
                'endFrame': SETTINGS.end_frame - 1,
                'meshFrameOffset': -1,
                'modelPositionOffset': [0, 0.05, 0]
            }, f)
        self.__logging_progress(5, 'Generate metadata.json')