from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from collections import deque
import time

from src.models.conversion_result import ConversionResult


class ProgressPanel(QWidget):
    """Panel for displaying conversion progress and statistics."""

    def __init__(self):
        super().__init__()
        self.start_time = None
        self.total_files = 0
        self.processed_files = 0
        self.successful = 0
        self.failed = 0
        self.current_file = ""

        # Rolling average for speed calculation (last 10 samples)
        self.speed_samples = deque(maxlen=10)
        self.last_update_time = None
        self.last_processed_count = 0

        self.init_ui()

        # Update timer (every 100ms for smooth UI)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Create group box
        group_box = QGroupBox("Progress")
        group_layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setFormat("%p%")
        group_layout.addWidget(self.progress_bar)

        # Stats grid
        stats_layout = QHBoxLayout()

        # Left column
        left_stats = QVBoxLayout()

        self.processed_label = QLabel("Processed: 0 / 0 images")
        self.processed_label.setObjectName("processed_label")
        left_stats.addWidget(self.processed_label)

        self.success_label = QLabel("Success: 0 | Failed: 0")
        self.success_label.setObjectName("success_label")
        left_stats.addWidget(self.success_label)

        stats_layout.addLayout(left_stats)

        # Right column
        right_stats = QVBoxLayout()

        self.speed_label = QLabel("Speed: 0 images/sec")
        self.speed_label.setObjectName("speed_label")
        right_stats.addWidget(self.speed_label)

        self.eta_label = QLabel("Time Remaining: --")
        self.eta_label.setObjectName("eta_label")
        right_stats.addWidget(self.eta_label)

        stats_layout.addLayout(right_stats)

        group_layout.addLayout(stats_layout)

        # Current file
        current_layout = QHBoxLayout()
        current_label = QLabel("Current:")
        current_layout.addWidget(current_label)

        self.current_file_label = QLabel("--")
        self.current_file_label.setObjectName("current_file_label")
        current_layout.addWidget(self.current_file_label, stretch=1)

        group_layout.addLayout(current_layout)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        # Initially hide (shown when batch starts)
        self.setVisible(False)

    def start_batch(self, total_files: int):
        """Start a new batch."""
        self.start_time = time.time()
        self.total_files = total_files
        self.processed_files = 0
        self.successful = 0
        self.failed = 0
        self.current_file = ""
        self.speed_samples.clear()
        self.last_update_time = time.time()
        self.last_processed_count = 0

        self.setVisible(True)
        self.update_display()

    def update_progress(self, result: ConversionResult):
        """Update progress with a conversion result."""
        self.processed_files += 1
        if self.processed_files > self.total_files:
            self.total_files = self.processed_files

        if result.success:
            self.successful += 1
        else:
            self.failed += 1

        self.current_file = str(result.input_path)

        # Calculate speed
        current_time = time.time()
        if self.last_update_time:
            elapsed = current_time - self.last_update_time
            if elapsed >= 0.5:  # Update speed every 0.5 seconds
                files_processed = self.processed_files - self.last_processed_count
                if elapsed > 0:
                    speed = files_processed / elapsed
                    self.speed_samples.append(speed)

                self.last_update_time = current_time
                self.last_processed_count = self.processed_files

    def update_display(self):
        """Update all display elements."""
        if not self.isVisible():
            return

        # Progress bar
        if self.total_files > 0:
            progress = int((self.processed_files / self.total_files) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"{progress}%")

        # Processed count
        self.processed_label.setText(f"Processed: {self.processed_files:,} / {self.total_files:,} images")

        # Success/Failure
        success_color = "#4CAF50" if self.successful > 0 else "#757575"
        failure_color = "#f44336" if self.failed > 0 else "#757575"
        self.success_label.setText(
            f"<span style='color:{success_color};'>Success: {self.successful:,}</span> | "
            f"<span style='color:{failure_color};'>Failed: {self.failed:,}</span>"
        )

        # Speed
        if self.speed_samples:
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)
            self.speed_label.setText(f"Speed: {avg_speed:.1f} images/sec")

            # ETA
            remaining = self.total_files - self.processed_files
            if avg_speed > 0 and remaining > 0:
                eta_seconds = remaining / avg_speed
                eta_str = self.format_time(eta_seconds)
                self.eta_label.setText(f"Time Remaining: {eta_str}")
            else:
                self.eta_label.setText("Time Remaining: --")
        else:
            self.speed_label.setText("Speed: Calculating...")
            self.eta_label.setText("Time Remaining: Calculating...")

        # Current file
        if self.current_file:
            # Truncate long file paths
            display_name = self.current_file
            if len(display_name) > 90:
                display_name = "..." + display_name[-87:]
            self.current_file_label.setText(display_name)
        else:
            self.current_file_label.setText("--")

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds into human-readable time string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def reset(self):
        """Reset to initial state."""
        self.start_time = None
        self.total_files = 0
        self.processed_files = 0
        self.successful = 0
        self.failed = 0
        self.current_file = ""
        self.speed_samples.clear()
        self.progress_bar.setValue(0)
        self.setVisible(False)

    def get_elapsed_time(self) -> float:
        """Get elapsed time since batch started."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    def get_stats(self) -> dict:
        """Get current statistics."""
        avg_speed = sum(self.speed_samples) / len(self.speed_samples) if self.speed_samples else 0

        return {
            'total_files': self.total_files,
            'processed': self.processed_files,
            'successful': self.successful,
            'failed': self.failed,
            'progress_pct': (self.processed_files / self.total_files * 100) if self.total_files > 0 else 0,
            'speed_per_sec': avg_speed,
            'elapsed_time': self.get_elapsed_time()
        }
