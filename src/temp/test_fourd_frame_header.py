from common.fourd_frame import FourdFrameManager


load_path = r'C:\Users\eli\Desktop\mu_test.4df'
fourd_frame = FourdFrameManager.load(load_path)

FourdFrameManager.save_from_frame_for_test(fourd_frame, r'C:\Users\eli\Desktop\mu_test_draco.4dr')

new_fourd_frame = FourdFrameManager.load(r'C:\Users\eli\Desktop\mu_test_draco.4dr')

print(fourd_frame.get_geo_data()[0][0], fourd_frame.get_geo_data()[1][0])
print(new_fourd_frame.get_geo_data()[0][0], new_fourd_frame.get_geo_data()[1][0])
print(len(fourd_frame.get_geo_data()[0]), len(fourd_frame.get_geo_data()[1]))
print(len(new_fourd_frame.get_geo_data()[0]) // 3, len(new_fourd_frame.get_geo_data()[1]) // 2)
