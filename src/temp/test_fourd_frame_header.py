from common.fourd_frame import FourdFrameManager


load_path = r'G:\temp\mu_test.4df'
fourd_frame = FourdFrameManager.load(load_path)

FourdFrameManager.save_from_frame(fourd_frame, r'G:\temp\mu_test_vison.4dr')

# new_fourd_frame = FourdFrameManager.load(r'G:\temp\mu_test_vison.4df')

# print(fourd_frame.get_geo_data()[0][:5])
# print(new_fourd_frame.get_geo_data()[0][:5])