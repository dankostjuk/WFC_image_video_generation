"""Custom browse button for selecting image files."""
# pylint: disable=no-name-in-module

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QFileDialog, QPushButton, QWidget

class ImageBrowseButton(QPushButton):  # pylint: disable=too-few-public-methods
    """Button that opens a file dialog and emits pathSelected(str) on success."""
    pathSelected = Signal(str)

    def __init__(self, text: str = "Add Image Input...", parent: QWidget | None = None) -> None:
        """Initialize button and connect click handler."""
        super().__init__(text, parent)
        self.clicked.connect(self._on_click)
        self._filter: str = "Images (*.png *.jpg *.jpeg )"


    @Slot()
    def _on_click(self) -> None:
        """Open a file dialog and emit the selected path."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose an image",
            self._filter
        )
        if path:
            self.pathSelected.emit(path)
