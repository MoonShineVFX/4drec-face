from PyQt5.Qt import (
    QDialog, Qt, QLabel, QDialogButtonBox, QLineEdit, QHBoxLayout, QWidget,
    QSpinBox, QDoubleSpinBox, QScrollArea, QVBoxLayout
)

from utility.setting import setting

from master.ui.custom_widgets import (
    move_center, make_layout
)
from master.ui.state import state, get_slider_range


class HeaderLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HeaderLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ShotSubmitDialog(QDialog):
    _default = '''
    HeaderLabel {
      font-size: 20px;
    }

    HeaderLineEdit {
      font-size: 18px;
      min-height: 30px;
      padding: 4px 16px;
      max-width: 200px;
    }

    QDialogButtonBox {
      min-height: 30px;
    }
    
    QScrollArea {
        min-height: 180px;
    }
    
    QGroupBox {
        font-weight: 600;
    }
    QGroupBox:title {
        subcontrol-origin: margin;
        subcontrol-position: top;
        padding: 0px 8px 0px 4px;
    }
    '''

    def __init__(self, parent):
        super().__init__(parent)
        self._text_name = None
        self._text_frames = None
        self._parms = []
        self._comboBox = None
        self._export_only = False
        self._submit_button = None
        self._setup_ui()

        state.on_changed('opencue_status', self._update_server_state)

        self._check_server()


    def _setup_ui(self):
        self.setStyleSheet(self._default)
        shot = state.get('current_shot')
        self.setWindowTitle(f'Submit [{shot.name}]')

        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

        # Job Name
        name_layout = make_layout(spacing=24)
        label = HeaderLabel('Job Name')
        name_layout.addWidget(label)

        name = f'resolve_{len(shot.jobs) + 1}'
        self._text_name = HeaderLineEdit()
        self._text_name.setAlignment(Qt.AlignRight)
        self._text_name.setText(name)
        self._text_name.setPlaceholderText('Submit Job Name')
        name_layout.addWidget(self._text_name)

        layout.addLayout(name_layout)

        # Frame Range
        frame_range_layout = make_layout(spacing=24)
        label = HeaderLabel('Frame Range')
        frame_range_layout.addWidget(label)

        min_slider_value, max_slider_value = get_slider_range()
        self._text_frames = HeaderLineEdit()
        self._text_frames.setAlignment(Qt.AlignRight)
        self._text_frames.setText(f'{min_slider_value}-{max_slider_value}')
        self._text_frames.setPlaceholderText('0-10')
        frame_range_layout.addWidget(self._text_frames)
        layout.addLayout(frame_range_layout)

        # Submit Parameter
        submit_widget = QWidget()
        submit_control = QVBoxLayout()
        submit_parameters = {
            'match_photos_interval',
            'mesh_clean_faces_threshold',
            'smooth_model',
            'texture_size',
            'region_size'
        }
        for parm_name in submit_parameters:
            parm_value = setting.submit[parm_name]
            parm_widget = ShotSubmitParameter(parm_name, parm_value)
            submit_control.addLayout(parm_widget)
            self._parms.append(parm_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        submit_widget.setLayout(submit_control)
        scroll.setWidget(submit_widget)
        layout.addWidget(scroll)

        # 底部按鈕組
        self._buttons = QDialogButtonBox()
        self._submit_button = self._buttons.addButton('Submit', QDialogButtonBox.NoRole)
        self._submit_button.setEnabled(False)
        export_button = self._buttons.addButton('Export Only', QDialogButtonBox.NoRole)
        self._buttons.addButton('Cancel', QDialogButtonBox.RejectRole)
        self._submit_button.clicked.connect(lambda x: self._on_accept())
        export_button.clicked.connect(lambda x: self._on_accept(True))
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setLayout(layout)

        self.setMinimumSize(500, 560)
        move_center(self)

    def _on_accept(self, export_only=False):
        self._export_only = export_only
        self.accept.emit()

    def _check_server(self):
        state.cast(
            'project', 'check_opencue_server'
        )

    def _update_server_state(self):
        check_result = state.get('opencue_status')
        self._submit_button.setEnabled(check_result)

    def showEvent(self, event):
        event.accept()

    def closeEvent(self, event):
        event.accept()

    def get_result(self):
        offset_frame = state.get('offset_frame')

        frame_str = self._text_frames.text().strip()
        if '-' not in frame_str:
            start_frame_str, end_frame_str = frame_str, frame_str
        else:
            start_frame_str, end_frame_str = frame_str.split('-')

        start_frame = int(start_frame_str) + offset_frame
        end_frame = int(end_frame_str) + offset_frame

        parms = {}
        for parm_widget in self._parms:
            name, value = parm_widget.get_result()
            parms[name] = value

        return {
            'name': self._text_name.text(),
            'frame_range': [start_frame, end_frame],
            'offset_frame': offset_frame,
            'parms': parms,
            'export_only': self._export_only
        }


class ShotSubmitParameter(QHBoxLayout):
    def __init__(self, parm_name, parm_value):
        super().__init__()
        self._parm_name = parm_name
        self._parm_value = parm_value
        self._input_widget = None
        self._setup_ui()
        
    def _create_widget(self, value):
        if isinstance(value, str):
            widget = QLineEdit()
            widget.setText(value)
            widget.setPlaceholderText('String Val')
        elif isinstance(value, list):
            return [
                self._create_widget(v)
                for v in value
            ]
        else:
            if isinstance(value, int):
                widget = QSpinBox()
            else:
                widget = QDoubleSpinBox()
                decimal = str(value)[::-1].find('.')
                widget.setDecimals(decimal)
                widget.setSingleStep(pow(10, -decimal))

            widget.setMinimum(-9999999)
            widget.setMaximum(9999999)
            widget.setValue(value)

        widget.setFixedWidth(100)
        widget.setAlignment(Qt.AlignRight)
        return widget

    def _get_widget_value(self, widget):
        if isinstance(widget, list):
            return [self._get_widget_value(w) for w in widget]
        if isinstance(widget, QLineEdit):
            return widget.text()
        return widget.value()
        
    def _setup_ui(self):
        margin = 8
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(8)
        if self._parm_name is not None:
            label = QLabel(self._parm_name)
            self.addWidget(label)
        
        self._input_widget = self._create_widget(self._parm_value)

        if isinstance(self._input_widget, list):
            for widget in self._input_widget:
                self.addWidget(widget)
        else:
            self.addWidget(self._input_widget)

    def get_result(self):
        value = self._get_widget_value(self._input_widget)
        return self._parm_name, value
