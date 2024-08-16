import requests
import json
from pathlib import Path
import yaml
import logging
from PIL import Image
from io import BytesIO

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


SECRET_PATH = Path("G:/app/secrets.yml")
SUBMIT_PATH = Path("G:/submit")
THUMBNAIL_CAMERA_NAME = "20087901"

REQUEST_API_TIMEOUT = 10
REQUEST_PUT_TIMEOUT = 60 * 20  # 20 minutes

JOB_STATUS = Literal["RUNNING", "COMPLETED", "FAILED"]
FRAME_STATUS = Literal[
    "RUNNING",
    "RESOLVED",
    "CONVERTED",
    "FAILED",
]


class CloudBridge:
    def __init__(
        self,
        project_id: str,
        project_name: str,
        shot_id: str,
        shot_name: str,
        job_id: str,
        job_name: str,
        frame_count: int,
        frame_number: int,
    ):
        self.project_id = project_id
        self.project_name = project_name
        self.shot_id = shot_id
        self.shot_name = shot_name
        self.job_id = job_id
        self.job_name = job_name
        self.frame_count = frame_count
        self.frame_number = frame_number

        # Secrets
        self.roll_web_api_key = ""
        self.roll_web_host = ""

        # Import secrets yaml
        secrets_yaml_path = Path(SECRET_PATH)
        if secrets_yaml_path.exists():
            with open(secrets_yaml_path, "r") as f:
                secrets_data = yaml.load(f, Loader=yaml.FullLoader)
                self.roll_web_api_key = secrets_data["roll_web_api_key"]
                self.roll_web_host = secrets_data["roll_web_host"]

    def __api(self, path: str, body: dict):
        url = f"{self.roll_web_host}/api/trpc/{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.roll_web_api_key}",
        }
        payload = json.dumps({"json": body})
        response = requests.post(
            url, data=payload, headers=headers, timeout=REQUEST_API_TIMEOUT
        )

        if response.status_code != 200:
            raise Exception(
                f"API request failed: {response.text}\n\n"
                f"Request: {headers}\n\n{payload}"
            )

        json_response = response.json()
        data = json_response["result"]["data"]["json"]
        return data

    def submit_job(self, thumbnail_frame_number: int = None):
        response = self.__api(
            "job.submit",
            {
                "projectId": self.project_id,
                "projectName": self.project_name,
                "shotId": self.shot_id,
                "shotName": self.shot_name,
                "id": self.job_id,
                "name": self.job_name,
                "frameCount": self.frame_count,
            },
        )

        # Check if thumbnail is uploaded
        if response == "no-url":
            return

        # Get thumbnail file path
        logging.info(f"Uploading thumbnail")
        camera_images_path = (
            SUBMIT_PATH
            / self.project_name
            / "shots"
            / self.shot_name
            / "images"
            / THUMBNAIL_CAMERA_NAME
        )
        thumbnail_paths = list(camera_images_path.glob("*.jpg"))
        if len(thumbnail_paths) == 0:
            logging.warning(f"No thumbnail found: {camera_images_path}")
            return

        thumbnail_path = str(thumbnail_paths[0])

        # Check if thumbnail_frame_number is provided
        if thumbnail_frame_number is not None:
            frame_number_thumbnail_path = (
                camera_images_path
                / f"{THUMBNAIL_CAMERA_NAME}_{thumbnail_frame_number:06d}.jpg"
            )
            if not frame_number_thumbnail_path.exists():
                logging.warning(f"Thumbnail frame not found: {thumbnail_path}")
            thumbnail_path = str(frame_number_thumbnail_path)

        # Resize thumbnail
        image = Image.open(thumbnail_path)
        image.thumbnail((1280, 1280))
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=80)
        image.close()

        # Upload file to cloud storage
        presigned_url: str = response
        requests.put(
            presigned_url, data=buffer.getvalue(), timeout=REQUEST_PUT_TIMEOUT
        )

        # Get file size
        file_size = buffer.tell()
        self.__api(
            "job.attachFile",
            {
                "id": self.job_id,
                "size": file_size,
                "type": "THUMBNAIL",
            },
        )

    def update_job(self, status: JOB_STATUS, file_path: str = None):
        response = self.__api(
            "job.update",
            {
                "id": self.job_id,
                "status": status,
            },
        )

        # If completed, upload file
        if status != "COMPLETED":
            return
        assert (
            file_path is not None
        ), "file_path is required for COMPLETED status"

        # Check if status is updated
        if response == "no-url":
            return

        # Upload file to cloud storage
        presigned_url: str = response
        with open(file_path, "rb") as f:
            requests.put(presigned_url, data=f, timeout=REQUEST_PUT_TIMEOUT)

        # Get file size
        file_size = Path(file_path).stat().st_size
        self.__api(
            "job.attachFile",
            {"id": self.job_id, "size": file_size, "type": "4DR"},
        )

    def update_frame(self, status: FRAME_STATUS, file_path: str = None):
        response = self.__api(
            "frame.update",
            {
                "jobId": self.job_id,
                "frameNumber": self.frame_number,
                "status": status,
            },
        )

        # If resolved, upload file
        if status != "RESOLVED":
            return
        assert (
            file_path is not None
        ), "file_path is required for RESOLVED status"

        # Check if status is updated
        if response == "no-url":
            return

        # Upload file to cloud storage
        presigned_url: str = response
        with open(file_path, "rb") as f:
            requests.put(presigned_url, data=f, timeout=REQUEST_PUT_TIMEOUT)

        # Get file size
        file_size = Path(file_path).stat().st_size
        self.__api(
            "frame.attachFile",
            {
                "jobId": self.job_id,
                "frameNumber": self.frame_number,
                "size": file_size,
            },
        )
