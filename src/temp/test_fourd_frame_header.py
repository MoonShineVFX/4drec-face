from common.fourd_frame import FourdFrameManager


load_path = r'G:\jobs\4cdd8d\87be91\3d9a44\output\035766.4df'
fourd_frame = FourdFrameManager.load(load_path)

print(fourd_frame.header)
fourd_frame.get_houdini_data()
