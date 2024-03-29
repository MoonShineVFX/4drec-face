from PyQt5.Qt import (
    Qt, QLabel, QThread, pyqtSignal, QPainterPath, QPixmap,
    QSlider, QRect, QPainter, QSize, QVBoxLayout, QColor, QBrush
)
from threading import Condition
from functools import partial
import math
from time import perf_counter

from utility.setting import setting
from utility.define import CameraCacheType, BodyMode, TaskState

from master.ui.state import state, EntityBinder, get_real_frame, step_pace
from master.ui.custom_widgets import LayoutWidget, make_layout, ToolButton


class PlaybackControl(QVBoxLayout):
    def __init__(self, parent):
        super().__init__()
        self._player = None
        self._entity = None
        self._playback_bar = None
        self._temp_parent = parent
        self._setup_ui()

        state.on_changed('current_slider_value', self._on_slider_value_changed)
        state.on_changed('closeup_camera', self._on_slider_value_changed)
        state.on_changed('texture_resolution', self._request_geometry)

        state.on_changed('body_mode', self._on_body_mode_changed)
        state.on_changed('current_shot', self._on_shot_changed)
        state.on_changed('current_job', self._on_job_changed)

        state.on_changed('key', self._on_key_pressed)

    def _on_body_mode_changed(self):
        new_body_mode = state.get('body_mode')
        if new_body_mode is BodyMode.MODEL:
            return
        elif new_body_mode is BodyMode.LIVEVIEW:
            self._entity = None
            return
        self._on_shot_changed()

    def _on_shot_changed(self):
        shot = state.get('current_shot')
        body_mode = state.get('body_mode')
        if shot is None or body_mode is BodyMode.MODEL:
            return
        self._entity = shot
        self._on_entity_changed()

    def _on_job_changed(self):
        job = state.get('current_job')
        body_mode = state.get('body_mode')
        if job is None or body_mode is BodyMode.PLAYBACK:
            self._on_shot_changed()
            return
        self._entity = job
        self._on_entity_changed()

    def _on_entity_changed(self):
        self._stop_function()

        self._playback_bar.on_entity_changed(self._entity)
        if self._entity is not None and self._entity.state != 0:
            self._on_slider_value_changed()

    def _setup_ui(self):
        self.setAlignment(Qt.AlignCenter)
        self.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)

        self._playback_bar = PlaybackBar()
        self.addWidget(self._playback_bar)

        layout = make_layout(alignment=Qt.AlignCenter, spacing=48)
        for source in ('clipleft', 'previous', 'play', 'next', 'clipright'):
            button = PlaybackButton(source, parent=self._playback_bar)
            button.clicked.connect(partial(self._on_click, source))
            layout.addWidget(button)

        self.addLayout(layout)

    def _on_slider_value_changed(self):
        if self._entity is None or not self.isEnabled():
            return

        slider_value = state.get('current_slider_value')
        real_frame = get_real_frame(slider_value)

        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            closeup_camera = state.get('closeup_camera')
            state.cast(
                'camera', 'request_shot_image', self._entity.get_id(),
                real_frame, closeup_camera=closeup_camera, delay=True
            )
        elif body_mode is BodyMode.MODEL:
            job = state.get('current_job')
            if job is None:
                return
            res = state.get('texture_resolution')
            state.cast(
                'resolve', 'request_geometry',
                self._entity, real_frame, res
            )

        shot = state.get('current_shot')
        if shot is None:
            return

        state.cast(
            'audio',
            'play_audio_file',
            shot.get_folder_path(), slider_value
        )

        self._playback_bar.on_slider_value_changed(slider_value)

    def _request_geometry(self):
        job = state.get('current_job')
        if job is None or self._entity is None:
            return

        slider_value = state.get('current_slider_value')
        frame = get_real_frame(slider_value)
        res = state.get('texture_resolution')

        state.cast(
            'resolve', 'request_geometry',
            self._entity, frame, res
        )

    def _stop_function(self):
        if state.get('playing'):
            state.set('playing', False)

        if state.get('Crop'):
            state.set('Crop', False)
            state.set('crop_range', [None, None])

        if state.get('Loop'):
            state.set('Loop', False)
            state.set('loop_range', [None, None])

    def _on_click(self, source):
        if source == 'previous':
            step_pace(forward=False)
        elif source == 'play':
            if state.get('playing'):
                state.set('playing', False)
                self._player = None
            else:
                self._player = ShotPlayer(
                    lambda: step_pace(stop=False)
                )
                state.set('playing', True)
        elif source == 'next':
            step_pace(forward=True)
        elif source == 'clipleft':
            self._on_clip_range(0)
        elif source == 'clipright':
            self._on_clip_range(1)

    def _on_clip_range(self, assign_idx):
        body_mode = state.get('body_mode')
        range_state = None
        if body_mode is BodyMode.PLAYBACK:
            range_state = 'crop_range'
        elif body_mode is BodyMode.MODEL:
            range_state = 'loop_range'
        clip_range = state.get(range_state)
        current_slider_value = state.get('current_slider_value')
        other_idx = abs(assign_idx - 1)
        other_frame = clip_range[other_idx]

        if other_idx == 1 and other_frame and current_slider_value > other_frame:
            return

        if other_idx == 0 and other_frame and current_slider_value < other_frame:
            return

        clip_range[assign_idx] = current_slider_value
        state.set(range_state, clip_range)

    def _on_key_pressed(self):
        if self.parentWidget() is None:
            return

        key = state.get('key')
        if key == Qt.Key_Space:
            self._on_click('play')


class ShotPlayer(QThread):

    tick = pyqtSignal()

    def __init__(self, callback):
        super().__init__()
        self._playing = False
        self._current_loaded = 0
        self._threashold = None
        self._sleep_time = 1 / setting.frame_rate * setting.speed_offset
        self._cond = Condition()
        self._prepare()
        self.tick.connect(callback)
        state.on_changed('playing', self._toggle)
        self.start()

    def run(self):
        self._playing = True
        while self._playing:
            start = perf_counter()
            self.tick.emit()
            self._cond.acquire()
            self._cond.wait()
            self._cond.release()
            duration = perf_counter() - start
            if duration < self._sleep_time:
                self.msleep(int((self._sleep_time - duration) * 1000))

    def _prepare(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            self._threashold = len(setting.get_working_camera_ids())
            for camera_id in setting.get_working_camera_ids():
                state.on_changed(f'pixmap_{camera_id}', self._loaded)
            if state.get('closeup_camera'):
                state.on_changed('pixmap_closeup', self._loaded)
                self._threashold += 1
        elif body_mode is BodyMode.MODEL:
            state.on_changed('tick_update_geo', self._notify)

    def _notify(self):
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        self._current_loaded = 0

    def _loaded(self):
        self._current_loaded += 1
        if self._current_loaded == self._threashold:
            self._notify()

    def _toggle(self):
        if not state.get('playing'):
            self._playing = False
            self._notify()


class PlaybackBar(LayoutWidget):
    _default = '''
    QLabel {
        font-size: 20px;
    }
    '''

    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            alignment=Qt.AlignCenter, spacing=16, margin=(32, 0, 32, 0)
        )
        self._labels = []
        self._slider = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(self._default)

        for i in range(2):
            label = QLabel()
            label.setMinimumWidth(50)
            if i == 0:
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            elif i == 1:
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._labels.append(label)

        self._slider = PlaybackSlider()
        self._slider.valueChanged.connect(self._on_slider_changed)

        self.layout().addWidget(self._labels[0])
        self.layout().addWidget(self._slider)
        self.layout().addWidget(self._labels[1])

    def on_entity_changed(self, entity):
        if entity is None:
            return

        # Playbar Frames Construct
        current_slider_value = state.get('current_slider_value')
        current_real_frame = get_real_frame(current_slider_value)

        # Prevent Non-Recorded
        if entity.has_prop('cali') and entity.state < 1:
            return

        # Get Real Frames
        real_sf, real_ef = entity.get_real_frame_range()
        offset_frame = entity.get_frame_offset()
        playbar_frame_range = [real_sf - offset_frame, real_ef - offset_frame]

        state.set('playbar_frame_offset', offset_frame)
        state.set('playbar_frame_range', playbar_frame_range)
        state.set('playbar_frame_count', real_ef - real_sf + 1)

        # Configure Slider
        self._slider.setMinimum(playbar_frame_range[0])
        self._slider.setMaximum(playbar_frame_range[1])

        if current_real_frame is not None and\
                real_sf <= current_real_frame <= real_ef:
            current_slider_value = current_real_frame - real_sf
        else:
            current_slider_value = 0
        current_slider_value += playbar_frame_range[0]
        state.set('current_slider_value', current_slider_value)

        self._labels[0].setText(str(playbar_frame_range[0]))
        self._labels[1].setText(str(playbar_frame_range[1]))

        self.on_slider_value_changed(current_slider_value)
        self._slider.on_entity_changed(entity)

    def on_slider_value_changed(self, frame):
        if self._slider.value() != frame:
            self._slider.setValue(frame)

    def _on_slider_changed(self, value):
        if state.get('current_slider_value') != value:
            state.set('current_slider_value', value)


class PlaybackSlider(QSlider, EntityBinder):
    _default = '''
    PlaybackSlider {
        height: 66px
    }
    PlaybackSlider::add-page, PlaybackSlider::sub-page {
      background: none;
    }
    PlaybackSlider::handle {
      margin: -4px 0px -8px 0px;
    }
    '''
    _deadline_color = {
        TaskState.QUEUED: QColor('#a3a3a3'),
        TaskState.SUSPENDED: QColor('#212121'),
        TaskState.RENDERING: QColor('#057907'),
        TaskState.COMPLETED: QColor('#055679'),
        TaskState.FAILED: QColor('#791e05'),
        TaskState.PENDING: QColor('#795c05')
    }
    _crop_size = (8, 8, 10)
    _bar_height = 10
    _handle_width = 8

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self._tasks = {}
        self._crop_path = None
        self._crop_brush = None
        self._bar_map = None
        self._painter = QPainter()
        self._setup_ui()
        state.on_changed('crop_range', self._update)
        state.on_changed('loop_range', self._update)
        state.on_changed('Crop', self._update)
        state.on_changed('Loop', self._update)
        state.on_changed('key', self._on_key_pressed)
        state.on_changed('caching', self._update_progress)

        state.on_changed('closeup_camera', self._update_progress)

    def _on_key_pressed(self):
        if not self.isVisible():
            return
        key = state.get('key')

        if key == Qt.Key_Left:
            self._change_slider_position(-1)
        elif key == Qt.Key_Right:
            self._change_slider_position(1)
        else:
            return

    def _change_slider_position(self, step):
        slider_position = self.sliderPosition()
        slider_position += step
        if slider_position < self.minimum():
            slider_position = self.maximum()
        elif slider_position > self.maximum():
            slider_position = self.minimum()

        self.setSliderPosition(slider_position)

    def _update(self):
        if not state.get('caching') and self.isVisible():
            self.update()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setFocusPolicy(Qt.NoFocus)

        self._create_crop_elements()
        self._create_bar_map()

    def on_entity_changed(self, entity):
        self.bind_entity(entity, self._update_progress, modify=False)
        self._update_progress()

    def _create_crop_elements(self):
        cw, ch, _ = self._crop_size
        path = QPainterPath()
        path.moveTo(0, ch)
        path.lineTo(cw / 2, 0)
        path.lineTo(cw, ch)
        path.lineTo(0, ch)
        self._crop_path = path
        self._crop_brush = QBrush(self.palette().light().color())

    def _create_bar_map(self):
        self._bar_map = QPixmap(self.width(), self.height())
        self._paint_progress()

    def resizeEvent(self, event):
        self._create_bar_map()

    def _update_progress(self):
        if state.get('caching') or not self.isVisible():
            return

        if self._entity is not None:
            progress = self._entity.get_cache_progress()

            if isinstance(progress, tuple):
                offset_tasks = {}
                offset_frame = state.get('playbar_frame_offset')
                for k, v in progress[1].items():
                    offset_tasks[k - offset_frame] = v
                self._tasks = offset_tasks

        self._paint_progress()
        self._update()

    def _get_base_unit(self) -> (int, int, int, int):
        w = self.width()
        hw = self._handle_width
        w -= hw

        h = self.height()

        if self.maximum() == 0 or self.maximum() - self.minimum() == 0:
            tw = 0
        else:
            tw = w / (self.maximum() - self.minimum())

        return w, h, hw, tw

    def _paint_progress(self):
        """
        繪製播放列進度條
        """
        if self._bar_map is None:
            return

        self._bar_map.fill(Qt.transparent)
        painter = self._painter
        painter.begin(self._bar_map)

        w, h, hw, tw = self._get_base_unit()

        hh = self._bar_height

        painter.translate(hw / 2, 0)
        painter.fillRect(
            QRect(0, (h - hh) / 2, w, hh),
            self.palette().dark().color()
        )

        shot = state.get('current_shot')
        job = state.get('current_job')
        body_mode = state.get('body_mode')
        if shot is not None and body_mode is BodyMode.PLAYBACK and shot.frame_range is not None:
            progress = shot.get_cache_progress()
            t_color = self.palette().midlight().color()
            c_color = QColor('#DB2A71')
            sf, ef = shot.frame_range

            closeup_camera = state.get('closeup_camera')

            if isinstance(progress, tuple):
                progress = {}

            progress_thumb = progress.get(CameraCacheType.THUMBNAIL, [])
            progress_origin = progress.get(CameraCacheType.ORIGINAL, [])
            is_closeup = closeup_camera and closeup_camera in progress_origin

            i = 0
            for f in range(sf, ef + 1):
                if f in progress_thumb:
                    alpha = progress_thumb[f]
                    if alpha > 1.0:
                        alpha = 1.0
                    t_color.setAlphaF(float(alpha))
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2, math.ceil(tw), hh),
                        t_color
                    )

                if is_closeup and f in progress_origin[closeup_camera]:
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2 - 2, math.ceil(tw), 2),
                        c_color
                    )

                i += 1
        elif job is not None and body_mode is BodyMode.MODEL:
            cache_progress, task_progress = job.get_cache_progress()
            offset_frame = state.get('playbar_frame_offset')

            t_color = self.palette().midlight().color()

            i = 0
            for f in range(job.frame_range[0], job.frame_range[1] + 1):
                if f + offset_frame in cache_progress:
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2, math.ceil(tw), hh),
                        t_color
                    )
                elif f in task_progress:
                    task_state = task_progress[f]
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2, math.ceil(tw), hh),
                        self._deadline_color[task_state]
                    )

                i += 1
        painter.end()

    def paintEvent(self, evt):
        painter = self._painter
        self._painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h, hw, tw = self._get_base_unit()

        # bar map
        painter.drawPixmap(0, 0, self._bar_map)

        # crop
        painter.translate(hw / 2, 0)
        body_mode = state.get('body_mode')
        if state.get('Crop') or state.get('Loop'):
            cw, ch, oh = self._crop_size
            clip_range = 'crop_range'
            if body_mode is BodyMode.MODEL:
                clip_range = 'loop_range'
            sc, ec = state.get(clip_range)

            if sc is not None:
                sc -= self.minimum()
                painter.fillPath(
                    self._crop_path.translated(tw * sc - cw / 2, h - ch - oh),
                    self._crop_brush
                )
            if ec is not None:
                ec -= self.minimum()
                painter.fillPath(
                    self._crop_path.translated(tw * ec - cw / 2, h - ch - oh),
                    self._crop_brush
                )
            if sc is not None and ec is not None:
                painter.fillRect(
                    tw * sc, h - ch - oh,
                    tw * (ec - sc), ch / 2,
                    self.palette().base().color()
                )
        painter.translate(-hw / 2, 0)

        # normal
        super().paintEvent(evt)
        fm = painter.fontMetrics()
        text = str(self.value())
        width = fm.width(text)
        x = (self.value() - self.minimum()) * tw - width / 2 + hw / 2
        x_max_width = self.width() - width

        if x < 0:
            x = 0
        elif x > x_max_width:
            x = x_max_width

        painter.drawText(
            x, 0, width, 20,
            Qt.AlignCenter,
            text
        )

        painter.end()


class PlaybackButton(ToolButton):
    def __init__(self, source, parent=None):
        super().__init__(parent=parent, source=source)
        if source == 'play':
            state.on_changed('playing', self._update_source)
        elif source.startswith('clip'):
            self.setVisible(False)
            state.on_changed('Crop', self._update_clip_visible)
            state.on_changed('Loop', self._update_clip_visible)

    def sizeHint(self):
        return QSize(26, 26)

    def _update_source(self):
        if state.get('playing'):
            self.change_source('pause')
        else:
            self.change_source('play')

    def _update_clip_visible(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            crop = state.get('Crop')
            self.setVisible(crop)
        elif body_mode is BodyMode.MODEL:
            loop = state.get('Loop')
            self.setVisible(loop)
