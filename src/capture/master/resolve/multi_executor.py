from queue import Queue
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
import alembic
import numpy as np
import imath
import imathnumpy

from .package import ResolvePackage


def load_geometry(job_id, job_folder_path, res, frame):
    package = ResolvePackage(job_id, job_folder_path, res, frame)
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

    mesh_samp = alembic.AbcGeom.OPolyMeshSchemaSample(verts, indices, counts, uvs_samp)
    return mesh_samp


def export_geometry(load_path, filename, frame, export_path, filetype):
    from common.fourd_frame import FourdFrameManager

    fourd_frame = FourdFrameManager.load(load_path)

    if filetype == '.obj':
        with open(f'{export_path}/obj/{filename}_{frame:04d}.obj', 'w') as f:
            f.write(fourd_frame.get_obj_data())

    if filetype == '.4dh':
        with open(f'{export_path}/geo/{filename}_{frame:04d}.4dh', 'wb') as f:
            f.write(fourd_frame.get_houdini_data())

    with open(f'{export_path}/texture/{filename}_{frame:04d}.jpg', 'wb') as f:
        f.write(fourd_frame.get_texture_data(raw=True))


def export_texture(frame_num: int, load_path: str, export_path: str):
    from common.fourd_frame import FourdFrameManager
    frame = FourdFrameManager.load(load_path)
    data = frame.get_texture_data(raw=True)
    with open(export_path, 'wb') as f:
        f.write(data)
    return frame_num, None


def decode_fourd_frame(frame_num: int, load_path: str):
    from common.fourd_frame import FourdFrameManager
    # load 4D
    frame = FourdFrameManager.load(load_path)

    vertex_arr, uv_arr = frame.get_geo_data()

    uv_arr = uv_arr.copy()
    uv_arr -= [0, 1.0]
    uv_arr *= [1, -1]
    uv_arr = np.array(uv_arr, np.float64)

    return frame_num, (vertex_arr, uv_arr)


class MultiExecutor(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self._queue = Queue()
        self._manager = manager
        self.start()

    def cache_all(self, tasks):
        future_list = []
        with ProcessPoolExecutor() as executor:
            for job_id, job_folder_path, res, f in tasks:
                future = executor.submit(
                    load_geometry, job_id, job_folder_path, res, f
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

        job_id, job_folder_path, frame_range, export_path = tasks

        # filter export_path
        export_path = Path(export_path)
        filetype = export_path.suffix
        filename = export_path.stem
        export_path = export_path.parent

        # define
        load_path = (
            f'{job_folder_path}/'
            f'{setting.submit.output_folder_name}/'
        )
        offset_frame = frame_range[0]

        if filetype != '.abc':
            # Export obj or 4dh
            folder_name = re.sub(r'[^\w\d-]', '_', filename)
            export_path = Path(f'{export_path}/{folder_name}/')
            if filetype == '.obj':
                (export_path / 'obj').mkdir(parents=True, exist_ok=True)
            if filetype == '.4dh':
                (export_path / 'geo').mkdir(parents=True, exist_ok=True)
            (export_path / 'texture').mkdir(parents=True, exist_ok=True)

            with ProcessPoolExecutor() as executor:
                future_list = []
                for f in range(frame_range[0], frame_range[1] + 1):
                    offset_f = f - offset_frame
                    file_path = f'{load_path}{f:06d}.4df'

                    if not os.path.isfile(file_path):
                        self._manager.ui_tick_export()
                        continue

                    future = executor.submit(
                        export_geometry,
                        file_path,
                        folder_name,
                        offset_f,
                        str(export_path),
                        filetype
                    )
                    future_list.append(future)

                for _ in as_completed(future_list):
                    self._manager.ui_tick_export()
        else:
            fps = 1 / setting.frame_rate

            # Export alembic
            (export_path / 'texture').mkdir(parents=True, exist_ok=True)

            # Build alembic file
            archive = alembic.Abc.OArchive(
                str(export_path / f'{filename}.abc'), asOgawa=False
            )
            archive.setCompressionHint(1)

            # Add TimeSampling
            time_sampling = alembic.AbcCoreAbstract.TimeSampling(fps, fps / 2)
            mesh_obj = alembic.AbcGeom.OPolyMesh(archive.getTop(), filename)
            mesh = mesh_obj.getSchema()
            mesh.setTimeSampling(time_sampling)

            # Run
            with ProcessPoolExecutor() as executor:
                future_list = []
                frame_complete = {}

                for f in range(frame_range[0], frame_range[1] + 1):
                    offset_f = f - offset_frame
                    file_path = f'{load_path}{f:06d}.4df'

                    if not os.path.isfile(file_path):
                        self._manager.ui_tick_export()
                        continue

                    future_geo = executor.submit(
                        decode_fourd_frame,
                        offset_f,
                        file_path
                    )
                    future_list.append(future_geo)

                    future_tex = executor.submit(
                        export_texture,
                        offset_f,
                        file_path,
                        rf'{export_path}\texture\{offset_f:06d}.jpg'
                    )
                    future_list.append(future_tex)

                    frame_complete[offset_f] = 0

                frame_cache = {}
                current_f = 0
                for task in as_completed(future_list):
                    frame_num, data = task.result()
                    frame_complete[frame_num] += 1

                    if data is not None:
                        if current_f == frame_num:
                            vertex_arr, uv_arr = data
                            mesh_samp = build_mesh_sample(vertex_arr, uv_arr)
                            mesh.set(mesh_samp)
                        else:
                            frame_cache[frame_num] = data

                    if current_f in frame_cache:
                        vertex_arr, uv_arr = frame_cache[current_f]
                        mesh_samp = build_mesh_sample(vertex_arr, uv_arr)
                        mesh.set(mesh_samp)
                        del frame_cache[current_f]

                    if frame_complete[frame_num] == 2:
                        self._manager.ui_tick_export()
                        current_f += 1
                end_f = frame_range[1] - offset_frame
                if current_f - 1 != end_f:
                    for i in range(current_f, end_f + 1):
                        vertex_arr, uv_arr = frame_cache[i]
                        mesh_samp = build_mesh_sample(vertex_arr, uv_arr)
                        mesh.set(mesh_samp)
                        del frame_cache[i]
                        self._manager.ui_tick_export()

    def run(self):
        while True:
            task_type, tasks = self._queue.get()

            if task_type == 'cache_all':
                self.cache_all(tasks)
            elif task_type == 'export_all':
                self.export_all(tasks)

    def add_task(self, task_type, tasks):
        self._queue.put((task_type, tasks))
