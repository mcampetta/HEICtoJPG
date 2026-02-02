from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QCheckBox, QGroupBox, QSpinBox, QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.models.app_settings import AppSettings


class SettingsPanel(QWidget):
    """Panel for conversion settings."""

    settings_changed = pyqtSignal(AppSettings)
    operator_mode_changed = pyqtSignal(bool)
    custom_output_dir_toggled = pyqtSignal(bool)
    output_dir_changed = pyqtSignal(object)  # Path or None
    context_menu_toggled = pyqtSignal(bool)

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.custom_output_dir = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Create group box
        group_box = QGroupBox("Settings")
        group_layout = QVBoxLayout()

        # JPG Quality Slider
        quality_layout = QVBoxLayout()
        quality_label = QLabel("JPG Quality:")
        quality_layout.addWidget(quality_label)

        quality_slider_layout = QHBoxLayout()

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setMinimum(0)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(self.settings.jpg_quality)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.quality_slider.setTickInterval(10)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        quality_slider_layout.addWidget(self.quality_slider)

        self.quality_value_label = QLabel(f"{self.settings.jpg_quality}%")
        self.quality_value_label.setMinimumWidth(40)
        self.quality_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        quality_slider_layout.addWidget(self.quality_value_label)

        quality_layout.addLayout(quality_slider_layout)

        # Quality indicator
        self.quality_indicator = QLabel(self.get_quality_description(self.settings.jpg_quality))
        self.quality_indicator.setStyleSheet("color: gray; font-size: 9pt;")
        quality_layout.addWidget(self.quality_indicator)

        group_layout.addLayout(quality_layout)

        # Spacer
        group_layout.addSpacing(15)

        # Delete source checkbox
        self.delete_source_checkbox = QCheckBox("Delete source files after successful conversion")
        self.delete_source_checkbox.setChecked(self.settings.delete_source_on_success)
        self.delete_source_checkbox.stateChanged.connect(self.on_settings_changed)
        self.delete_source_checkbox.setStyleSheet("font-weight: bold;")
        group_layout.addWidget(self.delete_source_checkbox)

        # Warning label for delete
        warning_label = QLabel("\u26a0 Files will be moved to Recycle Bin")
        warning_label.setStyleSheet("color: #ff9800; font-size: 9pt;")
        warning_label.setIndent(20)
        group_layout.addWidget(warning_label)

        # Spacer
        group_layout.addSpacing(15)

        # Thread count
        thread_layout = QHBoxLayout()
        thread_label = QLabel("Worker Threads:")
        thread_layout.addWidget(thread_label)

        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setMinimum(1)
        self.thread_spinbox.setMaximum(64)
        self.thread_spinbox.setValue(self.settings.max_workers)
        self.thread_spinbox.valueChanged.connect(self.on_settings_changed)
        thread_layout.addWidget(self.thread_spinbox)

        thread_layout.addStretch()
        group_layout.addLayout(thread_layout)

        # Thread info
        thread_info = QLabel("Higher values = faster for large datasets")
        thread_info.setStyleSheet("color: gray; font-size: 9pt;")
        group_layout.addWidget(thread_info)

        # Spacer
        group_layout.addSpacing(15)

        # Preserve EXIF checkbox
        self.preserve_exif_checkbox = QCheckBox("Preserve EXIF metadata")
        self.preserve_exif_checkbox.setChecked(self.settings.preserve_exif)
        self.preserve_exif_checkbox.stateChanged.connect(self.on_settings_changed)
        group_layout.addWidget(self.preserve_exif_checkbox)

        # EXIF info
        exif_info = QLabel("Keeps date, location, camera info, etc.")
        exif_info.setStyleSheet("color: gray; font-size: 9pt;")
        exif_info.setIndent(20)
        group_layout.addWidget(exif_info)

        # Spacer
        group_layout.addSpacing(15)

        # Operator Mode checkbox
        self.operator_mode_checkbox = QCheckBox("\U0001F5A5 Operator Mode")
        self.operator_mode_checkbox.setChecked(self.settings.operator_mode)
        self.operator_mode_checkbox.stateChanged.connect(self.on_operator_mode_changed)
        self.operator_mode_checkbox.setStyleSheet("font-weight: bold; color: #00E676;")
        group_layout.addWidget(self.operator_mode_checkbox)

        # Operator Mode info
        operator_info = QLabel("Matrix rain + extra glow effects")
        operator_info.setStyleSheet("color: gray; font-size: 9pt;")
        operator_info.setIndent(20)
        group_layout.addWidget(operator_info)

        # Spacer
        group_layout.addSpacing(15)

        # Explorer context menu checkbox
        self.context_menu_checkbox = QCheckBox("Enable Explorer right-click for folders")
        self.context_menu_checkbox.setChecked(self.settings.enable_context_menu)
        self.context_menu_checkbox.stateChanged.connect(self.on_context_menu_changed)
        group_layout.addWidget(self.context_menu_checkbox)

        # Use Custom Output Directory checkbox
        self.use_custom_output_dir_checkbox = QCheckBox("Use custom output directory")
        self.use_custom_output_dir_checkbox.setChecked(self.settings.use_custom_output_dir)
        self.use_custom_output_dir_checkbox.stateChanged.connect(self._on_use_custom_output_dir_changed)
        self.use_custom_output_dir_checkbox.setStyleSheet("font-weight: bold;")
        group_layout.addWidget(self.use_custom_output_dir_checkbox)

        # Preserve folder structure checkbox (only relevant when custom output is enabled)
        self.preserve_structure_checkbox = QCheckBox("Preserve folder structure in output")
        self.preserve_structure_checkbox.setChecked(self.settings.preserve_folder_structure)
        self.preserve_structure_checkbox.stateChanged.connect(self.on_settings_changed)
        group_layout.addWidget(self.preserve_structure_checkbox)

        # Output directory selection row (hidden until enabled)
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

        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self.open_output_directory)
        output_layout.addWidget(self.open_button)

        group_layout.addWidget(self.output_row)

        # Custom Output Directory info
        self.custom_output_info = QLabel("Converted files go to a chosen folder. Disable preserve to flatten into one folder.")
        self.custom_output_info.setStyleSheet("color: gray; font-size: 9pt;")
        self.custom_output_info.setIndent(20)
        group_layout.addWidget(self.custom_output_info)

        # Add stretch to push everything to top
        group_layout.addStretch()

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        # Initialize output row visibility/state
        self._set_output_row_visible(self.settings.use_custom_output_dir)
        if self.settings.custom_output_dir:
            self.custom_output_dir = self.settings.custom_output_dir
            self.output_path_label.setText(self.settings.custom_output_dir)
            self.output_path_label.setStyleSheet("color: #00E676; font-weight: bold;")
        self.preserve_structure_checkbox.setEnabled(self.settings.use_custom_output_dir)
        self.open_button.setEnabled(bool(self.custom_output_dir))

    def get_quality_description(self, quality: int) -> str:
        """Get description for quality level."""
        if quality < 50:
            return "Low quality - Small file size"
        elif quality < 70:
            return "Medium quality - Balanced"
        elif quality < 85:
            return "Good quality - Recommended"
        elif quality < 95:
            return "High quality - Larger file size"
        else:
            return "Maximum quality - Largest file size"

    def on_quality_changed(self, value: int):
        """Handle quality slider change."""
        self.quality_value_label.setText(f"{value}%")
        self.quality_indicator.setText(self.get_quality_description(value))
        self.on_settings_changed()

    def on_settings_changed(self):
        """Handle any settings change."""
        # Update settings object
        self.settings.jpg_quality = self.quality_slider.value()
        self.settings.delete_source_on_success = self.delete_source_checkbox.isChecked()
        self.settings.max_workers = self.thread_spinbox.value()
        self.settings.preserve_exif = self.preserve_exif_checkbox.isChecked()
        self.settings.operator_mode = self.operator_mode_checkbox.isChecked()
        self.settings.use_custom_output_dir = self.use_custom_output_dir_checkbox.isChecked()
        self.settings.custom_output_dir = self.custom_output_dir or ""
        self.settings.preserve_folder_structure = self.preserve_structure_checkbox.isChecked()

        # Emit signal
        self.settings_changed.emit(self.settings)

    def on_operator_mode_changed(self):
        """Handle operator mode change."""
        self.settings.operator_mode = self.operator_mode_checkbox.isChecked()
        self.operator_mode_changed.emit(self.settings.operator_mode)
        self.on_settings_changed()

    def on_context_menu_changed(self):
        """Handle context menu toggle."""
        self.settings.enable_context_menu = self.context_menu_checkbox.isChecked()
        self.context_menu_toggled.emit(self.settings.enable_context_menu)
        self.on_settings_changed()

    def _on_use_custom_output_dir_changed(self):
        """Handle use custom output directory checkbox change."""
        self.settings.use_custom_output_dir = self.use_custom_output_dir_checkbox.isChecked()
        self.custom_output_dir_toggled.emit(self.settings.use_custom_output_dir)
        self._set_output_row_visible(self.settings.use_custom_output_dir)
        self.preserve_structure_checkbox.setEnabled(self.settings.use_custom_output_dir)
        if self.settings.use_custom_output_dir:
            # Prompt immediately for output directory
            if not self.custom_output_dir:
                self.select_output_directory()
        else:
            # Clear output directory when disabled
            self.custom_output_dir = None
            self.settings.custom_output_dir = ""
            self.output_path_label.setText("(Not selected)")
            self.output_path_label.setStyleSheet("color: #7DE8A6; font-style: italic;")
            self.open_button.setEnabled(False)
            self.output_dir_changed.emit(None)
        self.on_settings_changed()

    def _set_output_row_visible(self, visible: bool):
        self.output_row.setVisible(visible)
        self.custom_output_info.setVisible(visible)

    def select_output_directory(self):
        """Open dialog to select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if directory:
            self.custom_output_dir = directory
            self.settings.custom_output_dir = directory
            self.output_path_label.setText(directory)
            self.output_path_label.setStyleSheet("color: #00E676; font-weight: bold;")
            self.open_button.setEnabled(True)
            self.output_dir_changed.emit(directory)
            self.on_settings_changed()
        else:
            # If user cancels and no prior selection, disable custom output
            if not self.custom_output_dir:
                self.use_custom_output_dir_checkbox.setChecked(False)

    def open_output_directory(self):
        """Open the selected output directory."""
        if not self.custom_output_dir:
            return
        try:
            import os
            from pathlib import Path
            output_dir = Path(self.custom_output_dir)
            if output_dir.exists() and os.name == 'nt':
                os.startfile(output_dir)
        except Exception:
            pass

    def get_settings(self) -> AppSettings:
        """Get current settings."""
        return self.settings

    def set_enabled(self, enabled: bool):
        """Enable/disable all controls."""
        self.quality_slider.setEnabled(enabled)
        self.delete_source_checkbox.setEnabled(enabled)
        self.thread_spinbox.setEnabled(enabled)
        self.preserve_exif_checkbox.setEnabled(enabled)
        self.operator_mode_checkbox.setEnabled(enabled)
        self.context_menu_checkbox.setEnabled(enabled)
        self.use_custom_output_dir_checkbox.setEnabled(enabled)
