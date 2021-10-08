import threading
import pyaudio
import wave
from typing import Optional
import math
import numpy as np
from pathlib import Path
from queue import Queue

from utility.define import UIEventType

from master.ui import ui

from .mic import MicDevice


INPUT_DEVICE_NAME = 'USB PnP'
SAMPLE_RATE = 44100
CHUNK = 1024
AUDIO_FILENAME = 'audio.wav'


class AudioManager(threading.Thread):
    def __init__(self):
        super().__init__()
        self.__task_queue = Queue()
        self.__is_running = True
        self.__wave_write_handle: Optional[wave.Wave_write] = None
        self.__wave_read_handle: Optional[wave.Wave_read] = None
        self.__read_path: Optional[str] = None

        self.start()

    def send_ui_decibel(self, data: bytes):
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        samples /= 32767
        volume = np.sum(samples**2)/len(samples)
        rms = math.sqrt(volume)
        db = 20 * math.log10(rms)

        ui.dispatch_event(
            UIEventType.AUDIO_DECIBEL,
            db
        )


    def __get_audio_file_path(self, path: str) -> str:
        return path + f'/{AUDIO_FILENAME}'

    def run(self):
        mic_device = MicDevice(self.__task_queue)
        while self.__is_running:
            audio_data = stream.read(CHUNK)

            # Send decibel
            ui.dispatch_event(
                UIEventType.AUDIO_DECIBEL,
                self.__get_decibel(audio_data)
            )

            # Record
            if self.__wave_write_handle is not None:
                self.__wave_write_handle.writeframes(audio_data)

        stream.stop_stream()
        stream.close()

    def start_record(self, shot_path):
        Path(shot_path).mkdir(parents=True, exist_ok=True)
        self.__wave_write_handle = wave.open(self.__get_audio_file_path(shot_path), 'wb')
        self.__wave_write_handle.setnchannels(1)
        self.__wave_write_handle.setsampwidth(
            self.__core.get_sample_size(pyaudio.paInt16)
        )
        self.__wave_write_handle.setframerate(SAMPLE_RATE)

    def stop_record(self):
        if self.__wave_write_handle is None:
            return
        self.__wave_write_handle.close()
        self.__wave_write_handle = None

    def play_audio(self, shot_path, frame):
        if self.__read_path != shot_path:
            self.__read_path = shot_path
        #TODO read audio file to frame
