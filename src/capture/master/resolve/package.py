import os
import lz4framed
import json
import numpy as np
import cv2
from pathlib import Path

from utility.setting import setting
from common.fourdrec_frame import FourdrecFrame
from utility.logger import log


class CompressedCache:
    def __init__(self, arr):
        self._shape = arr.shape
        self._type = arr.dtype
        self._data = lz4framed.compress(arr.tobytes())

    def load(self):
        data = lz4framed.decompress(self._data)
        arr = np.frombuffer(data, self._type)
        arr.shape = self._shape
        return arr

    def get_size(self):
        return len(self._data)


class ResolvePackage:
    def __init__(
        self, job_id, job_folder_path, resolution, frame, offset_frame
    ):
        self._geo_cache = None
        self._tex_cache = None
        self._job_id = job_id
        self._job_folder_path = job_folder_path
        self._real_frame = frame
        self._file_frame = (
            frame - offset_frame
        )  # offset_frame is job.get_frame_offset() + job.frame_range[0]
        self._resolution = resolution

    def get_name(self):
        return f"{self._job_id}_{self._real_frame:08d}"

    def get_meta(self):
        return self._job_id, self._real_frame

    def _cache_buffer(self, geo_data, texture_data):
        self._geo_cache = (
            CompressedCache(geo_data[0]),
            CompressedCache(geo_data[1]),
        )
        self._tex_cache = CompressedCache(texture_data)

    def get_cache_size(self):
        return (
            self._geo_cache[0].get_size()
            + self._geo_cache[1].get_size()
            + self._tex_cache.get_size()
        )

    def load(self):
        # If geo cache is not None, means already loaded.
        if self._geo_cache is not None:
            return True

        job_folder_path = Path(self._job_folder_path)
        output_folder = job_folder_path / setting.submit.output_folder_name

        frame_path = (
            output_folder / "frame" / f"{self._file_frame:04d}.4dframe"
        )

        # Old version, backward compatibility
        if not frame_path.exists():
            log.warning(f"4DFrame not found: {frame_path}")
            return None

        # Finally, load current version
        frame = FourdrecFrame(str(frame_path))
        pos_arr, uv_arr = frame.get_geometry_array()

        # Offset uv
        uv_arr[:, 1] = 1 - uv_arr[:, 1]

        self._cache_buffer(
            (pos_arr, uv_arr),
            self.optimize_texture(frame.get_texture_array()),
        )
        return True

    def optimize_texture(self, texture_data: np.ndarray):
        tex_res = texture_data.shape[0]
        # resize for better playback performance
        if tex_res > self._resolution:
            return cv2.resize(
                texture_data,
                dsize=(self._resolution, self._resolution),
                interpolation=cv2.INTER_CUBIC,
            )
        return texture_data

    def to_payload(self):
        geo_data = (self._geo_cache[0].load(), self._geo_cache[1].load())
        return (
            len(geo_data[0]),
            geo_data,
            self._tex_cache.load(),
            self._resolution,
        )


def build_camera_pos_list():
    with open("source/ui/camera.json") as f:
        clist = json.load(f)
    return np.array(clist, np.float32)
