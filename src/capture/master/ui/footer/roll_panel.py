from PyQt5.Qt import QFileDialog

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.dialog import CacheProgressDialog
from master.ui.popup import popup
from master.ui.dialog import ShotSubmitDialog, SubmitProgressDialog
from master.ui.state import state

from .support_button import SupportButtonGroup


class RollPanel(LayoutWidget):
    def __init__(self, playback_control):
        super().__init__(spacing=24)
        self._playback_control = playback_control
        self._setup_ui()

    def _setup_ui(self):
        buttons = SupportButtonGroup(('Serial', 'Cache', 'Crop'))
        buttons.buttons['Cache'].clicked.connect(self._on_cache)

        self.addLayout(
            buttons
        )

        self.addWidget(SubmitButton())

    def showEvent(self, event):
        self.layout().insertLayout(1, self._playback_control)

    def hideEvent(self, event):
        self.layout().removeItem(self._playback_control)

    def _on_cache(self):
        popup(dialog=CacheProgressDialog)


class SubmitButton(PushButton):
    def __init__(self):
        super().__init__(self._connect_text, '  SUBMIT', size=(180, 60))
        self.clicked.connect(self._submit)

        state.on_changed('current_shot', self._update_shot)

    def _update_shot(self):
        shot = state.get('current_shot')

        if shot is None:
            return

        self.setEnabled(True)

    def _submit(self):
        result = popup(dialog=ShotSubmitDialog)

        if result:
            popup(
                dialog=SubmitProgressDialog,
                dialog_args=(
                    result['name'],
                    result['frame_range'],
                    result['export_only'],
                    result['offset_frame'],
                    result['parms']
                )
            )
