import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from queue import Queue

from .package import ResolvePackage


def load_geometry(job_id, job_folder_path, res, frame, offset_frame):
    package = ResolvePackage(job_id, job_folder_path, res, frame, offset_frame)
    result = package.load()

    # no files
    if result is None:
        return None
    return package


class MultiExecutor(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self._queue = Queue()
        self._manager = manager
        self.start()

    def cache_all(self, tasks):
        future_list = []
        with ProcessPoolExecutor() as executor:
            for job_id, job_folder_path, res, f, offset_frame in tasks:
                future = executor.submit(
                    load_geometry,
                    job_id,
                    job_folder_path,
                    res,
                    f,
                    offset_frame,
                )
                future_list.append(future)
            for future in as_completed(future_list):
                package = future.result()
                if package is not None:
                    self._manager.save_package(package)
                self._manager.send_ui(None)

    def run(self):
        while True:
            task_type, tasks = self._queue.get()

            if task_type == "cache_all":
                self.cache_all(tasks)

    def add_task(self, task_type, tasks):
        self._queue.put((task_type, tasks))
