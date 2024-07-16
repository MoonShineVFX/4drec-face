from enum import Enum


class ResolveStage(Enum):
    INITIALIZE = "initialize"
    RESOLVE = "resolve"
    POSTPROCESS = "postprocess"
    CONVERSION = "conversion"  # Deprecated

    def __str__(self):
        return self.value


class ResolveEvent(Enum):
    COMPLETE = "complete"
    FAIL = "fail"
    LOG_INFO = "log_info"
    LOG_STDOUT = "log_stdout"
    LOG_WARNING = "log_warning"
    PROGRESS = "progress"
