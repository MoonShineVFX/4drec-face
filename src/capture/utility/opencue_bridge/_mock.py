from .opencue_bridge import OpenCueBridge as RealOpenCueBridge


class OpenCueBridge(RealOpenCueBridge):
    @staticmethod
    def get_frame_list(job_id):
        frame_list = {}
        task_state = (0, 6, 2, 3, 5, 4)
        for i, f in enumerate(range(5, 18)):
            frame_list[str(f)] = task_state[(i + 1) % 6]
        return frame_list
