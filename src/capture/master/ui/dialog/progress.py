from PyQt5.Qt import QDialog, QProgressBar, Qt
from pathlib import Path
import re

from utility.setting import setting
from utility.define import BodyMode, SubmitOrder

from master.ui.custom_widgets import move_center, make_layout
from master.ui.state import state, get_slider_range


class ProgressDialog(QDialog):
    _default = """
    QProgressBar {
      min-width: 350px;
    }
    """

    def __init__(self, parent, title, total_progress):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._total_progress = total_progress

        self._progress_bar = None

        self._setup_ui()
        self._prepare()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint
        )

        self.setStyleSheet(self._default)
        layout = make_layout(horizon=False, margin=24, spacing=24)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, self._total_progress)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat(r"%p% (%v/%m)")
        self._progress_bar.setValue(0)

        layout.addWidget(self._progress_bar)

        self.setLayout(layout)
        move_center(self)

    def _prepare(self):
        return

    def increase(self, step=1):
        self._progress_bar.setValue(self._progress_bar.value() + step)

        if self._progress_bar.value() == self._progress_bar.maximum():
            self.close()

    def _on_show(self):
        return

    def _on_close(self):
        return

    def showEvent(self, event):
        self._on_show()
        event.accept()

    def closeEvent(self, event):
        self._on_close()
        event.accept()


class ScreenshotProgressDialog(ProgressDialog):
    def __init__(self, parent, export_path):
        self._export_path = export_path
        self._range = get_slider_range()
        super().__init__(
            parent, "Grab Preview", self._range[1] - self._range[0] + 1
        )

    def _prepare(self):
        project = state.get("current_project")
        shot = state.get("current_shot")
        job = state.get("current_job")
        folder_name = f"{project.name}_{shot.name}_{job.name}"
        folder_name = re.sub(r"[^\w\d-]", "_", folder_name)
        path = Path(self._export_path)
        path = path.joinpath(folder_name)
        path.mkdir(exist_ok=True, parents=True)
        state.set("screenshot_export_path", str(path))
        state.on_changed("tick_update_geo", self._play_next)

    def _on_show(self):
        state.set("current_slider_value", self._range[0])

    def _on_close(self):
        state.set("screenshot_export_path", None)

    def _play_next(self):
        self.increase()
        state.set(
            "current_slider_value", self._progress_bar.value() + self._range[0]
        )


class CacheProgressDialog(ProgressDialog):
    def __init__(self, parent):
        super().__init__(parent, "Caching", self._get_total_progress())

    def _get_total_progress(self):
        shot = state.get("current_shot")
        body_mode = state.get("body_mode")
        if body_mode is BodyMode.PLAYBACK:
            count = len(setting.get_working_camera_ids())

            if state.get("closeup_camera"):
                count += 1

            return (shot.frame_range[1] - shot.frame_range[0] + 1) * count
        elif body_mode is BodyMode.MODEL:
            return state.get("playbar_frame_count")

    def _prepare(self):
        body_mode = state.get("body_mode")
        if body_mode is BodyMode.PLAYBACK:
            for camera_id in setting.get_working_camera_ids():
                state.on_changed(f"pixmap_{camera_id}", self.increase)
            if state.get("closeup_camera"):
                state.on_changed("pixmap_closeup", self.increase)
        elif body_mode is BodyMode.MODEL:
            state.on_changed("opengl_data", self.increase)

    def _on_show(self):
        body_mode = state.get("body_mode")
        if body_mode is BodyMode.PLAYBACK:
            state.cast(
                "camera", "cache_whole_shot", state.get("closeup_camera")
            )
        elif body_mode is BodyMode.MODEL:
            state.cast(
                "resolve", "cache_whole_job", state.get("texture_resolution")
            )
        state.set("caching", True)

    def _on_close(self):
        state.set("caching", False)


class SubmitProgressDialog(ProgressDialog):
    def __init__(self, parent, submit_order: SubmitOrder):
        camera_count = len(setting.get_working_camera_ids())
        message = "Exporting" if submit_order.transfer_only else "Submitting"
        super().__init__(
            parent, message, submit_order.get_frame_length() * camera_count
        )
        self._submit_order = submit_order

    def _prepare(self):
        state.on_changed("tick_submit", self._on_submit)

    def _on_submit(self):
        submit_count = state.get("tick_submit")
        current_count = self._progress_bar.value()
        if current_count >= submit_count:
            return
        self.increase(submit_count - current_count)

    def _on_show(self):
        state.cast("camera", "submit_shot", self._submit_order)
