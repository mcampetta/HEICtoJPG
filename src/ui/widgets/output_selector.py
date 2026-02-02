from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OutputSelectorWidget(QWidget):
    """Widget for selecting optional custom output directory."""

    output_dir_changed = pyqtSignal(object)  # Path or None

    def __init__(self):
        super().__init__()
        self.output_dir = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Checkbox to enable custom output
        self.enable_checkbox = QCheckBox("Use custom output directory (preserves folder structure)")
        self.enable_checkbox.setChecked(False)
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        layout.addWidget(self.enable_checkbox)

        # Output directory selection row
        self.output_row = QWidget()
        output_layout = QHBoxLayout(self.output_row)
        output_layout.setContentsMargins(20, 0, 0, 0)

        output_label = QLabel("Output to:")
        output_layout.addWidget(output_label)

        self.output_path_label = QLabel("(Not selected)")
        self.output_path_label.setStyleSheet("color: #7DE8A6; font-style: italic;")
        output_layout.addWidget(self.output_path_label, stretch=1)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.select_output_directory)
        output_layout.addWidget(self.browse_button)

        layout.addWidget(self.output_row)

        # Initially hide output row
        self.output_row.setVisible(False)

        # Info label
        self.info_label = QLabel("💡 Subdirectories will be recreated in the output folder")
        self.info_label.setStyleSheet("color: #00B8D4; font-size: 9pt;")
        self.info_label.setIndent(20)
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)

    def on_enable_changed(self, state):
        """Handle enable/disable of custom output directory."""
        enabled = self.enable_checkbox.isChecked()

        self.output_row.setVisible(enabled)
        self.info_label.setVisible(enabled)

        if not enabled:
            # Clear output directory
            self.output_dir = None
            self.output_path_label.setText("(Not selected)")
            self.output_dir_changed.emit(None)
        else:
            # If already selected, emit it
            if self.output_dir:
                self.output_dir_changed.emit(self.output_dir)

    def select_output_directory(self):
        """Open dialog to select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if directory:
            self.output_dir = Path(directory)
            self.output_path_label.setText(str(self.output_dir))
            self.output_path_label.setStyleSheet("color: #00E676; font-weight: bold;")
            logger.info(f"Output directory selected: {self.output_dir}")
            self.output_dir_changed.emit(self.output_dir)

    def get_output_dir(self) -> Path:
        """Get the selected output directory, or None for same-as-source."""
        if self.enable_checkbox.isChecked():
            logger.info(f"Custom output directory enabled: {self.output_dir}")
            return self.output_dir
        else:
            logger.info("Custom output directory disabled - using source directory")
            return None

    def reset(self):
        """Reset to default state."""
        self.enable_checkbox.setChecked(False)
        self.output_dir = None
        self.output_path_label.setText("(Not selected)")
        self.output_path_label.setStyleSheet("color: #7DE8A6; font-style: italic;")

    def is_enabled(self) -> bool:
        """Check if custom output directory is enabled."""
        return self.enable_checkbox.isChecked()
