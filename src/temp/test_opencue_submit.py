import os
os.environ['4DREC_TYPE'] = 'MASTER'
os.environ['CUEBOT_HOSTS'] = '192.168.29.10'
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
from utility.opencue_bridge import OpenCueBridge


job_id = OpenCueBridge.submit(
    'mi_dance', '2-min', 'depend_fix', 'shottoken', 'show_t/shot_t/job_t', (13, 27),
    99770, 'cali_id'
)

print(job_id)

# job_id = 'e3ec1f66-2da4-4e3c-abdc-bda290cbfd17'
# print(OpenCueBridge.get_frame_list(job_id))
