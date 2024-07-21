import struct
from pathlib import Path
from typing import Callable, List, Union
from datetime import datetime
import json
from dataclasses import asdict
from io import BytesIO

from .header import Header


# Define a type for the progress update callback function
OnProgressUpdateCallback = Callable[[float], None]
InputPath = Union[str, Path]


class FourdrecRoll:
    def __init__(self, path: InputPath):
        self._path = Path(path)

        with open(self._path, "rb") as f:
            self.header: Header = Header.from_file(file=f)

    def __str__(self):
        return f"FourdrecRoll\n{json.dumps(asdict(self.header), indent=4)}"

    @staticmethod
    def pack(
        name: str,
        drc_folder_path: InputPath,
        jpeg_folder_path: InputPath,
        output_path: InputPath,
        audio_path: InputPath = None,
        hd_drc_folder_path: InputPath = None,
        hd_jpeg_folder_path: InputPath = None,
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
        hd_drc_folder_path = (
            Path(hd_drc_folder_path)
            if hd_drc_folder_path is not None
            else None
        )
        hd_jpeg_folder_path = (
            Path(hd_jpeg_folder_path)
            if hd_jpeg_folder_path is not None
            else None
        )
        audio_path = Path(audio_path) if audio_path is not None else None
        output_path = Path(str(output_path).lower())

        # Get file paths
        drc_file_paths = list(Path(drc_folder_path).rglob("*.drc"))
        jpg_file_paths = list(Path(jpeg_folder_path).rglob("*.jpg"))

        hd_drc_file_paths = []
        hd_jpg_file_paths = []
        if hd_drc_folder_path:
            hd_drc_file_paths = list(Path(hd_drc_folder_path).rglob("*.drc"))
            assert hd_jpeg_folder_path is not None, "HD jpg path is required"
        if hd_jpeg_folder_path:
            hd_jpg_file_paths = list(Path(hd_jpeg_folder_path).rglob("*.jpg"))
            assert hd_drc_folder_path is not None, "HD drc path is required"
        has_hd = hd_drc_folder_path is not None

        # Validate file paths
        assert name != "", "Name should not be empty"

        assert len(drc_file_paths) > 0, "No DRC files found"
        assert len(jpg_file_paths) > 0, "No JPG files found"

        assert len(drc_file_paths) == len(
            jpg_file_paths
        ), f"Jpg and drc files are not matched"

        if has_hd:
            assert len(hd_drc_file_paths) == len(
                hd_jpg_file_paths
            ), f"HD jpg and drc files are not matched"

            assert len(hd_drc_file_paths) > 0, "No HD DRC files found"
            assert len(hd_jpg_file_paths) > 0, "No HD JPG files found"

        if audio_path is not None:
            assert audio_path.suffix.lower() == ".wav", "Audio should be WAV"

        assert (
            output_path.suffix.lower() == ".4dr"
        ), "Output should ends with .4dr"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare header
        header = Header(
            name=name,
            id=roll_id if roll_id is not None else name,
            frame_count=len(drc_file_paths),
            audio_format="WAV" if audio_path is not None else "NULL",
            created_date=created_date.isoformat()
            if created_date
            else datetime.now().isoformat(),
        )

        progress_per_step = 1 / (
            len(drc_file_paths)
            + len(jpg_file_paths)
            + len(hd_drc_file_paths)
            + len(hd_jpg_file_paths)
            + 1
        )
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
            for drc_path, jpg_path in zip(drc_paths, jpg_paths):
                with open(drc_path, "rb") as fd:
                    drc_buffer = fd.read()
                    handler.write(struct.pack("I", len(drc_buffer)))
                    handler.write(drc_buffer)
                log_progress()

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

            if has_hd:
                header.set_positions(
                    "HD_FRAME",
                    dump_frame(
                        buffer_handler, hd_drc_file_paths, hd_jpg_file_paths
                    ),
                )

            # Pack header
            with open(output_path, "wb") as file_handler:
                file_handler.write(header.to_bytes())
                file_handler.write(buffer_handler.getvalue())
        except Exception as e:
            # Delete the file if failed
            buffer_handler.close()
            output_path.unlink()
            raise e
        finally:
            buffer_handler.close()

        return str(output_path)
