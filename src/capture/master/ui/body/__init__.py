from utility.define import BodyMode

from master.ui.state import state
from master.ui.custom_widgets import LayoutWidget

from .model_view import ModelView
from .camera_view import CameraViewLayout


class Body(LayoutWidget):
    def __init__(self, parent):
        super().__init__(parent=parent, stack=True)
        self._setup_ui()
        state.on_changed('body_mode', self._update)
        state.on_changed('trigger', self._update)
        state.on_changed('live_view_size', self._update)
        state.on_changed('closeup_camera', self._update)

    def _update(self):
        body_mode = state.get('body_mode')

        if body_mode is BodyMode.MODEL:
            self.layout().setCurrentIndex(1)
        else:
            self.layout().setCurrentIndex(0)

        if body_mode is BodyMode.LIVEVIEW:
            state.cast('camera', 'offline')

            trigger = state.get('trigger')
            if trigger:
                state.cast(
                    'camera', 'live_view', True,
                    scale_length=state.get('live_view_size'),
                    close_up=state.get('closeup_camera')
                )
        elif state.get('live_view'):
            state.cast('camera', 'live_view', False)

    def _setup_ui(self):
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.addWidget(CameraViewLayout(self))
        self.addWidget(ModelView(self))

        self._update()
