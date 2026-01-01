"""Output preview widget for generated images."""
# pylint: disable=no-name-in-module

from PySide6.QtCore import Signal, Slot, QTimer
from PySide6.QtGui import QPixmap, QMouseEvent, Qt, QImage, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSizePolicy, QHBoxLayout, QLabel, QPushButton,
)


class OutputWidget(QWidget):
    """Display generated output with start/cancel controls."""

    startGeneration = Signal()
    cancelGeneration = Signal()
    nextFrame = Signal()

    def __init__(self, img: QImage, parent: QWidget | None = None):
        """Create the output widget with an initial image."""
        super().__init__(parent)
        self.image_label = QLabel(self)
        self.start_button = QPushButton("Generate", self)
        self.cancel_button = QPushButton("Cancel", self)
        self.image = img
        self.image_np = None
        self._build_ui()

    @Slot(QImage)
    def set_image(self, qimg: QImage, show_grid: bool) -> None:
        """Update the displayed image."""
        self.image = qimg
        self._update(show_grid)

    def _draw_grid_overlay(
        self, img: QImage, thickness: int = 1, color: QColor = QColor("black")
    ) -> QImage:
        """Return the input image (grid overlay not implemented yet)."""
        _ = thickness, color
        return img

    def _build_ui(self) -> None:
        """Build labels, buttons, and layout."""
        self.image_label.setAlignment(Qt.AlignCenter)
        self.start_button.setMinimumHeight(36)
        self.start_button.clicked.connect(self.startGeneration.emit)
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.clicked.connect(self.cancelGeneration.emit)

        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        v = QVBoxLayout(self)
        v.setContentsMargins(2, 2, 2, 2)
        v.setSpacing(8)
        v.addWidget(self.image_label, 0)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addWidget(self.start_button, 1)
        buttons.addWidget(self.cancel_button, 1)
        v.addLayout(buttons, 0)
        QTimer.singleShot(0, self._update)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        """Trigger generation on click."""
        if e.button() == Qt.LeftButton:
            self.startGeneration.emit()
            e.accept()
            return
        super().mouseReleaseEvent(e)


    def resizeEvent(self, e) -> None:
        """Refresh image scaling on resize."""
        super().resizeEvent(e)
        self._update(False)

    def _update(self, show_grid: bool = False) -> None:
        """Scale the image to fit the label."""
        if not self.image or self.image_label.size().isEmpty():
            return
        scaled = self.image.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )
        if show_grid:
            scaled = self._draw_grid_overlay(scaled)
        self.image_label.setPixmap(QPixmap.fromImage(scaled))
