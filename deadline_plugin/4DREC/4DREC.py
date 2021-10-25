#!/usr/bin/env python3
from System import *
from System.Diagnostics import *
from System.IO import *
from Deadline.Plugins import *
from Deadline.Scripting import *


def GetDeadlinePlugin():
    """get 4DREC plugin"""
    return FourDRecPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    """flush memory"""
    deadlinePlugin.Cleanup()


class FourDRecPlugin(DeadlinePlugin):
    """4DREC Plugin"""
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
        from launch import launch
        from define import ResolveStage
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
        from define import ResolveEvent
        if event is ResolveEvent.COMPLETE:
            try:
                self.ExitWithSuccess()
            except Exception as error:
                self.LogWarning(str(error))
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
