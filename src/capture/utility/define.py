from enum import Enum, auto
from dataclasses import dataclass, field


class EntityEvent(Enum):
    """實體事件

    實體觸發的事件類別

    """

    CREATE = auto()
    REMOVE = auto()
    MODIFY = auto()
    PROGRESS = auto()


class UIEventType(Enum):
    """事件類型"""

    UI_SHOW = auto()
    UI_CONNECT = auto()
    UI_STATUS = auto()
    CAMERA_STATE = auto()
    CAMERA_PIXMAP = auto()  # 圖像傳送
    CAMERA_PARAMETER = auto()  # 相機參數
    CLOSEUP_CAMERA = auto()
    CAMERA_FOCUS = auto()
    PROJECTS_INITIALIZED = auto()
    PROJECT_MODIFIED = auto()
    PROJECT_SELECTED = auto()
    SHOT_MODIFIED = auto()
    SHOT_SELECTED = auto()
    JOB_MODIFIED = auto()
    JOB_SELECTED = auto()
    TRIGGER = auto()
    LIVE_VIEW = auto()
    RECORDING = auto()
    NOTIFICATION = auto()
    RESOLVE_GEOMETRY = auto()
    DEADLINE_STATUS = auto()
    HAS_ARDUINO = auto()
    CALI_LIST = auto()
    TICK_EXPORT = auto()
    TICK_SUBMIT = auto()
    AUDIO_DECIBEL = auto()
    MIC_OPEN = auto()


class BodyMode(Enum):
    LIVEVIEW = "LIVE"
    PLAYBACK = "ROLL"
    MODEL = "3D"


class CameraState(Enum):
    """相機運作狀態"""

    CAPTURING = auto()  # 擷取中
    STANDBY = auto()  # 等待觸發
    CLOSE = auto()  # 已關閉擷取
    OFFLINE = auto()


class CameraRotation(Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NONE = "NONE"


class CameraLibraryTask(Enum):
    IMPORT = auto()
    REQUEST = auto()


class CameraCacheType(Enum):
    ORIGINAL = auto()
    THUMBNAIL = auto()


class MessageType(Enum):
    RETRIGGER = auto()

    LIVE_VIEW_IMAGE = auto()
    # {camera_id}

    TOGGLE_LIVE_VIEW = auto()
    # {camera_ids[], quality, scale_length}

    TOGGLE_RECORDING = auto()
    # {is_start, shot_id}

    GET_SHOT_IMAGE = auto()
    # {camera_id, shot_id, frame, quality, scale_length}

    SHOT_IMAGE = auto()
    # {camera_id, shot_id, frame, quality, scale_length, download}

    SLAVE_DOWN = auto()

    MASTER_UP = auto()

    MASTER_DOWN = auto()

    CAMERA_STATUS = auto()
    # {camera_id: status,}

    CAMERA_PARM = auto()
    # {camera_parm: (name, value)}

    RECORD_REPORT = auto()
    # {camera_id, shot_id, missing_frames, frame_range, size}

    REMOVE_SHOT = auto()
    # {shot_id}

    SUBMIT_SHOT = auto()
    # {shot_id, frame_range}

    SUBMIT_REPORT = auto()
    # {camera_id, shot_id, progress}

    SLAVE_ERROR = auto()
    # {slave_name: str, error_message: str, require_restart: bool}

    SLAVE_RESTART = auto()
    # {slave_name: str}


class TaskState(Enum):
    QUEUED = 2
    SUSPENDED = 3
    RENDERING = 4
    COMPLETED = 5
    FAILED = 6
    PENDING = 8


class AudioSource(Enum):
    Mic = auto()
    File = auto()


@dataclass
class SubmitOrder:
    name: str
    frame_range: [int]
    transfer_only: bool
    offset_frame: int
    bypass_jpeg_transfer: bool
    resolve_only: bool
    no_cloud_sync: bool
    cali_path: str = ""
    parms: dict = field(default_factory=dict)

    def get_frame_length(self):
        return self.frame_range[1] - self.frame_range[0] + 1

    def get_offset_frame_range(self):
        return (
            self.frame_range[0] - self.offset_frame,
            self.frame_range[1] - self.offset_frame,
        )
