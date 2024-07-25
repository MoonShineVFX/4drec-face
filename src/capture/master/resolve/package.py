import os
import lz4framed
from utility.setting import setting
from common.fourd_frame import FourdFrameManager
import json
import numpy as np
import cv2
from pathlib import Path

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
    def __init__(self, job_id, job_folder_path, resolution, frame):
        self._geo_cache = None
        self._tex_cache = None
        self._job_id = job_id
        self._job_folder_path = job_folder_path
        self._real_frame = frame
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
        # if geo cache is not None, means already loaded.
        if self._geo_cache is not None:
            return True

        # Check version 3 first, geo folder and texture
        job_folder_path = Path(self._job_folder_path)
        geo_path = (
            job_folder_path / "output" / "geo" / f"{self._real_frame:04d}.geo"
        )

        # open file
        file_path = (
            f"{self._job_folder_path}/output/4df/{self._real_frame:06d}.4df"
        )

        if not os.path.isfile(file_path):
            # version 2, backward compatibility
            file_path = f"{self._job_folder_path}/export/4df/{self._real_frame:06d}.4df"

        if not os.path.isfile(file_path):
            # version 1, backward compatibility
            file_path = (
                f"{self._job_folder_path}/output/{self._real_frame:06d}.4df"
            )

        if not os.path.isfile(file_path):
            log.warning(f"4DF File not found: {file_path}")
            return None

        # Check file exists
        fourd_frame = FourdFrameManager.load(file_path)
        geo_data = fourd_frame.get_geo_data()
        tex_data = fourd_frame.get_texture_data()
        tex_res = fourd_frame.get_texture_resolution()

        # resize for better playback performance
        if tex_res > self._resolution:
            tex_data = cv2.resize(
                tex_data,
                dsize=(self._resolution, self._resolution),
                interpolation=cv2.INTER_CUBIC,
            )
        elif tex_res < self._resolution:
            self._resolution = tex_res

        self._cache_buffer(geo_data, tex_data)
        return True

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
