import os

os.environ.update({
    'agisoft_LICENSE': 'D:\\',
    'shot_path': r'C:\Users\eli\Desktop\export\near4d',
    'job_path': r'C:\Users\eli\Desktop\metashape\auto',
    'start_frame': '0',
    'end_frame': '119',
    'current_frame': '0'
})


if __name__ == '__main__':
    from common.metashape_manager import MetashapeProject
    project = MetashapeProject()
    # project.initial()
    project.calibrate()
    # project.resolve()

    # for f in range(5981, 6012):
    #     print(f'=================== {f} =================== ')
    #     os.environ['current_frame'] = str(f)
    #     project = MetashapeProject()
    #     project.resolve()
