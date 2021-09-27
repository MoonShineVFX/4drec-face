from PyQt5.Qt import QFileDialog

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.dialog import CacheProgressDialog
from master.ui.popup import popup
from master.ui.dialog import ShotSubmitDialog, SubmitProgressDialog
from master.ui.state import state

from utility.define import SubmitOrder

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
        super().__init__('  SUBMIT', 'submit', size=(180, 60))
        self.clicked.connect(self._submit)

        state.on_changed('current_shot', self._update_shot)

    def _update_shot(self):
        shot = state.get('current_shot')

        if shot is None or (
            shot.is_cali() and shot.is_submitted()
        ):
            self.setEnabled(False)
            return

        self.setEnabled(True)

    def _submit(self):
        shot = state.get('current_shot')
        if not shot.is_cali():
            submit_order = popup(dialog=ShotSubmitDialog)
            if submit_order:
                popup(
                    dialog=SubmitProgressDialog,
                    dialog_args=(submit_order,)
                )
        else:
            submit_order = SubmitOrder(
                'cali_submit',
                [0, 0],
                False,
                0,
                '',
                {}
            )
            state.cast(
                'camera',
                'submit_shot',
                submit_order
            )
