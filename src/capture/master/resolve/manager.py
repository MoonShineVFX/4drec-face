import threading
from queue import Queue

from utility.define import UIEventType
from utility.setting import setting
from utility.delay_executor import DelayExecutor
from utility.logger import log

from master.ui import ui
from master.projects import project_manager

from .package import ResolvePackage
from .multi_executor import MultiExecutor


class ResolveManager(threading.Thread):
    def __init__(self):
        super().__init__()

        self._queue = Queue()
        self._cache = {}
        self._delay = DelayExecutor()
        self._multi_executor = MultiExecutor(self)
        self._prefer_resolution = setting.default_texture_display_resolution

        # 綁定 UI
        ui.dispatch_event(UIEventType.UI_CONNECT, {"resolve": self})

        self.start()

    def run(self):
        while True:
            package = self._queue.get()
            self._handle_package(package)

    def _handle_package(self, package):
        result = package.load()
        if result is None:
            self.send_ui(None)
            return

        self.save_package(package)
        self.send_ui(package)

    def _send_payload(self, payload):
        ui.dispatch_event(UIEventType.RESOLVE_GEOMETRY, payload)

    def ui_tick_export(self):
        ui.dispatch_event(UIEventType.TICK_EXPORT)

    def send_ui(self, package):
        if package is not None:
            self._send_payload(package.to_payload())
        else:
            self._send_payload(None)

    def _add_task(self, package):
        self._queue.put(package)

    def save_package(self, package):
        job_id, frame = package.get_meta()
        if job_id not in self._cache:
            self._cache[job_id] = {}

        self._cache[job_id][frame] = package

        if frame is not None:
            job = project_manager.get_job(job_id)
            job.update_cache_progress(frame, package.get_cache_size())

    def cache_whole_job(self, resolution):
        if resolution != self._prefer_resolution:
            self._cache = {}

        job = project_manager.current_job
        job_id = job.get_id()
        job_folder_path = job.get_folder_path()
        real_frame_range = job.get_real_frame_range()

        tasks = []
        for f in range(real_frame_range[0], real_frame_range[1] + 1):
            if self.has_cache(job_id, f):
                self.send_ui(None)
                continue
            tasks.append(
                (
                    job_id,
                    job_folder_path,
                    self._prefer_resolution,
                    f,
                    job.get_frame_offset() + job.frame_range[0],
                )
            )

        self._multi_executor.add_task("cache_all", tasks)

    def has_cache(self, job_id, frame):
        return job_id in self._cache and frame in self._cache[job_id]

    def request_geometry(self, job, frame, resolution, is_delay=True):
        if resolution != self._prefer_resolution:
            log.info(
                "Change resolution "
                f"{self._prefer_resolution} -> {resolution}"
            )
            self._prefer_resolution = resolution
            self._cache = {}

        job_id = job.get_id()

        # get already cached
        if self.has_cache(job_id, frame):
            package = self._cache[job_id][frame]
            self.send_ui(package)
        # load frame 4dh
        elif frame is not None:
            job_folder_path = job.get_folder_path()
            package = ResolvePackage(
                job_id,
                job_folder_path,
                self._prefer_resolution,
                frame,
                job.get_frame_offset() + job.frame_range[0],
            )
            if is_delay:
                self._delay.execute(lambda: self._add_task(package))
            else:
                self._add_task(package)
