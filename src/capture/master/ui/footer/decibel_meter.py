from PyQt5.Qt import (
    Qt, QProgressBar
)

from master.ui.state import state


class DecibelMeter(QProgressBar):
    def __init__(self):
        super(DecibelMeter, self).__init__()
        self.setOrientation(Qt.Vertical)
        self.setMinimum(-600)
        self.setMaximum(0)
        self._setup_ui()
        self._peak = 0

        state.on_changed('audio_decibel', self._update)

    def _setup_ui(self):
        self.setFixedWidth(12)
        self.setTextVisible(False)

    def _get_gradient(self):
        step = self.value() - self.minimum()
        duration = self.maximum() - self.minimum() + 1
        percent = step / duration
        if percent == 0:
            y = 0
        else:
            y = -1 / percent + 1
        style = f'''
        QProgressBar::chunk:vertical {{
            background: qlineargradient(
                x1: 0, y1: {y},
                x2: 0, y2: 1, 
                stop: 0.1 red, 
                stop: 0.3 yellow,
                stop: 0.6 green
            );
        }}
        '''
        if self._peak > 0:
            style += '''
            QProgressBar {
                border: 2px solid red;
            }
            '''
        return style

    def _update(self):
        if not self.isEnabled() or not self.isVisible():
            return

        real_decibel = state.get('audio_decibel')

        # Peak
        if real_decibel > -6:
            self._peak = 60
        elif self._peak != 0:
            self._peak -= 1

        # Progress
        decibel = int(real_decibel * 10)
        if decibel < self.minimum():
            value = self.minimum()
        elif decibel > self.maximum():
            value = self.maximum()
        else:
            value = decibel

        self.setStyleSheet(self._get_gradient())
        self.setValue(value)
