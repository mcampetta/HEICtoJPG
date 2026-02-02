from PIL import Image
from pillow_heif import register_heif_opener
from pathlib import Path
import time
import logging
from typing import Optional

from src.models.conversion_task import ConversionTask
from src.models.conversion_result import ConversionResult

# Register HEIF opener to enable HEIC support in Pillow
register_heif_opener()

logger = logging.getLogger(__name__)


class HEICConverter:
    """Handles HEIC to JPG conversion."""

    @staticmethod
    def convert(task: ConversionTask) -> ConversionResult:
        """
        Convert a HEIC image to JPG format.

        Args:
            task: ConversionTask with input/output paths and settings

        Returns:
            ConversionResult with success status and metadata
        """
        start_time = time.time()

        try:
            # Validate input file exists
            if not task.input_path.exists():
                raise FileNotFoundError(f"Input file not found: {task.input_path}")

            # Get original file size
            file_size_before = task.input_path.stat().st_size

            # Open and convert image
            with Image.open(task.input_path) as img:
                # Convert to RGB if necessary (JPEG doesn't support transparency)
                if img.mode not in ('RGB', 'L'):
                    logger.debug(f"Converting {img.mode} to RGB for {task.input_filename}")
                    img = img.convert('RGB')

                # Create output directory if it doesn't exist
                task.output_path.parent.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Output directory created/verified: {task.output_path.parent}")

                # Prepare save parameters
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': task.quality,
                    'optimize': True,
                }

                # Preserve EXIF metadata if requested
                if task.preserve_exif and 'exif' in img.info:
                    save_kwargs['exif'] = img.info['exif']

                # Save as JPEG
                img.save(task.output_path, **save_kwargs)

            # Get output file size
            file_size_after = task.output_path.stat().st_size

            # Calculate conversion time
            conversion_time = time.time() - start_time

            logger.info(f"Converted: {task.input_filename} → {task.output_path} "
                       f"({file_size_before / 1024:.1f}KB → {file_size_after / 1024:.1f}KB, "
                       f"{conversion_time:.2f}s)")

            return ConversionResult(
                success=True,
                input_path=task.input_path,
                output_path=task.output_path,
                file_size_before=file_size_before,
                file_size_after=file_size_after,
                conversion_time=conversion_time
            )

        except Exception as e:
            conversion_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"

            logger.error(f"Conversion failed for {task.input_path}: {error_msg}")

            return ConversionResult(
                success=False,
                input_path=task.input_path,
                output_path=None,
                error=error_msg,
                file_size_before=task.file_size_mb * 1024 * 1024 if task.file_size_mb else None,
                conversion_time=conversion_time
            )

    @staticmethod
    def create_output_path(input_path: Path, output_dir: Optional[Path] = None) -> Path:
        """
        Generate output path for a HEIC file.

        Args:
            input_path: Path to input HEIC file
            output_dir: Optional output directory (default: same as input)

        Returns:
            Path for output JPG file
        """
        if output_dir is None:
            output_dir = input_path.parent

        # Change extension to .jpg
        output_filename = input_path.stem + '.jpg'
        return output_dir / output_filename

    @staticmethod
    def is_heic_file(path: Path) -> bool:
        """
        Check if a file is a HEIC image based on extension.

        Args:
            path: Path to check

        Returns:
            True if file has HEIC/HEIF extension
        """
        return path.suffix.lower() in ('.heic', '.heif')

    @staticmethod
    def validate_conversion_possible(input_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that a conversion can be performed.

        Args:
            input_path: Path to input file

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_path.exists():
            return False, f"File not found: {input_path}"

        if not input_path.is_file():
            return False, f"Not a file: {input_path}"

        if not HEICConverter.is_heic_file(input_path):
            return False, f"Not a HEIC file: {input_path}"

        # Check if file is readable
        try:
            with open(input_path, 'rb') as f:
                f.read(1)
        except (PermissionError, OSError) as e:
            return False, f"Cannot read file: {e}"

        return True, None
