from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class ConversionResult:
    """Represents the result of a HEIC to JPG conversion."""

    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    error: Optional[str] = None
    file_size_before: Optional[int] = None  # bytes
    file_size_after: Optional[int] = None  # bytes
    conversion_time: Optional[float] = None  # seconds
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if not isinstance(self.input_path, Path):
            self.input_path = Path(self.input_path)
        if self.output_path and not isinstance(self.output_path, Path):
            self.output_path = Path(self.output_path)

    @property
    def compression_ratio(self) -> Optional[float]:
        """Calculate compression ratio (0-1), if applicable."""
        if self.success and self.file_size_before and self.file_size_after:
            return self.file_size_after / self.file_size_before
        return None

    @property
    def size_saved_mb(self) -> Optional[float]:
        """Calculate space saved in MB, if applicable."""
        if self.success and self.file_size_before and self.file_size_after:
            return (self.file_size_before - self.file_size_after) / (1024 * 1024)
        return None

    @property
    def input_filename(self) -> str:
        """Get the input filename."""
        return self.input_path.name

    @property
    def output_filename(self) -> Optional[str]:
        """Get the output filename."""
        return self.output_path.name if self.output_path else None

    def to_dict(self) -> dict:
        """Convert result to dictionary for logging/export."""
        return {
            'success': self.success,
            'input_path': str(self.input_path),
            'output_path': str(self.output_path) if self.output_path else None,
            'error': self.error,
            'file_size_before_bytes': self.file_size_before,
            'file_size_after_bytes': self.file_size_after,
            'compression_ratio': self.compression_ratio,
            'size_saved_mb': self.size_saved_mb,
            'conversion_time_seconds': self.conversion_time,
            'timestamp': self.timestamp.isoformat()
        }
