
![HEICtoJPG](https://github.com/user-attachments/assets/6ab86cdd-c4ad-4312-95a0-4aedc4dbea00)

# HEIC to JPG Converter - Cyber Ops Console

A high-performance, GUI-based batch converter for transforming HEIC images to JPG format. Built for engineers who need to process massive datasets (100k+ images) with speed, reliability, and style.

![Version](https://img.shields.io/badge/version-1.0--alpha2-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-Non--Commercial-blue.svg)

## Features

### Core Functionality
- **Batch Conversion**: Convert entire directories of HEIC images to JPG
- **Multi-Threading**: Parallel processing with optimized worker pool (up to 32 threads)
- **Recursive Scanning**: Automatically finds HEIC files in nested subdirectories
- **Smart File Handling**: Preserves directory structure in output
- **Error Resilience**: Failed conversions don't stop the batch - source files are preserved

### Performance Optimized
- Handles hundreds of thousands of images efficiently
- Memory-conscious processing (chunks of 10,000 files)
- Generator-based file iteration to avoid memory overflow
- Batched UI updates (every 100ms) to maintain responsiveness
- Thread pool automatically sized for optimal I/O performance

### User Experience
- **Drag-and-Drop**: Simply drop a folder to queue conversion
- **Quality Control**: Adjustable JPG quality (0-100%, default 85%)
- **Batch Queue**: Queue multiple folders and process sequentially
- **Progress Tracking**: Real-time stats including speed, ETA, success/failure counts
- **Preview Mode**: View thumbnails of images before conversion
- **Detailed Logging**: Comprehensive logs with separate error log for failures

### Safety Features
- **Safe Deletion**: Source files moved to Recycle Bin (not permanently deleted)
- **Failure Protection**: Never deletes source files if conversion fails
- **EXIF Preservation**: Maintains metadata (date, location, camera info)
- **Comprehensive Logging**: All operations logged for audit trail

### Matrix/Cyber-Ops Theme
A futuristic console aesthetic that's both visually striking and highly functional:
- **Dark cyberpunk UI** with neon green/cyan accents
- **Glass panel design** with subtle borders and shadows
- **Monospace telemetry displays** for system stats
- **Operator Mode**: Optional matrix rain animation header (toggle ON/OFF)
- **High contrast** for long-duration readability
- **Professional and functional** - style never compromises usability

## Installation

### Requirements
- **Python 3.11+**
- **Windows** (primary target platform)
- **PyQt6** for GUI
- **Pillow + pillow-heif** for image processing

### Setup

1. **Clone or download this repository**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the application**:
```bash
python main.py
```

## Usage

### Basic Workflow

1. **Launch the application**
   ```bash
   python main.py
   ```

2. **Select folder containing HEIC files**
   - Drag and drop a folder onto the drop zone, OR
   - Click the drop zone to browse for a folder

3. **Choose output location** (optional)
   - **Default**: JPG files created in same directory as source HEIC files
   - **Custom**: Check "Use custom output directory" and browse to select a destination folder
   - **Structure preserved**: Subdirectories are recreated in custom output folder

4. **Review scan results**
   - Application will scan recursively and show:
     - Number of HEIC files found
     - Total files scanned
     - Total size
     - Directories containing HEIC files

5. **Configure settings** (optional)
   - **JPG Quality**: Adjust slider (0-100%, default 90%)
   - **Delete Source**: Enable to move source files to Recycle Bin after successful conversion
   - **Worker Threads**: Adjust thread count (default: auto-detected optimal)
   - **Preserve EXIF**: Keep metadata (default: ON)
   - **Operator Mode**: Matrix rain effects (default: ON)

6. **Start conversion**
   - Click "⚡ RUN CONVERSION" button
   - Monitor progress in real-time:
     - Progress bar with percentage
     - Speed in images/sec
     - Estimated time remaining
     - Success/failure counts
     - Current file being processed

7. **Manage queue** (optional)
   - Add more folders while processing
   - Pause/Resume conversion
   - Stop conversion (graceful shutdown)
   - Clear completed jobs from queue

8. **Review results**
   - Check completion summary dialog
   - View logs for any failures
   - Click "View Logs" to open log directory

### Settings Explained

#### Output Directory
- **Default (unchecked)**: JPG files created in same directories as source HEIC files
  ```
  Input:  C:\Photos\Vacation\IMG_001.heic
  Output: C:\Photos\Vacation\IMG_001.jpg
  ```
- **Custom (checked)**: Select a destination folder - subdirectory structure is preserved
  ```
  Input:  C:\Photos\Vacation\2024\Summer\IMG_001.heic
  Output: D:\Converted\2024\Summer\IMG_001.jpg
  ```
- **Use case**: Perfect for testing without modifying original data locations

#### JPG Quality
- **0-49%**: Low quality, small file size (not recommended)
- **50-69%**: Medium quality, balanced
- **70-89%**: Good quality
- **90-94%**: High quality (default: 90%)
- **95-100%**: Maximum quality, largest files

#### Worker Threads
- **Default**: Auto-detected optimal (min(32, CPU_count * 2))
- **Higher values**: Faster for large datasets (I/O bound)
- **Lower values**: Reduce system load

#### Delete Source Files
- **OFF** (default): Original HEIC files are kept
- **ON**: Original files moved to Recycle Bin after successful conversion
- **Safe**: Failed conversions NEVER delete source files

#### Operator Mode
- **ON** (default): Matrix rain header animation + extra glow effects
- **OFF**: Clean cyber UI without animations
- **Performance**: No impact on conversion speed

## File Structure

```
HEICtoJPG/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # This file
│
├── src/
│   ├── core/                  # Business logic
│   │   ├── converter.py       # HEIC→JPG conversion
│   │   ├── batch_manager.py   # Batch queue management
│   │   ├── worker_pool.py     # Multi-threaded processing
│   │   └── file_scanner.py    # Directory scanning
│   │
│   ├── models/                # Data structures
│   │   ├── conversion_task.py
│   │   ├── conversion_result.py
│   │   └── app_settings.py
│   │
│   ├── ui/                    # GUI components
│   │   ├── main_window.py     # Main application window
│   │   └── widgets/
│   │       ├── drop_zone.py
│   │       ├── settings_panel.py
│   │       ├── progress_panel.py
│   │       ├── queue_panel.py
│   │       ├── preview_panel.py
│   │       └── matrix_rain.py
│   │
│   └── utils/                 # Utilities
│       ├── logger.py
│       ├── image_utils.py
│       └── file_utils.py
│
├── logs/                      # Log files
│   ├── app.log
│   ├── conversion_errors.log
│   └── session_*.json
│
└── resources/                 # Assets
    ├── styles.qss             # Matrix/Cyber-Ops theme
    └── icons/
```

## Architecture

### Design Pattern
**MVC with Worker Thread Pool**
- **Model**: Business logic (conversion, file operations, batch management)
- **View**: PyQt6 GUI components
- **Controller**: Main window coordinates UI and processing
- **Worker Pool**: Multi-threaded task processing with queue management

### Key Components

#### Converter (`src/core/converter.py`)
- Uses Pillow with pillow-heif for HEIC support
- Handles RGB conversion for JPEG compatibility
- Preserves EXIF metadata
- Robust error handling per file

#### Worker Pool (`src/core/worker_pool.py`)
- ThreadPoolExecutor-based parallel processing
- Pause/resume/stop functionality
- Memory-managed task queuing (max 1000 tasks in memory)
- Thread-safe statistics tracking

#### Batch Manager (`src/core/batch_manager.py`)
- Manages multiple batch jobs
- Queue-based task distribution
- Per-job progress tracking
- Status management (queued, processing, completed, failed)

#### File Scanner (`src/core/file_scanner.py`)
- Recursive directory traversal
- Statistics collection (file counts, sizes, directory breakdown)
- Generator-based scanning for memory efficiency
- Error handling for permission issues

## Performance

### Benchmarks
- **Small dataset** (10 files): ~0.5 seconds
- **Medium dataset** (1,000 files): ~30-60 seconds (depending on hardware)
- **Large dataset** (100,000 files): ~45-90 minutes (depending on hardware)

### Optimization Strategies
1. **Multi-threading**: Optimal thread pool size for I/O-bound operations
2. **Memory management**: Process in chunks, use generators, clear data immediately
3. **UI updates**: Batched every 100ms to avoid UI freezing
4. **Preview loading**: Lazy-loaded thumbnails, limited to first 100

## Logging

### Log Files
- **`logs/app.log`**: General application log (rotating, 10MB max)
- **`logs/conversion_errors.log`**: Failed conversions only (for engineer review)
- **`logs/session_*.json`**: JSON summary of each batch run with statistics

### Log Levels
- **DEBUG**: Detailed processing information
- **INFO**: Conversion starts, completions, batch operations
- **WARNING**: Recoverable errors, skipped files
- **ERROR**: Conversion failures, file I/O errors
- **CRITICAL**: Application-level failures

## Theme Customization

The Matrix/Cyber-Ops theme is defined in `resources/styles.qss` using Qt Style Sheets (QSS). You can customize:

- **Colors**: Modify the color palette variables
- **Fonts**: Change font families and sizes
- **Effects**: Adjust glow effects, borders, shadows
- **Animations**: Modify matrix rain speed and density

To apply changes:
1. Edit `resources/styles.qss`
2. Restart the application (stylesheet loads on startup)

## Troubleshooting

### Common Issues

**Issue**: "No HEIC files found" but folder contains HEIC files
- **Solution**: Check file extensions (.heic or .HEIF)
- **Note**: Files with .jpg or .jpeg extensions are not HEIC files

**Issue**: Don't want to modify original folder structure / testing conversions
- **Solution**: Use custom output directory feature
  1. Check "Use custom output directory" below the drop zone
  2. Browse to select a test/output folder
  3. Subdirectories will be recreated in the output folder
  4. Original files remain untouched in their original location

**Issue**: Conversion fails with "Permission denied"
- **Solution**: Ensure you have read/write permissions for the folder
- **Check**: Run application as administrator if needed
- **Custom output**: Try using a custom output directory with full write permissions

**Issue**: Very slow conversion speed
- **Solution 1**: Increase worker threads in settings
- **Solution 2**: Check if antivirus is scanning files during conversion
- **Solution 3**: Ensure source folder is on a fast drive (SSD preferred)

**Issue**: Out of memory error with very large datasets
- **Solution**: The application is designed to handle this, but if it occurs:
  - Process folders in smaller batches
  - Close other applications to free up RAM

**Issue**: Matrix rain animation is laggy
- **Solution**: Disable Operator Mode in settings
- **Note**: Matrix rain has minimal performance impact on conversion speed

### Getting Help

If you encounter issues:
1. Check the logs in the `logs/` directory
2. Look for errors in `conversion_errors.log`
3. Review session JSON files for detailed statistics

## Technical Details

### Dependencies
- **PyQt6**: Cross-platform GUI framework
- **Pillow**: Image processing library
- **pillow-heif**: HEIC format support for Pillow
- **send2trash**: Safe file deletion (Recycle Bin)
- **psutil**: System resource monitoring

### Supported Formats
- **Input**: .heic, .heif
- **Output**: .jpg (JPEG)

### Thread Safety
- All UI updates use Qt signals/slots
- Worker pool uses thread-safe queues
- Statistics tracking uses threading locks

## License

This project uses the "iOS Backup Manager License" (Non-Commercial Source-Available).
See `LICENSE` for full terms.

## Credits

Built with:
- Python 3.11+
- PyQt6
- Pillow & pillow-heif
- Love for cyberpunk aesthetics

---

**Ready to convert?** Launch the app and drop your first folder!

```bash
python main.py
```

**Need help?** Check the logs or review this README.

**Want more style?** Enable Operator Mode and watch the Matrix rain!
