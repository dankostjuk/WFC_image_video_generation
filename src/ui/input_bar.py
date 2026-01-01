"""Input list widgets for selecting images."""
# pylint: disable=no-name-in-module

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.converters import np_to_qimage
from src.services.data_model import InputItem


class PreviewInputFile(QPushButton):  # pylint: disable=too-few-public-methods
    """Clickable preview for an input image."""

    doubleClickForSelect = Signal(InputItem)
    doubleClickForUnselect = Signal(InputItem)

    def __init__(self, input_file: InputItem, parent: QWidget | None = None):
        """Create the preview widget."""
        super().__init__(parent)
        self.item = input_file
        self.selected = False
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the preview layout."""
        name_label = QLabel(self.item.name)
        name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        img_preview = QLabel()
        img_preview.setFixedSize(46, 46)
        img_preview.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        qimg = np_to_qimage(self.item.image)
        img_preview.setPixmap(QPixmap.fromImage(
            qimg.scaled(46, 46, Qt.KeepAspectRatio, Qt.FastTransformation)
        ))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)
        outer.addWidget(name_label, 1)
        outer.addStretch(1)
        outer.addWidget(img_preview, 0, Qt.AlignRight | Qt.AlignVCenter)

        self.setCheckable(False)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(70)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("""
        PreviewInputFile {
            border: 3px solid rgba(0,0,0,0.30);
            border-radius: 8px;
        }
        PreviewInputFile:hover {
            border-color: rgba(0,0,0,0.90);
        }
        """)

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        """Toggle selection on double-click."""
        if e.button() == Qt.LeftButton:
            self.selected = not self.selected
            if self.selected:
                self.setStyleSheet("""
                       PreviewInputFile {
                           border: 3px solid rgba(0,180,0,1);
                           border-radius: 8px;
                       }
                       """)
                self.doubleClickForSelect.emit(self.item)
            else:
                self.setStyleSheet("""
                       PreviewInputFile {
                           border: 3px solid rgba(0,0,0,0.30);
                           border-radius: 8px;
                       }
                       """)
                self.doubleClickForUnselect.emit(self.item)
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


class InputBar(QWidget):
    """Scrollable list of input previews."""

    widgetAdded = Signal(QWidget)
    widgetRemoved = Signal(QWidget)
    widgetsReplaced = Signal()

    def __init__(self, parent: QWidget | None = None, width: int = 260) -> None:
        """Create the input list container."""
        super().__init__(parent)
        self._build_ui()
        self.setFixedWidth(width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def _build_ui(self) -> None:
        """Build scrollable list layout."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Box)

        container = QWidget(scroll)
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(4, 8, 8, 8)
        self.layout.setSpacing(8)
        self.layout.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll, 1)


    def set_widgets(self, widgets: Iterable[QWidget]) -> None:
        """Replace all current children with the given widgets."""
        self._remove_all_items()
        for w in widgets:
            self.add_widget(w)
        self.widgetsReplaced.emit()

    def add_widget(self, widget: QWidget) -> None:
        """Append a widget to the bottom."""
        self.layout.insertWidget(self.layout.count() - 1, widget)
        self.widgetAdded.emit(widget)

    def insert_widget(self, index: int, widget: QWidget) -> None:
        """Insert a widget at a 0-based index (before the stretch)."""
        index = max(0, min(index, self.layout.count() - 1))
        self.layout.insertWidget(index, widget)
        self.widgetAdded.emit(widget)

    def remove_widget(self, widget: QWidget) -> None:
        """Remove (but do not deleteLater) the given widget if present."""
        if widget is None:
            return
        # Find and remove from layout
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if item and item.widget() is widget:
                self.layout.removeItem(item)
                widget.setParent(None)
                self.widgetRemoved.emit(widget)
                return

    def clear(self, delete: bool = False) -> None:
        """Remove all widgets. If delete=True, call deleteLater on them."""
        children = list(self._widgets())
        self._remove_all_items(delete=delete)
        for w in children:
            self.widgetRemoved.emit(w)
        self.widgetsReplaced.emit()

    def _widgets(self) -> Iterable[QWidget]:
        """Iterate current user widgets (excludes the bottom stretch)."""
        for i in range(self.layout.count() - 1):
            item = self.layout.itemAt(i)
            w = item.widget() if item else None
            if w is not None:
                yield w

    def unselect_all(self) -> None:
        """Clear selection highlighting for all preview widgets."""
        children = list(self._widgets())
        for w in children:
            w.selected = False
            w.setStyleSheet("""
                   PreviewInputFile {
                       border: 3px solid rgba(0,0,0,0.30);
                       border-radius: 8px;
                   }
                   """)

    def update_settings(self) -> list[tuple[str, str]]:
        """Return input settings for widgets that expose name/edit fields."""
        children = list(self._widgets())[1:-1]
        ret = []
        for w in children:
            ret.append((w.name, w.edit.text()))
        return ret

    def _remove_all_items(self, *, delete: bool = False) -> None:
        items: list[QWidget] = []
        for i in range(self.layout.count() - 1):
            it = self.layout.itemAt(i)
            w = it.widget() if it else None
            if w is not None:
                items.append(w)
        # Actually remove them
        for w in items:
            self.layout.removeWidget(w)
            w.setParent(None)
            if delete:
                w.deleteLater()
        # Ensure stretch exists at the end (re-add if somebody removed it)
        if self.layout.itemAt(self.layout.count() - 1) is None:
            self.layout.addStretch(1)
