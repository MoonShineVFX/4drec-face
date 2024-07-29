from resolve.resolver import Resolver
from pathlib import Path


export_root_path = Path(r"G:\postprocess\export")
shot_names = ["banban", "xiang", "jia", "mu-shot_3"]


def print_progress(label: str, progress: float):
    print(f"[{label}] Progress: {round(progress * 100)}%")


for shot_name in shot_names:
    print("Convert", shot_name)

    Resolver.export_fourdrec_roll(
        output_path=str(export_root_path / shot_name),
        project_name="Legacy",
        shot_name=shot_name,
        job_name="resolve1",
        with_hd=True,
        on_progress_update=lambda progress: print_progress(
            shot_name, progress
        ),
    )
