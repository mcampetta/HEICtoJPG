from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QFont
import random


class MatrixRainWidget(QWidget):
    """
    Matrix rain animation widget for Operator Mode.
    Displays falling characters in a header strip.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMinimumWidth(400)

        # Matrix characters (mix of katakana, numbers, and symbols)
        self.chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"

        # Columns of falling characters
        self.columns = []
        self.column_count = 0

        # Animation settings
        self.speed = 50  # ms per frame
        self.enabled = False

        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)

        # Font
        self.font = QFont("Consolas", 12)

    def showEvent(self, event):
        """Start animation when widget is shown."""
        super().showEvent(event)
        self.initialize_columns()
        if self.enabled:
            self.start()

    def hideEvent(self, event):
        """Stop animation when widget is hidden."""
        super().hideEvent(event)
        self.stop()

    def resizeEvent(self, event):
        """Reinitialize columns when widget is resized."""
        super().resizeEvent(event)
        self.initialize_columns()

    def initialize_columns(self):
        """Initialize or reinitialize the columns."""
        if self.width() == 0:
            return

        # Calculate number of columns based on width
        char_width = 14  # Approximate width of each character
        self.column_count = max(1, self.width() // char_width)

        # Create columns with random starting positions
        self.columns = []
        for i in range(self.column_count):
            column = {
                'x': i * char_width,
                'y': random.randint(-20, 0),  # Start above visible area
                'speed': random.uniform(0.5, 2.0),  # Random fall speed
                'chars': [random.choice(self.chars) for _ in range(10)],  # Trail of chars
                'brightness': [1.0 - (j * 0.1) for j in range(10)]  # Fade trail
            }
            self.columns.append(column)

    def start(self):
        """Start the animation."""
        self.enabled = True
        if not self.timer.isActive():
            self.timer.start(self.speed)

    def stop(self):
        """Stop the animation."""
        self.enabled = False
        self.timer.stop()

    def update_animation(self):
        """Update animation state."""
        for column in self.columns:
            # Move column down
            column['y'] += column['speed']

            # Reset to top when it goes off screen
            if column['y'] > self.height() + 100:
                column['y'] = -20
                column['chars'] = [random.choice(self.chars) for _ in range(10)]

            # Occasionally change the first character for sparkle effect
            if random.random() < 0.3:
                column['chars'][0] = random.choice(self.chars)

        self.update()

    def paintEvent(self, event):
        """Paint the matrix rain effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(5, 7, 10, 255))

        # Draw matrix rain
        painter.setFont(self.font)

        for column in self.columns:
            for i, char in enumerate(column['chars']):
                y = int(column['y'] - (i * 16))

                # Skip if outside visible area
                if y < -20 or y > self.height():
                    continue

                # Calculate color with fade
                brightness = column['brightness'][i]

                # First character is brightest (white)
                if i == 0:
                    color = QColor(255, 255, 255, int(255 * brightness))
                else:
                    # Trail is green with fade
                    color = QColor(0, 230, 118, int(255 * brightness))

                painter.setPen(color)
                painter.drawText(int(column['x']), y, char)

        painter.end()


class ScanlineOverlay(QWidget):
    """
    Subtle scanline overlay for cyber aesthetic.
    Very low opacity to not interfere with readability.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        """Paint scanlines."""
        painter = QPainter(self)

        # Very subtle scanlines
        painter.setPen(QColor(255, 255, 255, 3))  # Extremely low opacity

        # Draw horizontal lines every 4 pixels
        for y in range(0, self.height(), 4):
            painter.drawLine(0, y, self.width(), y)

        painter.end()
