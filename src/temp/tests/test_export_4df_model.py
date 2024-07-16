from settings import SETTINGS
from project import ResolveProject
from define import ResolveStage
from pathlib import Path
from common.fourd_frame import FourdFrameManager


# export model
SETTINGS.initialize(
    192,
    # Redefined for preventing outside import
    ResolveStage.RESOLVE,
    r'G:\jobs\4cdd8d\87be91\3d9a44\job.yml'
)
SETTINGS.export_4df_path = Path(r'C:\Users\eli.hung\Desktop')
project = ResolveProject()

project.export_4df(project.get_current_chunk())


# save to 4dh
frame = FourdFrameManager.load(r'C:\Users\eli.hung\Desktop\035766.4df')
with open(r'C:\Users\eli.hung\Desktop\test.4dh', 'wb') as f:
    f.write(frame.get_houdini_data())
