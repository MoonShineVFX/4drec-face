from PyQt5.Qt import QObject, pyqtSignal, QApplication

from utility.setting import setting
from utility.define import EntityEvent, BodyMode
from utility.logger import log

from .event import UIEventHandler


class UIState:
    def __init__(self):
        self.event = UIEventHandler()

        self._caster = {}

        self._state = {}
        self._build_state()

        self._callbacks = {}
        for key in self._state:
            self._callbacks[key] = UIStateSignal()

    def _build_state(self):
        # ui
        self._state["status"] = {"slaves": 0, "bias": 0.0, "frames": -1}
        self._state["body_mode"] = BodyMode.LIVEVIEW
        self._state["closeup_camera"] = None
        self._state["project_list_dialog"] = False
        self._state["project_list_select"] = None
        self._state["project_new_dialog"] = False
        self._state["shot_new_dialog"] = False
        self._state["is_cali"] = False
        self._state["live_view_size"] = 150
        self._state["caching"] = False
        self._state["key"] = None
        self._state["second_screen"] = False

        # projects
        self._state["deadline_status"] = False
        self._state["current_project"] = None
        self._state["projects"] = []

        # shots
        self._state["current_shot"] = None
        self._state["shots"] = []

        # jobs
        self._state["current_job"] = None
        self._state["jobs"] = []
        self._state["cali_list"] = []

        # parameter
        for key, parm in setting.camera_parameters.items():
            self._state[key] = parm["default"]
        self._state["parm_outside"] = False

        # playbar
        self._state["current_slider_value"] = 0
        self._state["playbar_frame_range"] = [0, 0]
        self._state["playbar_frame_count"] = 0
        self._state["playbar_frame_offset"] = 0
        self._state["playing"] = False
        self._state["crop_range"] = [None, None]
        self._state["loop_range"] = [None, None]

        # support
        self._state["Calibrate"] = False
        self._state["Focus"] = False
        self._state["Serial"] = False
        self._state["Crop"] = False
        self._state["Rig"] = False
        self._state["Wireframe"] = False
        self._state["Loop"] = False

        # pixmap
        for camera_id in setting.get_working_camera_ids():
            self._state[f"pixmap_{camera_id}"] = None
        self._state["pixmap_closeup"] = None
        self._state["tick_submit"] = None

        # model
        self._state["opengl_data"] = None
        self._state["tick_update_geo"] = None
        self._state["screenshot_export_path"] = None
        self._state[
            "texture_resolution"
        ] = setting.default_texture_display_resolution

        # camera
        self._state["trigger"] = False
        self._state["live_view"] = False
        self._state["recording"] = False

        # arduino
        self._state["has_arduino"] = False

        # audio
        self._state["audio_decibel"] = -100
        self._state["is_mic_open"] = False

    def get(self, state_name):
        return self._state[state_name]

    def set(self, state_name, value):
        self._state[state_name] = value

        self._callbacks[state_name].signal.emit()

    def on_changed(self, state_name, func):
        self._callbacks[state_name].signal.connect(func)

    def connect(self, caster):
        self._caster.update(caster)

    def cast(self, target, func, *arg, **kwargs):
        if target in self._caster:
            getattr(self._caster[target], func)(*arg, **kwargs)
        else:
            log.warning(
                f"can't find cast target [{target}]: {func} {arg} {kwargs}"
            )


class UIStateSignal(QObject):
    signal = pyqtSignal()

    def __init__(self):
        super().__init__()


class EntityBinder:
    def __init__(self):
        self._entity = None
        self._func = None
        self._event = None

    def bind_entity(self, entity, func, modify=True):
        if self._entity == entity:
            return

        if modify:
            self._event = EntityEvent.MODIFY
        else:
            self._event = EntityEvent.PROGRESS

        if self._entity:
            self._entity.unregister_callback(self._on_entity_event)

        self._entity = entity
        self._func = func

        if self._entity:
            self._entity.register_callback(self._on_entity_event)

    def _on_entity_event(self, event, entity):
        if event is self._event and entity == self._entity:
            self._func()


state = UIState()


def get_slider_range():
    body_mode = state.get("body_mode")
    min_slider_value, max_slider_value = None, None

    if body_mode is BodyMode.PLAYBACK and state.get("Crop"):
        min_slider_value, max_slider_value = state.get("crop_range")
    elif body_mode is BodyMode.MODEL and state.get("Loop"):
        min_slider_value, max_slider_value = state.get("loop_range")

    if min_slider_value is None or max_slider_value is None:
        min_slider_value, max_slider_value = state.get("playbar_frame_range")

    return min_slider_value, max_slider_value


def step_pace(forward=True, stop=True):
    if state.get("playing") and stop:
        state.set("playing", False)

    slider_value = state.get("current_slider_value")
    min_value, max_value = get_slider_range()

    step_value = 1 if forward else -1
    slider_value += step_value

    if slider_value < min_value:
        state.set("current_slider_value", max_value)
    elif slider_value > max_value:
        state.set("current_slider_value", min_value)
    else:
        state.set("current_slider_value", slider_value)


def get_real_frame(frame):
    sf, ef = state.get("playbar_frame_range")
    if sf > frame or frame > ef:
        return None

    offset_frame = state.get("playbar_frame_offset")
    real_frame = frame + offset_frame
    return real_frame
