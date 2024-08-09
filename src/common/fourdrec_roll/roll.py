import struct
from pathlib import Path
from typing import Callable, List, Union, Tuple
from datetime import datetime
import json
from dataclasses import asdict
from io import BytesIO
import logging

from .header import Header


# Define a type for the progress update callback function
OnProgressUpdateCallback = Callable[[float], None]
InputPath = Union[str, Path]


class FourdrecRoll:
    def __init__(self, path: InputPath):
        self._path = Path(path)

        with open(self._path, "rb") as f:
            (self.header, self.header_size) = Header.from_file(file=f)

    def __str__(self):
        return f"FourdrecRoll\n{json.dumps(asdict(self.header), indent=4)}"

    def get_frame(self, frame_number: int) -> Tuple[bytes, bytes]:
        frame_positions = self.header.positions.frame_buffer_positions
        assert frame_number < len(frame_positions) - 1, "Frame not found"

        with open(self._path, "rb") as f:
            f.seek(self.header_size + frame_positions[frame_number])
            geo_size: int = struct.unpack("I", f.read(struct.calcsize("I")))[0]
            logging.debug(
                "seek start: ",
                self.header_size + frame_positions[frame_number],
            )
            logging.debug("geo_size: ", geo_size)
            geo_buffer = f.read(geo_size)
            jpg_buffer = f.read(
                frame_positions[frame_number + 1]
                - frame_positions[frame_number]
                - geo_size
                - struct.calcsize("I")
            )

        return geo_buffer, jpg_buffer

    @staticmethod
    def pack(
        name: str,
        drc_folder_path: InputPath,
        jpeg_folder_path: InputPath,
        export_path: InputPath,
        audio_path: InputPath = None,
        roll_id: str = None,
        on_progress_update: OnProgressUpdateCallback = None,
        created_date: datetime = None,
    ) -> str:
        """Pack data from given paths to a roll.

        :return: The path to the packed roll.
        """

        # Get paths
        drc_folder_path = Path(drc_folder_path)
        jpeg_folder_path = Path(jpeg_folder_path)
        audio_path = Path(audio_path) if audio_path is not None else None
        export_path = Path(str(export_path).lower())

        # Get file paths
        drc_file_paths = list(Path(drc_folder_path).rglob("*.drc"))
        jpg_file_paths = list(Path(jpeg_folder_path).rglob("*.jpg"))

        # Validate file paths
        assert name != "", "Name should not be empty"

        assert len(drc_file_paths) > 0, "No DRC files found"
        assert len(jpg_file_paths) > 0, "No JPG files found"

        for drc_path in drc_file_paths:
            frame_number = int(drc_path.stem)
            jpg_path = jpeg_folder_path / f"{frame_number:04d}.jpg"
            assert jpg_path.exists(), f"DRC -> JPG file not found: {jpg_path}"

        if audio_path is not None:
            assert audio_path.suffix.lower() == ".wav", "Audio should be WAV"

        assert (
            export_path.suffix.lower() == ".4dr"
        ), "Export path should ends with .4dr"
        export_path.parent.mkdir(parents=True, exist_ok=True)

        # Get frame count
        start_frame = 0
        end_frame = None

        for drc_path in drc_file_paths:
            frame_number = int(drc_path.stem)
            end_frame = (
                max(end_frame, frame_number)
                if end_frame is not None
                else frame_number
            )

        frame_count = end_frame - start_frame + 1
        assert frame_count > 0, "Frame count should be greater than 0"

        if frame_count != len(drc_file_paths):
            logging.warning(
                f"Frame count mismatch: {frame_count} != {len(drc_file_paths)}"
            )

        # Prepare header
        header = Header(
            name=name,
            id=roll_id if roll_id is not None else name,
            frame_count=frame_count,
            audio_format="WAV" if audio_path is not None else "NULL",
            created_date=created_date.isoformat()
            if created_date
            else datetime.now().isoformat(),
        )

        progress_per_step = 1 / (len(drc_file_paths) + len(jpg_file_paths) + 1)
        total_progress = 0

        def log_progress():
            if on_progress_update:
                nonlocal total_progress
                nonlocal progress_per_step
                total_progress += progress_per_step
                on_progress_update(total_progress)

        def dump_frame(
            handler: BytesIO, drc_paths: List[Path], jpg_paths: List[Path]
        ) -> List[int]:
            positions = [handler.tell()]

            nonlocal start_frame
            nonlocal end_frame
            for this_frame_number in range(start_frame, end_frame + 1):
                # DRC
                frame_drc_path = (
                    Path(drc_folder_path) / f"{this_frame_number:04d}.drc"
                )

                # Consider the case where the frame number is not continuous
                if frame_drc_path.exists():
                    with open(drc_path, "rb") as fd:
                        drc_buffer = fd.read()
                else:
                    drc_buffer = b""

                handler.write(struct.pack("I", len(drc_buffer)))
                handler.write(drc_buffer)
                log_progress()

                # JPG
                frame_jpg_path = (
                    Path(jpeg_folder_path) / f"{this_frame_number:04d}.jpg"
                )

                if frame_jpg_path.exists():
                    with open(jpg_path, "rb") as fj:
                        handler.write(fj.read())
                log_progress()

                positions.append(handler.tell())
            return positions

        # Dump data
        buffer_handler = BytesIO()
        try:
            header.set_positions(
                "FRAME",
                dump_frame(buffer_handler, drc_file_paths, jpg_file_paths),
            )

            if audio_path is not None:
                audio_positions = [buffer_handler.tell()]
                with open(audio_path, "rb") as f:
                    buffer_handler.write(f.read())
                audio_positions.append(buffer_handler.tell())
                header.set_positions("AUDIO", audio_positions)

            # Pack header
            with open(export_path, "wb") as file_handler:
                file_handler.write(header.to_bytes())
                file_handler.write(buffer_handler.getvalue())
        except Exception as e:
            # Delete the file if failed
            buffer_handler.close()
            export_path.unlink()
            raise e
        finally:
            buffer_handler.close()

        return str(export_path)
