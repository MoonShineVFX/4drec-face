import struct
import zlib
import numpy as np


class FourdrecGeo:
    @staticmethod
    def open(file_path: str):
        with open(file_path, "rb") as f:
            point_count, pos_size, uv_size = struct.unpack("III", f.read(12))
            pos_buf = f.read(pos_size)
            uv_buf = f.read(uv_size)

        # pos
        pos_data = zlib.decompress(pos_buf)
        pos_arr = np.frombuffer(pos_data, dtype=np.float32)

        # uv
        uv_data = zlib.decompress(uv_buf)
        uv_arr = np.frombuffer(uv_data, dtype=np.float32)
        return pos_arr, uv_arr

    @staticmethod
    def save(file_path: str, pos_arr: np.ndarray, uv_arr: np.ndarray):
        pos_arr_data = pos_arr.tobytes()
        point_count = int(len(pos_arr_data) / 3 / 4)
        pos_data = zlib.compress(pos_arr_data)
        uv_data = zlib.compress(uv_arr.tobytes())

        with open(file_path, "wb") as f:
            f.write(
                struct.pack("III", point_count, len(pos_data), len(uv_data))
            )
            f.write(pos_data)
            f.write(uv_data)
