from capture.utility.setting import setting

from outline import Outline, cuerun
from outline.modules.shell import Shell, ShellCommand
from opencue import api
from opencue.wrappers.service import Service
from opencue.wrappers.show import Show


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
    def ensure_service():
        check_service = api.getService(setting.opencue.service_name)
        if check_service is not None:
            return

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
        is_created = False
        for show in api.getShows():
            if show_name == show.data.name:
                is_created = True
                break
        if not is_created:
            new_show: Show = api.createShow(show_name)
            alloc = api.getAllocation(setting.opencue.allocation_name)
            new_show.createSubscription(alloc, 1000, 1000)

    @staticmethod
    def submit(show_name: str, shot_name: str, job_name: str,
               frame_range: str, yaml_path: str):
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
