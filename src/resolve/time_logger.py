from time import perf_counter

from settings import SETTINGS


class Timelogger:
    def __init__(self):
        self._time = perf_counter()

    def tick(self, name='tick'):
        duration = perf_counter() - self._time
        with open(str(SETTINGS.timelog_path), 'a') as f:
            f.write(f'{name}: {duration}\n')
        self._time = perf_counter()