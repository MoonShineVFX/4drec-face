from capture.utility.setting import setting

import opencue.exception
from outline import Outline, cuerun
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
               frame_range: (int, int), parameters: dict) -> [str]:
        # TODO: Add parameters update and yaml file creation

        # Ensure
        OpenCueBridge.ensure_service()
        OpenCueBridge.ensure_show(show_name)

        # Layers
        initial_layer = MetashapeInitialLayer(yaml_path)
        resolve_layer = MetashapeResolveLayer(yaml_path)
        resolve_layer.depend_on(initial_layer)

        # Outline
        outline = Outline(job_name,
                          frame_range=frame_range,
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

        return [job.id() for job in jobs]