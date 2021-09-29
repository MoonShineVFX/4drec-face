import mongomock
from datetime import datetime


def get_mock_client() -> mongomock.MongoClient:
    client = mongomock.MongoClient()
    db_projects = client['4drec']['projects']
    db_projects.insert_one({
        '_id': 'project_id_token',
        'name': 'test_project',
        'shot_count': 0,
        'is_archived': False,
        'created_at': datetime.now()
    })
    db_shots = client['4drec']['shots']
    db_shots.insert_one({
        '_id': 'shot_id_token',
        'project_id': 'project_id_token',
        'name': 'test_shot',
        'frame_range': [916, 1125],
        'size': 53453434599770,
        'missing_frames': {},
        'camera_parameters': {},
        'state': 2,  # created, recorded, submitted
        'cali': False,
        'created_at': datetime.now()
    })
    db_jobs = client['4drec']['jobs']
    db_jobs.insert_one({
        '_id': 'job_id_token',
        'shot_id': 'shot_id_token',
        'opencue_job_id': 'opencue_job_id',
        'name': 'test_job',
        'frame_range': [5, 17],
        'parameters': {},
        'state': 0,  # created, resolved
        'frame_list': {},
        'created_at': datetime.now()
    })
    return client
