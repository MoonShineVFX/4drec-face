from utility.define import CameraState
from utility.delay_executor import DelayExecutor

from .library import CameraLibrary


class CameraProxy:
    """相機代理

    對應 slave 端的相機，處理狀態變化跟該相機拍攝的圖像處理

    Args:
        camera_id: 相機 ID
        on_state_changed: 相機狀態改變的回調

    """

    def __init__(self, camera_id, on_state_changed):
        self._id = camera_id

        self._status = {
            "state": CameraState.OFFLINE,  # 相機 state
            "perf_bias": -1,  # 實際擷取的張數誤差(秒)
            "current_frame": -1,  # 目前擷取的相機格數
            "record_frames_count": -1,  # 錄製的格數
        }

        self._library = CameraLibrary()  # 相機快取圖庫
        self._delay = DelayExecutor(1)

        # 連結自身狀態
        self._on_state_changed = on_state_changed

        # 連結 library
        self.on_image_received = self._library.on_image_received

    def __getattr__(self, prop):
        return self._status[prop]

    def set_offline(self):
        self.update_status({"state": CameraState.OFFLINE}, True)

    def is_offline(self):
        return self.state is CameraState.OFFLINE

    def update_status(self, status, from_offline=False):
        """更新相機狀態

        Args:
            status: 相機狀態

        """
        if not from_offline:
            self._delay.execute(self.set_offline)

        # 轉為相機狀態 Enum
        status["state"] = CameraState(status["state"])

        # 狀態是否改變
        is_state_changed = (
            status["state"] != self.state
            or status["state"] is CameraState.OFFLINE
        )

        # 如果要更新的 state 一樣而且不是擷取的狀況，不更新狀態
        if status["state"] is not CameraState.CAPTURING:
            if not is_state_changed:
                return

        self._status.update(status)

        if is_state_changed:
            self._on_state_changed(self)
            self._library.on_image_received(
                {"state": status["state"], "camera_id": self._id}, True
            )

    def get_id(self):
        """取得相機 ID"""
        return self._id

    def import_image(self, *args, **kwargs):
        self._image_buffers.import_image(*args, **kwargs)

    def get_shot_image(self, *args, **kwargs):
        self._image_buffers.get_shot_image(*args, **kwargs)

    def on_image_requested(
        self,
        camera_id,
        shot_id,
        frame,
        quality,
        scale_length,
        delay,
        shot_path,
    ):
        offline_path = None
        if self.is_offline():
            offline_path = (
                f"{shot_path}/images/{camera_id}/{camera_id}_{frame:06d}.jpg"
            )

        self._library.on_image_requested(
            camera_id,
            shot_id,
            frame,
            quality,
            scale_length,
            delay,
            offline_path,
        )
