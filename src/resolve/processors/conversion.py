from pathlib import Path
import subprocess
import logging
from typing import Callable
from PIL import Image
from datetime import datetime

from settings import SETTINGS
from common.fourdrec_frame import FourdrecFrame


class Conversion:
    @staticmethod
    def get_houdini_path():
        se_folder = Path("C:\\Program Files\\Side Effects Software")
        if not se_folder.exists() or not se_folder.is_dir():
            return None
        for folder in Path("C:\\Program Files\\Side Effects Software").glob(
            "Houdini 19*"
        ):
            if folder.is_dir():
                return folder
        return None

    @staticmethod
    def run_process(commands: [str]):
        process = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        for line in process.stdout:
            logging.info(line.strip())
        process.stdout.close()

        return_code = process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, process.args)

    @staticmethod
    def convert_glb():
        output_path = SETTINGS.output_path
        frame_number = SETTINGS.output_frame_number

        # Run hython
        logging.info("Run Houdini")

        houdini_path = Conversion.get_houdini_path()
        if houdini_path is None:
            logging.critical("Houdini not found")
            raise ValueError("Houdini not found")

        hython_path = houdini_path / "bin" / "hython3.9.exe"
        if not hython_path.exists():
            logging.critical("Hython not found")
            raise ValueError("Hython not found")

        Conversion.run_process(
            [
                str(hython_path),
                str(Path(__file__).parent / "houdini.py"),
                "-i",
                str(output_path / "frame" / f"{frame_number:04d}.4dframe"),
                "-o",
                str(output_path / "glb" / f"{frame_number:04d}.glb"),
            ]
        )

    @staticmethod
    def convert_draco():
        logging.info("Convert draco drc")

        output_path = SETTINGS.output_path
        frame_number = SETTINGS.output_frame_number

        source_glb = Path(output_path / "glb" / f"{frame_number:04d}.glb")
        target_drc_folder = output_path / "drc"
        target_drc_folder.mkdir(parents=True, exist_ok=True)
        target_drc = target_drc_folder / (source_glb.stem + ".drc")

        Conversion.run_process(
            [
                "G:\\app\\draco_encoder",
                "-i",
                str(source_glb),
                "-o",
                str(target_drc),
                "-qp",
                "14",
                "-qt",
                "14",
                "-cl",
                "5",
            ]
        )

    @staticmethod
    def convert_texture():
        logging.info("Convert texture")

        output_path = SETTINGS.output_path
        frame_number = SETTINGS.output_frame_number
        frame_path = output_path / "frame" / f"{frame_number:04d}.4dframe"
        frame = FourdrecFrame(str(frame_path))

        target_folder = output_path / f"texture_2k"
        target_folder.mkdir(parents=True, exist_ok=True)
        target_path = target_folder / f"{frame_number:04d}.jpg"

        image = Image.fromarray(frame.get_texture_array(), mode="RGB")
        image.thumbnail((2048, 2048), Image.LANCZOS)
        image.save(str(target_path), "JPEG", quality=75)

    @staticmethod
    def convert_audio():
        logging.info("Convert audio")
        # Save audio
        audio_path = SETTINGS.shot_path.parent / "audio.wav"
        if audio_path.exists():
            audio_target_path = SETTINGS.output_path / "audio.wav"
            audio_start_time = SETTINGS.start_frame / 30
            audio_duration = (SETTINGS.end_frame - SETTINGS.start_frame) / 30

            Conversion.run_process(
                [
                    "g:\\app\\ffmpeg",
                    "-i",
                    str(audio_path).replace("/", "\\"),
                    "-ss",
                    str(audio_start_time),
                    "-t",
                    str(audio_duration),
                    str(audio_target_path).replace("/", "\\"),
                    "-y",
                ]
            )
        else:
            logging.warning(
                f"Audio {audio_path} not exists, skip audio conversion."
            )

    @staticmethod
    def export_fourdrec_roll(
        # Names
        on_progress_update: Callable[[float], None] = None,
    ):
        logging.info("Export 4DR file")
        from common.fourdrec_roll import FourdrecRoll

        # Get metadata
        project_name = SETTINGS.project_name
        shot_name = SETTINGS.shot_name

        # Get paths
        output_path = SETTINGS.output_path

        drc_folder_path = output_path / "drc"
        jpeg_folder_path = output_path / "texture_2k"
        export_path = output_path / f"export.4dr"
        audio_path = output_path / "audio.wav"

        if not audio_path.is_file():
            audio_path = None

        # Try to get created_date from job.yaml
        created_date = SETTINGS.created_at
        # Get datetime from export_path created date if is not set
        if created_date is None:
            created_date = datetime.fromtimestamp(output_path.stat().st_ctime)

        return FourdrecRoll.pack(
            name=f"{project_name} - {shot_name}",
            drc_folder_path=drc_folder_path,
            jpeg_folder_path=jpeg_folder_path,
            export_path=export_path,
            audio_path=audio_path,
            roll_id=SETTINGS.job_id,
            on_progress_update=on_progress_update,
            created_date=created_date,
        )
