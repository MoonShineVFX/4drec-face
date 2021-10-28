from PyQt5.Qt import Qt, QFileDialog

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.dialog import (
    CacheProgressDialog, ExportProgressDialog, ScreenshotProgressDialog
)
from master.ui.popup import popup
from master.ui.state import state

from .support_button import SupportButtonGroup


class ModelPanel(LayoutWidget):
    def __init__(self, decibel_meter, playback_control):
        super().__init__(spacing=12)
        self._playback_control = playback_control
        self._decibel_meter = decibel_meter
        self.buttons = None
        self._setup_ui()

        state.on_changed('key', self._on_key_pressed)

    def _setup_ui(self):
        self.buttons = SupportButtonGroup(
            ('Cache', 'Rig', 'Wireframe', 'Loop', 'Screenshot')
        )
        self.buttons.buttons['Cache'].clicked.connect(self._on_cache)
        self.buttons.buttons['Screenshot'].clicked.connect(
            self._on_take_screenshot
        )

        self.layout().addLayout(
            self.buttons
        )

        self.layout().addSpacing(24)

        button = PushButton(
            '  EXPORT', 'export', size=(180, 60)
        )
        button.clicked.connect(self._export_model)

        self.addWidget(button)

    def showEvent(self, event):
        self.layout().insertWidget(1, self._decibel_meter)
        self.layout().insertLayout(1, self._playback_control)

    def hideEvent(self, event):
        self.layout().removeItem(self._playback_control)
        self.layout().removeWidget(self._decibel_meter)

    def _on_cache(self):
        popup(dialog=CacheProgressDialog)

    def _on_take_screenshot(self):
        if state.get('playing'):
            state.set('playing', False)
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if directory is not None and directory != '':
            popup(dialog=ScreenshotProgressDialog, dialog_args=(directory,))

    def _on_key_pressed(self):
        if self.isHidden():
            return

        key = state.get('key')
        if key == Qt.Key_W:
            self.buttons.buttons['Wireframe'].animateClick()
        elif key == Qt.Key_R:
            self.buttons.buttons['Rig'].animateClick()
        elif key == Qt.Key_C:
            self.buttons.buttons['Cache'].animateClick()

    def _export_model(self):
        shot = state.get('current_shot')
        result = QFileDialog.getSaveFileName(
            self, 'Export Model', f'{shot.get_parent().name}-{shot.name}',
            'Alembic (*.abc);;Houdini (*.4dh);;Wavefront (*.obj)'
        )
        file_path, ext = result
        if file_path is not None and file_path != '':
            popup(dialog=ExportProgressDialog, dialog_args=(file_path,))
