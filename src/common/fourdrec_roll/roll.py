from pathlib import Path
from typing import Callable, BinaryIO, List, Union
from datetime import datetime

from .header import Header


# Define a type for the progress update callback function
OnProgressUpdateCallback = Callable[[float], None]
InputPath = Union[str, Path]


class FourdrecRoll:
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

        total_progress = 0

        def log_progress(progress: float):
            if on_progress_update:
                nonlocal total_progress
                total_progress += progress
                on_progress_update(total_progress)

        def dump(
            handle: BinaryIO,
            paths: List[Path],
            per_dump_complete: Callable = None,
        ) -> List[int]:
            positions = []
            for path in paths:
                with open(path, "rb") as f:
                    this_data = f.read()
                    positions.append(handle.tell())
                    handle.write(this_data)
                if per_dump_complete:
                    per_dump_complete(path)
            positions.append(handle.tell())
            return positions

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

        # Dump data
        file_handler = open(output_path, "wb")
        try:
            header.set_positions(
                "GEOMETRY",
                dump(
                    file_handler,
                    drc_file_paths,
                    lambda path: log_progress(progress_per_step),
                ),
            )
            header.set_positions(
                "TEXTURE",
                dump(
                    file_handler,
                    jpg_file_paths,
                    lambda path: log_progress(progress_per_step),
                ),
            )

            if has_hd:
                header.set_positions(
                    "HD_GEOMETRY",
                    dump(
                        file_handler,
                        hd_drc_file_paths,
                        lambda path: log_progress(progress_per_step),
                    ),
                )
                header.set_positions(
                    "HD_TEXTURE",
                    dump(
                        file_handler,
                        hd_jpg_file_paths,
                        lambda path: log_progress(progress_per_step),
                    ),
                )

            if audio_path is not None:
                header.set_positions(
                    "AUDIO",
                    dump(
                        file_handler,
                        [audio_path],
                        lambda path: log_progress(progress_per_step),
                    ),
                )

            # Pack header
            header_position = file_handler.tell()
            file_handler.write(header.to_bytes(header_position))
        except Exception as e:
            # Delete the file if failed
            file_handler.close()
            output_path.unlink()
            raise e
        finally:
            file_handler.close()

        return str(output_path)
