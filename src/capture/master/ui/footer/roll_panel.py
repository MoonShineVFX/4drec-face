from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.popup import popup
from master.ui.dialog import ShotSubmitDialog, SubmitProgressDialog
from master.ui.state import state

from utility.define import SubmitOrder


class RollPanel(LayoutWidget):
    def __init__(self, playback_control, body_switcher, parent):
        super().__init__(spacing=12, parent=parent)
        self._playback_control = playback_control
        self._body_switcher = body_switcher
        self._setup_ui()

    def _setup_ui(self):
        self.addWidget(SubmitButton())

    def showEvent(self, event):
        self.layout().insertWidget(0, self._body_switcher)
        self.layout().insertLayout(1, self._playback_control)

    def hideEvent(self, event):
        self.layout().removeItem(self._playback_control)
        self.layout().removeWidget(self._body_switcher)


class SubmitButton(PushButton):
    def __init__(self):
        super().__init__("  SUBMIT", "submit", size=(180, 60))
        self.clicked.connect(self._submit)

        state.on_changed("current_shot", self._update_shot)

    def _update_shot(self):
        shot = state.get("current_shot")

        if shot is None or (shot.is_cali() and shot.is_submitted()):
            self.setEnabled(False)
            return

        self.setEnabled(True)

    def _submit(self):
        shot = state.get("current_shot")
        if not shot.is_cali():
            submit_order = popup(dialog=ShotSubmitDialog)
            if submit_order:
                popup(dialog=SubmitProgressDialog, dialog_args=(submit_order,))
        else:
            submit_order = SubmitOrder(
                name="cali_submit",
                frame_range=[0, 0],
                transfer_only=False,
                offset_frame=0,
                bypass_jpeg_transfer=False,
                resolve_only=False,
                no_cloud_sync=True,
                cali_path="",
                parms={},
            )
            state.cast("camera", "submit_shot", submit_order)
