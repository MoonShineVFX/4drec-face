import os
if 'agisoft_LICENSE' not in os.environ:
    os.environ['agisoft_LICENSE'] = 'C:\\Program Files\\Agisoft\\Metashape Pro\\'

from .project import MetashapeProject