from common.fourdrec_roll import FourdrecRoll

ROLL_FILE_PATH = r"G:\postprocess\export\mu-shot_2\demo-mu-shot_2.4dr"

roll = FourdrecRoll(ROLL_FILE_PATH)

geo_buffer, jpg_buffer = roll.get_frame(0)
print(len(geo_buffer), len(jpg_buffer))
