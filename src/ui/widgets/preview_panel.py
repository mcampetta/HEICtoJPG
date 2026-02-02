from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGroupBox, QPushButton, QStackedWidget, QToolButton, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QIcon
from pathlib import Path
from PIL import Image
from pillow_heif import register_heif_opener
import logging

from src.ui.widgets.drop_zone import DropZoneWidget

# Register HEIF opener
register_heif_opener()

logger = logging.getLogger(__name__)


class ThumbnailWidget(QWidget):
    """Widget for displaying a single image thumbnail."""

    def __init__(self, file_path: Path, size: int = 80, show_converted_badge: bool = False, auto_load: bool = True):
        super().__init__()
        self.file_path = file_path
        self.thumbnail_size = size
        self.show_converted_badge = show_converted_badge
        self.init_ui()
        if auto_load:
            self.load_thumbnail()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.thumbnail_size, self.thumbnail_size)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Different border for converted files
        if self.show_converted_badge:
            self.image_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #00E676;
                    background-color: #0C1218;
                }
            """)
        else:
            self.image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #1B2A33;
                    background-color: #0C1218;
                }
            """)
        layout.addWidget(self.image_label)

        # Filename
        name_label = QLabel(self.file_path.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 8pt; color: #7DE8A6;")
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(self.thumbnail_size)
        layout.addWidget(name_label)

        # Status badge for converted files
        if self.show_converted_badge:
            badge_label = QLabel("✓ CONVERTED")
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_label.setStyleSheet("""
                font-size: 7pt;
                color: #00E676;
                font-weight: bold;
                background-color: rgba(0, 230, 118, 0.2);
                border-radius: 3px;
                padding: 2px;
            """)
            badge_label.setMaximumWidth(self.thumbnail_size)
            layout.addWidget(badge_label)

    def load_thumbnail(self):
        """Load and display thumbnail."""
        try:
            # Open image and create thumbnail
            with Image.open(self.file_path) as img:
                # Convert to RGB if needed
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail((self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS)

                # Convert to QPixmap
                img_data = img.tobytes('raw', 'RGB')
                qimage = QImage(
                    img_data,
                    img.width,
                    img.height,
                    img.width * 3,
                    QImage.Format.Format_RGB888
                )
                pixmap = QPixmap.fromImage(qimage)

                self.image_label.setPixmap(pixmap)

        except Exception as e:
            logger.warning(f"Could not load thumbnail for {self.file_path}: {e}")
            self.image_label.setText("?")
            self.image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #1B2A33;
                    background-color: #0C1218;
                    color: #FF5252;
                    font-size: 24pt;
                }
            """)

    def set_pixmap(self, pixmap: QPixmap):
        """Set thumbnail pixmap from a background loader."""
        if pixmap and not pixmap.isNull():
            self.image_label.setPixmap(pixmap)


class ThumbnailLoader(QThread):
    """Background loader for thumbnails to keep UI responsive."""

    thumbnail_ready = pyqtSignal(object, object)  # file_path, QPixmap

    def __init__(self, files: list[Path], size: int):
        super().__init__()
        self.files = files
        self.size = size
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        for file_path in self.files:
            if self._stopped:
                break
            try:
                with Image.open(file_path) as img:
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    img.thumbnail((self.size, self.size), Image.Resampling.LANCZOS)
                    img_data = img.tobytes('raw', 'RGB')
                    qimage = QImage(
                        img_data,
                        img.width,
                        img.height,
                        img.width * 3,
                        QImage.Format.Format_RGB888
                    )
                    pixmap = QPixmap.fromImage(qimage)
                    self.thumbnail_ready.emit(file_path, pixmap)
            except Exception as e:
                logger.warning(f"Could not load thumbnail for {file_path}: {e}")


class LiveImageLoader(QThread):
    """Background loader for the latest converted image."""

    image_ready = pyqtSignal(object, object)  # file_path, QPixmap

    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            with Image.open(self.file_path) as img:
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                img_data = img.tobytes('raw', 'RGB')
                qimage = QImage(
                    img_data,
                    img.width,
                    img.height,
                    img.width * 3,
                    QImage.Format.Format_RGB888
                )
                pixmap = QPixmap.fromImage(qimage)
                self.image_ready.emit(self.file_path, pixmap)
        except Exception as e:
            logger.warning(f"Could not load live preview for {self.file_path}: {e}")


class LiveImageLabel(QLabel):
    """Label that doesn't request size based on pixmap dimensions."""

    def sizeHint(self):
        return QSize(0, 0)

    def minimumSizeHint(self):
        return QSize(0, 0)


class PreviewPanel(QWidget):
    """Panel for previewing images that will be converted."""
    folder_to_scan = pyqtSignal(Path)
    clear_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.files = []
        self.thumbnail_widgets = []
        self.max_thumbnails = 20  # Limit to prevent UI lag
        self.live_mode = False
        self.thumbnail_loader = None
        self.live_loader = None
        self.pending_live_path = None
        self._stale_loaders = []
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # View 0: Drop Zone
        self.drop_zone = DropZoneWidget()
        self.drop_zone.folder_selected.connect(self._on_folder_selected)
        self.stacked_widget.addWidget(self.drop_zone)

        # View 1: Preview Panel
        preview_container = QWidget()
        layout = QVBoxLayout(preview_container)

        # Create group box
        group_box = QGroupBox()
        group_layout = QVBoxLayout()

        # Custom title bar
        title_layout = QHBoxLayout()
        title_label = QLabel("Preview")
        title_label.setStyleSheet("font-weight: bold; color: #00E676;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.add_folder_button = QToolButton()
        self.add_folder_button.setText("Add Folder")
        self.add_folder_button.setIcon(QIcon(str(Path(__file__).parent.parent.parent.parent / "resources" / "icons" / "folder_add.svg")))
        self.add_folder_button.setObjectName("icon_tool")
        self.add_folder_button.clicked.connect(self._browse_for_folder)
        title_layout.addWidget(self.add_folder_button)

        self.clear_button = QToolButton()
        self.clear_button.setText("X")
        self.clear_button.setFixedSize(20, 20)
        self.clear_button.setObjectName("clear_button")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        self.clear_button.setVisible(False)
        title_layout.addWidget(self.clear_button)
        group_layout.addLayout(title_layout)

        # Info label
        self.info_label = QLabel("Preview of images to convert")
        self.info_label.setStyleSheet("color: #7DE8A6; font-size: 9pt;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.info_label)

        # Preview stack (thumbnails or live image)
        self.preview_stack = QStackedWidget()

        # Thumbnails view
        thumbnails_view = QWidget()
        thumbnails_layout = QVBoxLayout(thumbnails_view)
        thumbnails_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(150)

        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QHBoxLayout(self.thumbnail_container)
        self.thumbnail_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.thumbnail_layout.setSpacing(5)

        scroll_area.setWidget(self.thumbnail_container)
        thumbnails_layout.addWidget(scroll_area)

        # Live image view
        live_view = QWidget()
        live_layout = QVBoxLayout(live_view)
        live_layout.setContentsMargins(0, 0, 0, 0)

        self.live_image_label = LiveImageLabel("Live preview")
        self.live_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_image_label.setStyleSheet("color: #7DE8A6; font-size: 10pt;")
        self.live_image_label.setMinimumHeight(150)
        self.live_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        live_layout.addWidget(self.live_image_label)

        self.preview_stack.addWidget(thumbnails_view)
        self.preview_stack.addWidget(live_view)
        group_layout.addWidget(self.preview_stack)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        self.stacked_widget.addWidget(preview_container)

    def _on_folder_selected(self, folder_path: Path):
        self.folder_to_scan.emit(folder_path)
        self.stacked_widget.setCurrentIndex(1)
        self.clear_button.setVisible(True)

    def select_folder(self, folder_path: Path):
        """Public method to select a folder programmatically."""
        self._on_folder_selected(folder_path)

    def _browse_for_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing HEIC Files",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if folder_path:
            self._on_folder_selected(Path(folder_path))

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Allow dropping folders anywhere on the preview panel."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle folder drop to add another batch."""
        urls = event.mimeData().urls()
        if not urls:
            return

        folder_path = Path(urls[0].toLocalFile())
        if folder_path.is_file():
            folder_path = folder_path.parent

        if folder_path.is_dir():
            self._on_folder_selected(folder_path)

    def set_files(self, files: list[Path]):
        """Set files to preview."""
        self.files = files
        self.stacked_widget.setCurrentIndex(1)
        self.clear_button.setVisible(True)
        self.preview_stack.setCurrentIndex(0)


        # Clear existing thumbnails
        self.clear_thumbnails()

        if not files:
            self.info_label.setText("No files to preview")
            self.clear_button.setVisible(False)
            return

        # Update info label
        if len(files) > self.max_thumbnails:
            self.info_label.setText(
                f"Showing {self.max_thumbnails} of {len(files):,} images"
            )
        else:
            self.info_label.setText(f"Previewing {len(files):,} images")

        # Create thumbnail shells (loaded asynchronously)
        preview_files = files[:self.max_thumbnails]
        for file_path in preview_files:
            thumbnail = ThumbnailWidget(file_path, auto_load=False)
            self.thumbnail_layout.addWidget(thumbnail)
            self.thumbnail_widgets.append(thumbnail)

        # Add stretch to push thumbnails to left
        self.thumbnail_layout.addStretch()

        # Start background thumbnail loader
        self._start_thumbnail_loader(preview_files)

    def clear_thumbnails(self):
        """Clear all thumbnails."""
        self._stop_thumbnail_loader()
        for widget in self.thumbnail_widgets:
            widget.deleteLater()

        self.thumbnail_widgets.clear()

    def set_max_thumbnails(self, count: int):
        """Set maximum number of thumbnails to display."""
        self.max_thumbnails = count

    def enable_live_mode(self):
        """Enable live preview mode to show files as they're converted."""
        self.live_mode = True
        self.info_label.setText("LIVE: Latest converted image")
        self.info_label.setStyleSheet("color: #00E676; font-size: 9pt; font-weight: bold;")
        self.stacked_widget.setCurrentIndex(1)
        self.clear_button.setVisible(True)
        self.preview_stack.setCurrentIndex(1)
        self._stop_thumbnail_loader()
        self.clear_thumbnails()
        self.live_image_label.setText("Waiting for first conversion...")
        self.live_image_label.setPixmap(QPixmap())

    def disable_live_mode(self):
        """Disable live preview mode."""
        self.live_mode = False
        if self.live_loader and self.live_loader.isRunning():
            self._stale_loaders.append(self.live_loader)
        self.live_loader = None
        self.pending_live_path = None
        self.info_label.setText("Preview of images to convert")
        self.info_label.setStyleSheet("color: #7DE8A6; font-size: 9pt;")
        self.preview_stack.setCurrentIndex(0)

    def add_conversion(self, file_path: Path):
        """Add a converted file to the live preview."""
        if self.live_mode:
            self.pending_live_path = file_path
            if not self.live_loader or not self.live_loader.isRunning():
                self._start_live_loader()

    def update_live_preview(self):
        """Deprecated: live preview now shows only the latest image."""
        return

    def _start_live_loader(self):
        if not self.pending_live_path:
            return
        file_path = self.pending_live_path
        self.pending_live_path = None
        if self.live_loader and self.live_loader.isRunning():
            self._stale_loaders.append(self.live_loader)
        self.live_loader = LiveImageLoader(file_path)
        self.live_loader.finished.connect(lambda loader=self.live_loader: self._cleanup_loader(loader))
        self.live_loader.image_ready.connect(self._set_live_image)
        self.live_loader.start()

    def _set_live_image(self, file_path: Path, pixmap: QPixmap):
        if pixmap.isNull():
            self.live_image_label.setText("Live preview unavailable")
            return
        scaled = pixmap.scaled(
            self.live_image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self.live_image_label.setPixmap(scaled)
        self.live_image_label.setText("")
        if self.pending_live_path:
            self._start_live_loader()

    def reset(self):
        """Reset the panel to its initial state (drop zone)."""
        self.disable_live_mode()
        self.clear_thumbnails()
        self.drop_zone.reset()
        self.stacked_widget.setCurrentIndex(0)
        self.clear_button.setVisible(False)

    def shutdown(self):
        """Stop background loaders before app exit."""
        self.disable_live_mode()
        self._stop_thumbnail_loader()
        if self.live_loader and self.live_loader.isRunning():
            self._stale_loaders.append(self.live_loader)
        self.live_loader = None
        self.pending_live_path = None

    def _start_thumbnail_loader(self, files: list[Path]):
        self._stop_thumbnail_loader()
        if not files:
            return
        self.thumbnail_loader = ThumbnailLoader(files, self.thumbnail_widgets[0].thumbnail_size if self.thumbnail_widgets else 80)
        self.thumbnail_loader.finished.connect(lambda loader=self.thumbnail_loader: self._cleanup_loader(loader))
        self.thumbnail_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.thumbnail_loader.start()

    def _stop_thumbnail_loader(self):
        if self.thumbnail_loader and self.thumbnail_loader.isRunning():
            self.thumbnail_loader.stop()
            self._stale_loaders.append(self.thumbnail_loader)
        self.thumbnail_loader = None

    def _on_thumbnail_ready(self, file_path: Path, pixmap: QPixmap):
        for widget in self.thumbnail_widgets:
            if widget.file_path == file_path:
                widget.set_pixmap(pixmap)
                break

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.live_mode and self.live_image_label.pixmap():
            current = self.live_image_label.pixmap()
            if current and not current.isNull():
                scaled = current.scaled(
                    self.live_image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.live_image_label.setPixmap(scaled)

    def _cleanup_loader(self, loader):
        if loader in self._stale_loaders:
            self._stale_loaders.remove(loader)
        if loader is self.live_loader:
            self.live_loader = None
