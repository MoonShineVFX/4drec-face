from common.fourd_frame import FourdFrameManager
import numpy as np
import cv2


for i in range(3000, 3031):
    load_path = rf'G:\submit\demo0318\shots\shot_9\jobs\resolve_1\output\00{i:4d}.4df'
    fourd_frame = FourdFrameManager.load(load_path)

    export_path = r'C:\Users\eli.hung\WebstormProjects\web-gl-pftest'

    geo = fourd_frame.get_geo_data()

    with open(export_path + rf'\resource\geo_{i:4d}.bin', 'wb') as f:
        f.write(np.ascontiguousarray(geo[0]))

    with open(export_path + rf'\resource\uv_{i:4d}.bin', 'wb') as f:
        f.write(np.ascontiguousarray(geo[1]))

    tex_data = cv2.resize(
        fourd_frame.get_texture_data(),
        dsize=(
            2048,
            2048
        ),
        interpolation=cv2.INTER_CUBIC
    )

    with open(export_path + rf'\resource\texture_{i:4d}.bin', 'wb') as f:
        f.write(tex_data)
