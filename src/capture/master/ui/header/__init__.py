from PyQt5.Qt import Qt, QFileDialog

from utility.define import BodyMode

from master.ui.custom_widgets import LayoutWidget, make_layout
from master.ui.dialog import CacheProgressDialog, ScreenshotProgressDialog
from master.ui.popup import popup
from master.ui.state import state

from .project_title import ProjectTitle
from .status_indicator import StatusIndicator
from .support_button import SupportButtonGroup


class Header(LayoutWidget):
    _default = 'Header {background-color: palette(base)}'

    def __init__(self, parent):
        super().__init__(spacing=16, parent=parent)
        self._command_layout = None

        self._live_view_commands = SupportButtonGroup(('Serial', 'Calibrate', 'Focus'), self)

        self._roll_commands = SupportButtonGroup(('Serial', 'Cache', 'Crop'), self)
        self._roll_commands.buttons['Cache'].clicked.connect(self._on_cache)

        self._model_commands = SupportButtonGroup(
            ('Cache', 'Rig', 'Wireframe', 'Loop', 'Screenshot'), self
        )
        self._model_commands.buttons['Cache'].clicked.connect(self._on_cache)
        self._model_commands.buttons['Screenshot'].clicked.connect(
            self._on_take_screenshot
        )

        self._setup_ui()

        state.on_changed('body_mode', self._update)

    def _update(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.LIVEVIEW:
            self._command_layout.setCurrentIndex(0)
        elif body_mode is BodyMode.PLAYBACK:
            self._command_layout.setCurrentIndex(1)
        elif body_mode is BodyMode.MODEL:
            self._command_layout.setCurrentIndex(2)

    def _setup_ui(self):
        title_layout = make_layout(alignment=Qt.AlignLeft)
        title_layout.addWidget(ProjectTitle())

        self._command_layout = make_layout(
            alignment=Qt.AlignLeft, stack=True
        )
        self._command_layout.addWidget(self._live_view_commands)
        self._command_layout.addWidget(self._roll_commands)
        self._command_layout.addWidget(self._model_commands)

        status_layout = make_layout(
            alignment=Qt.AlignRight, margin=(0, 0, 0, 0)
        )
        status_layout.addWidget(StatusIndicator(self))

        self.addLayout(title_layout)
        self.addLayout(self._command_layout)
        self.addLayout(status_layout)

        self.setFixedHeight(65)
        self.setStyleSheet(self._default)

    def _on_cache(self):
        popup(dialog=CacheProgressDialog)

    def _on_take_screenshot(self):
        if state.get('playing'):
            state.set('playing', False)
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if directory is not None and directory != '':
            popup(dialog=ScreenshotProgressDialog, dialog_args=(directory,))
