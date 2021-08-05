import os
os.environ['4DREC_TYPE'] = 'MASTER'
from utility.opencue_bridge import OpenCueBridge


# OpenCueBridge.ensure_service()
# OpenCueBridge.ensure_show('mi_dance')

# os.environ['CUEBOT_HOSTS'] = 'localhost'
print(OpenCueBridge.check_server())