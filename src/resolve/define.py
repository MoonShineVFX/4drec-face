from enum import Enum


class ResolveStage(Enum):
    INITIALIZE = 'initialize'
    RESOLVE = 'resolve'

    def __str__(self):
        return self.value
