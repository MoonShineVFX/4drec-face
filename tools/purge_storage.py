import shutil
from pathlib import Path
from datetime import datetime, timedelta
import os


if os.getenv('DELETABLE_DATE') is not None:
    DELETABLE_DATE = datetime.fromisoformat(os.getenv('DELETABLE_DATE'))
else:
    DELETABLE_DATE = datetime.now() - timedelta(days=365)
DISKS = ['d:/', 'e:/', 'f:/']

# get disk usage
def get_disk_usage(path: str):
    total, used, free = shutil.disk_usage(path)
    return total, used, free

def get_size_before_time(disk: str, before_time: float):
    total_size_before_date = 0
    for file in Path(f'{disk}/4drec_data').glob('**/*'):
        if file.is_file():
            stat = file.stat()
            if stat.st_ctime < before_time:
                total_size_before_date += stat.st_size
    return total_size_before_date


for disk in DISKS:
    total, used, free = get_disk_usage(disk)

    # print usage with percent
    deletable_size = get_size_before_time(disk, DELETABLE_DATE.timestamp())
    print(f'{disk} used: {used / total * 100:.2f}%, deletable size: {deletable_size / (2**30):.2f} GB ({deletable_size / total * 100:.2f}%)')

user_input = input('Delete? (y/n): ')

if user_input.lower() in ['y', 'yes']:
    errors = []
    for disk in DISKS:
        for file in Path(f'{disk}/4drec_data').glob('**/*'):
            if file.is_file():
                stat = file.stat()
                if stat.st_ctime < DELETABLE_DATE.timestamp():
                    print(f'delete {file}')
                    try:
                        file.unlink()
                    except Exception as e:
                        errors.append((file, e))

    print('done')

    if len(errors) > 0:
        print('errors:')
        for error in errors:
            print(f'{error[0]}: {error[1]}')
