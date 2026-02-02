from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator, Dict
from collections import defaultdict
import logging

from src.core.converter import HEICConverter

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Results from scanning a directory for HEIC files."""

    root_path: Path
    heic_files: list[Path] = field(default_factory=list)
    total_files_scanned: int = 0
    total_directories_scanned: int = 0
    heic_by_directory: Dict[Path, int] = field(default_factory=lambda: defaultdict(int))
    total_size_bytes: int = 0
    scan_errors: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def heic_count(self) -> int:
        """Get total number of HEIC files found."""
        return len(self.heic_files)

    @property
    def total_size_mb(self) -> float:
        """Get total size of HEIC files in MB."""
        return self.total_size_bytes / (1024 * 1024)

    def total_size_human(self) -> str:
        """Get total size in a human-readable unit."""
        size = float(self.total_size_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"

    @property
    def directories_with_heic(self) -> int:
        """Get count of directories containing HEIC files."""
        return len(self.heic_by_directory)

    def get_summary(self) -> str:
        """Get a human-readable summary of the scan results."""
        summary_lines = [
            f"Scan Summary for: {self.root_path}",
            f"  HEIC files found: {self.heic_count:,}",
            f"  Total files scanned: {self.total_files_scanned:,}",
            f"  Total directories: {self.total_directories_scanned:,}",
            f"  Directories with HEIC: {self.directories_with_heic}",
            f"  Total size: {self.total_size_mb:.2f} MB",
        ]

        if self.scan_errors:
            summary_lines.append(f"  Scan errors: {len(self.scan_errors)}")

        return "\n".join(summary_lines)


class FileScanner:
    """Scans directories for HEIC files."""

    HEIC_EXTENSIONS = {'.heic', '.heif'}

    @classmethod
    def scan_directory(cls, directory: Path, progress_callback=None) -> ScanResult:
        """
        Recursively scan a directory for HEIC files.

        Args:
            directory: Root directory to scan
            progress_callback: Optional callback function(current_file, files_scanned)

        Returns:
            ScanResult with statistics and file list
        """
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            raise NotADirectoryError(f"Not a directory: {directory}")

        logger.info(f"Starting scan of: {directory}")

        result = ScanResult(root_path=directory)

        try:
            # Walk through directory tree
            for item in directory.rglob('*'):
                try:
                    if item.is_file():
                        result.total_files_scanned += 1

                        # Check if it's a HEIC file
                        if item.suffix.lower() in cls.HEIC_EXTENSIONS:
                            result.heic_files.append(item)
                            result.heic_by_directory[item.parent] += 1

                            # Add file size
                            try:
                                result.total_size_bytes += item.stat().st_size
                            except OSError as e:
                                logger.warning(f"Could not get size for {item}: {e}")

                        # Call progress callback if provided
                        if progress_callback and result.total_files_scanned % 100 == 0:
                            progress_callback(item, result.total_files_scanned)

                    elif item.is_dir():
                        result.total_directories_scanned += 1

                except (PermissionError, OSError) as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    result.scan_errors.append((item, error_msg))
                    logger.warning(f"Error accessing {item}: {error_msg}")
                    continue

        except Exception as e:
            logger.error(f"Unexpected error during scan: {e}")
            raise

        logger.info(result.get_summary())

        return result

    @classmethod
    def scan_directory_generator(cls, directory: Path) -> Iterator[tuple[Path, ScanResult]]:
        """
        Generator that yields HEIC files as they are found.
        Useful for processing large directories without loading all paths into memory.

        Args:
            directory: Root directory to scan

        Yields:
            Tuple of (heic_file_path, partial_scan_result)
        """
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Invalid directory: {directory}")

        result = ScanResult(root_path=directory)

        try:
            for item in directory.rglob('*'):
                try:
                    if item.is_file():
                        result.total_files_scanned += 1

                        if item.suffix.lower() in cls.HEIC_EXTENSIONS:
                            result.heic_by_directory[item.parent] += 1

                            try:
                                file_size = item.stat().st_size
                                result.total_size_bytes += file_size
                            except OSError:
                                pass

                            # Yield this file immediately
                            yield (item, result)

                    elif item.is_dir():
                        result.total_directories_scanned += 1

                except (PermissionError, OSError) as e:
                    result.scan_errors.append((item, str(e)))
                    continue

        except Exception as e:
            logger.error(f"Error in generator scan: {e}")
            raise

    @staticmethod
    def get_directory_breakdown(scan_result: ScanResult, top_n: int = 10) -> list[tuple[Path, int]]:
        """
        Get the top N directories by HEIC file count.

        Args:
            scan_result: ScanResult from scan_directory
            top_n: Number of top directories to return

        Returns:
            List of (directory_path, heic_count) tuples, sorted by count descending
        """
        sorted_dirs = sorted(
            scan_result.heic_by_directory.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_dirs[:top_n]

    @staticmethod
    def estimate_output_size(scan_result: ScanResult, quality: int = 85) -> float:
        """
        Estimate output size in MB based on compression quality.

        Args:
            scan_result: ScanResult from scan_directory
            quality: JPG quality (0-100)

        Returns:
            Estimated output size in MB
        """
        # Rough estimation: JPG is typically 30-70% of HEIC size depending on quality
        # Quality 85 ≈ 50% compression ratio
        compression_factor = 0.3 + (quality / 100) * 0.4

        return scan_result.total_size_mb * compression_factor
