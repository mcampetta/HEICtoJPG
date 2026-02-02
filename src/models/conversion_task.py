from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ConversionTask:
    """Represents a single HEIC to JPG conversion task."""

    input_path: Path
    output_path: Path
    quality: int = 85
    delete_source: bool = False
    preserve_exif: bool = True

    def __post_init__(self):
        """Validate task parameters."""
        if not isinstance(self.input_path, Path):
            self.input_path = Path(self.input_path)
        if not isinstance(self.output_path, Path):
            self.output_path = Path(self.output_path)

        if not 0 <= self.quality <= 100:
            raise ValueError(f"Quality must be between 0 and 100, got {self.quality}")

    @property
    def input_filename(self) -> str:
        """Get the input filename."""
        return self.input_path.name

    @property
    def output_filename(self) -> str:
        """Get the output filename."""
        return self.output_path.name

    @property
    def file_size_mb(self) -> Optional[float]:
        """Get input file size in MB, if file exists."""
        try:
            return self.input_path.stat().st_size / (1024 * 1024)
        except (OSError, FileNotFoundError):
            return None
