"""Video playback and generation progress widget."""
# pylint: disable=no-name-in-module

from PySide6.QtCore import QUrl, Qt, QRectF, Signal
from PySide6.QtGui import QPainterPath, QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QProgressBar,
)
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink


class MaskedVideoItem(QGraphicsPixmapItem):
    """Pixmap item with optional circular masking."""
    def __init__(self):
        super().__init__()
        self.circular_mask = False
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

    def setCircularMask(self, enabled: bool):
        """Enable or disable circular mask."""
        self.circular_mask = bool(enabled)
        self.update()

    def paint(self, painter, option, widget=None):
        """Paint the item, optionally clipped to a circle."""
        if self.circular_mask:
            br = self.boundingRect()
            d = min(br.width(), br.height())
            rect = QRectF(
                br.center().x() - d / 2,
                br.center().y() - d / 2,
                d, d
            )
            path = QPainterPath()
            path.addEllipse(rect)
            painter.save()
            painter.setClipPath(path)
            super().paint(painter, option, widget)
            painter.restore()
        else:
            super().paint(painter, option, widget)


class VideoOutputWidget(QWidget):  # pylint: disable=too-many-instance-attributes
    """Widget combining video playback and generation controls."""

    startGeneration = Signal()
    def __init__(self, parent: QWidget | None = None, circular_mask: bool = True):
        """Initialize UI widgets and player."""
        super().__init__(parent)
        self.setWindowTitle("PySide6 Video Player (QGraphicsView)")

        self.play_button = QPushButton("Play / Pause", self)
        self.generate_button = QPushButton("Generate", self)
        self.mask_button = QPushButton("Circular Mask", self)


        self.view = QGraphicsView(self)
        self.view.setRenderHints(self.view.renderHints() | QPainter.RenderHint.Antialiasing)
        self.scene = QGraphicsScene(self.view)
        self.view.setScene(self.scene)

        self.video_item = MaskedVideoItem()
        self.video_item.setCircularMask(circular_mask)
        self.scene.addItem(self.video_item)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.mask_button)
        layout.addWidget(self.progress)

        self.player = QMediaPlayer(self)

        self.play_button.clicked.connect(self._toggle)
        self.mask_button.clicked.connect(self._toggle_mask)
        self.generate_button.clicked.connect(self._start_generation)

        self.set_video("../../samples/videos/reversed.mp4")


    def set_video(self,video_path):
        """Load and play the selected video file."""
        self.sink = QVideoSink(self)
        self.sink.videoFrameChanged.connect(self._on_frame)
        self.player.setVideoSink(self.sink)
        self.player.setSource(QUrl.fromLocalFile("../../samples/videos/reversed.mp4"))
        self.player.setSource(QUrl.fromLocalFile(video_path))
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.player.play()
        self.progress.setVisible(False)
        self.generate_button.setEnabled(True)
        self.play_button.setEnabled(True)

    def _on_frame(self, frame):
        """Update the graphics view from a video frame."""
        if not frame.isValid():
            return

        img = frame.toImage()
        if img.isNull():
            return

        pix = QPixmap.fromImage(img)
        self.video_item.setPixmap(pix)

        br = self.video_item.boundingRect()
        self.scene.setSceneRect(br)
        self.view.fitInView(br, Qt.AspectRatioMode.KeepAspectRatio)

    def _toggle_mask(self):
        """Toggle the circular mask."""
        self.video_item.setCircularMask(not self.video_item.circular_mask)

    def _start_generation(self):
        """Pause playback and emit a generation request."""
        self.player.pause()

        self.generate_button.setEnabled(False)
        self.play_button.setEnabled(False)

        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.startGeneration.emit()

    def on_progress(self, p: float):
        """Update the progress bar from 0..1."""
        p = max(0.0, min(1.0, float(p)))
        self.progress.setValue(int(p * 100))

    def _toggle(self):
        """Play or pause based on current state."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
