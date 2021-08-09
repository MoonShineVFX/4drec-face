import os
os.environ['4DREC_TYPE'] = 'MASTER'
from utility.opencue_bridge import OpenCueBridge


job_id = OpenCueBridge.submit(
    'mi_dance', '2-min', 'depend_fix', 'shottoken', 'show_t/shot_t/job_t', (13, 27)
)

print(job_id)

# job_id = 'e3ec1f66-2da4-4e3c-abdc-bda290cbfd17'
# print(OpenCueBridge.get_frame_list(job_id))