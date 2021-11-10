from PyQt5.Qt import Qt, QPushButton, QIcon

from utility.define import BodyMode

from master.ui.custom_widgets import LayoutWidget
from master.ui.state import state, EntityBinder
from master.ui.resource import icons


class BodySwitcher(LayoutWidget, EntityBinder):
    def __init__(self, parent=None):
        super().__init__(parent=parent, alignment=Qt.AlignCenter)
        self._switches = []
        self._setup_ui()
        self._state = None
        state.on_changed('current_shot', self._update)

    def _setup_ui(self):
        for mode in BodyMode:
            button = BodySwitchButton(mode)
            self.addWidget(button)
            self._switches.append(button)

    def _update(self):
        shot = state.get('current_shot')
        if shot is None:
            return

        self.bind_entity(shot, self._update)

        if shot.state != self._state:
            self._state = shot.state

        for button in self._switches:
            button.show()

        self.setVisible(shot.state != 0)

        if shot.state == 0:
            self._set((0, 3, 2))
        elif shot.state == 1 or shot.is_cali():
            self._set((3, 0, 2))
        else:
            self._set((3, 1, 0))

    def _set(self, set_list):
        for i, button in zip(set_list, self._switches):
            button.setEnabled(i < 2)
            button.setVisible(i < 3)

            if i == 0:
                button.on_clicked()


class BodySwitchButton(QPushButton):
    _default = '''
    * {
      border: 1px solid palette(dark);
    }

    *:hover {
      background-color: palette(base);
    }

    *:checked {
      color: palette(bright-text);
      background-color: palette(dark);
      font-weight: 500;
    }

    *:disabled {
      color: palette(dark);
    }

    '''

    def __init__(self, mode):
        super().__init__()
        self._mode = mode
        self.clicked.connect(self.on_clicked)
        state.on_changed('body_mode', self._update)
        self._icon = None
        self._icon_hl = None
        self._setup_ui()
        self._update()

    def _setup_ui(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(80, 60)
        self.setStyleSheet(self._default)
        self.setCheckable(True)
        text = 'model' if self._mode is BodyMode.MODEL else 'roll'
        self._icon = QIcon(icons.get(text))
        self._icon_hl = QIcon(icons.get(text + '_hl'))
        self.setIconSize(self._icon.availableSizes()[0])

    def _update(self):
        self.setChecked(self._mode is state.get('body_mode'))
        if self.isChecked():
            self.setIcon(self._icon_hl)
        else:
            self.setIcon(self._icon)

    def on_clicked(self):
        if self._mode is state.get('body_mode'):
            self.setChecked(True)
        else:
            state.set('body_mode', self._mode)
