from utility.setting import setting
if setting.is_testing():
    from ._mock import OpenCueBridge
else:
    from .opencue_bridge import OpenCueBridge
