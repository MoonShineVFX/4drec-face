import subprocess

from PyQt5.Qt import Qt

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.state import state
from utility.define import UIEventType


class ModelPanel(LayoutWidget):
    def __init__(self, playback_control, body_switcher, parent):
        super().__init__(spacing=12, parent=parent)
        self._playback_control = playback_control
        self._body_switcher = body_switcher
        self.buttons = None
        self._setup_ui()

    def _setup_ui(self):
        button = PushButton("  OPEN", "export", size=(180, 60))
        button.clicked.connect(self._open_folder)
        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(self._export)
        self.addWidget(button)

    def showEvent(self, event):
        self.layout().insertWidget(0, self._body_switcher)
        self.layout().insertLayout(1, self._playback_control)

    def hideEvent(self, event):
        self.layout().removeItem(self._playback_control)
        self.layout().removeWidget(self._body_switcher)

    def _open_folder(self):
        job = state.get("current_job")
        job_path = job.get_folder_path().replace("/", "\\")
        # Open using explorer
        subprocess.Popen(f'explorer "{job_path}"')

    def _export(self):
        job = state.get("current_job")
        is_success = job.submit_for_alembic_export()

        from master.ui import ui
        if is_success:
            ui.dispatch_event(
                UIEventType.NOTIFICATION,
                {
                    "title": "Export Success",
                    "description": "Export job has been submitted successfully.",
                },
            )
        else:
            ui.dispatch_event(
                UIEventType.NOTIFICATION,
                {
                    "title": "Export Failed",
                    "description": "Export job submission failed.",
                },
            )
