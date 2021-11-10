import threading
import wave
from typing import Optional

from pathlib import Path
from queue import Queue
from io import BytesIO

from utility.setting import setting
from utility.logger import log

from .device import MicDevice, SpeakerDevice


CHUNK_PER_FRAME = setting.audio.sample_rate // setting.frame_rate


class AudioManager(threading.Thread):
    def __init__(self):
        super().__init__()
        self.__is_running = True
        self.__is_mic_active = False

        self.__mic_queue = Queue()
        self.__mic_device = MicDevice(self.__mic_queue)
        self.__wave_write_handle: Optional[wave.Wave_write] = None

        self.__speaker_device = SpeakerDevice()
        self.__wave_read_handle: Optional[wave.Wave_read] = None
        self.__read_buffer: Optional[BytesIO] = None
        self.__read_path: Optional[str] = None

        self.start()

    def __get_audio_file_path(self, path: str) -> str:
        return f'{path}/{setting.audio.record_filename}'

    def run(self):
        while self.__is_running:
            mic_audio_data = self.__mic_queue.get()

            # Record
            if self.__wave_write_handle is not None:
                self.__wave_write_handle.writeframes(mic_audio_data)

    def start_record(self, shot_path: str):
        record_path = self.__get_audio_file_path(shot_path)
        Path(record_path).parent.mkdir(parents=True, exist_ok=True)
        self.__wave_write_handle = wave.open(
            record_path, 'wb'
        )
        self.__wave_write_handle.setnchannels(1)
        self.__wave_write_handle.setsampwidth(2)  # int16 size in bytes
        self.__wave_write_handle.setframerate(setting.audio.sample_rate)

    def stop_record(self):
        if self.__wave_write_handle is None:
            return
        self.__wave_write_handle.close()
        self.__wave_write_handle = None

    def play_audio_file(self, shot_path, frame):
        file_path = self.__get_audio_file_path(shot_path)

        # Check audio file loaded
        if self.__read_path != file_path:
            self.__read_path = file_path
            log.debug(f'Change audio file: {file_path}')

            if self.__wave_read_handle is not None:
                self.__wave_read_handle.close()
                self.__wave_read_handle = None
            if self.__read_buffer is not None:
                self.__read_buffer.close()
                self.__read_buffer = None

            if not Path(file_path).is_file():
                log.warning(f'No audio file found: {file_path}')
                return

            with open(file_path, 'rb') as f:
                self.__read_buffer = BytesIO(f.read())
            self.__wave_read_handle = wave.open(self.__read_buffer, 'rb')

        # If file not exists
        if self.__wave_read_handle is None:
            return

        # If out of range
        try:
            self.__wave_read_handle.setpos(frame * CHUNK_PER_FRAME)
        except wave.Error as error:
            log.error(str(error))
            return

        # Play sound
        audio_data = self.__wave_read_handle.readframes(CHUNK_PER_FRAME)
        self.__speaker_device.play_sound(audio_data)

    def toggle_mic(self, toggle: bool):
        self.__is_mic_active = toggle
