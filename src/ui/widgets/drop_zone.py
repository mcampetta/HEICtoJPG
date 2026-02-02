from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen, QPixmap
from pathlib import Path


class DropZoneWidget(QWidget):
    """Widget for drag-and-drop folder selection."""

    folder_selected = pyqtSignal(Path)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("DropZoneWidget")
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Drop zone illustration
        illustration_path = Path(__file__).parent.parent.parent.parent / "resources" / "illustrations" / "drop_zone.png"
        if illustration_path.exists():
            pixmap = QPixmap(str(illustration_path))
            scaled_pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label = QLabel()
            self.icon_label.setPixmap(scaled_pixmap)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.icon_label)
        else:
            # Fallback to text if image not found
            self.icon_label = QLabel("DROP HEIC FOLDERS HERE\n— SYSTEM READY —")
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = self.icon_label.font()
            font.setPointSize(16)
            font.setBold(True)
            self.icon_label.setFont(font)
            layout.addWidget(self.icon_label)

        # Subtitle (only shown when folder selected)
        self.subtitle_label = QLabel("or click to browse")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.subtitle_label.font()
        font.setPointSize(10)
        self.subtitle_label.setFont(font)
        self.subtitle_label.setVisible(False)  # Hidden by default with new design
        layout.addWidget(self.subtitle_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.setProperty("dragging", False)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        self.setProperty("dragging", False)
        self.style().polish(self)

        urls = event.mimeData().urls()
        if urls:
            folder_path = Path(urls[0].toLocalFile())

            if folder_path.is_dir():
                self.folder_selected.emit(folder_path)
                self.show_selected_folder(folder_path)
            else:
                # If a file was dropped, use its parent directory
                if folder_path.is_file():
                    folder_path = folder_path.parent
                    self.folder_selected.emit(folder_path)
                    self.show_selected_folder(folder_path)

    def mousePressEvent(self, event):
        """Handle mouse press to open folder dialog."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_folder_dialog()

    def open_folder_dialog(self):
        """Open folder selection dialog."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing HEIC Files",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if folder_path:
            self.folder_selected.emit(Path(folder_path))
            self.show_selected_folder(Path(folder_path))

    def show_selected_folder(self, folder_path: Path):
        """Update display to show selected folder."""
        # Show subtitle with folder path
        self.subtitle_label.setText(f"Selected: {folder_path}")
        self.subtitle_label.setStyleSheet("color: #00E676; font-weight: bold;")
        self.subtitle_label.setVisible(True)

    def reset(self):
        """Reset to initial state."""
        self.subtitle_label.setVisible(False)
        self.subtitle_label.setText("or click to browse")
        self.subtitle_label.setStyleSheet("color: #7DE8A6;")

        # Restore original illustration
        illustration_path = Path(__file__).parent.parent.parent.parent / "resources" / "illustrations" / "drop_zone.png"
        if illustration_path.exists():
            pixmap = QPixmap(str(illustration_path))
            scaled_pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(scaled_pixmap)

