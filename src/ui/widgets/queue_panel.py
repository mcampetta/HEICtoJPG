from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from pathlib import Path

from src.core.batch_manager import BatchJob, BatchStatus


class QueueItemWidget(QWidget):
    """Widget for displaying a single queue item."""

    remove_clicked = pyqtSignal(str)  # job_id

    def __init__(self, job: BatchJob):
        super().__init__()
        self.job = job
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumHeight(60)

        # Status indicator (icon)
        self.status_label = QLabel()
        self.status_label.setFixedSize(80, 24)
        self.status_label.setScaledContents(False)
        self.update_status_icon()
        layout.addWidget(self.status_label)

        # Job info
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Folder name and count
        name_label = QLabel(f"{self.job.folder_path.name}")
        name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(name_label)

        # Details
        self.details_label = QLabel(self.get_details_text())
        self.details_label.setStyleSheet("color: gray; font-size: 9pt;")
        info_layout.addWidget(self.details_label)

        layout.addLayout(info_layout, stretch=1)

        # Remove button
        self.remove_button = QPushButton("\u2715")  # X symbol
        self.remove_button.setFixedSize(25, 25)
        self.remove_button.setToolTip("Remove from queue")
        self.remove_button.clicked.connect(lambda: self.remove_clicked.emit(self.job.id))
        layout.addWidget(self.remove_button)

    def update_status_icon(self):
        """Update status icon based on current job status."""
        icon_base_path = Path(__file__).parent.parent.parent.parent / "resources" / "icons"

        if self.job.status == BatchStatus.QUEUED:
            # No icon for queued, just text
            self.status_label.setText("Queued")
            self.status_label.setStyleSheet("color: #00B8D4; font-weight: bold;")
            self.status_label.setPixmap(QPixmap())
        elif self.job.status == BatchStatus.PROCESSING:
            icon_path = icon_base_path / "run.png"
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                self.status_label.setPixmap(pixmap.scaled(80, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.status_label.setText("")
            else:
                self.status_label.setText("Running")
                self.status_label.setStyleSheet("color: #00E676; font-weight: bold;")
        elif self.job.status == BatchStatus.COMPLETED:
            icon_path = icon_base_path / "done.png"
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                self.status_label.setPixmap(pixmap.scaled(80, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.status_label.setText("")
            else:
                self.status_label.setText("Done")
                self.status_label.setStyleSheet("color: #00B8D4; font-weight: bold;")
        elif self.job.status == BatchStatus.FAILED:
            icon_path = icon_base_path / "fail.png"
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                self.status_label.setPixmap(pixmap.scaled(80, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.status_label.setText("")
            else:
                self.status_label.setText("Failed")
                self.status_label.setStyleSheet("color: #FF5252; font-weight: bold;")
        else:
            self.status_label.setText("Unknown")
            self.status_label.setStyleSheet("color: #7DE8A6;")

    def get_details_text(self) -> str:
        """Get details text for current job state."""
        if self.job.status == BatchStatus.QUEUED:
            return f"{self.job.total_files:,} files | Queued"
        elif self.job.status == BatchStatus.PROCESSING:
            progress = (self.job.processed_files / self.job.total_files * 100) if self.job.total_files > 0 else 0
            return f"{self.job.processed_files:,} / {self.job.total_files:,} files | {progress:.0f}% complete"
        elif self.job.status == BatchStatus.COMPLETED:
            return f"{self.job.successful:,} successful, {self.job.failed:,} failed | Completed"
        else:
            return f"{self.job.total_files:,} files | {self.job.status.value}"

    def update_job(self, job: BatchJob):
        """Update display with new job state."""
        self.job = job
        self.update_status_icon()
        self.details_label.setText(self.get_details_text())

        # Disable remove button if processing
        if job.status == BatchStatus.PROCESSING:
            self.remove_button.setEnabled(False)
        else:
            self.remove_button.setEnabled(True)


class QueuePanel(QWidget):
    """Panel for displaying and managing the batch queue."""

    job_removed = pyqtSignal(str)  # job_id

    def __init__(self):
        super().__init__()
        self.job_widgets = {}  # job_id -> QueueItemWidget
        self.list_items = {}   # job_id -> QListWidgetItem
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Create group box
        group_box = QGroupBox("Batch Queue")
        group_box.setObjectName("queue_group")
        group_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(8, 8, 8, 8)
        group_layout.setSpacing(6)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        group_layout.addWidget(self.list_widget)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)

        self.clear_completed_button = QPushButton("Clear Completed")
        self.clear_completed_button.setToolTip("Remove completed batches from the list")
        self.clear_completed_button.clicked.connect(self.clear_completed)
        button_layout.addWidget(self.clear_completed_button)

        button_layout.addStretch()

        group_layout.addLayout(button_layout)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        # Initially hide (shown when jobs are added)
        self.setVisible(False)

    def add_job(self, job: BatchJob):
        """Add a job to the queue display."""
        # Create widget for this job
        widget = QueueItemWidget(job)
        widget.remove_clicked.connect(self.on_remove_clicked)

        # Create list item
        item = QListWidgetItem(self.list_widget)
        size = widget.sizeHint()
        if size.height() < 60:
            size.setHeight(60)
        item.setSizeHint(size)

        # Add to list
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

        # Store references
        self.job_widgets[job.id] = widget
        self.list_items[job.id] = item

        # Show panel
        self.setVisible(True)
        self.update_list_height()
        self.adjustSize()

    def update_job_progress(self, job: BatchJob):
        """Update a job's progress display."""
        if job and job.id in self.job_widgets:
            self.job_widgets[job.id].update_job(job)

    def set_job_processing(self, job_id: str):
        """Mark a job as processing."""
        if job_id in self.job_widgets:
            job = self.job_widgets[job_id].job
            job.status = BatchStatus.PROCESSING
            self.job_widgets[job_id].update_job(job)

    def set_job_completed(self, job_id: str):
        """Mark a job as completed."""
        if job_id in self.job_widgets:
            job = self.job_widgets[job_id].job
            job.status = BatchStatus.COMPLETED
            self.job_widgets[job_id].update_job(job)

    def remove_job(self, job_id: str):
        """Remove a job from the queue display."""
        if job_id in self.list_items:
            # Remove from list widget
            item = self.list_items[job_id]
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

            # Remove from dictionaries
            del self.list_items[job_id]
            del self.job_widgets[job_id]

            # Hide panel if empty
            if self.list_widget.count() == 0:
                self.setVisible(False)
        self.update_list_height()

    def on_remove_clicked(self, job_id: str):
        """Handle remove button click."""
        self.remove_job(job_id)
        self.job_removed.emit(job_id)

    def clear_jobs(self):
        """Clear all jobs from the queue display."""
        self.list_widget.clear()
        self.job_widgets.clear()
        self.list_items.clear()
        self.setVisible(False)
        self.update_list_height()
        self.adjustSize()

    def clear_completed(self):
        """Clear all completed jobs from the queue."""
        # Find all completed jobs
        completed_ids = []
        for job_id, widget in self.job_widgets.items():
            if widget.job.status == BatchStatus.COMPLETED:
                completed_ids.append(job_id)

        # Remove them
        for job_id in completed_ids:
            self.remove_job(job_id)
            self.job_removed.emit(job_id)
        self.update_list_height()

    def get_job_count(self) -> int:
        """Get number of jobs in queue."""
        return self.list_widget.count()

    def update_list_height(self):
        """Adjust list height to fit current items."""
        if self.list_widget.count() == 0:
            return
        item_height = self.list_widget.sizeHintForRow(0)
        if item_height <= 0:
            item_height = 60
        visible_rows = min(self.list_widget.count(), 4)
        padding = 12
        target_height = (item_height * visible_rows) + padding
        self.list_widget.setFixedHeight(target_height)
        self.list_widget.updateGeometry()
        self.updateGeometry()
        self.adjustSize()
