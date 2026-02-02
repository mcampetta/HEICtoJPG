from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication,
    QPushButton, QLabel, QMessageBox, QProgressDialog, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QCloseEvent, QIcon
from pathlib import Path
from typing import Optional
import logging
import sys

from src.models.app_settings import AppSettings
from src.models.conversion_result import ConversionResult
from src.core.batch_manager import BatchManager, BatchJob, BatchStatus
from src.core.worker_pool import WorkerPool
from src.ui.widgets.settings_panel import SettingsPanel
from src.ui.widgets.progress_panel import ProgressPanel
from src.ui.widgets.queue_panel import QueuePanel
from src.ui.widgets.preview_panel import PreviewPanel
from src.ui.widgets.matrix_rain import MatrixRainWidget, ScanlineOverlay
from src.utils import win_context_menu

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Worker thread for scanning directories without blocking UI."""

    scan_progress = pyqtSignal(str, int)  # current_file, files_scanned
    scan_complete = pyqtSignal(object)  # ScanResult
    scan_error = pyqtSignal(str)  # error_message

    def __init__(self, batch_manager, job):
        super().__init__()
        self.batch_manager = batch_manager
        self.job = job

    def run(self):
        """Scan the job's folder in background."""
        try:
            def progress_callback(current_file, files_scanned):
                self.scan_progress.emit(str(current_file), files_scanned)

            scan_result = self.batch_manager.scan_job(self.job, progress_callback)
            self.scan_complete.emit(scan_result)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.scan_error.emit(str(e))


class ConversionWorker(QThread):
    """Worker thread for running conversions without blocking UI."""

    progress_update = pyqtSignal(ConversionResult)
    job_started = pyqtSignal(BatchJob)
    paused = pyqtSignal()
    job_completed = pyqtSignal(BatchJob)
    all_completed = pyqtSignal()

    def __init__(self, batch_manager: BatchManager, worker_pool: WorkerPool):
        super().__init__()
        self.batch_manager = batch_manager
        self.worker_pool = worker_pool
        self.current_job: BatchJob = None

    def run(self):
        """Process all queued jobs."""
        while True:
            # Get next job
            job = self.batch_manager.get_next_job()
            if job is None:
                break

            self.current_job = job
            job.status = BatchStatus.PROCESSING
            self.job_started.emit(job)

            # Generate tasks and process
            tasks = self.batch_manager.generate_tasks(job)

            def result_callback(result: ConversionResult):
                self.batch_manager.update_job_progress(job, result)
                self.progress_update.emit(result)

            # Process tasks with worker pool
            self.worker_pool.process_tasks(tasks, result_callback, pause_callback=self.paused.emit)

            # If pause requested, wait for active tasks to finish then signal paused
            if self.worker_pool.is_paused_state():
                self.worker_pool.wait_for_idle()
                self.paused.emit()

            # Mark job as completed
            self.job_completed.emit(job)
            self.current_job = None

        self.all_completed.emit()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, settings: AppSettings, initial_folder: Optional[Path] = None):
        super().__init__()
        # Do not retain custom output directory across runs
        settings.use_custom_output_dir = False
        settings.custom_output_dir = ""
        if win_context_menu.is_supported():
            settings.enable_context_menu = win_context_menu.is_enabled()
        self.settings = settings
        self.batch_manager = BatchManager()
        self.worker_pool = WorkerPool(max_workers=settings.max_workers)
        self.conversion_worker: ConversionWorker = None
        self.stop_requested = False
        self._initial_size = None
        self.pause_check_timer = QTimer()
        self.pause_check_timer.setInterval(200)
        self.pause_check_timer.timeout.connect(self._check_paused_state)
        self._compact_mode = False
        self._initial_folder = initial_folder

        self.init_ui()
        self.connect_signals()
        # Ensure operator mode visual state is applied after the window is shown
        QTimer.singleShot(0, lambda: self.toggle_operator_mode(self.settings.operator_mode))
        QTimer.singleShot(0, self._capture_initial_size)
        QTimer.singleShot(0, self._apply_initial_folder)

        logger.info("Main window initialized")

    def init_ui(self):
        """Initialize the user interface."""
        # Set window title based on operator mode
        if self.settings.operator_mode:
            self.setWindowTitle("HEIC to JPG Converter - OPERATOR MODE ACTIVE")
        else:
            self.setWindowTitle("HEIC to JPG Converter - Cyber Ops Console")

        self.resize(self.settings.window_width, self.settings.window_height)
        # Adjust minimum height based on available screen height
        screen = QApplication.primaryScreen()
        if screen:
            available_height = screen.availableGeometry().height()
            min_height = 920
            if available_height < min_height:
                min_height = max(600, available_height - 40)
            self.setMinimumHeight(min_height)
            # Ensure current height fits the available screen
            if self.height() > available_height - 20:
                self.resize(self.width(), max(min_height, available_height - 20))
        else:
            self.setMinimumHeight(920)

        # Set application icon
        icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / "app.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Load and apply stylesheet
        self.load_stylesheet()

        # Create container widget
        container_widget = QWidget()
        self.setCentralWidget(container_widget)

        # Create main layout on the container widget
        main_layout = QVBoxLayout(container_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.container_widget = container_widget
        self.main_layout = main_layout

        # Matrix rain header (Operator Mode)
        self.matrix_rain = MatrixRainWidget()
        self.matrix_rain.setVisible(self.settings.operator_mode)
        if self.settings.operator_mode:
            self.matrix_rain.start()  # Start animation if enabled by default
        main_layout.addWidget(self.matrix_rain)

        # Scanline overlay (Operator Mode)
        self.scanlines = ScanlineOverlay(container_widget)
        self.scanlines.setVisible(self.settings.operator_mode)
        self.scanlines.raise_()

        # Horizontal layout for settings and preview
        middle_layout = QHBoxLayout()

        # Settings panel (left)
        self.settings_panel = SettingsPanel(self.settings)
        middle_layout.addWidget(self.settings_panel, stretch=1)

        # Preview panel (right)
        self.preview_panel = PreviewPanel()
        middle_layout.addWidget(self.preview_panel, stretch=2)

        main_layout.addLayout(middle_layout)

        # Queue panel
        self.queue_panel = QueuePanel()
        main_layout.addWidget(self.queue_panel)

        # Progress panel
        self.progress_panel = ProgressPanel()
        main_layout.addWidget(self.progress_panel)

        # Compact controls (shown only on small vertical screens)
        self.compact_bar = QWidget()
        compact_layout = QHBoxLayout(self.compact_bar)
        compact_layout.setContentsMargins(0, 0, 0, 0)
        compact_layout.addStretch()

        self.compact_label = QLabel("Compact mode enabled")
        self.compact_label.setStyleSheet("color: #FFB300; font-size: 9pt;")
        compact_layout.addWidget(self.compact_label)

        self.toggle_queue_button = QToolButton()
        self.toggle_queue_button.setText("Show Queue")
        self.toggle_queue_button.setCheckable(True)
        compact_layout.addWidget(self.toggle_queue_button)

        self.toggle_progress_button = QToolButton()
        self.toggle_progress_button.setText("Show Progress")
        self.toggle_progress_button.setCheckable(True)
        compact_layout.addWidget(self.toggle_progress_button)

        compact_layout.addStretch()
        self.compact_bar.setVisible(False)
        main_layout.addWidget(self.compact_bar)

        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_button = QPushButton("RUN CONVERSION")
        self.start_button.setObjectName("start_button")
        self.start_button.setMinimumHeight(40)
        self.start_button.setEnabled(False)
        self.start_button.setIcon(QIcon(str(Path(__file__).parent.parent.parent / "resources" / "icons" / "run.svg")))
        self.start_button.setProperty("iconButton", True)
        self.start_button.setToolTip("Start converting all queued folders")
        button_layout.addWidget(self.start_button)

        self.pause_button = QPushButton("PAUSE")
        self.pause_button.setObjectName("pause_button")
        self.pause_button.setMinimumHeight(40)
        self.pause_button.setEnabled(False)
        self.pause_button.setIcon(QIcon(str(Path(__file__).parent.parent.parent / "resources" / "icons" / "paused.svg")))
        self.pause_button.setProperty("iconButton", True)
        self.pause_button.setToolTip("Pause or resume conversion")
        button_layout.addWidget(self.pause_button)

        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.setIcon(QIcon(str(Path(__file__).parent.parent.parent / "resources" / "icons" / "stop.svg")))
        self.stop_button.setProperty("iconButton", True)
        self.stop_button.setToolTip("Stop conversion after current tasks finish")
        button_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("CLEAR")
        self.clear_button.setObjectName("clear_button")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.setEnabled(False)
        self.clear_button.setIcon(QIcon(str(Path(__file__).parent.parent.parent / "resources" / "icons" / "trash.svg")))
        self.clear_button.setProperty("iconButton", True)
        self.clear_button.setToolTip("Remove the most recently added batch")
        button_layout.addWidget(self.clear_button)

        self.view_logs_button = QPushButton("View Logs")
        self.view_logs_button.setMinimumHeight(40)
        self.view_logs_button.setToolTip("Open the logs folder")
        button_layout.addWidget(self.view_logs_button)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

    def connect_signals(self):
        """Connect signals and slots."""
        # Preview panel
        self.preview_panel.folder_to_scan.connect(self.scan_folder)
        self.preview_panel.clear_requested.connect(self.clear_last_job)

        # Settings panel
        self.settings_panel.settings_changed.connect(self.on_settings_changed)
        self.settings_panel.operator_mode_changed.connect(self.toggle_operator_mode)
        self.settings_panel.custom_output_dir_toggled.connect(self.on_custom_output_toggled)
        self.settings_panel.output_dir_changed.connect(self.on_output_dir_changed)
        self.settings_panel.context_menu_toggled.connect(self.on_context_menu_toggled)

        # Queue panel
        self.queue_panel.job_removed.connect(self.on_job_removed)

        # Control buttons
        self.start_button.clicked.connect(self.start_conversion)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop_conversion)
        self.clear_button.clicked.connect(self.clear_last_job)
        self.view_logs_button.clicked.connect(self.view_logs)
        self.toggle_queue_button.clicked.connect(self._toggle_queue_visibility)
        self.toggle_progress_button.clicked.connect(self._toggle_progress_visibility)

        # Normalize output directory state at startup
        self.on_custom_output_toggled(self.settings.use_custom_output_dir)
        self._resize_to_contents()
        self._evaluate_compact_mode()

    def scan_folder(self, folder_path: Path):
        """Handle folder selection."""
        logger.info(f"Folder selected: {folder_path}")

        # Validate folder
        if not folder_path.exists() or not folder_path.is_dir():
            QMessageBox.warning(self, "Invalid Folder", f"Folder does not exist: {folder_path}")
            return

        # Get output directory based on setting
        output_dir = None
        if self.settings.use_custom_output_dir:
            logger.info(
                "Custom output enabled: %s | path: %s | preserve_structure: %s",
                self.settings.use_custom_output_dir,
                self.settings.custom_output_dir,
                self.settings.preserve_folder_structure
            )
            if not self.settings.custom_output_dir:
                QMessageBox.warning(self, "Output Directory Required", "Please select a custom output directory.")
                return
            output_dir = Path(self.settings.custom_output_dir)
            if not output_dir.exists() or not output_dir.is_dir():
                QMessageBox.warning(self, "Invalid Output Directory", "Please select a valid custom output directory.")
                return
            # Basic write-access check
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                test_file = output_dir / ".heic2jpg_write_test.tmp"
                with open(test_file, "wb") as f:
                    f.write(b"test")
                test_file.unlink(missing_ok=True)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Output Directory Not Writable",
                    f"Cannot write to output directory:\n{output_dir}\n\n{e}"
                )
                return

        logger.info(f"Creating batch job with output_dir: {output_dir}")

        # Create batch job
        job = self.batch_manager.add_job(
            folder_path=folder_path,
            quality=self.settings.jpg_quality,
            delete_source=self.settings.delete_source_on_success,
            preserve_exif=self.settings.preserve_exif,
            output_dir=output_dir,
            preserve_folder_structure=self.settings.preserve_folder_structure
        )
        logger.info(f"Batch job created with ID: {job.id}, output_dir: {job.output_dir}")

        # Scan folder in background thread
        self.scan_job_async(job)

    def on_custom_output_toggled(self, enabled: bool):
        """Handle custom output toggle changes."""
        if not enabled:
            self.settings.custom_output_dir = ""

    def on_output_dir_changed(self, output_dir):
        """Handle output directory selection changes."""
        if output_dir:
            self.settings.custom_output_dir = str(output_dir)
        else:
            self.settings.custom_output_dir = ""

    def scan_job_async(self, job: BatchJob):
        """Scan a job's folder for HEIC files asynchronously."""
        # Create progress dialog
        self.scan_progress_dialog = QProgressDialog(
            "Scanning directory for HEIC files...\nPlease wait...",
            "Cancel",
            0,
            0,  # 0 max = indeterminate/busy indicator
            self
        )
        self.scan_progress_dialog.setWindowTitle("Scanning Directory")
        self.scan_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.scan_progress_dialog.setMinimumDuration(500)  # Show after 500ms
        self.scan_progress_dialog.setAutoClose(True)
        self.scan_progress_dialog.setAutoReset(True)

        # Create and start scan worker
        self.scan_worker = ScanWorker(self.batch_manager, job)
        self.scan_worker.scan_progress.connect(self.on_scan_progress)
        self.scan_worker.scan_complete.connect(lambda result: self.on_scan_complete(job, result))
        self.scan_worker.scan_error.connect(lambda error: self.on_scan_error(job, error))

        # Handle cancel button
        self.scan_progress_dialog.canceled.connect(self.scan_worker.terminate)

        self.scan_worker.start()

    def on_scan_progress(self, current_file: str, files_scanned: int):
        """Handle scan progress updates."""
        if hasattr(self, 'scan_progress_dialog') and self.scan_progress_dialog:
            # Truncate long paths
            display_file = current_file
            if len(display_file) > 60:
                display_file = "..." + display_file[-57:]

            self.scan_progress_dialog.setLabelText(
                f"Scanning directory for HEIC files...\n\n"
                f"Files scanned: {files_scanned:,}\n"
                f"Current: {display_file}"
            )

    def on_scan_complete(self, job: BatchJob, scan_result):
        """Handle scan completion."""
        # Close progress dialog
        if hasattr(self, 'scan_progress_dialog') and self.scan_progress_dialog:
            self.scan_progress_dialog.close()

        if scan_result.heic_count == 0:
            QMessageBox.information(
                self,
                "No HEIC Files",
                f"No HEIC files found in {job.folder_path}\n\n"
                f"Total files scanned: {scan_result.total_files_scanned:,}\n"
                f"Directories scanned: {scan_result.total_directories_scanned:,}"
            )
            self.batch_manager.remove_job(job.id)
            self.preview_panel.reset()
            return

        # Build scan summary (include output directory if custom)
        output_line = ""
        if self.settings.use_custom_output_dir and self.settings.custom_output_dir:
            mode = "Preserve folder structure" if self.settings.preserve_folder_structure else "Flatten into one folder"
            output_line = f"\nOutput directory: {self.settings.custom_output_dir}\nOutput mode: {mode}"

        # Show scan summary
        QMessageBox.information(
            self,
            "Scan Complete",
            f"Found {scan_result.heic_count:,} HEIC files\n\n"
            f"Total files scanned: {scan_result.total_files_scanned:,}\n"
            f"Total size: {scan_result.total_size_human()}\n"
            f"Directories with HEIC: {scan_result.directories_with_heic}"
            f"{output_line}"
        )

        # Add job to queue panel
        self.queue_panel.add_job(job)
        self.queue_panel.updateGeometry()
        self._resize_to_contents()
        self._evaluate_compact_mode()

        # Update preview panel (limit to 20 for performance with large datasets)
        if scan_result.heic_files:
            # Load full preview list (single-image gallery view)
            self.preview_panel.set_files(scan_result.heic_files)

        # Enable start button
        self.start_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.preview_panel.set_clear_enabled(True)

    def on_scan_error(self, job: BatchJob, error: str):
        """Handle scan error."""
        # Close progress dialog
        if hasattr(self, 'scan_progress_dialog') and self.scan_progress_dialog:
            self.scan_progress_dialog.close()

        logger.error(f"Error scanning job: {error}")
        QMessageBox.critical(self, "Scan Error", f"Error scanning folder: {error}")
        self.batch_manager.remove_job(job.id)
        self.preview_panel.reset()

    def on_settings_changed(self, settings: AppSettings):
        """Handle settings changes."""
        self.settings = settings
        self.settings.save()
        logger.info("Settings updated")

    def on_context_menu_toggled(self, enabled: bool):
        """Enable/disable Windows Explorer context menu entry."""
        if not win_context_menu.is_supported():
            QMessageBox.information(self, "Not Supported", "Context menu integration is supported on Windows only.")
            self.settings_panel.context_menu_checkbox.setChecked(False)
            return
        exe_path = Path(sys.argv[0]).resolve()
        if enabled:
            win_context_menu.enable(exe_path)
        else:
            win_context_menu.disable()
        self.settings.enable_context_menu = win_context_menu.is_enabled()
        self.settings.save()

    def on_job_removed(self, job_id: str):
        """Handle job removal from queue."""
        self.batch_manager.remove_job(job_id)

        # Disable start button if no jobs
        if len(self.batch_manager.get_queued_jobs()) == 0:
            self.start_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.preview_panel.reset()
            self._resize_to_contents()
            self._evaluate_compact_mode()
        else:
            self.clear_button.setEnabled(True)
            self.preview_panel.set_clear_enabled(True)

    def clear_last_job(self):
        """Clear only the most recently added job."""
        if self.worker_pool.is_running():
            return
        last_job = self.batch_manager.remove_last_job()
        if last_job:
            self.queue_panel.remove_job(last_job.id)
        if len(self.batch_manager.get_queued_jobs()) == 0:
            self.start_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.preview_panel.reset()
        self._resize_to_contents()
        self._evaluate_compact_mode()


    def start_conversion(self):
        """Start conversion process."""
        if not self.batch_manager.get_queued_jobs():
            QMessageBox.warning(self, "No Jobs", "No jobs in queue to process")
            return

        logger.info("Starting conversion")
        self._apply_current_settings_to_jobs()
        if self.batch_manager.current_job:
            logger.info("Current job total_files: %s", self.batch_manager.current_job.total_files)

        # Create and start worker thread
        self.conversion_worker = ConversionWorker(self.batch_manager, self.worker_pool)
        self.conversion_worker.progress_update.connect(self.on_progress_update)
        self.conversion_worker.job_started.connect(self.on_job_started)
        self.conversion_worker.job_completed.connect(self.on_job_completed)
        self.conversion_worker.all_completed.connect(self.on_all_completed)
        self.conversion_worker.paused.connect(self.on_paused)
        self.conversion_worker.start()

        # Enable live preview mode
        self.preview_panel.enable_live_mode()

        # Update UI
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.clear_button.setEnabled(False)
        self.preview_panel.set_clear_enabled(False)
        if self._compact_mode:
            self.progress_panel.setVisible(True)
            self.toggle_progress_button.setChecked(True)
            self.toggle_progress_button.setText("Hide Progress")
        QTimer.singleShot(0, self._evaluate_compact_mode)

    def _apply_current_settings_to_jobs(self):
        """Apply current settings to queued jobs before conversion."""
        output_dir = None
        if self.settings.use_custom_output_dir and self.settings.custom_output_dir:
            output_dir = Path(self.settings.custom_output_dir)

        for job in self.batch_manager.get_queued_jobs():
            job.quality = self.settings.jpg_quality
            job.delete_source = self.settings.delete_source_on_success
            job.preserve_exif = self.settings.preserve_exif
            job.output_dir = output_dir
            job.preserve_folder_structure = self.settings.preserve_folder_structure
            logger.info(
                "Applied settings to job %s | output_dir: %s | preserve_structure: %s",
                job.id,
                job.output_dir,
                job.preserve_folder_structure
            )


    def toggle_pause(self):
        """Toggle pause state."""
        if self.worker_pool.is_paused_state():
            self.worker_pool.resume()
            self.pause_button.setText("PAUSE")
            self.pause_check_timer.stop()
            logger.info("Conversion resumed")
        else:
            self.worker_pool.pause()
            self.pause_button.setText("PAUSING...")
            self.pause_check_timer.start()
            logger.info("Conversion paused")
            # Fallback: force state update after a short delay
            QTimer.singleShot(1500, self._check_paused_state)

    def on_paused(self):
        """Handle paused state after workers go idle."""
        self.pause_button.setText("RESUME")

    def _check_paused_state(self):
        if self.worker_pool.is_paused_state() and self.worker_pool.get_in_flight_count() == 0:
            self.pause_check_timer.stop()
            self.pause_button.setText("RESUME")

    def stop_conversion(self):
        """Stop conversion process."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Stop Conversion")
        msg_box.setText(
            "Are you sure you want to stop the conversion?\n"
            "Current tasks will finish, but no new tasks will start."
        )
        msg_box.setIcon(QMessageBox.Icon.NoIcon)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("Stopping conversion")
            self.stop_requested = True
            self.worker_pool.stop()
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)


    def clear_all(self):
        """Clear all jobs and reset the UI."""
        self.batch_manager.clear_all_jobs()
        self.queue_panel.clear_jobs()
        self.progress_panel.reset()
        self.preview_panel.reset()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.preview_panel.set_clear_enabled(True)
        self._resize_to_contents()
        self._restore_initial_size()
        self._evaluate_compact_mode()

    def on_progress_update(self, result: ConversionResult):
        """Handle progress update from worker."""
        self.progress_panel.update_progress(result)
        self.queue_panel.update_job_progress(self.conversion_worker.current_job)

        # Add successfully converted file to live preview
        if result.success and result.output_path:
            self.preview_panel.add_conversion(result.output_path)

    def on_job_started(self, job: BatchJob):
        """Handle job start."""
        logger.info(f"Job started: {job.id}")
        self.queue_panel.set_job_processing(job.id)
        self.progress_panel.start_batch(job.total_files)
        self._resize_to_contents()
        self._evaluate_compact_mode()

    def on_job_completed(self, job: BatchJob):
        """Handle job completion."""
        logger.info(f"Job completed: {job.id}")
        self.queue_panel.set_job_completed(job.id)

    def on_all_completed(self):
        """Handle all jobs completion."""
        logger.info("All conversions completed")

        # Disable live preview mode
        self.preview_panel.disable_live_mode()

        # Show completion message (offer to open output directory)
        stats = self.batch_manager.get_total_stats()
        msg_box = QMessageBox(self)
        if self.stop_requested:
            msg_box.setWindowTitle("Conversion Stopped")
            msg_box.setText("Conversion stopped by user.")
        else:
            msg_box.setWindowTitle("Conversion Complete")
            msg_box.setText("All conversions completed!")
        msg_box.setInformativeText(
            f"Total processed: {stats['processed_files']:,}\n"
            f"Successful: {stats['successful']:,}\n"
            f"Failed: {stats['failed']:,}\n"
            f"Success rate: {stats['success_rate']}"
        )

        if self.settings.delete_source_on_success:
            msg_box.setInformativeText(
                msg_box.informativeText()
                + f"\nSource files deleted: {stats['successful']:,}"
            )

        open_output_button = None
        if self.settings.use_custom_output_dir and self.settings.custom_output_dir:
            open_output_button = msg_box.addButton("Open Output Folder", QMessageBox.ButtonRole.ActionRole)

        msg_box.addButton(QMessageBox.StandardButton.Ok)
        msg_box.exec()

        if open_output_button and msg_box.clickedButton() == open_output_button:
            try:
                output_dir = Path(self.settings.custom_output_dir)
                if output_dir.exists():
                    import os
                    if os.name == 'nt':
                        os.startfile(output_dir)
            except Exception:
                pass

        # Reset UI
        self.stop_requested = False
        self.clear_all()


    def view_logs(self):
        """Open logs directory."""
        from pathlib import Path
        import os
        import subprocess

        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Open in file explorer
        if os.name == 'nt':  # Windows
            os.startfile(log_dir)
        else:  # Unix-like
            subprocess.call(['xdg-open', str(log_dir)])

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Check if conversion is running
        if self.conversion_worker and self.conversion_worker.isRunning():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Conversion in Progress")
            msg_box.setText("Conversion is still running. Are you sure you want to quit?")
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            reply = msg_box.exec()

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            # Stop conversion
            self.worker_pool.stop()
            self.conversion_worker.wait(10000)  # Wait up to 10 seconds

        # Stop preview/background loaders
        try:
            self.preview_panel.shutdown()
        except Exception:
            pass

        # Save settings
        self.settings.save()

        event.accept()
        QApplication.quit()

    def load_stylesheet(self):
        """Load and apply the Matrix/Cyber-Ops stylesheet."""
        stylesheet_path = Path(__file__).parent.parent.parent / "resources" / "styles.qss"

        if stylesheet_path.exists():
            try:
                with open(stylesheet_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                logger.info("Stylesheet loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load stylesheet: {e}")
        else:
            logger.warning(f"Stylesheet not found: {stylesheet_path}")

    def toggle_operator_mode(self, enabled: bool):
        """Toggle Operator Mode (Matrix rain + effects)."""
        logger.info(f"Operator Mode: {'ENABLED' if enabled else 'DISABLED'}")

        # Show/hide matrix rain
        self.matrix_rain.setVisible(enabled)
        self.scanlines.setVisible(enabled)

        if enabled:
            self.matrix_rain.start()
        else:
            self.matrix_rain.stop()

        # Update window title
        if enabled:
            self.setWindowTitle("HEIC to JPG Converter - OPERATOR MODE ACTIVE")
        else:
            self.setWindowTitle("HEIC to JPG Converter - Cyber Ops Console")

    def _resize_to_contents(self):
        """Resize window to fit current content without exceeding screen bounds."""
        if not hasattr(self, "container_widget"):
            return
        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        hint = self.container_widget.sizeHint()
        target_width = min(hint.width() + 40, available.width() - 20)
        target_height = min(hint.height() + 40, available.height() - 20)
        target_width = max(target_width, self.minimumWidth() or 600)
        target_height = max(target_height, self.minimumHeight() or 600)
        self.resize(target_width, target_height)

    def resizeEvent(self, event: QCloseEvent):
        super().resizeEvent(event)
        if hasattr(self, "scanlines") and self.scanlines:
            self.scanlines.setGeometry(self.centralWidget().rect())
        self._evaluate_compact_mode()

    def _capture_initial_size(self):
        """Capture initial window size for later reset."""
        if self._initial_size is None:
            self._initial_size = self.size()

    def _restore_initial_size(self):
        """Restore window size to initial launch size."""
        if self._initial_size is not None:
            self.resize(self._initial_size)

    def _apply_initial_folder(self):
        if self._initial_folder and self._initial_folder.exists():
            self.preview_panel.select_folder(self._initial_folder)

    def _evaluate_compact_mode(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry().height()
        content_height = self.container_widget.sizeHint().height() + 40
        needs_compact = content_height > (available - 20)
        logger.info("Compact mode check | content: %s | available: %s | needs_compact: %s", content_height, available, needs_compact)
        if needs_compact != self._compact_mode:
            self._set_compact_mode(needs_compact)

    def _set_compact_mode(self, enabled: bool):
        self._compact_mode = enabled
        self.compact_bar.setVisible(enabled)
        self.compact_label.setVisible(enabled)
        if enabled:
            if self.queue_panel.get_job_count() > 0:
                self.queue_panel.setVisible(False)
                self.toggle_queue_button.setChecked(False)
                self.toggle_queue_button.setText("Show Queue")
            if not self.progress_panel.isVisible():
                self.toggle_progress_button.setChecked(False)
                self.toggle_progress_button.setText("Show Progress")
        else:
            if self.queue_panel.get_job_count() > 0:
                self.queue_panel.setVisible(True)
            self.toggle_queue_button.setChecked(False)
            self.toggle_progress_button.setChecked(False)
            self.toggle_queue_button.setText("Show Queue")
            self.toggle_progress_button.setText("Show Progress")

    def _toggle_queue_visibility(self):
        visible = not self.queue_panel.isVisible()
        self.queue_panel.setVisible(visible)
        self.toggle_queue_button.setText("Hide Queue" if visible else "Show Queue")
        self._resize_to_contents()

    def _toggle_progress_visibility(self):
        visible = not self.progress_panel.isVisible()
        self.progress_panel.setVisible(visible)
        self.toggle_progress_button.setText("Hide Progress" if visible else "Show Progress")
        self._resize_to_contents()
