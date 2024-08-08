from pathlib import Path

from common.fourd_frame import FourdFrameManager

output_path = Path(r"G:\submit\newapart\shots\eli\jobs\resolve_1\output")
old_file_path = output_path / "4df" / "001076.4df"
new_file_path = output_path / "frame" / "0000.4dframe"
new_file_path.parent.mkdir(parents=True, exist_ok=True)

FourdFrameManager.convert_to_new_fourdrec_frame(
    old_file_path, new_file_path, True
)
