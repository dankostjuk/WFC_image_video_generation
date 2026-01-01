"""Settings widgets for image and video generation."""
# pylint: disable=no-name-in-module

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


def read_int(line: QLineEdit, current: int) -> int:
    """Parse int from line edit, falling back to current."""
    text = line.text().strip()
    return int(text) if text else current


class WFCConfig(QWidget):  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """UI widget exposing WFC configuration values."""
    def __init__(self, parent=None):
        """Initialize defaults and build the form."""
        super().__init__(parent)
        self.tile_size: int = 3
        self.output_width: int = 30
        self.output_height: int = 30
        self.periodic_input: bool = True
        self.periodic_output: bool = False
        self.symmetry: int = 1
        self.seed: int | None = None
        self.backtrack_limit: int = 1000
        self.show_grid: bool = True
        self._build_ui()

    def _build_ui(self) -> None:
        """Create inputs for WFC parameters."""
        self.tile_size_edit_line = QLineEdit()
        self.output_width_edit_line = QLineEdit()
        self.symmetry_edit_line = QLineEdit()

        self.tile_size_edit_line.setPlaceholderText(f"{self.tile_size} ex. 2, 3, 4")
        self.output_width_edit_line.setPlaceholderText(f"{self.output_width} ex. 50, 70")
        self.symmetry_edit_line.setPlaceholderText(f"{self.symmetry} ex. 1, 2, 4, 8")


        layout = QFormLayout(self)
        layout.addRow(QLabel("Tile size:"), self.tile_size_edit_line)
        layout.addRow(QLabel("Output size:"), self.output_width_edit_line)
        layout.addRow(QLabel("Symmetry:"), self.symmetry_edit_line)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)

        layout.addRow(self.apply_button)

    def apply(self) -> None:
        """Apply edits to config values."""
        self.tile_size = read_int(self.tile_size_edit_line, self.tile_size)
        self.output_width = read_int(self.output_width_edit_line, self.output_width)
        self.output_height = read_int(self.output_width_edit_line, self.output_height)
        self.symmetry = read_int(self.symmetry_edit_line, self.symmetry)


class VideoConfig(QWidget):  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """UI widget exposing video generation configuration values."""
    def __init__(self, parent=None):
        """Initialize defaults and build the form."""
        super().__init__(parent)

        self.out_dir: str = "frames"
        self.name_fmt: str = "frame_%06d.png"

        self.fps: int = 24
        self.frames_per_segment: int = 60
        self.b_start_frame: int = 1
        self.rotation_speed: int = 1

        self.start_zoom: float = 1.0
        self.end_zoom: float = 10.0
        self.anchor_x: float = 0.5
        self.anchor_y: float = 0.5
        self.target_x: float = self.anchor_x
        self.target_y: float = self.anchor_y
        self.circle_input: bool = False
        self.circle_radius_frac: float = 0.50
        self.rotate_input: bool = False
        self.reverse_output: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        """Create inputs for video parameters."""
        self.fps_edit_line = QLineEdit()
        self.frames_per_segment_edit_line = QLineEdit()
        self.b_start_frame_edit_line = QLineEdit()
        self.rotation_speed_edit_line = QLineEdit()
        self.rotate_input_check = QCheckBox()
        self.circle_input_check = QCheckBox()
        self.reverse_output_check = QCheckBox()



        self.fps_edit_line.setPlaceholderText(f"{self.fps} ex. 24, 30, 60")
        self.frames_per_segment_edit_line.setPlaceholderText(f"{self.frames_per_segment} ex. 60, 90, 360")
        self.b_start_frame_edit_line.setPlaceholderText(f"{self.b_start_frame} ex. 1, 10, 30")
        self.rotation_speed_edit_line.setPlaceholderText("ex. 1, 2, 3")

        layout = QFormLayout(self)
        layout.addRow(QLabel("fps:"), self.fps_edit_line)
        layout.addRow(QLabel("frames per segment:"), self.frames_per_segment_edit_line)
        layout.addRow(QLabel("start appear frame:"), self.b_start_frame_edit_line)
        layout.addRow(QLabel("Rotation speed:"), self.rotation_speed_edit_line)
        layout.addRow(QLabel("Rotate:"), self.rotate_input_check)
        layout.addRow(QLabel("Circular input:"), self.circle_input_check)
        layout.addRow(QLabel("Reverse output:"), self.reverse_output_check)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        layout.addRow(self.apply_button)

    def apply(self) -> None:
        """Apply edits to config values."""
        self.fps = read_int(self.fps_edit_line, self.fps)
        self.frames_per_segment = read_int(self.frames_per_segment_edit_line, self.frames_per_segment)
        self.b_start_frame = read_int(self.b_start_frame_edit_line, self.b_start_frame)
        self.rotation_speed = read_int(self.rotation_speed_edit_line, self.rotation_speed)
        self.b_start_frame = max(1, min(self.b_start_frame, self.frames_per_segment))

        self.rotate_input = self.rotate_input_check.isChecked()
        self.circle_input = self.circle_input_check.isChecked()
        self.reverse_output = self.reverse_output_check.isChecked()
