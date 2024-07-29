import struct
import zlib
import numpy as np
from PIL import Image
from io import BytesIO
import os

HEADER_FORMAT = "III"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class FourdrecFrame:
    def __init__(self, file_path: str):
        with open(file_path, "rb") as f:
            point_count, pos_size, uv_size = struct.unpack(
                HEADER_FORMAT, f.read(HEADER_SIZE)
            )
        self.file_path = file_path
        self.point_count = point_count
        self.pos_size = pos_size
        self.uv_size = uv_size
        self.texture_size = (
            os.path.getsize(file_path) - HEADER_SIZE - pos_size - uv_size
        )

    def get_geometry_array(self):
        with open(self.file_path, "rb") as f:
            f.seek(HEADER_SIZE)
            pos_buf = f.read(self.pos_size)
            uv_buf = f.read(self.uv_size)
        # pos
        pos_data = zlib.decompress(pos_buf)
        pos_arr = np.frombuffer(pos_data, dtype=np.float32)
        pos_arr.shape = (self.point_count, 3)

        # uv
        uv_data = zlib.decompress(uv_buf)
        uv_arr = np.copy(np.frombuffer(uv_data, dtype=np.float32))
        uv_arr.shape = (self.point_count, 2)

        return [pos_arr, uv_arr]

    def get_texture_array(self):
        with open(self.file_path, "rb") as f:
            f.seek(HEADER_SIZE + self.pos_size + self.uv_size)
            tex_buf = f.read(self.texture_size)
        tex = Image.open(BytesIO(tex_buf))
        tex_arr = np.array(tex)
        return tex_arr

    @staticmethod
    def save(
        file_path: str,
        pos_arr: np.ndarray,
        uv_arr: np.ndarray,
        tex_arr: np.ndarray,
    ):
        # Geo
        pos_arr_data = pos_arr.tobytes()
        point_count = int(len(pos_arr_data) / 3 / 4)
        pos_data = zlib.compress(pos_arr_data)
        uv_data = zlib.compress(uv_arr.tobytes())

        # Tex
        tex = Image.fromarray(tex_arr, mode="RGB")
        tex_bytes = BytesIO()
        tex.save(tex_bytes, format="JPEG", quality=85)

        with open(file_path, "wb") as f:
            f.write(
                struct.pack("III", point_count, len(pos_data), len(uv_data))
            )
            f.write(pos_data)
            f.write(uv_data)
            f.write(tex_bytes.getvalue())
        tex_bytes.close()
