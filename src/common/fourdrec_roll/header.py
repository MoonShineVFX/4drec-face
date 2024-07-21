from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Type, BinaryIO, Tuple
import json
import struct
from datetime import datetime

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


VERSION = "1"
FORMAT = "4DR1"


GeometryFormat: Type[str] = Literal["DRC"]
TextureFormat: Type[str] = Literal["JPEG"]
AudioFormat: Type[str] = Literal["WAV", "NULL"]


@dataclass
class HeaderPositions:
    """This class is used to store the positions of the buffers in the header.

    Length of the list should be frame_count + 1.
    It's because the first position is the start of the first frame and
    the last position is the end of the last frame.
    """

    frame_buffer_positions: List[int] = field(default_factory=list)
    hd_frame_buffer_positions: List[int] = field(default_factory=list)
    audio_buffer_positions: List[int] = field(default_factory=list)


@dataclass
class Header:
    """This class is used to store the header of the roll file.

    It'll be encoded to json and stored in the end of the roll file.
    Maybe should call it Footer instead of Header :thinking:
    """

    # Meta
    name: str
    id: str
    # Playback
    frame_count: int
    fps: int = 30
    # 3D adjust
    rotation: float = 0.0  # Axis Y, for old 180 model
    clip: float = 0.0  # Z clip below
    offset: List[float] = field(
        default_factory=lambda: [0.0, 0.0, 0.0]
    )  # X, Y, Z
    # Data format
    geometry_format: GeometryFormat = "DRC"
    texture_format: TextureFormat = "JPEG"
    audio_format: AudioFormat = "WAV"
    texture_resolutions: List[int] = field(
        default_factory=lambda: [2048, 4096]
    )  # HD use 4096
    # Positions
    positions: HeaderPositions = field(default_factory=HeaderPositions)
    # Misc
    version: str = "1"
    created_date: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def set_positions(
        self,
        position_type: Literal["FRAME", "HD_FRAME", "AUDIO"],
        positions: List[int],
    ):
        """Set the positions of the buffers in the header.

        For validation and frame count auto-detection.
        """

        if position_type == "FRAME":
            self.positions.frame_buffer_positions = positions
        elif position_type == "HD_FRAME":
            self.positions.hd_frame_buffer_positions = positions
        elif position_type == "AUDIO":
            self.positions.audio_buffer_positions = positions
        else:
            raise ValueError(f"Unknown position type: {position_type}")

        if position_type == "AUDIO":
            assert len(positions) == 2, "Audio should have only 2 position"
        else:
            frame_count = len(positions) - 1
            if self.frame_count == 0:
                self.frame_count = frame_count
            else:
                assert self.frame_count == frame_count, "Frame count mismatch"

    def to_bytes(self) -> bytes:
        json_data = json.dumps(asdict(self)).encode("utf-8")

        # Pack footer
        header_hint = {
            "format": FORMAT.encode("ascii"),
            "header_size": len(json_data),
        }
        header_hint_bytes = struct.pack("4sI", *header_hint.values())

        return header_hint_bytes + json_data

    @classmethod
    def from_file(cls, file: BinaryIO) -> Tuple[Header, int]:
        file.seek(0)
        header_hint = struct.unpack("4sI", file.read(struct.calcsize("4sI")))

        assert header_hint[0] == FORMAT.encode("ascii"), "Invalid format"

        json_data = file.read(header_hint[1])
        header_dict = json.loads(json_data.decode("utf-8"))
        header_dict["positions"] = HeaderPositions(**header_dict["positions"])
        return cls(**header_dict), struct.calcsize("4sI") + header_hint[1]
