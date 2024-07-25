from PyQt5.Qt import QMainWindow, QApplication, Qt, QWidget

from utility.message import message_manager
from utility.define import (UIEventType, BodyMode, CameraState,
                            MessageType, AudioSource)
from utility.logger import log


class MainWindow(QMainWindow):
    """主介面總成"""
    _default = 'MainWindow {background-color: palette(dark)}'

    def __init__(self, splash):
        super().__init__()

        # 基礎屬性
        self.setWindowTitle('4DREC [FACE]')  # 程式名稱
        self._second_screen = None
        self._splash = splash

        # 綁定事件
        from .state import state
        self._state = state
        self.dispatch_event = state.event.dispatch
        self.get_state = state.get
        state.event.on_receive.connect(self._on_receive_event)
        state.on_changed('project_list_dialog', self._on_project_list_open)
        state.on_changed('second_screen', self._on_second_screen_toggle)

        # UI
        self._setup_ui()
        self._setChildrenFocusPolicy(Qt.NoFocus)

    def _setChildrenFocusPolicy (self, policy):
        def recursiveSetChildFocusPolicy (parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)
        recursiveSetChildFocusPolicy(self)

    def _setup_ui(self):
        log.info('create widgets')
        """創建介面物件"""
        from .custom_widgets import LayoutWidget, make_layout
        from .header import Header
        from .body import Body
        from .footer import Footer
        from .sidebar import Sidebar
        from .dialog import SecondScreenView

        self.setStyleSheet(self._default)
        log.info('finish widgets')

        # 尺寸
        self.setGeometry(100, 80, 1520, 850)

        # 版面
        widget = LayoutWidget(parent=self, horizon=False)

        hlayout = make_layout()
        vlayout = make_layout(horizon=False)

        vlayout.addWidget(Body(self))
        vlayout.addWidget(Footer(self))

        hlayout.addWidget(Sidebar(self))
        hlayout.addLayout(vlayout)

        # 設定
        widget.addWidget(Header(self))
        widget.addLayout(hlayout)

        self.setCentralWidget(widget)

        # 置中
        self.layout().invalidate()
        self.layout().activate()
        center = self.rect().center()
        dcenter = QApplication.desktop().screenGeometry().center()
        self.move(dcenter - center)

        # 全螢幕預覽
        self._second_screen = SecondScreenView(self)

    def _on_receive_event(self, event):
        """事件接收回調

        Args:
            event: UIEvent

        """
        state = self._state

        if event.type is UIEventType.UI_SHOW:
            self.show()
            self._splash.close()
        elif event.type is UIEventType.UI_CONNECT:
            state.connect(event.get_payload())

        elif event.type is UIEventType.CAMERA_STATE:
            from .resource import icons
            pixmap = None
            camera_id, camera_state = event.get_payload()
            if camera_state is CameraState.STANDBY:
                pixmap = icons.get('connect_stdby')
            elif camera_state is CameraState.CLOSE:
                pixmap = icons.get('connect_close')
            elif camera_state is CameraState.OFFLINE:
                pixmap = icons.get('connect_none')
            if pixmap:
                state.set(f'pixmap_{camera_id}', pixmap)

        elif event.type is UIEventType.CAMERA_PIXMAP:
            camera_id, pixmap, is_live_view = event.get_payload()
            body_mode = state.get('body_mode')
            if is_live_view and body_mode is not BodyMode.LIVEVIEW:
                return
            elif not is_live_view and body_mode is BodyMode.LIVEVIEW:
                return
            state.set(f'pixmap_{camera_id}', pixmap)
            if state.get('closeup_camera') == camera_id:
                state.set('pixmap_closeup', pixmap)

        elif event.type is UIEventType.CAMERA_PARAMETER:
            parm_name, value, affect_slider = event.get_payload()
            if affect_slider:
                state.set('parm_outside', True)
            state.set(parm_name, value)
            if affect_slider:
                state.set('parm_outside', False)

        elif event.type is UIEventType.PROJECTS_INITIALIZED:
            state.set('projects', event.get_payload())

        elif event.type is UIEventType.PROJECT_SELECTED:
            project = event.get_payload()
            state.set('current_project', project)

            if project:
                shots = project.shots
            else:
                shots = []

            state.set('shots', shots)

        elif event.type is UIEventType.PROJECT_MODIFIED:
            state.set('projects', event.get_payload())

        elif event.type is UIEventType.SHOT_MODIFIED:
            state.set('shots', event.get_payload())

        elif event.type is UIEventType.SHOT_SELECTED:
            shot = event.get_payload()
            state.set('current_shot', shot)

            if shot:
                jobs = shot.jobs
            else:
                jobs = []

            state.set('jobs', jobs)

        elif event.type is UIEventType.JOB_MODIFIED:
            state.set('jobs', event.get_payload())

        elif event.type is UIEventType.JOB_SELECTED:
            state.set('current_job', event.get_payload())

        elif event.type is UIEventType.TRIGGER:
            is_trigger = event.get_payload()
            state.set('trigger', is_trigger)

        elif event.type is UIEventType.LIVE_VIEW:
            state.set('live_view', event.get_payload())

        elif event.type is UIEventType.UI_STATUS:
            state.set('status', event.get_payload())

        elif event.type is UIEventType.RECORDING:
            state.set('recording', event.get_payload())

        elif event.type is UIEventType.NOTIFICATION:
            payload = event.get_payload()
            from .popup import notify
            notify(self, **payload)

        elif event.type is UIEventType.RESOLVE_GEOMETRY:
            state.set('opengl_data', event.get_payload())

        elif event.type is UIEventType.CLOSEUP_CAMERA:
            state.set('closeup_camera', event.get_payload())

        elif event.type is UIEventType.CAMERA_FOCUS:
            state.set('Focus', event.get_payload())

        elif event.type is UIEventType.DEADLINE_STATUS:
            state.set('deadline_status', event.get_payload())

        elif event.type is UIEventType.HAS_ARDUINO:
            state.set('has_arduino', event.get_payload())

        elif event.type is UIEventType.CALI_LIST:
            state.set('cali_list', event.get_payload())

        elif event.type is UIEventType.TICK_EXPORT:
            state.set('tick_export', event.get_payload())

        elif event.type is UIEventType.TICK_SUBMIT:
            state.set('tick_submit', event.get_payload())

        elif event.type is UIEventType.AUDIO_DECIBEL:
            source, db = event.get_payload()
            body_mode = state.get('body_mode')
            if source is AudioSource.Mic and body_mode is BodyMode.LIVEVIEW:
                state.set('audio_decibel', db)
            elif source is AudioSource.File and body_mode is not BodyMode.LIVEVIEW:
                state.set('audio_decibel', db)

        elif event.type is UIEventType.MIC_OPEN:
            state.set('is_mic_open', True)

    def _on_project_list_open(self):
        if self._state.get('project_list_dialog'):
            from .projects import ProjectListDialog
            from .popup import popup
            popup(self, dialog=ProjectListDialog)

    def _on_second_screen_toggle(self):
        for tl in QApplication.topLevelWidgets():
            name = tl.__class__.__name__
            if name == 'QFrame':
                print(tl.isVisible())
                # tl.setVisible(True)
        return
        toggle = self._state.get('second_screen')
        if toggle:
            self._second_screen.show()
            self._second_screen.windowHandle().setScreen(QApplication.screens()[1])
            self._second_screen.showFullScreen()
        else:
            self._second_screen.close()

    def keyPressEvent(self, event):
        self._state.set('key', event.key())

    def closeEvent(self, event):
        """關閉視窗"""
        message_manager.send_message(MessageType.MASTER_DOWN, is_local=True)
