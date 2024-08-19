from queue import Queue
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
import alembic
import numpy as np
import imath
import imathnumpy
import subprocess

from utility.logger import log
from .package import ResolvePackage


def load_geometry(job_id, job_folder_path, res, frame, offset_frame):
    package = ResolvePackage(job_id, job_folder_path, res, frame, offset_frame)
    result = package.load()

    # no files
    if result is None:
        return None
    return package


def build_mesh_sample(vertex_arr, uv_arr):
    indices_arr = np.arange(len(vertex_arr), dtype=np.int32)
    counts_arr = np.array([3] * int(len(vertex_arr) / 3), np.int32)

    verts = imath.V3fArray(len(vertex_arr))
    verts_mem = imathnumpy.arrayToNumpy(verts)
    np.copyto(verts_mem, vertex_arr)

    indices = imath.IntArray(len(vertex_arr))
    indices_mem = imathnumpy.arrayToNumpy(indices)
    np.copyto(indices_mem, indices_arr)

    counts = imath.IntArray(int(len(vertex_arr) / 3))
    counts_mem = imathnumpy.arrayToNumpy(counts)
    np.copyto(counts_mem, counts_arr)

    # uv
    uvs = imath.V2fArray(len(uv_arr))
    imath_arr = [imath.V2f(*u) for u in uv_arr]
    for i in range(len(uv_arr)):
        uvs[i] = imath_arr[i]
    uvs_samp = alembic.AbcGeom.OV2fGeomParamSample(
        uvs, alembic.AbcGeom.GeometryScope.kFacevaryingScope
    )

    mesh_samp = alembic.AbcGeom.OPolyMeshSchemaSample(
        verts, indices, counts, uvs_samp
    )
    return mesh_samp


def export_texture(frame_num: int, load_path: str, export_path: str):
    from common.fourdrec_frame import FourdrecFrame

    frame = FourdrecFrame(load_path)
    frame.export_texture(export_path)
    return frame_num


def convert_fourd_frame_to_alembic(
    frame_num: int, load_path: str, export_path: str
):
    from common.fourdrec_frame import FourdrecFrame

    # load 4D
    frame = FourdrecFrame(load_path)

    vertex_arr, uv_arr = frame.get_geometry_array()

    uv_arr = uv_arr.copy()
    uv_arr = np.array(uv_arr, np.float64)

    # Build mesh sample
    mesh_samp = build_mesh_sample(vertex_arr, uv_arr)

    # Create alembic file
    archive = alembic.Abc.OArchive(export_path, asOgawa=True)
    archive.setCompressionHint(1)
    mesh_obj = alembic.AbcGeom.OPolyMesh(archive.getTop(), "scan_model")
    mesh = mesh_obj.getSchema()
    mesh.set(mesh_samp)

    return frame_num


class MultiExecutor(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self._queue = Queue()
        self._manager = manager
        self.start()

    def cache_all(self, tasks):
        future_list = []
        with ProcessPoolExecutor() as executor:
            for job_id, job_folder_path, res, f, offset_frame in tasks:
                future = executor.submit(
                    load_geometry,
                    job_id,
                    job_folder_path,
                    res,
                    f,
                    offset_frame,
                )
                future_list.append(future)
            for future in as_completed(future_list):
                package = future.result()
                if package is not None:
                    self._manager.save_package(package)
                self._manager.send_ui(None)

    def export_all(self, tasks):
        from utility.setting import setting
        import os
        import re
        from pathlib import Path

        (
            job_id,
            job_folder_path,
            job_frame_range,  # [27755, 29015]
            shot_folder_path,
            shot_frame_range,  # [27754, 29015]
            export_path,
        ) = tasks

        # filter export_path
        export_path = Path(export_path)
        filename = export_path.stem
        export_path = export_path.parent

        folder_name = re.sub(r"[^\w\d-]", "_", filename)
        export_path = Path(f"{export_path}/{folder_name}/")
        export_alembic_path = export_path / "alembic"
        export_texture_path = export_path / "texture"
        export_alembic_path.mkdir(parents=True, exist_ok=True)
        export_texture_path.mkdir(parents=True, exist_ok=True)

        # define
        output_path = Path(job_folder_path) / setting.submit.output_folder_name
        start_frame = job_frame_range[0] - shot_frame_range[0]
        end_frame = job_frame_range[1] - shot_frame_range[0]

        # Export audio
        log.info("Export Audio")
        audio_source_path = Path(shot_folder_path) / "audio.wav"
        if audio_source_path.exists():
            audio_target_path = export_path / "audio.wav"
            audio_start_time = (
                job_frame_range[0] - shot_frame_range[0]
            ) / setting.frame_rate
            audio_duration = (
                job_frame_range[1] - job_frame_range[0]
            ) / setting.frame_rate
            cmd = (
                f"ffmpeg -i {audio_source_path} "
                f"-ss {audio_start_time} "
                f"-t {audio_duration} "
                f"{audio_target_path}"
            )
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            for line in process.stdout:
                log.info(f"[ffmpeg] {line}")
        else:
            log.warning(
                f"Audio {audio_source_path} not exists, skip audio conversion."
            )

        # Run
        with ProcessPoolExecutor() as executor:
            future_list = []
            frame_complete = {}

            for f in range(start_frame, end_frame + 1):
                file_path = f"{output_path}/frame/{f:04d}.4dframe"

                if not os.path.isfile(file_path):
                    self._manager.ui_tick_export()
                    continue

                # Add geo decode task
                future_geo = executor.submit(
                    convert_fourd_frame_to_alembic,
                    f,
                    file_path,
                    rf"{export_alembic_path}\{f:04d}.abc",
                )
                future_list.append(future_geo)

                # Add texture export task
                future_tex = executor.submit(
                    export_texture,
                    f,
                    file_path,
                    rf"{export_texture_path}\{f:04d}.jpg",
                )
                future_list.append(future_tex)

                frame_complete[f] = 0

            for task in as_completed(future_list):
                task_done_frame = task.result()
                frame_complete[task_done_frame] += 1

                if frame_complete[task_done_frame] == 2:
                    self._manager.ui_tick_export()

    def run(self):
        while True:
            task_type, tasks = self._queue.get()

            if task_type == "cache_all":
                self.cache_all(tasks)
            elif task_type == "export_all":
                self.export_all(tasks)

    def add_task(self, task_type, tasks):
        self._queue.put((task_type, tasks))
