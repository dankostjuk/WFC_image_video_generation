"""Application state shared across UI widgets."""
# pylint: disable=no-name-in-module

from typing import Dict

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QMainWindow

from wfcqt.services.data_model import InputDataModel, InputItem

class AppState(QObject):
    """Shared UI state: input image, output image, and current config."""

    inputsChanged = Signal()
    currentChanged = Signal()

    def __init__(self) -> None:
        """Initialize empty data stores for inputs and selections."""
        super().__init__()
        self.data = InputDataModel()
        self.image_data = InputDataModel()
        self.selected_data: Dict[str, InputItem] = {}

    def add_input(self, main_window: QMainWindow, paths: list[tuple[str, str]]) -> list[InputItem]:
        """Add image inputs and return created items."""
        input_items = []
        for path, name in paths:
            try:
                self.data.add_from_path(path, name)
                self.inputsChanged.emit()
                item = self.data.get(name)
                if item:
                    input_items.append(item)
            except FileNotFoundError:
                QMessageBox.warning(main_window, "File not found", f"Could not find:\n{path}")
            except ValueError as e:
                QMessageBox.warning(main_window, "Invalid image", f"{name}\n\n{e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                QMessageBox.critical(main_window, "Unexpected error", f"{type(e).__name__}: {e}")

        return input_items

    def add_image_input(self, main_window: QMainWindow, paths: list[tuple[str, str]]) -> list[InputItem]:
        """Add image inputs for video mode and return created items."""
        input_items = []
        for path, name in paths:
            try:
                self.image_data.add_from_path(path, name)
                self.inputsChanged.emit()
                item = self.image_data.get(name)
                if item:
                    input_items.append(item)
            except FileNotFoundError:
                QMessageBox.warning(main_window, "File not found", f"Could not find:\n{path}")
            except ValueError as e:
                QMessageBox.warning(main_window, "Invalid image", f"{name}\n\n{e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                QMessageBox.critical(main_window, "Unexpected error", f"{type(e).__name__}: {e}")

        return input_items

    def add_selected_item(self, item: InputItem) -> bool:
        """Add a selected item if missing; return True if added."""
        add_item = False
        if item.name not in self.selected_data:
            self.selected_data[item.name] = item
            add_item = True
        return add_item

    def remove_selected_item(self, item: InputItem) -> bool:
        """Remove a selected item if present; return True if removed."""
        remove_item = False
        if item.name in self.selected_data:
            remove_item = True
            self.selected_data.pop(item.name, None)
        return remove_item
