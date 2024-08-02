import zipfile
import os
import Metashape
import numpy as np
import logging
import shutil
from PIL import Image
from pathlib import Path
import math
from typing import Callable

from common.profiler import Profiler
from common.fourdrec_frame import FourdrecFrame

from settings import SETTINGS
from define import ResolveStage


MAX_CALIBRATE_FRAMES = 5
MIN_VALID_MARKERS = 3


LoggingProgress = Callable[[float, str], None]


class MetashapeResolver:
    def __init__(self, logging_progress: LoggingProgress):
        # Check metashape documents
        self.__doc = Metashape.Document()
        self.__logging_progress = logging_progress

        # Initial load project file
        if SETTINGS.resolve_stage is ResolveStage.INITIALIZE:
            if SETTINGS.project_path.exists():
                logging.info("Project file exists, loading")
                self.__doc.open(
                    str(SETTINGS.project_path),
                    ignore_lock=True,
                    read_only=False,
                )
            else:
                logging.info("Project file not found, create one")
                SETTINGS.project_path.parent.mkdir(parents=True, exist_ok=True)
                self.__doc.save(
                    str(SETTINGS.project_path), absolute_paths=True
                )
        # Resolve load archive zip
        elif SETTINGS.resolve_stage is ResolveStage.RESOLVE:
            logging.info("Project file exists, extract to local")
            if not SETTINGS.archive_path.exists():
                raise ValueError(
                    f"Project file {SETTINGS.archive_path} not found!"
                )
            if SETTINGS.temp_path.exists():
                shutil.rmtree(str(SETTINGS.temp_path), ignore_errors=True)
            SETTINGS.temp_path.mkdir(parents=True, exist_ok=True)
            zf = zipfile.ZipFile(str(SETTINGS.archive_path), "r")
            zf.extractall(str(SETTINGS.temp_path))
            self.__doc.open(
                str(SETTINGS.temp_project_path),
                ignore_lock=True,
                read_only=False,
            )
        else:
            raise ValueError("Resolve stage not implemented")

    def initialize(self):
        logging.info("Initialize")
        if self.__doc.chunk is not None:
            raise ValueError("Project chunk is not empty")

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
                f"Import camera {camera_count}/{camera_total_count}",
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
            sensor.label = f"sensor_{camera.label}"
            camera.sensor = sensor
        chunk.remove([ref_sensor])

        self.save(chunk)

    def calibrate(self):
        logging.info("Calibrate")
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

        self.__logging_progress(2.0, f"Match photos every {interval} frames")

        progress_point_step = 85.0 / len(chunk.frames)
        for frame_number, frame in enumerate(chunk.frames):
            if frame_number % interval != 0:
                continue
            frame.matchPhotos(tiepoint_limit=8000)
            self.__logging_progress(
                progress_point_step,
                f"Match photos - {frame_number} / {len(chunk.frames)}",
            )

        # Align photos
        chunk.alignCameras()

        # Redetect markers for low parity markers
        chunk.remove(chunk.markers)
        chunk.detectMarkers(tolerance=50, inverted=True, frames=[0])

        # Align chunk
        logging.info("Normalize chunk transform")
        self.__normalize_chunk_transform()

        # Save and archive
        self.save(chunk)
        Metashape.Document()
        self.__archive_project()

    def resolve(self):
        logging.info("Resolve")
        frame = self.get_current_chunk()
        self.__logging_progress(1, "Resolve Process")

        # Align chunk again if setting changed
        profiler = Profiler("Start")
        self.__align_region()
        profiler.mark("Align Region")

        # Build points
        is_cali_frame = frame.point_cloud is not None
        if not is_cali_frame:
            logging.info("Point cloud not found, build one")
            frame.matchPhotos(
                tiepoint_limit=8000, filter_stationary_points=False
            )
            profiler.mark("Match Photos")

            frame.triangulatePoints()
            profiler.mark("Triangulate Points")
        self.__logging_progress(8, "Match Photos")

        # Apply mask
        if SETTINGS.skip_masks:
            profiler.mark("Skip Background Removal")
            self.__logging_progress(11, "Skip Background Removal")
        else:
            self.__load_image_masks()
            profiler.mark("Background Removal")
            self.__logging_progress(11, "Background Removal")

        # Build dense
        frame.buildDepthMaps()
        profiler.mark("Depth Map")
        frame.buildDenseCloud(point_colors=False, keep_depth=False)
        profiler.mark("Dense Cloud")
        self.__logging_progress(10, "Dense Cloud")

        # Build mesh
        frame.buildModel()
        profiler.mark("Build Model")
        frame.model.removeComponents(SETTINGS.mesh_clean_faces_threshold)
        profiler.mark("Remove Small Parts")
        frame.smoothModel(SETTINGS.smooth_model)
        profiler.mark("Smooth Model")
        self.__logging_progress(15, "Model Process")

        # Build texture
        frame.buildUV()
        profiler.mark("Build UV")
        self.__logging_progress(30, "Build UV")
        frame.buildTexture(texture_size=SETTINGS.texture_size)
        profiler.mark("Build Texture")
        self.__logging_progress(15, "Build Texture")

        # Output result
        output_path = self.output(frame)
        profiler.mark("Output result")

        # Clean data
        shutil.rmtree(str(SETTINGS.temp_path), ignore_errors=True)

        return output_path

    def save(self, chunk: Metashape.Chunk):
        self.__doc.save(
            str(SETTINGS.project_path), [chunk], absolute_paths=True
        )

    def get_current_chunk(self):
        return self.__doc.chunk.frames[SETTINGS.current_frame_at_chunk]

    @staticmethod
    def __archive_project():
        zf = zipfile.ZipFile(
            str(SETTINGS.archive_path), "w", zipfile.ZIP_STORED
        )
        zf.write(str(SETTINGS.project_path), str(SETTINGS.project_path.name))
        for root, dirs, files in os.walk(str(SETTINGS.files_path)):
            for file in files:
                zf.write(
                    os.path.join(root, file),
                    os.path.relpath(
                        os.path.join(root, file),
                        os.path.join(str(SETTINGS.files_path), ".."),
                    ),
                )
        zf.close()
        os.remove(str(SETTINGS.project_path))
        shutil.rmtree(str(SETTINGS.files_path), ignore_errors=True)

    def __align_region(self):
        chunk = self.__doc.chunk

        # Define region transform
        chunk_transform = chunk.transform
        region = chunk.region
        region.rot = chunk_transform.matrix.rotation().inv()
        region.size = (
            Metashape.Vector(SETTINGS.region_size) / chunk_transform.scale
        )
        region.center = chunk_transform.matrix.inv().mulp(
            Metashape.Vector(SETTINGS.nct_center_offset)
        )

    def __normalize_chunk_transform(self):
        chunk = self.__doc.chunk

        # Define marker locations and update chunk transform
        markers_ref_count = len(SETTINGS.nct_marker_locations.keys())
        markers_real_count = 0
        for marker in chunk.markers:
            marker_num = marker.label.split(" ")[-1]
            # Find specify markers
            if marker_num in SETTINGS.nct_marker_locations.keys():
                # Get marker error pix
                if not marker.position:
                    logging.warning(f"Marker[{marker_num}] has no position.")
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
                    logging.warning(
                        f"Marker[{marker_num}] has no valid projections."
                    )
                    continue

                error_pix = math.sqrt(proj_sqsum / len(proj_error))

                # Filter by error_pix
                if error_pix > 1:
                    logging.warning(
                        f"Marker[{marker_num}] error pix is too big ({error_pix})."
                    )
                    continue

                # Apply location data
                marker.reference.location = Metashape.Vector(
                    SETTINGS.nct_marker_locations[marker_num]
                )
                logging.info(
                    f"Marker[{marker_num} apply location with error pix {error_pix}"
                )
                markers_real_count += 1

        if markers_real_count < MIN_VALID_MARKERS:
            error_message = f"Markers valid count not enough: {markers_real_count} ({MIN_VALID_MARKERS})"
            raise ValueError(error_message)

        chunk.updateTransform()

        self.__align_region()

    def __load_image_masks(self):
        from common.bg_remover import detect

        logging.info("Generate Mask")
        # Get images
        frame = self.get_current_chunk()
        image_path_list = []
        for camera in frame.cameras:
            image_path_list.append(camera.photo.path)

        images = [
            (image_path, np.array(Image.open(image_path).convert("RGB")))
            for image_path in image_path_list
        ]
        h, w, c = images[0][1].shape

        # Generate masks
        logging.info("Generating")
        SETTINGS.temp_masks_path.mkdir(parents=True, exist_ok=True)
        detect.generate_mask(images, w, h, str(SETTINGS.temp_masks_path))

        # Apply masks
        for camera in frame.cameras:
            filename = Path(camera.photo.path).stem
            mask_image_path = str(SETTINGS.temp_masks_path / f"{filename}.png")
            mask = Metashape.Mask()
            mask.load(mask_image_path)
            camera.mask = mask

    @staticmethod
    def get_average_position(
        camera_list: [Metashape.Camera],
    ) -> Metashape.Vector:
        position = Metashape.Vector((0, 0, 0))
        for camera in camera_list:
            position += camera.transform.translation()
        return position / len(camera_list)

    @staticmethod
    def output(chunk: Metashape.Chunk):
        logging.info("Output resolved result to 4dframe")

        # Get transform
        transform = chunk.transform.matrix
        rot_mat = np.array(list(transform.rotation().inv()), np.float32)
        rot_mat = rot_mat.reshape((3, 3))
        scale = transform.scale()
        offset = np.array(list(transform.translation()), np.float32)
        nct_offset = np.array(SETTINGS.nct_center_offset, np.float32)

        # Rotate 180 along y-axis for maker v2
        rot_180_mat = np.array(
            [
                [-1, 0, 0],
                [0, 1, 0],
                [0, 0, -1],
            ],
            np.float32,
        )

        # Get model
        model: Metashape.Model = chunk.model

        # Geo
        vtx_idxs: [int] = []
        uv_idxs: [int] = []
        for face in model.faces:
            vtx_idxs += face.vertices
            uv_idxs += face.tex_vertices

        vtx_arr = np.array(
            [list(vtx.coord) for vtx in model.vertices], np.float32
        )
        uv_arr = np.array(
            [list(uv.coord) for uv in model.tex_vertices], np.float32
        )
        vtx_arr = vtx_arr[vtx_idxs]
        uv_arr = uv_arr[uv_idxs]

        # Apply transform
        vtx_arr = np.dot(vtx_arr, rot_mat) * scale + offset - nct_offset
        vtx_arr = np.dot(vtx_arr, rot_180_mat)

        # Texture
        image = model.textures[0].image()
        tex_arr = np.fromstring(image.tostring(), dtype=np.uint8)
        tex_arr = tex_arr.reshape((image.width, image.height, 4))
        tex_arr = tex_arr[:, :, :3]

        # Make dir
        SETTINGS.output_path.mkdir(parents=True, exist_ok=True)
        frame_path = SETTINGS.output_path / "frame"
        frame_path.mkdir(parents=True, exist_ok=True)

        frame_number = SETTINGS.output_frame_number

        # Save 4dframe
        output_file_path = f"{frame_path}/{frame_number:04d}.4dframe"
        FourdrecFrame.save(
            output_file_path,
            vtx_arr,
            uv_arr,
            tex_arr,
        )

        return output_file_path
