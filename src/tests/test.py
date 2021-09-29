import sys
import os
from pathlib import Path
import mongomock

from capture.main import start


os.environ['testing'] = 'true'


# Define paths
current_path = Path(__file__)
src_path = current_path.parent.parent
capture_path = src_path / 'capture'

sys.path.insert(0, str(src_path))
sys.path.insert(0, str(capture_path))

# Mock sys.argv
main_py = capture_path / 'main.py'
sys.argv = [str(main_py), 'MASTER']

# Mock DB
client = mongomock.MongoClient()

# Execute
start()
