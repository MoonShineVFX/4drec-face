import yaml
from pathlib import Path

from capture.utility.setting import setting

import opencue.exception
from outline import Outline, cuerun
from outline.depend import DependType
from outline.modules.shell import Shell, ShellCommand
from opencue import api
from opencue.wrappers.service import Service
from opencue.wrappers.show import Show

from utility.logger import log


class MetashapeInitialLayer(ShellCommand):
    def __init__(self, yaml_path: str, **kwargs):
        kwargs['command'] = [
            setting.resolve_path + '\\resolve.bat',
            '--resolve_stage initialize',
            f'--yaml_path "{yaml_path}"'
        ]
        super(ShellCommand, self).__init__('Initial', **kwargs)
        self.set_service(setting.opencue.service_name)


class MetashapeResolveLayer(Shell):
    def __init__(self, yaml_path: str, **kwargs):
        kwargs['command'] = [
            setting.resolve_path + '\\resolve.bat',
            '--frame #IFRAME#',
            '--resolve_stage resolve',
            f'--yaml_path "{yaml_path}"'
        ]
        super(Shell, self).__init__('Resolve', **kwargs)
        self.set_service(setting.opencue.service_name)


class OpenCueBridge:
    @staticmethod
    def check_server() -> str:
        try:
            log.debug(api.getSystemStats())
        except opencue.exception.ConnectionException as error:
            log.warning('OpenCue server not found.')
            return str(error)
        return ''

    @staticmethod
    def ensure_service():
        check_service = api.getService(setting.opencue.service_name)
        if check_service is not None:
            log.info(f'Service {setting.opencue.service_name} exists.')
            return

        log.info(f'Create service {setting.opencue.service_name}.')
        service: Service = api.createService(None)
        service.setName(setting.opencue.service_name)
        service.setThreadable(True)
        service.setMinCores(400)
        service.setMaxCores(0)
        service.setMinMemory(4096 * 1024)
        service.setMinGpu(1024 * 1024)
        service.setTags(['general', 'metashape'])
        service.update()

    @staticmethod
    def ensure_show(show_name: str):
        for show in api.getShows():
            if show_name == show.data.name:
                log.info(f'Show {show_name} exists.')
                return

        log.info(f'Create show {show_name}.')
        new_show: Show = api.createShow(show_name)
        alloc = api.getAllocation(setting.opencue.allocation_name)
        new_show.createSubscription(alloc, 1000, 1000)

    @staticmethod
    def submit(show_name: str, shot_name: str, job_name: str,
               shot_folder: str, job_folder: str,
               frame_range: (int, int), parameters: dict=None) -> [str]:
        # Build yaml file
        yaml_data = setting.submit.copy()
        yaml_data['start_frame'] = frame_range[0]
        yaml_data['end_frame'] = frame_range[1]
        yaml_data['shot_path'] += shot_folder
        yaml_data['job_path'] += job_folder
        if parameters is not None:
            yaml_data.update(parameters)
        yaml_path = f'{yaml_data["job_path"]}/job.yml'

        Path(yaml_data["job_path"]).mkdir(exist_ok=True, parents=True)

        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_data, f)

        # Ensure
        OpenCueBridge.ensure_service()
        OpenCueBridge.ensure_show(show_name)

        # Layers
        initial_layer = MetashapeInitialLayer(yaml_path)
        resolve_layer = MetashapeResolveLayer(yaml_path)
        resolve_layer.depend_on(initial_layer, depend_type=DependType.LayerOnLayer)

        # Outline
        outline = Outline(job_name,
                          frame_range=f'{frame_range[0]}-{frame_range[1]}',
                          show=show_name,
                          shot=shot_name,
                          user=setting.opencue.user_name,
                          name_unique=True)
        outline.add_layer(initial_layer)
        outline.add_layer(resolve_layer)

        # Submit
        jobs = cuerun.launch(outline, use_pycuerun=False)
        for job in jobs:
            job.setPriority(100)

        assert len(jobs) == 1

        return jobs[0].id()

    @staticmethod
    def get_frame_list(job_id):
        job = api.getJob(job_id)
        layer = job.getLayers()[-1]
        frames = layer.getFrames()

        frame_list = {}

        for frame in frames:
            frame_list[frame.data.number] = frame.data.state

        return frame_list
