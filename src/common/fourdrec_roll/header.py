from dataclasses import dataclass, field, asdict
from typing import List, Type
import json
import struct

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

    geometry_buffer_positions: List[int] = field(default_factory=list)
    texture_buffer_positions: List[int] = field(default_factory=list)
    hd_geometry_buffer_positions: List[int] = field(default_factory=list)
    hd_texture_buffer_positions: List[int] = field(default_factory=list)
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
    version: str = "1"

    def set_positions(
        self,
        position_type: Literal[
            "GEOMETRY", "TEXTURE", "AUDIO", "HD_GEOMETRY", "HD_TEXTURE"
        ],
        positions: List[int],
    ):
        """Set the positions of the buffers in the header.

        For validation and frame count auto-detection.
        """

        if position_type == "GEOMETRY":
            self.positions.geometry_buffer_positions = positions
        elif position_type == "TEXTURE":
            self.positions.texture_buffer_positions = positions
        elif position_type == "AUDIO":
            self.positions.audio_buffer_positions = positions
        elif position_type == "HD_GEOMETRY":
            self.positions.hd_geometry_buffer_positions = positions
        elif position_type == "HD_TEXTURE":
            self.positions.hd_texture_buffer_positions = positions
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

    def to_bytes(self, header_position) -> bytes:
        json_data = json.dumps(asdict(self)).encode("utf-8")

        # Pack footer
        header_hint = {
            "format": FORMAT.encode("ascii"),
            "header_position": header_position,
            "header_size": len(json_data),
        }
        header_hint_bytes = struct.pack("4sII", *header_hint.values())

        return json_data + header_hint_bytes
