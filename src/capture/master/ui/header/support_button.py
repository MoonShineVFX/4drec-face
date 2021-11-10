from PyQt5.Qt import (
    Qt, QSize, QHBoxLayout
)

from master.ui.custom_widgets import ToolButton, LayoutWidget
from master.ui.state import state


class SupportButtonGroup(LayoutWidget):
    _checkable_list = [
        'Serial', 'Calibrate', 'Focus', 'Rig', 'Wireframe', 'Crop', 'Loop'
    ]

    def __init__(self, button_texts, parent):
        super().__init__(parent=parent)
        self._button_texts = button_texts
        self.buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        self.layout().setAlignment(Qt.AlignLeft)
        self.layout().setContentsMargins(0, 8, 0, 8)
        self.layout().setSpacing(8)

        for text in self._button_texts:
            checkable = text in self._checkable_list
            button = SupportButton(text, checkable)
            self.buttons[text] = button
            self.addWidget(button)


class SupportButton(ToolButton):
    def __init__(self, text, checkable=False):
        super().__init__(text, checkable, spacing=4)
        self.setFocusPolicy(Qt.NoFocus)
        self._text = text
        self.clicked.connect(self._on_click)
        if checkable:
            state.on_changed(text, self._update_check)

    def sizeHint(self):
        return QSize(70, 70)

    def _update_check(self):
        is_check = state.get(self._text)
        if is_check != self.isChecked():
            self.setChecked(is_check)

    def _on_click(self):
        if self.isCheckable():
            state.set(self._text, self.isChecked())
