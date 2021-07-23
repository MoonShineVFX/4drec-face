# 藉由相機位置去將 Metashape 的 Chunk 扳回原點
import Metashape


# Define
GROUP_UP: [int] = [2, 3]
GROUP_ORIGIN: [int] = [4, 5]
GROUP_HORIZON: [int] = [12, 13]
GROUP_DISTANCE: [int] = [5, 12]
CAMERA_REFERENCE_DISTANCE = 0.5564
CENTER_OFFSET = (0.0, -0.2, 0.3)
REGION_SIZE = (0.5, 0.5, 0.5)


def get_camera_number(camera: Metashape.Camera) -> int:
    return int(camera.label.split('_')[1])


def get_average_position(camera_list: [Metashape.Camera]) -> Metashape.Vector:
    position = Metashape.Vector((0, 0, 0))
    for camera in camera_list:
        position += camera.transform.translation()
    return position / len(camera_list)


# Main
print('==================== Camera Transform Calibration ====================')

doc: Metashape.Document = Metashape.app.document
chunk: Metashape.Chunk = doc.chunk
cameras: [Metashape.Camera] = chunk.cameras

cameras_up: [Metashape.Camera] = []
cameras_origin: [Metashape.Camera] = []
cameras_horizon: [Metashape.Camera] = []
cameras_distance: [Metashape.Camera] = []

# Get groups
for cam in cameras:
    camera_number = get_camera_number(cam)
    if camera_number in GROUP_UP:
        cameras_up.append(cam)
    elif camera_number in GROUP_ORIGIN:
        cameras_origin.append(cam)
    elif camera_number in GROUP_HORIZON:
        cameras_horizon.append(cam)
    if camera_number in GROUP_DISTANCE:
        cameras_distance.append(cam)

# Get scale ratio
scale_vector = cameras_distance[0].transform.translation()\
               - cameras_distance[1].transform.translation()
camera_distance = scale_vector.norm()
scale_ratio = CAMERA_REFERENCE_DISTANCE / camera_distance

# Get positions
position_up = get_average_position(cameras_up)
position_origin = get_average_position(cameras_origin)
position_left = get_average_position(cameras_horizon)

# Get vectors for rotation matrix
vector_up: Metashape.Vector = (position_up - position_origin).normalized()
vector_horizon: Metashape.Vector = (
        position_left - position_origin
).normalized()
vector_forward = Metashape.Vector.cross(vector_horizon, vector_up)

# Get pivot_center
pivot_center = position_left + (position_origin - position_left) / 2
pivot_offset = Metashape.Vector(CENTER_OFFSET)

# Create matrix_target
vector_horizon.size = 4
vector_horizon.w = 0
vector_up.size = 4
vector_up.w = 0
vector_forward.size = 4
vector_forward.w = 0
matrix_target = Metashape.Matrix((
    vector_horizon, vector_up, vector_forward, (0.0, 0.0, 0.0, 1.0)
))

# Apply Chunk transform
chunk.transform.matrix = matrix_target
chunk.transform.scale = scale_ratio
chunk.transform.translation = -matrix_target.mulp(
    pivot_center * scale_ratio
)
chunk.transform.translation += pivot_offset

# Apply Region transform
region = chunk.region
region.center = pivot_center - matrix_target.inv().mulp(
    pivot_offset / scale_ratio
)
region.rot = matrix_target.rotation().inv()
region.size = Metashape.Vector(REGION_SIZE) / scale_ratio
