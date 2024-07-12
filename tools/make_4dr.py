import json
from pathlib import Path
import struct


def make_4dr(root_path, isHD=False):
    root_path = Path(root_path)

    name = root_path.stem

    geometry_path = root_path / 'drc' if not isHD else 'drc_hd'
    texture_path = root_path / 'texture_2k' if not isHD else 'texture_4k'
    texture_resolution = 2048 if not isHD else 4096
    export_path = root_path / 'vision.4dr' if not isHD else 'vision_hd.4dr'

    # Get audio
    audio_path = root_path / 'audio.wav'
    if not audio_path.exists():
        audio_path = None

    # Prepare header
    # Buffer position should be more 1 than count, because of range
    header = {
        "version": "1",
        "name": name,
        "frame_count": 0,
        "geometry_format": "DRC",
        "geometry_resolution": 'HD' if isHD else 'SD',  # HD, SD
        "texture_format": "JPEG",  # MP4, NULL
        "texture_resolution": texture_resolution,
        "audio_format": "WAV" if audio_path is not None else "NULL",  # MP3, NULL
        "geometry_buffer_positions": [],
        "texture_buffer_positions": [],  # ONLY 1 if MP4
        "audio_buffer_positions": [],  # ONLY 1
    }

    # Get files
    drc_file_paths = list(Path(geometry_path).rglob('*.drc'))
    tex_file_paths = list(Path(texture_path).rglob('*.jpg'))

    if len(tex_file_paths) != len(drc_file_paths):
        raise ValueError('Texture and drc files are not matched')

    header['frame_count'] = len(drc_file_paths)

    # Dump data
    filehandler = open(export_path, 'wb')
    total_count = (len(drc_file_paths) +
                   len(tex_file_paths) +
                   (1 if audio_path is not None else 0))

    for drc_file_path in drc_file_paths:
        with open(drc_file_path, 'rb') as f:
            drc_data = f.read()
            header['geometry_buffer_positions'].append(filehandler.tell())
            filehandler.write(drc_data)
    header['geometry_buffer_positions'].append(filehandler.tell())

    for tex_file_path in tex_file_paths:
        with open(tex_file_path, 'rb') as f:
            tex_data = f.read()
            header['texture_buffer_positions'].append(filehandler.tell())
            filehandler.write(tex_data)
    header['texture_buffer_positions'].append(filehandler.tell())

    if audio_path is not None:
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
            header['audio_buffer_positions'].append(filehandler.tell())
            filehandler.write(audio_data)
    header['audio_buffer_positions'].append(filehandler.tell())

    # Pack header
    header_position = filehandler.tell()
    header_json = json.dumps(header)
    filehandler.write(header_json.encode('utf-8'))

    # Pack footer
    footer_hint = {
        'format': b'4DR1',
        'header_position': header_position,
        'header_size': len(header_json),
    }
    footer_buffer = struct.pack(
        '4sII',
        *footer_hint.values()
    )
    filehandler.write(footer_buffer)
    filehandler.close()
