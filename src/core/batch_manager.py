from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Iterator
from enum import Enum
import uuid
import logging

from src.models.conversion_task import ConversionTask
from src.models.conversion_result import ConversionResult
from src.core.file_scanner import FileScanner, ScanResult
from src.core.converter import HEICConverter

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Status of a batch job."""
    QUEUED = "queued"
    SCANNING = "scanning"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Represents a batch conversion job for a directory."""

    id: str
    folder_path: Path
    status: BatchStatus = BatchStatus.QUEUED
    output_dir: Optional[Path] = None  # None = same as source

    # Scan results
    scan_result: Optional[ScanResult] = None

    # Progress tracking
    total_files: int = 0
    processed_files: int = 0
    successful: int = 0
    failed: int = 0

    # Conversion settings
    quality: int = 85
    delete_source: bool = False
    preserve_exif: bool = True
    preserve_folder_structure: bool = True

    # Results storage
    results: list[ConversionResult] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as a percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def is_complete(self) -> bool:
        """Check if batch is complete."""
        return self.status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Check if batch is actively processing."""
        return self.status in (BatchStatus.SCANNING, BatchStatus.PROCESSING)

    @property
    def display_name(self) -> str:
        """Get a display name for the batch."""
        return f"{self.folder_path.name} ({self.total_files:,} files)"

    def get_summary(self) -> str:
        """Get a human-readable summary of the batch."""
        return (
            f"Batch: {self.folder_path}\n"
            f"Status: {self.status.value}\n"
            f"Progress: {self.processed_files}/{self.total_files} ({self.progress_percentage:.1f}%)\n"
            f"Successful: {self.successful}\n"
            f"Failed: {self.failed}"
        )


class BatchManager:
    """Manages a queue of batch conversion jobs."""

    def __init__(self):
        self.jobs: list[BatchJob] = []
        self.current_job: Optional[BatchJob] = None

    def add_job(
        self,
        folder_path: Path,
        quality: int = 85,
        delete_source: bool = False,
        preserve_exif: bool = True,
        output_dir: Optional[Path] = None,
        preserve_folder_structure: bool = True
    ) -> BatchJob:
        """
        Add a new batch job to the queue.

        Args:
            folder_path: Path to folder containing HEIC files
            quality: JPG quality (0-100)
            delete_source: Whether to delete source files after successful conversion
            preserve_exif: Whether to preserve EXIF metadata
            output_dir: Optional output directory (None = same as source)

        Returns:
            Created BatchJob
        """
        job = BatchJob(
            id=str(uuid.uuid4()),
            folder_path=folder_path,
            quality=quality,
            delete_source=delete_source,
            preserve_exif=preserve_exif,
            output_dir=output_dir,
            preserve_folder_structure=preserve_folder_structure
        )

        self.jobs.append(job)
        logger.info(f"Added batch job: {job.id} for {folder_path}")

        return job

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the queue.

        Args:
            job_id: ID of job to remove

        Returns:
            True if job was removed, False if not found
        """
        original_count = len(self.jobs)
        self.jobs = [j for j in self.jobs if j.id != job_id]

        removed = len(self.jobs) < original_count
        if removed:
            logger.info(f"Removed batch job: {job_id}")

        return removed

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get a job by ID."""
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def get_next_job(self) -> Optional[BatchJob]:
        """
        Get the next queued job.

        Returns:
            Next BatchJob with QUEUED status, or None if no jobs are queued
        """
        for job in self.jobs:
            if job.status == BatchStatus.QUEUED:
                self.current_job = job
                return job
        return None

    def scan_job(self, job: BatchJob, progress_callback=None) -> ScanResult:
        """
        Scan a job's folder for HEIC files.

        Args:
            job: BatchJob to scan
            progress_callback: Optional callback for scan progress

        Returns:
            ScanResult with file list and statistics
        """
        job.status = BatchStatus.SCANNING
        logger.info(f"Scanning job {job.id}: {job.folder_path}")

        scan_result = FileScanner.scan_directory(job.folder_path, progress_callback)

        job.scan_result = scan_result
        job.total_files = scan_result.heic_count
        job.status = BatchStatus.QUEUED

        logger.info(f"Scan complete for job {job.id}: {scan_result.heic_count} HEIC files found")

        return scan_result

    def generate_tasks(self, job: BatchJob) -> Iterator[ConversionTask]:
        """
        Generate conversion tasks for a batch job.

        Args:
            job: BatchJob to generate tasks for

        Yields:
            ConversionTask objects
        """
        if job.scan_result is None:
            raise ValueError(f"Job {job.id} has not been scanned yet")

        # Ensure totals reflect the actual task list
        job.total_files = len(job.scan_result.heic_files)
        logger.info(f"Generating tasks for job {job.id} with output_dir: {job.output_dir} (total_files: {job.total_files})")
        task_count = 0

        for heic_file in job.scan_result.heic_files:
            # Determine output directory
            if job.output_dir:
                if job.preserve_folder_structure:
                    # Preserve subdirectory structure
                    relative_path = heic_file.parent.relative_to(job.folder_path)
                    output_dir = job.output_dir / relative_path
                else:
                    # Flatten into root output directory
                    output_dir = job.output_dir
            else:
                # Same directory as source
                output_dir = heic_file.parent

            output_path = HEICConverter.create_output_path(heic_file, output_dir)

            # Log first few tasks for verification
            if task_count < 3:
                logger.info(f"Task {task_count}: {heic_file} → {output_path}")
            task_count += 1

            yield ConversionTask(
                input_path=heic_file,
                output_path=output_path,
                quality=job.quality,
                delete_source=job.delete_source,
                preserve_exif=job.preserve_exif
            )

    def update_job_progress(self, job: BatchJob, result: ConversionResult) -> None:
        """
        Update job progress with a conversion result.

        Args:
            job: BatchJob to update
            result: ConversionResult from a completed task
        """
        job.processed_files += 1

        if result.success:
            job.successful += 1
        else:
            job.failed += 1

        job.results.append(result)

        # Update status if complete
        if job.processed_files >= job.total_files:
            if job.failed > 0:
                job.status = BatchStatus.COMPLETED  # Still completed even with failures
            else:
                job.status = BatchStatus.COMPLETED

            logger.info(f"Job {job.id} completed: {job.successful} successful, {job.failed} failed")

    def get_queued_jobs(self) -> list[BatchJob]:
        """Get all jobs with QUEUED status."""
        return [j for j in self.jobs if j.status == BatchStatus.QUEUED]

    def get_active_jobs(self) -> list[BatchJob]:
        """Get all active jobs (scanning or processing)."""
        return [j for j in self.jobs if j.is_active]

    def get_completed_jobs(self) -> list[BatchJob]:
        """Get all completed jobs."""
        return [j for j in self.jobs if j.is_complete]

    def get_all_jobs(self) -> list[BatchJob]:
        """Get all jobs."""
        return self.jobs.copy()

    def clear_completed_jobs(self) -> int:
        """
        Remove all completed jobs from the queue.

        Returns:
            Number of jobs removed
        """
        original_count = len(self.jobs)
        self.jobs = [j for j in self.jobs if not j.is_complete]
        removed_count = original_count - len(self.jobs)

        if removed_count > 0:
            logger.info(f"Cleared {removed_count} completed jobs")

        return removed_count

    def clear_all_jobs(self) -> int:
        """
        Remove all jobs from the queue.

        Returns:
            Number of jobs removed
        """
        original_count = len(self.jobs)
        self.jobs.clear()
        removed_count = original_count

        if removed_count > 0:
            logger.info(f"Cleared {removed_count} jobs")

        return removed_count

    def remove_last_job(self) -> Optional[BatchJob]:
        """Remove the most recently added job (if any)."""
        if not self.jobs:
            return None
        job = self.jobs.pop()
        logger.info(f"Removed last batch job: {job.id}")
        return job

    def get_total_stats(self) -> dict:
        """Get aggregated statistics across all jobs."""
        total_files = sum(j.total_files for j in self.jobs)
        processed_files = sum(j.processed_files for j in self.jobs)
        successful = sum(j.successful for j in self.jobs)
        failed = sum(j.failed for j in self.jobs)

        return {
            'total_jobs': len(self.jobs),
            'queued_jobs': len(self.get_queued_jobs()),
            'active_jobs': len(self.get_active_jobs()),
            'completed_jobs': len(self.get_completed_jobs()),
            'total_files': total_files,
            'processed_files': processed_files,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful / processed_files * 100):.1f}%" if processed_files > 0 else "0%"
        }
