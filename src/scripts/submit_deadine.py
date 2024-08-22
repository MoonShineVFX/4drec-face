import os

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
from utility.Deadline import DeadlineConnect


deadline = DeadlineConnect.DeadlineCon("192.168.29.10", 8081, insecure=True)

job_info = {
    "Plugin": "4DREC",
    "BatchName": f"TEST export abc",
    "Name": f"test - abc",
    "UserName": "autobot",
    "ChunkSize": "1",
    "Frames": "0",
    "OutputDirectory0": r"G:\submit\wrap_test\shots\eli\jobs\resolve_1\output",
    "ExtraInfoKeyValue0": "resolve_stage=export_alembic",
    "ExtraInfoKeyValue1": r"yaml_path=G:\submit\wrap_test\shots\eli\jobs\resolve_1\job.yml",
}

result = deadline.Jobs.SubmitJob(job_info, {})
print(result)
