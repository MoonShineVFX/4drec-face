# 藉由相機位置去將 Metashape 的 Chunk 扳回原點
import Metashape


# Define
GROUP_UP: [int] = [2, 3]
GROUP_ORIGIN: [int] = [4, 5]
GROUP_LEFT: [int] = [12, 13]
Z_OFFSET = 0.3


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
cameras_left: [Metashape.Camera] = []

# Get groups
for camera in cameras:
    camera_number = get_camera_number(camera)
    if camera_number in GROUP_UP:
        cameras_up.append(camera)
    elif camera_number in GROUP_ORIGIN:
        cameras_origin.append(camera)
    elif camera_number in GROUP_LEFT:
        cameras_left.append(camera)

# Get positions
position_up = get_average_position(cameras_up)
position_origin = get_average_position(cameras_origin)
position_left = get_average_position(cameras_left)

# Calculate vectors
vector_up: Metashape.Vector = (position_up - position_origin).normalized()
vector_left: Metashape.Vector = (position_left - position_origin).normalized()
vector_forward = Metashape.Vector.cross(vector_left, vector_up)
position_pivot = position_left + (position_origin - position_left) / 2

# Create matrix
vector_left.size = 4
vector_left.w = 0
vector_up.size = 4
vector_up.w = 0
vector_forward.size = 4
vector_forward.w = 0
matrix_target = Metashape.Matrix((
    vector_left, vector_up, vector_forward, (0.0, 0.0, 0.0, 1.0)
))

# Apply transform
chunk.transform.matrix = matrix_target
position_pivot = matrix_target.mulp(position_pivot)
chunk.transform.translation = -position_pivot

# Region
region = chunk.region
region.center = matrix_target.inv().mulp(position_pivot)
region.rot = matrix_target.rotation().inv()
region.size = Metashape.Vector((1, 1, 1))