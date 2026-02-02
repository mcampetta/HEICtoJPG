import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


class LoggerSetup:
    """Configure application logging."""

    _initialized = False

    @classmethod
    def setup(cls, log_dir: Path = None, log_level: str = "INFO") -> None:
        """
        Set up application logging with file and console handlers.

        Args:
            log_dir: Directory for log files (default: ./logs)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if cls._initialized:
            return

        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Clear any existing handlers
        logger.handlers.clear()

        # Format for log messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Main application log file (rotating, 10MB max, keep 5 backups)
        app_log_path = log_dir / "app.log"
        file_handler = RotatingFileHandler(
            app_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Conversion errors log (failures only, rotating)
        error_log_path = log_dir / "conversion_errors.log"
        error_handler = RotatingFileHandler(
            error_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

        cls._initialized = True

        logger.info("Logging system initialized")
        logger.info(f"Log directory: {log_dir.absolute()}")

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a logger instance for a module.

        Args:
            name: Usually __name__ from the calling module

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)


def create_session_log(log_dir: Path, batch_id: str, results: list) -> Path:
    """
    Create a detailed JSON log file for a conversion session.

    Args:
        log_dir: Directory for log files
        batch_id: Unique batch identifier
        results: List of ConversionResult objects

    Returns:
        Path to the created log file
    """
    import json

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = log_dir / f"session_{batch_id}_{timestamp}.json"

    # Summary statistics
    total = len(results)
    successes = sum(1 for r in results if r.success)
    failures = total - successes

    total_size_before = sum(r.file_size_before or 0 for r in results if r.success)
    total_size_after = sum(r.file_size_after or 0 for r in results if r.success)
    total_saved = total_size_before - total_size_after

    total_time = sum(r.conversion_time or 0 for r in results if r.conversion_time)

    session_data = {
        'batch_id': batch_id,
        'timestamp': timestamp,
        'summary': {
            'total_files': total,
            'successful': successes,
            'failed': failures,
            'success_rate': f"{(successes / total * 100):.2f}%" if total > 0 else "0%",
            'total_size_before_mb': f"{total_size_before / (1024 * 1024):.2f}",
            'total_size_after_mb': f"{total_size_after / (1024 * 1024):.2f}",
            'total_saved_mb': f"{total_saved / (1024 * 1024):.2f}",
            'total_time_seconds': f"{total_time:.2f}",
            'avg_time_per_file_ms': f"{(total_time / total * 1000):.2f}" if total > 0 else "0"
        },
        'results': [r.to_dict() for r in results]
    }

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    return log_path
