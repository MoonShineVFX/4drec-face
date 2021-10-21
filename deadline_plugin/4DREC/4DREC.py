from System import *
from System.Diagnostics import *
from System.IO import *

from Deadline.Plugins import *
from Deadline.Scripting import *

from launch import launch
from define import ResolveStage, ResolveEvent


def GetDeadlinePlugin():
    """get 4DREC plugin"""
    return FourDRecPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    """flush memory"""
    deadlinePlugin.Cleanup()


class FourDRecPlugin(DeadlinePlugin):
    """4DREC Plugin"""
    _app_path = '\\\\4dk-sto\\storage\\app\\'

    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.StartJobCallback += self.StartJob
        self.RenderTasksCallback += self.RenderTasks
        self._process = None

    def Cleanup(self):
        """flush memory"""
        del self.InitializeProcessCallback
        del self.StartJobCallback
        del self.RenderTasksCallback

    def InitializeProcess(self):
        """initialize process"""
        self.SingleFramesOnly = False
        self.PluginType = PluginType.Advanced

    def StartJob(self):
        """prepare resolve"""
        return

    def RenderTasks(self):
        """render"""
        job = self.GetJob()
        resolve_stage = job.GetJobExtraInfoKeyValue('resolve_stage')
        yaml_path = job.GetJobExtraInfoKeyValue('yaml_path')

        launch(
            self.GetStartFrame(),
            ResolveStage(resolve_stage),
            yaml_path,
            debug=True,
            on_event=self._on_event_emit
        )

    def _on_event_emit(self, event, payload=None):
        if event is ResolveEvent.COMPLETE:
            self.ExitWithSuccess()
        elif event is ResolveEvent.FAIL:
            self.FailRender(payload)
        elif event is ResolveEvent.LOG_INFO:
            self.LogInfo(payload)
        elif event is ResolveEvent.LOG_STDOUT:
            self.LogStdout(payload)
        elif event is ResolveEvent.LOG_WARNING:
            self.LogWarning(payload)
        elif event is ResolveEvent.PROGRESS:
            self.SetProgress(payload)
