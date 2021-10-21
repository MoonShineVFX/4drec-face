from utility.Deadline import DeadlineConnect


deadline = DeadlineConnect.DeadlineCon('192.168.29.10', 8080)

job_info = {
    'Plugin': '4DREC',
    'BatchName': f'TEST BIG BATCH',
    'Name': f'test - calibrate',
    'UserName': 'autobot',
    'ChunkSize': '1',
    'Frames': '0',
    'OutputDirectory0': r'G:\jobs\9e9802\test_shot\test_job',
    'ExtraInfoKeyValue0': 'resolve_stage=INITIALIZE',
    'ExtraInfoKeyValue1': r'yaml_path=G:\jobs\9e9802\test_shot\test_job\job.yml'
}

result = deadline.Jobs.SubmitJobs(job_info, {})
init_id = ''
if isinstance(result, dict) and '_id' in result:
    init_id = result['_id']
else:
    raise ValueError(result)

job_info = {
    'Plugin': '4DREC',
    'BatchName': f'TEST BIG BATCH',
    'Name': f'test - resolve',
    'UserName': 'autobot',
    'ChunkSize': '1',
    'Frames': '0-1593',
    'OutputDirectory0': r'G:\jobs\9e9802\test_shot\test_job',
    'JobDependencies': init_id,
    'ExtraInfoKeyValue0': 'resolve_stage=RESOLVE',
    'ExtraInfoKeyValue1': r'yaml_path=G:\jobs\9e9802\test_shot\test_job\job.yml'
}

result = deadline.Jobs.SubmitJobs(job_info, {})
print(result)