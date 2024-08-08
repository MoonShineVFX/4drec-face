"""
This script is used to migrate old job structure to current(2024/8/8) structure
- Rename export folder to output folder
- Move 4df files to frame folder
- Convert 4df to 4dframe
- Remove 4df folder
"""

from pymongo import MongoClient
from bson.codec_options import CodecOptions
import os
import pytz
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

os.environ["4DREC_TYPE"] = "MASTER"

from utility.setting import setting
from utility.logger import get_prefix_log
from common.fourd_frame import FourdFrameManager

# Define MongoDB client
CLIENT = MongoClient(host=[setting.mongodb_address])
DB = CLIENT["4drec"]
DB.with_options(
    codec_options=CodecOptions(
        tz_aware=True, tzinfo=pytz.timezone("Asia/Taipei")
    )
)


# Define logger
logger = get_prefix_log("JOB")

# Define complete jobs
SUBMIT_PATH = Path(r"G:\submit")


class CompleteJob:
    def __init__(self, job, shot, project):
        self.job = job
        self.shot = shot
        self.project = project

    def __str__(self):
        return (
            f"[{self.project['name']}]"
            f" {self.shot['name']} - {self.job['name']}"
        )

    def __get_job_path(self):
        return (
            SUBMIT_PATH
            / self.project["name"]
            / "shots"
            / self.shot["name"]
            / "jobs"
            / self.job["name"]
        )

    def migrate(self):
        logger.info(f"Migrating job: {self}")

        # Check if job folder exists
        if not self.__get_job_path().exists():
            logger.warning(f"Job not found: {self}")
            return

        # Rename export path to output path
        export_path = self.__get_job_path() / "export"
        output_path = self.__get_job_path() / "output"
        if export_path.exists():
            logger.debug(f"Export path exists: {export_path}, renaming")
            export_path.rename(output_path)

        if not output_path.exists():
            logger.warning(f"Output path not found: {output_path}")
            return

        # If 4df on root folder, move to 4df folder
        old_frame_path = output_path / "4df"
        for file in output_path.iterdir():
            if file.suffix == ".4df":
                logger.debug(f"Move 4df to 4df folder: {file}")
                new_path = old_frame_path / file.name
                new_path.parent.mkdir(parents=True, exist_ok=True)
                file.rename(new_path)

        # If frame folder not exist or files count not the same as 4df
        # convert 4df to 4dframe, and start with 0 frame number
        should_convert = False
        frame_path = output_path / "frame"

        if frame_path.exists() and old_frame_path.exists():
            old_frame_files_count = len(list(old_frame_path.glob("*.4df")))
            frame_files_count = len(list(frame_path.glob("*.4dframe")))
            should_convert = old_frame_files_count != frame_files_count

        if not frame_path.exists() or should_convert:
            logger.debug(f"Frame path convert: {frame_path}")
            frame_path.mkdir(parents=True, exist_ok=True)

            # Project after 2023/04/12 and before 2024/07/28 should rotate
            # 180 degrees
            job_datetime = self.job["_id"].generation_time.replace(tzinfo=None)
            is_180_rotation = (
                datetime(2023, 4, 12) <= job_datetime < datetime(2024, 7, 28)
            )

            # Get frame offset
            old_frame_files = list((output_path / "4df").glob("*.4df"))
            start_frame_number = min(
                int(file.stem) for file in old_frame_files
            )

            # Convert 4df to 4dframe
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_list = []
                for file in old_frame_files:
                    this_frame_number = int(file.stem) - start_frame_number
                    new_path = frame_path / f"{this_frame_number:04d}.4dframe"

                    # Bypass if file converted
                    if new_path.exists():
                        continue

                    future = executor.submit(
                        FourdFrameManager.convert_to_new_fourdrec_frame,
                        str(file),
                        str(new_path),
                        is_180_rotation,
                    )
                    future_list.append(future)

                count = 1
                for future in as_completed(future_list):
                    future.result()
                    logger.debug(f"Convert {count}/{len(future_list)}")
                    count += 1

        # Remove 4df folder
        if old_frame_path.exists():
            folder_size = sum(
                file.stat().st_size for file in old_frame_path.glob("*")
            )
            size_str = f"{folder_size / 1024 / 1024:.2f} MB"
            logger.debug(f"Remove 4df folder: {old_frame_path} ({size_str})")
            shutil.rmtree(str(old_frame_path))
            return folder_size
        return 0


def get_complete_jobs():
    # Get all jobs before 2024/07/22
    jobs = list(DB.jobs.find())

    # Get shots
    shot_ids = [job["shot_id"] for job in jobs]
    shots = list(DB.shots.find({"_id": {"$in": shot_ids}}))

    # Get projects
    project_ids = [shot["project_id"] for shot in shots]
    projects = list(DB.projects.find({"_id": {"$in": project_ids}}))

    # Create complete jobs
    this_complete_jobs = []
    for job in jobs:
        # Get relations
        shot = next(
            (shot for shot in shots if shot["_id"] == job["shot_id"]), None
        )
        if shot is None:
            logger.warning(f"Shot not found: {job}")
            continue

        project = next(
            (
                project
                for project in projects
                if project["_id"] == shot["project_id"]
            ),
            None,
        )
        if project is None:
            logger.warning(f"Project not found: {job}")
            continue

        this_complete_jobs.append(CompleteJob(job, shot, project))

    return this_complete_jobs


if __name__ == "__main__":
    complete_jobs = get_complete_jobs()

    remove_size = 0
    for complete_job in complete_jobs:
        result = complete_job.migrate()
        if result is not None:
            remove_size += result

    logger.info(f"Remove size: {remove_size / 1024 / 1024 / 1024:.2f} GB")
