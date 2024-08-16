from PyQt5.Qt import Qt, QFileDialog
import subprocess

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.dialog import ExportProgressDialog
from master.ui.popup import popup
from master.ui.state import state

from utility.setting import setting


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
        shot = state.get("current_shot")

        result = QFileDialog.getSaveFileName(
            self,
            "Export Model",
            f"{setting.output.path}\\{shot.get_parent().name}-{shot.name}",
            "Alembic (*.abc)",
        )
        file_path, ext = result
        if file_path is not None and file_path != "":
            popup(dialog=ExportProgressDialog, dialog_args=(file_path,))
