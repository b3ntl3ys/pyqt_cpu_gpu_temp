import sys
import time
import wmi
import GPUtil
import pythoncom
import pywintypes
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont, QPen
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QAction


# ---------------- TEMPERATURE THREAD ----------------
class TemperatureThread(QThread):
    temperature_signal = pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        pythoncom.CoInitialize()

        try:
            w = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
        except:
            w = None

        while self.running:
            cpu_temperature = None
            gpu_temperature = None

            try:
                # CPU
                if w:
                    sensors = w.Sensor()
                    cpu_temps = []

                    for s in sensors:
                        if s.SensorType != 'Temperature':
                            continue

                        name = s.Name.lower()

                        if 'gpu' in name:
                            continue

                        # prioritize real CPU sensors
                        if any(x in name for x in ['cpu', 'core', 'package']):
                            cpu_temps.append(s.Value)

                    # fallback if nothing matched
                    if not cpu_temps:
                        cpu_temps = [
                            s.Value for s in sensors
                            if s.SensorType == 'Temperature' and 'gpu' not in s.Name.lower()
                        ]

                    # ✅ THIS IS WHAT YOU WERE MISSING
                    if cpu_temps:
                        cpu_temperature = sum(cpu_temps) / len(cpu_temps)

                # GPU
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_temperature = gpus[0].temperature
                except:
                    pass

            except Exception as e:
                print(f"Error retrieving temperatures: {e}")

            self.temperature_signal.emit(cpu_temperature, gpu_temperature)
            time.sleep(1)

    def stop(self):
        self.running = False


# ---------------- MAIN WINDOW ----------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.cpu_temp = None
        self.gpu_temp = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        font = QFont("Segoe UI", 12, QFont.Bold)

        self.cpu_label = QLabel("CPU: --", self)
        self.cpu_label.setFont(font)

        self.gpu_label = QLabel("GPU: --", self)
        self.gpu_label.setFont(font)

        layout = QVBoxLayout()
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.gpu_label)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        self.thread = TemperatureThread()
        self.thread.temperature_signal.connect(self.update_temperature)
        self.thread.start()

        self.dragging = False
        self.offset = None

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 200, 0)

    # ---------------- COLOR LOGIC ----------------
    def get_color(self, temp):
        if temp is None:
            return QColor(200, 200, 200)

        if temp < 50:
            return QColor(0, 255, 100)     # green
        elif temp < 80:
            return QColor(255, 170, 0)     # orange
        else:
            return QColor(255, 50, 50)     # red

    def is_overheating(self):
        return (
            (self.cpu_temp and self.cpu_temp > 85) or
            (self.gpu_temp and self.gpu_temp > 85)
        )

    # ---------------- UPDATE UI ----------------
    def update_temperature(self, cpu, gpu):
        self.cpu_temp = cpu
        self.gpu_temp = gpu

        # CPU
        if cpu is None:
            self.cpu_label.setText("CPU: N/A")
        else:
            self.cpu_label.setText(f"CPU: {cpu:.1f}°C")

        # GPU
        if gpu is None:
            self.gpu_label.setText("GPU: N/A")
        else:
            self.gpu_label.setText(f"GPU: {gpu:.1f}°C")

        # Apply colors
        self.cpu_label.setStyleSheet(f"color: {self.get_color(cpu).name()};")
        self.gpu_label.setStyleSheet(f"color: {self.get_color(gpu).name()};")

        self.update()  # repaint for glow

    # ---------------- GLOW EFFECT ----------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        if self.is_overheating():
            # Glow effect
            for i in range(8, 0, -1):
                alpha = 20 + i * 15
                pen = QPen(QColor(255, 0, 0, alpha), i)
                painter.setPen(pen)
                painter.drawRoundedRect(rect, 12, 12)
        else:
            # Normal border
            pen = QPen(QColor(0, 0, 0, 150), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 0, 0, 10)))
            painter.drawRoundedRect(rect, 12, 12)

    # ---------------- DRAG + MENU ----------------
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            close_action = QAction("Close", self)
            close_action.triggered.connect(self.close)
            menu.addAction(close_action)
            menu.exec_(self.mapToGlobal(event.pos()))
        elif event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def closeEvent(self, event):
        self.thread.stop()
        self.thread.wait()
        event.accept()


# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
