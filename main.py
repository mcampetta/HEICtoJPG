import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.main_window import MainWindow
from src.models.app_settings import AppSettings
from src.utils.logger import LoggerSetup


def main():
    """Main application entry point."""
    # Set up logging
    LoggerSetup.setup(log_level="INFO")

    # Load application settings
    settings = AppSettings.load()

    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("HEIC to JPG Converter")
    app.setOrganizationName("HEICtoJPG")

    # Check for initial folder argument
    initial_folder = None
    if len(sys.argv) > 1:
        arg_path = Path(sys.argv[1]).expanduser()
        if arg_path.exists() and arg_path.is_dir():
            initial_folder = arg_path

    # Create and show main window
    window = MainWindow(settings, initial_folder=initial_folder)
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
