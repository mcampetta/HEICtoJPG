from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os


@dataclass
class AppSettings:
    """Application settings with persistence."""

    # Conversion settings
    jpg_quality: int = 90
    preserve_exif: bool = True
    delete_source_on_success: bool = True

    # Performance settings
    max_workers: int = None  # None = auto-detect optimal
    batch_size: int = 10000

    # UI settings
    window_width: int = 900
    window_height: int = 700
    show_preview: bool = True
    preview_limit: int = 100
    operator_mode: bool = True  # Matrix rain + extra effects
    use_custom_output_dir: bool = False
    custom_output_dir: str = ""
    preserve_folder_structure: bool = True
    enable_context_menu: bool = False

    # Logging settings
    log_level: str = "INFO"
    keep_log_days: int = 30

    def __post_init__(self):
        """Set defaults for None values."""
        if self.max_workers is None:
            self.max_workers = min(32, (os.cpu_count() or 4) * 2)

        # Validate settings
        if not 0 <= self.jpg_quality <= 100:
            self.jpg_quality = 85
        if self.max_workers < 1:
            self.max_workers = 4
        if self.batch_size < 100:
            self.batch_size = 10000

    @classmethod
    def get_settings_path(cls) -> Path:
        """Get the path to the settings file."""
        # Store in user's app data directory
        if os.name == 'nt':  # Windows
            app_data = Path(os.environ.get('APPDATA', Path.home()))
            settings_dir = app_data / 'HEICtoJPG'
        else:  # Unix-like
            settings_dir = Path.home() / '.config' / 'HEICtoJPG'

        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / 'settings.json'

    @classmethod
    def load(cls) -> 'AppSettings':
        """Load settings from file, or create defaults."""
        settings_path = cls.get_settings_path()

        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                # If settings file is corrupted, return defaults
                pass

        return cls()

    def save(self) -> None:
        """Save settings to file."""
        settings_path = self.get_settings_path()

        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save settings: {e}")

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return asdict(self)
