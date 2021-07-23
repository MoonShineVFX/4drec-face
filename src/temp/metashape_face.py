import os
from time import perf_counter

os.environ.update({
    'shot_path': r'D:\4dface\export\near4d',
    'job_path': r'D:\4dface\metashape\auto',
    'start_frame': '0',
    'end_frame': '119',
    'current_frame': '2'
})

class Timelogger:
    def __init__(self):
        self._time = perf_counter()

    def tick(self, name='tick'):
        duration = perf_counter() - self._time
        with open(f'{os.environ["job_path"]}\\timelog.txt', 'a') as f:
            f.write(f'{name}: {duration}\n')
        self._time = perf_counter()


if __name__ == '__main__':
    from common.metashape_manager import MetashapeProject
    project = MetashapeProject()
    t = Timelogger()
    project.initial()
    t.tick('initial')
    project.calibrate()
    t.tick('calibrate')
    project.resolve()
    t.tick('resolve')
