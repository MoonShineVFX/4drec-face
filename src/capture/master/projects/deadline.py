from pymongo import MongoClient
import os
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

from utility.Deadline import DeadlineConnect
from utility.setting import setting
from utility.logger import log


# 連線 deadline
deadline = DeadlineConnect.DeadlineCon(
    setting.deadline_connect.ip, setting.deadline_connect.port,
    insecure=True
)

# mongodb
DMC = MongoClient(setting.deadline_mongo.ip, setting.deadline_mongo.port)
JOBS = DMC.deadline10db.Jobs
TASKS = DMC.deadline10db.JobTasks
DELETES = DMC.deadline10db.DeletedJobs


def check_deadline_server():
    try:
        deadline.Repository.GetWindowsAlternateAuxiliaryPath()
    except Exception as error:
        return str(error)

    return ''


def submit_deadline(shot, job):
    job_info = {
        'Plugin': '4DREC',
        'BatchName': f'{shot.name} - {job.name}',
        'Name': f'{shot.name} - {job.name} (calibrate)',
        'UserName': 'autobot',
        'ChunkSize': '1',
        'Frames': '0',
        'OutputDirectory0': job.get_folder_path(),
        'ExtraInfoKeyValue0': 'resolve_stage=initialize',
        'ExtraInfoKeyValue1': f'yaml_path={job.get_folder_path()}/job.yml'
    }

    result = deadline.Jobs.SubmitJob(job_info, {})
    if not (isinstance(result, dict) and '_id' in result):
        log.error(result)
        return None

    init_id = result['_id']

    job_info.update({
        'Name': f'{shot.name} - {job.name} (resolve)',
        'Frames': f'{job.frame_range[0]}-{job.frame_range[1]}',
        'ExtraInfoKeyValue0': 'resolve_stage=resolve',
        'JobDependencies': init_id
    })

    result = deadline.Jobs.SubmitJob(job_info, {})
    if not (isinstance(result, dict) and '_id' in result):
        log.error(result)
        return None

    resolve_id = result['_id']

    return init_id, resolve_id


def get_task_list(deadline_id):
    is_delete = DELETES.find_one({'_id': deadline_id})
    if is_delete is not None:
        return {}

    task_list = {}
    tasks = TASKS.find({'JobID': deadline_id})

    for task in tasks:
        frame = task['Frames'].split('-')[0]
        state = task['Stat']
        task_list[frame] = state

    return task_list
