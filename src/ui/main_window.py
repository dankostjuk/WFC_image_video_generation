"""Main application window and UI wiring."""
# pylint: disable=no-name-in-module

from collections import deque
import os
import shutil

import numpy as np
from PIL import Image

from PySide6.QtCore import Slot, QThreadPool, QTimer, Qt, QUrl
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.converters import np_to_qimage
from src.core.worker import WFCWorker
from src.services.app_state import AppState
from src.services.data_model import InputItem
from src.ui.browse_button import ImageBrowseButton
from src.ui.input_bar import InputBar, PreviewInputFile
from src.ui.output_widget import OutputWidget
from src.ui.settings_widget import VideoConfig, WFCConfig
from src.ui.video_output_widget import VideoOutputWidget
from src.wfc.analyzer import Analyzer
from src.wfc.solver import Solver
from src.wfc.video_generation import VideoGenerator


class MainWindow(QMainWindow):  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """Top-level app window containing all widgets and actions."""
    def __init__(self) -> None:
        """Initialize UI state, workers, and layout."""
        super().__init__()
        self.worker_solver = None
        self.app_state = AppState()
        self.option_bar = InputBar(self, width=240)
        self.input_bar_image = InputBar(self, width=240)
        self.input_bar_video = InputBar(self, width=240)

        self.wfc_cfg = WFCConfig()
        self.video_cfg = VideoConfig()

        self._load_testing_data()
        self.threadpool = QThreadPool()
        self.solver = Solver()
        self.video_generator = VideoGenerator()
        self.video_generator.progressUpdate.connect(self._video_generation_finish)
        self.solver.on_progress.connect(self._add_output_frame)

        self.threadpool = QThreadPool.globalInstance()
        self._frame_queue = deque()
        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(20)
        self._frame_timer.timeout.connect(self._update_output)

        self.output_to_draw = deque()
        self.output_bar = OutputWidget(QImage(), self)
        self.output_bar.startGeneration.connect(self._on_generation_start)
        self.output_bar.cancelGeneration.connect(self._on_cancel)

        self.video_output_bar = VideoOutputWidget(self)
        self.video_output_bar.startGeneration.connect(self._on_video_generation_start)

        self._build_ui()
        self._build_menubar()

        self.output_image = None

    def _build_ui(self) -> None:
        """Construct the main window layout."""
        self.setWindowTitle("WFC Qt")
        self.resize(1200, 850)

        self.option_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.wfc_cfg.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.output_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        add_input_button = ImageBrowseButton()
        add_input_button.pathSelected.connect(self._add_input)
        self.save_botton = QPushButton("Save output")
        self.save_botton.pressed.connect(self._on_save_output)

        hint = QLabel("Double click to select image")
        self.option_bar.set_widgets([self.save_botton, add_input_button, hint])

        self.input_stack = QStackedWidget(self)
        self.input_stack.addWidget(self.input_bar_image)
        self.input_stack.addWidget(self.input_bar_video)
        self.input_stack.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        left_col = QWidget(self)
        left_col.setFixedWidth(240)
        vleft = QVBoxLayout(left_col)
        vleft.setContentsMargins(0, 0, 0, 0)
        vleft.setSpacing(6)
        vleft.addWidget(self.option_bar, 0)
        vleft.addWidget(self.input_stack, 2)

        main_widget = QWidget(self)
        h = QHBoxLayout(main_widget)
        h.setContentsMargins(6, 6, 6, 6)
        h.setSpacing(6)
        h.addWidget(left_col, 0)

        self.settings_stack = QStackedWidget(self)
        self.settings_stack.addWidget(self.wfc_cfg)
        self.settings_stack.addWidget(self.video_cfg)

        h.addWidget(self.settings_stack, 0)

        self.top_dock = QDockWidget(self)
        self.top_dock.setAllowedAreas(Qt.TopDockWidgetArea)
        self.top_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.TopDockWidgetArea, self.top_dock)
        self.tabs = QTabWidget()
        self.top_dock.setWidget(self.tabs)

        self.tabs.addTab(self.output_bar, "Image output")
        self.tabs.addTab(self.video_output_bar, "Video output")

        h.addWidget(self.top_dock, 1)

        self.setCentralWidget(main_widget)

        self.tabs.currentChanged.connect(self._on_output_tab_changed)
        self._on_output_tab_changed(self.tabs.currentIndex())

    def _on_output_tab_changed(self, idx: int):
        """Switch settings/input stacks to match the active tab."""
        self.settings_stack.setCurrentIndex(idx)
        self.input_stack.setCurrentIndex(idx)
        self.input_stack.currentWidget().unselect_all()
        self.app_state.selected_data.clear()

    def _build_menubar(self) -> None:
        """Create the application menu bar."""
        bar = self.menuBar() if self.menuBar() else QMenuBar(self)  # pylint: disable=disallowed-name
        self.setMenuBar(bar)

        file_menu = QMenu("&File", self)
        self.act_save = file_menu.addAction("&Save Output…")
        self.act_save.triggered.connect(self._on_save_output)
        bar.addMenu(file_menu)

    def _load_testing_data(self):
        """Load sample images into the UI for quick testing."""
        input_meta_data = []
        directory = "samples/"
        for entry in os.scandir(directory):
            if entry.is_file():
                input_meta_data.append((entry, os.path.basename(entry)))
        input_items = self.app_state.add_input(self, input_meta_data)

        input_bar_widgets = []
        for item in input_items:
            item_widget = PreviewInputFile(item, self)
            item_widget.doubleClickForSelect.connect(self._select_item)
            item_widget.doubleClickForUnselect.connect(self._remove_item)
            input_bar_widgets.append(item_widget)

        self.input_bar_image.set_widgets(input_bar_widgets)


    @Slot()
    def _add_input(self, path: str) -> None:
        """Add a user-selected input to the active bar."""
        if self.tabs.currentIndex() == 0:
            item = self.app_state.add_input(self, [(path, os.path.basename(path))])[0]
            item_widget = PreviewInputFile(item)
            item_widget.doubleClickForSelect.connect(self._select_item)
            item_widget.doubleClickForUnselect.connect(self._remove_item)
            self.input_bar_image.add_widget(item_widget)
        else:
            item = self.app_state.add_image_input(self, [(path, os.path.basename(path))])[0]
            item_widget = PreviewInputFile(item)
            item_widget.doubleClickForSelect.connect(self._select_item)
            item_widget.doubleClickForUnselect.connect(self._remove_item)
            self.input_bar_video.add_widget(item_widget)

    @Slot()
    def _select_item(self, item: InputItem) -> None:
        """Mark an input as selected."""
        self.app_state.add_selected_item(item)

    def _remove_item(self, item: InputItem) -> None:
        """Remove a selected input."""
        self.app_state.remove_selected_item(item)


    @Slot()
    def _on_generation_start(self) -> None:
        """Start image generation in the background worker."""
        try:
            self.solver.reset_cancel()
            analyzer = Analyzer()
            samples = [i.image for i in self.app_state.selected_data.values()]
            tiles = analyzer.from_samples(samples, self.wfc_cfg)
            self.worker_solver = WFCWorker(self.solver.run, tiles, self.wfc_cfg)
            self.threadpool.start(self.worker_solver)
            self._frame_queue.clear()
            QTimer.singleShot(500, self._frame_timer.start)
        except Exception:  # pylint: disable=broad-exception-caught
            QMessageBox.critical(self, "Error", "Please select input (double click on image)")


    @Slot()
    def _on_video_generation_start(self) -> None:
        """Start video generation in the background worker."""
        def clear_dir(path: str):
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)
        clear_dir("frames")
        input_images = [i.path for i in self.app_state.selected_data.values()]

        if len(input_images) < 1:
            QMessageBox.critical(self, "Error", "Input is empty (select input)")
            self.video_output_bar.set_video("reversed.mp4")
            return

        if self.video_cfg.rotate_input:
            input_images *= self.video_cfg.rotation_speed

        self.worker_solver = WFCWorker(self.video_generator.run, input_images, self.video_cfg)
        self.threadpool.start(self.worker_solver)



    @Slot()
    def _video_generation_finish(self, progress) -> None:
        """Handle progress updates for video generation."""
        self.video_output_bar.on_progress(progress)
        if progress >= 1:
            if self.video_cfg.reverse_output:
                self.video_output_bar.set_video("output_video_reverse.mp4")
            else:
                self.video_output_bar.set_video("output_video.mp4")


    @Slot()
    def _add_output_frame(self, out_np: object) -> None:
        """Collect frames emitted from the solver."""
        if isinstance(out_np, np.ndarray):
            self._frame_queue.append(out_np)
            self.output_image =  out_np

    @Slot()
    def _update_output(self) -> None:
        """Update output display with queued frames."""
        if not self._frame_queue:
            return
        out_np = self._frame_queue.popleft()
        self.output_bar.set_image(np_to_qimage(out_np), self.wfc_cfg.show_grid)

    @Slot()
    def _on_cancel(self) -> None:
        """Cancel an in-progress generation."""
        self.solver.request_cancel()
        self._frame_timer.stop()

    @Slot()
    def _on_save_output(self) -> None:
        """Save the most recent output to disk."""
        image_output_index = 0
        video_output_index = 1
        if self.tabs.currentIndex() == image_output_index:
            self._save_image()
        elif self.tabs.currentIndex() == video_output_index:
            self._save_video()



    def _save_image(self) -> None:
        """Save the most recent output image to disk."""
        try:
            img = Image.fromarray(self.output_image)

            name = next(iter(self.app_state.selected_data.values())).name
            base = os.path.splitext(name)[0]

            out_dir = "."
            stem = f"{base}_generated"
            out_path = os.path.join(out_dir, f"{stem}.png")

            if os.path.exists(out_path):
                n = 2
                while True:
                    candidate = os.path.join(out_dir, f"{stem}_{n:}.png")
                    if not os.path.exists(candidate):
                        out_path = candidate
                        break
                    n += 1

            img.save(out_path)

        except Exception:  # pylint: disable=broad-exception-caught
            QMessageBox.critical(self, "Error", "Output is empty")

    def _save_video(self):
        """Save the most recent output video to disk."""
        out_dir = "."
        stem = "output_video"
        out_path = os.path.join(out_dir, f"{stem}.mp4")

        url: QUrl = self.video_output_bar.player.source()
        src = url.toLocalFile()

        if not os.path.exists(out_path):
            n = 2
            while True:
                candidate = os.path.join(out_dir, f"{stem}_{n}.mp4")
                if not os.path.exists(candidate):
                    out_path = candidate
                    break
                n += 1

        shutil.copy2(src, out_path)
