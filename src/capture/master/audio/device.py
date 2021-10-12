import threading
import pyaudio
from queue import Queue
import math
import numpy as np

from utility.setting import setting
from utility.logger import log
from utility.define import UIEventType, AudioSource

from master.ui import ui


AUDIO_FORMAT = pyaudio.paInt16
AUDIO_CORE = pyaudio.PyAudio()


def send_ui_decibel(audio_data: bytes, source: AudioSource):
    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    samples /= 32767
    volume = np.sum(samples ** 2) / len(samples)
    rms = math.sqrt(volume)
    db = 20 * math.log10(rms)

    ui.dispatch_event(
        UIEventType.AUDIO_DECIBEL,
        {
            source, db
        }
    )


class MicDevice(threading.Thread):
    def __init__(self, listen_queue: Queue):
        super().__init__()
        self.__is_running = True
        self.__listen_queue = listen_queue
        self.start()

    def run(self) -> None:
        input_stream = AUDIO_CORE.open(
            format=AUDIO_FORMAT,
            channels=1,
            input=True,
            rate=setting.audio.sample_rate,
            frames_per_buffer=setting.audio.chunk_size
        )
        while self.__is_running:
            audio_data = input_stream.read(setting.audio.chunk_size)
            self.__listen_queue.put(audio_data)
            send_ui_decibel(audio_data, AudioSource.Mic)


class SpeakerDevice(threading.Thread):
    def __init__(self):
        super(SpeakerDevice, self).__init__()
        self.__is_running = True
        self.__play_queue = Queue()
        self.start()

    def play_sound(self, audio_data: bytes):
        with self.__play_queue.mutex:
            self.__play_queue.queue.clear()
        self.__play_queue.put(audio_data)

    def run(self) -> None:
        output_stream = AUDIO_CORE.open(format=AUDIO_FORMAT,
                                        channels=1,
                                        output=True,
                                        rate=setting.audio.sample_rate)
        log.debug('Speaker device initialized.')

        while self.__is_running:
            audio_data = self.__play_queue.get()
            output_stream.write(audio_data)
            send_ui_decibel(audio_data, AudioSource.File)
