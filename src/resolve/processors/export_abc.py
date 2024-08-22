from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import logging
from typing import Callable
import shutil
import alembic
import numpy as np
import imath
import imathnumpy

from common.fourdrec_frame import FourdrecFrame


class AlembicExporter:
    @staticmethod
    def export(
        output_path: str,
        start_frame: int,
        end_frame: int,
        export_path: str,
        on_progress: Callable[[float, str], None],
    ):
        # Ensure export path
        export_path = Path(export_path)
        export_alembic_path = export_path / "alembic"
        export_texture_path = export_path / "texture"
        export_alembic_path.mkdir(parents=True, exist_ok=True)
        export_texture_path.mkdir(parents=True, exist_ok=True)

        output_path = Path(output_path)

        # Export audio
        on_progress(1.0, "Export Audio")
        audio_path = output_path / "audio.wav"
        if audio_path.exists():
            audio_target_path = export_path / "audio.wav"
            shutil.copy(str(audio_path), str(audio_target_path))
        else:
            logging.warning(
                f"Audio {audio_path} not exists, skip audio conversion."
            )

        # Run
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_list = []
            progress_per_task = 99.0 / ((end_frame - start_frame + 1) * 2)

            for f in range(start_frame, end_frame + 1):
                frame_path = output_path / "frame" / f"{f:04d}.4dframe"

                if not frame_path.exists() or not frame_path.is_file():
                    on_progress(progress_per_task * 2, f"Skip frame {f}")
                    continue

                # Add geo decode task
                future_geo = executor.submit(
                    AlembicExporter.export_alembic,
                    f,
                    str(frame_path),
                    rf"{export_alembic_path}\{f:04d}.abc",
                )
                future_list.append(future_geo)

                # Add texture export task
                future_tex = executor.submit(
                    AlembicExporter.export_texture,
                    f,
                    str(frame_path),
                    rf"{export_texture_path}\{f:04d}.jpg",
                )
                future_list.append(future_tex)

            for task in as_completed(future_list):
                task_frame, task_type = task.result()
                on_progress(
                    progress_per_task,
                    f"Export frame {task_frame} ({task_type})",
                )

    @staticmethod
    def export_texture(frame_index: int, frame_path: str, export_path: str):
        frame = FourdrecFrame(frame_path)
        frame.export_texture(export_path)
        return frame_index, "texture"

    @staticmethod
    def export_alembic(frame_index: int, load_path: str, export_path: str):
        # load 4D
        frame = FourdrecFrame(load_path)

        vertex_arr, uv_arr = frame.get_geometry_array()

        uv_arr = uv_arr.copy()
        uv_arr = np.array(uv_arr, np.float64)

        # Build mesh sample
        mesh_samp = AlembicExporter.build_mesh_sample(vertex_arr, uv_arr)

        # Create alembic file
        archive = alembic.Abc.OArchive(export_path, asOgawa=True)
        archive.setCompressionHint(1)
        mesh_obj = alembic.AbcGeom.OPolyMesh(archive.getTop(), "scan_model")
        mesh = mesh_obj.getSchema()
        mesh.set(mesh_samp)

        return frame_index, "alembic"

    @staticmethod
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
