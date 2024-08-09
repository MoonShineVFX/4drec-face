# Sync data and files to cloudflare r2 and d1
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytz
import yaml
from bson.codec_options import CodecOptions
from pymongo import MongoClient

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["4DREC_TYPE"] = "MASTER"

from utility.setting import setting
from utility.logger import get_prefix_log
from common.cloud_bridge import CloudBridge
from utility.Deadline import DeadlineConnect

# Define MongoDB client
CLIENT = MongoClient(host=[setting.mongodb_address])
DB = CLIENT["4drec"]
DB.with_options(
    codec_options=CodecOptions(
        tz_aware=True, tzinfo=pytz.timezone("Asia/Taipei")
    )
)

# Define Deadline client
deadline = DeadlineConnect.DeadlineCon("192.168.29.10", 8081, insecure=True)

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

    # Remove unused files from old structured renders
    def purge_unused_files(self):
        output_path = self.__get_job_path() / "output"

        # If export_file_path not exists, it's old structure
        export_file_path = output_path / "export.4dr"
        if not export_file_path.exists():
            for file in output_path.iterdir():
                if file.name == "frame" and file.is_dir():
                    continue

                if file.is_dir():
                    logger.warning(f"Remove folder: {file}")
                    shutil.rmtree(file)
                else:
                    logger.warning(f"Remove file: {file}")
                    file.unlink()

    # Sync job to cloudflare including frame 4dframe files
    def sync(self, sync_frames=True):
        if self.job.get("synced", False):
            return

        logger.info(f"Sync job: {self}")

        # Submit job and shot/project database
        cloud_bridge = self.get_cloud_bridge(0)
        cloud_bridge.submit_job()

        # Upload job frames
        if sync_frames:
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_list = []

                for file in Path(
                    self.__get_job_path() / "output" / "frame"
                ).glob("*.4dframe"):
                    future = executor.submit(self.sync_frame, file)
                    future_list.append(future)

                count = 1
                for future in as_completed(future_list):
                    future.result()
                    logger.debug(f"Convert {count}/{len(future_list)}")
                    count += 1
            logger.info(f"Complete syncing job: {self}")

        # Mark job as synced
        DB.jobs.update_one(
            {"_id": self.job["_id"]},
            {"$set": {"synced": True}},
        )

    def sync_frame(self, frame_file: Path):
        frame_number = int(frame_file.stem)
        cloud_bridge = self.get_cloud_bridge(frame_number)
        cloud_bridge.update_frame("RESOLVED", str(frame_file))

    def get_cloud_bridge(self, frame_number: int):
        return CloudBridge(
            str(self.project["_id"]),
            self.project["name"],
            str(self.shot["_id"]),
            self.shot["name"],
            str(self.job["_id"]),
            self.job["name"],
            self.job["frame_range"][1] - self.job["frame_range"][0] + 1,
            frame_number,
        )

    # Let deadline handle the conversion and 4dr export
    def submit_conversion_to_deadline(self):
        if self.job.get("is_manual_submitted", False):
            return

        # Patch job yaml
        job_yaml_path = self.__get_job_path() / "job.yml"
        with open(job_yaml_path, "r") as f:
            job_config = yaml.load(f, Loader=yaml.FullLoader)
        if job_config.get("version", 0) < 3 or job_config.get(
            "job_path", ""
        ) != str(self.__get_job_path()):
            job_config.update(
                {
                    "version": 3,
                    "job_path": str(self.__get_job_path()),
                    "job_id": str(self.job["_id"]),
                    "job_name": self.job["name"],
                    "shot_id": str(self.shot["_id"]),
                    "shot_name": self.shot["name"],
                    "project_id": str(self.project["_id"]),
                    "project_name": self.project["name"],
                    "output_folder_name": "output",
                    "skip_masks": False,
                }
            )
            with open(job_yaml_path, "w") as f:
                yaml.dump(job_config, f)

        # Conversion payload
        job_info = {
            "Plugin": "4DREC",
            "BatchName": f"<PATCH> [{self.project['name']}] {self.shot['name']}"
            f" - {self.job['name']}",
            "Name": f"{self.shot['name']} - {self.job['name']} (conversion)",
            "UserName": "autobot",
            "ChunkSize": "1",
            "Frames": f"{self.job['frame_range'][0]}-{self.job['frame_range'][1]}",
            "isFrameDependent": "true",
            "OutputDirectory0": str(self.__get_job_path()),
            "ExtraInfoKeyValue0": "resolve_stage=conversion",
            "ExtraInfoKeyValue1": (
                f"yaml_path={self.__get_job_path() / 'job.yml'}"
            ),
        }
        result = deadline.Jobs.SubmitJob(job_info, {})
        if not (isinstance(result, dict) and "_id" in result):
            logger.error(result)
            return

        conversion_id = result["_id"]

        # Export stage
        job_info.update(
            {
                "Name": f"{self.shot['name']} - {self.job['name']} (export)",
                "Frames": "0",
                "ExtraInfoKeyValue0": "resolve_stage=export",
                "JobDependencies": conversion_id,
                "IsFrameDependent": "false",
            }
        )
        result = deadline.Jobs.SubmitJob(job_info, {})
        if not (isinstance(result, dict) and "_id" in result):
            logger.error(result)
            return

        export_id = result["_id"]

        # Update job with deadline ids and mark as manual submitted
        DB.jobs.update_one(
            {"_id": self.job["_id"]},
            {
                "$push": {"deadline_ids": [conversion_id, export_id]},
                "$set": {"is_manual_submitted": True},
            },
        )

    def is_valid(self):
        frame_path = self.__get_job_path() / "output" / "frame"
        return frame_path.exists()


def get_complete_jobs():
    # Find jobs that not synced
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
            DB.jobs.delete_one({"_id": job["_id"]})
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
            DB.shots.delete_one({"_id": shot["_id"]})
            continue

        this_complete_job = CompleteJob(job, shot, project)
        if not this_complete_job.is_valid():
            logger.warning(f"Job path not found: {this_complete_job}")
            continue

        this_complete_jobs.append(this_complete_job)

    return this_complete_jobs


if __name__ == "__main__":
    complete_jobs = get_complete_jobs()

    job_count = len(complete_jobs)
    progress = 1
    for job in complete_jobs:
        logger.info(f"======= Sync ({progress}/{job_count}) =======")
        job.sync()
        # job.submit_conversion_to_deadline()
        progress += 1
