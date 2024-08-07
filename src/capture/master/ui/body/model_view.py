from PyQt5.Qt import QLabel, QWidget, Qt, QRect, QComboBox
from datetime import datetime

from utility.fps_counter import FPScounter
from utility.setting import setting

from master.ui.state import state, get_real_frame

from .opengl_core import OpenGLCore


class ModelView(QWidget):
    _offset_parm_value = 0.1

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._interface = ModelInterface()
        self._res_select = TextureResolutionComboBox()

        self._core = OpenGLCore(self, self._interface)

        self._interface.setParent(self)
        self._res_select.setParent(self)
        self._cache = {}

        self._turntable_speed = 0.0
        self._fps_counter = FPScounter(self._interface.update_fps)

        state.on_changed("opengl_data", self._update_geo)
        state.on_changed("Rig", self._update_rig)
        state.on_changed("Wireframe", self._update_shader)
        state.on_changed("key", self._on_key_pressed)
        state.on_changed("current_job", self._update_job_rotation)

    def resizeEvent(self, event):
        self._core.setFixedSize(event.size())

    def _update_shader(self):
        self._core.toggle_wireframe(state.get("Wireframe"))

    def _update_rig(self):
        self._core.toggle_rig(state.get("Rig"))

    def _update_geo(self):
        if state.get("caching"):
            return
        turntable = self._turntable_speed if state.get("playing") else 0
        self._core.set_geo(state.get("opengl_data"), turntable)
        self._fps_counter.tick()

        # screenshot
        screenshot_path = state.get("screenshot_export_path")
        if screenshot_path is not None:
            self._take_screenshot(screenshot_path)

        state.set("tick_update_geo", None)

    def _on_key_pressed(self):
        if not self.isVisible():
            return
        key = state.get("key")
        if key == Qt.Key_Z:
            self._core.reset_camera_transform()
        elif key == Qt.Key_Q:
            self._core.offset_model_shader("gamma", -self._offset_parm_value)
        elif key == Qt.Key_E:
            self._core.offset_model_shader("gamma", self._offset_parm_value)
        elif key == Qt.Key_A:
            self._core.offset_model_shader(
                "saturate", -self._offset_parm_value
            )
        elif key == Qt.Key_D:
            self._core.offset_model_shader("saturate", self._offset_parm_value)
        elif key == Qt.Key_S:
            self._core.offset_model_shader("exposure", self._offset_parm_value)
        elif key == Qt.Key_X:
            self._core.offset_model_shader(
                "exposure", -self._offset_parm_value
            )
        elif key == Qt.Key_F:
            self._update_turntable(-self._offset_parm_value)
        elif key == Qt.Key_G:
            self._update_turntable(self._offset_parm_value)

    def _update_turntable(self, offset_value):
        self._turntable_speed += offset_value
        self._interface.update_turntable(self._turntable_speed)

    def _take_screenshot(self, export_path):
        frame = state.get("current_slider_value")
        rect = QRect(0, 0, self._core.width(), self._core.height())
        pixmap = self._core.grab(rect)
        pixmap.save(f"{export_path}/{frame:06d}.png")

    def _update_job_rotation(self):
        pass
        # Old version backward compatibility, not needed anymore
        #
        # Project after 2023/04/12 and before 2024/07/28 should rotate 180
        #
        # job = state.get("current_job")
        # if job is None:
        #     return
        #
        # job_datetime = job._doc_id.generation_time.replace(tzinfo=None)
        # is_180_rotation = (
        #     datetime(2023, 4, 12) <= job_datetime < datetime(2024, 7, 28)
        # )
        #
        # self._core.toggle_base_rotation(is_180_rotation)


class ModelInterface(QLabel):
    _default = """
        font-size: 13;
        color: palette(window-text);
        min-width: 200px;
        min-height: 400px;
    """

    def __init__(self):
        super().__init__()
        self._vertex_count = 0
        self._shader_parms = OpenGLCore._default_shader_parms.copy()
        self._turntable_speed = 0
        self._real_frame = -1
        self._fps = 0

        self._setup_ui()
        state.on_changed("current_slider_value", self._update_real_frame)

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.move(24, 16)
        self.setAlignment(Qt.AlignTop)

    def update_vertex_count(self, data):
        self._vertex_count = data
        self._update()

    def update_parm(self, parm_name, value):
        self._shader_parms[parm_name] = value
        self._update()

    def update_sat(self, value):
        self._saturate = value
        self._update()

    def update_fps(self, fps):
        self._fps = fps
        self._update()

    def update_turntable(self, turntable):
        self._turntable_speed = turntable
        self._update()

    def _update_real_frame(self):
        slider_value = state.get("current_slider_value")
        self._real_frame = get_real_frame(slider_value)
        self._update()

    def _update(self):
        text = (
            f"Resolution: \n\n"
            + f"Vertices:  {self._vertex_count}\n"
            + f"Real Frame:  {self._real_frame}\n"
            + "\n".join(
                [
                    f"{k.capitalize()}: {v:.2f}"
                    for k, v in self._shader_parms.items()
                ]
            )
            + "\n\n"
            + "[Q/E]  Gamma Offset\n"
            + "[A/D]  Saturate Offset\n"
            + "[S/X]  Exposure Offset\n"
            + "[F/G]  Turntable\n"
            + "[Z]  Reset Camera"
        )

        if state.get("playing"):
            text += (
                f"\n\nfps: {self._fps}\n"
                f"turntable speed: {self._turntable_speed:.1f}"
            )

        self.setText(text)


class TextureResolutionComboBox(QComboBox):
    _res_list = [8192, 4096, 3000, 2048, 1024, 512]

    def __init__(self):
        super().__init__()

        for res in self._res_list:
            self.addItem(str(res), res)

        self._setup_ui()
        self.setCurrentIndex(
            self._res_list.index(setting.default_texture_display_resolution)
        )

        self.currentIndexChanged.connect(self._on_changed)

    def _setup_ui(self):
        self.move(120, 12)

    def _on_changed(self, index: int):
        resolution = self.currentData()
        state.set("texture_resolution", resolution)
