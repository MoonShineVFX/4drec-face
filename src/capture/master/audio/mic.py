import threading
import pyaudio
from queue import Queue

from utility.setting import setting


class MicDevice(threading.Thread):
    def __init__(self, task_queue: Queue):
        super().__init__()
        self.__is_running = True
        self.__task_queue = task_queue

    def run(self) -> None:
        core = pyaudio.PyAudio()
        input_stream = core.open(format=pyaudio.paInt16,
                                 channels=1,
                                 input=True,
                                 rate=setting.audio.sample_rate,
                                 frames_per_buffer=setting.audio.chunk_size)

        while self.__is_running:
            audio_data = input_stream.read(setting.audio.chunk_size)
            self.__task_queue.put(audio_data)
