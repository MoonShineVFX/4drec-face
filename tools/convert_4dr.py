import json
from pathlib import Path
import struct

# From houdini drc and texture
NAME = '阿木試拍'
RES = 'SD'
GEOMETRY_PATH = r'G:\postprocess\export\mu-shot_3\drc_sd'
TEXTURE_PATH = r'G:\postprocess\export\mu-shot_3\texture_2k'
TEXTURE_RESOLUTION = 2048
AUDIO_PATH = r'G:\postprocess\export\mu-shot_3\audio_trim.wav'
EXPORT_PATH = r'C:\Users\eli.hung\Desktop\mu_sd_2k.4dr'

# Check audio path
if 'AUDIO_PATH' not in locals():
    AUDIO_PATH = None

# Prepare header
header = {
    "version": "1",
    "name": NAME,
    "frame_count": 0,
    "geometry_format": "DRC",
    "geometry_resolution": RES,  # HD, SD
    "texture_format": "JPEG",  # MP4, NULL
    "texture_resolution": TEXTURE_RESOLUTION,
    "audio_format": "WAV" if AUDIO_PATH is not None else "NULL",  # MP3, NULL
    "geometry_buffer_positions": [],
    "texture_buffer_positions": [],  # ONLY 1 if MP4
    "audio_buffer_positions": [],  # ONLY 1
}

# Get files
drc_file_paths = list(Path(GEOMETRY_PATH).rglob('*.drc'))
tex_file_paths = list(Path(TEXTURE_PATH).rglob('*.jpg'))

if len(tex_file_paths) != len(drc_file_paths):
    raise ValueError('Texture and drc files are not matched')

header['frame_count'] = len(drc_file_paths)

# Dump data
filehandler = open(EXPORT_PATH, 'wb')
total_count = (len(drc_file_paths) +
               len(tex_file_paths) +
               (1 if AUDIO_PATH is not None else 0))


class ProgressLogger:
    def __init__(self, total):
        self.count = 0
        self.total_count = total

    def next(self):
        self.count += 1
        print(f'{self.count}/{self.total_count}')


progress = ProgressLogger(total_count)


for drc_file_path in drc_file_paths:
    with open(drc_file_path, 'rb') as f:
        drc_data = f.read()
        header['geometry_buffer_positions'].append(filehandler.tell())
        filehandler.write(drc_data)
        progress.next()

for tex_file_path in tex_file_paths:
    with open(tex_file_path, 'rb') as f:
        tex_data = f.read()
        header['texture_buffer_positions'].append(filehandler.tell())
        filehandler.write(tex_data)
        progress.next()

if AUDIO_PATH is not None:
    with open(AUDIO_PATH, 'rb') as f:
        audio_data = f.read()
        header['audio_buffer_positions'].append(filehandler.tell())
        filehandler.write(audio_data)
        progress.next()


# Pack header
header_json = json.dumps(header)
filehandler.write(header_json.encode('utf-8'))

# Pack footer
footer_hint = {
    'format': b'4DR1',
    'header_size': len(header_json),
}
footer_buffer = struct.pack(
    '4sI',
    *footer_hint.values()
)
filehandler.write(footer_buffer)
filehandler.close()
