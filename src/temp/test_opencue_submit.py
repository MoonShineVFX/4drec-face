import os
os.environ['4DREC_TYPE'] = 'MASTER'
# from utility.opencue_bridge import OpenCueBridge
from capture.utility.setting import setting
from opencue import api
from opencue.wrappers.frame import Frame

# OpenCueBridge.ensure_service()
# OpenCueBridge.ensure_show('mi_dance')

# os.environ['CUEBOT_HOSTS'] = 'localhost'

job_id = '3f83d145-256e-4879-bcbc-f9a6ca592c65'
job = api.getJob(job_id)

layer = job.getLayers()[-1]
frames = layer.getFrames()
for frame in frames:
    state = Frame.FrameState(frame.data.state)
    print(state.name.__class__)
