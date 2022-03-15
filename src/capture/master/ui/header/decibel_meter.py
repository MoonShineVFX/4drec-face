import math

from PyQt5.Qt import (
    Qt, QProgressBar
)

from master.ui.state import state


class DecibelMeter(QProgressBar):
    __max_db = 0
    __min_db = -60
    __warning_db = -6
    __warning_duration = 60
    __scale_ratio = 10

    def __init__(self):
        super(DecibelMeter, self).__init__()
        self.setOrientation(Qt.Vertical)
        self.setMinimum(self.__min_db * self.__scale_ratio)
        self.setMaximum(self.__max_db * self.__scale_ratio)
        self.setValue(self.__min_db * self.__scale_ratio)
        self._peak = 0
        self._setup_ui()

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
        if self._peak > self.__max_db:
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
        if real_decibel > self.__warning_db:
            self._peak = self.__warning_duration
        elif self._peak != self.__max_db:
            self._peak -= 1

        # Progress
        if math.isnan(real_decibel):
            return

        decibel = int(real_decibel * self.__scale_ratio)
        if decibel < self.minimum():
            value = self.minimum()
        elif decibel > self.maximum():
            value = self.maximum()
        else:
            value = decibel

        self.setStyleSheet(self._get_gradient())
        self.setValue(value)
