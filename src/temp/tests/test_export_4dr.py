from resolve.project import ResolveProject
from common.fourdrec_roll.header import Header, AudioFormat
from typing import cast

header = Header(id="test", name="123", frame_count=1, audio_format="WAV")
header.to_bytes(123)

# ResolveProject.export_fourdrec_roll(
#     export_path=r"G:\postprocess\export\jia",
#     with_hd=True,
#     project_name="Demo",
#     shot_name="Jiajia",
#     job_name="resolve1",
#     on_progress_update=lambda x: print(x),
# )
