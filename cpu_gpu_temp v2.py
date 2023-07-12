import sys
import time
import cpuinfo
import wmi
import GPUtil
import pythoncom
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QAction

class TemperatureThread(QThread):
    temperature_signal = pyqtSignal(float, float)
    
    def run(self):
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        while True:
            try:
                # Get CPU temperature using wmi
                w = wmi.WMI(namespace="root\OpenHardwareMonitor")
                temperature_infos = w.Sensor()
                cpu_temperatures = [x for x in temperature_infos if x.SensorType==u'Temperature' and 'CPU' in x.Name]

                if len(cpu_temperatures) == 0:
                    cpu_temperature = None
                else:
                    temperature = cpu_temperatures[0].Value
                    cpu_temperature = float(temperature)

                # Get GPU temperature using GPUtil
                gpu = GPUtil.getGPUs()[0]
                gpu_temperature = gpu.temperature

                # Emit signal with temperature values
                self.temperature_signal.emit(cpu_temperature, gpu_temperature)
                
            except Exception as e:
                print(f"Error retrieving temperatures: {e}")
                
            time.sleep(1)
        
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # Set window attributes
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set font for labels
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        
        # Create labels for CPU and GPU temperature
        self.cpu_label = QLabel(self)
        self.cpu_label.setText("CPU: ")
        self.cpu_label.setFont(font)
        self.cpu_label.setStyleSheet("color: #c90f02;")
        
        self.gpu_label = QLabel(self)
        self.gpu_label.setText("GPU: ")
        self.gpu_label.setFont(font)
        self.gpu_label.setStyleSheet("color: #c90f02;")
        
        # Create a layout and add the labels to it
        layout = QVBoxLayout()
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.gpu_label)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        # Set up temperature thread to update the labels
        self.temperature_thread = TemperatureThread()
        self.temperature_thread.temperature_signal.connect(self.update_temperature)
        self.temperature_thread.start()
        
        # Initialize variables for window dragging
        self.dragging = False
        self.offset = None

       # Set the initial position of the window to the top right corner of the screen
        desktop = QApplication.desktop()
        x = 2440#desktop.width() - 100
        y = 0
        self.move(x, y)
        
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

    def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Set the pen color and style for the box
            pen_color = QColor(0, 0, 0, 150)  # Red color with alpha value (transparency) 0,0,0 is color 150 is transparency
            pen_width = 2 # changes border thickness
            pen = painter.pen()
            pen.setWidth(pen_width)
            pen.setColor(pen_color)
            painter.setPen(pen)

            # Set the brush color and style for the box
            brush_color = QColor(255, 0, 0, 2)  # Red color with alpha value (transparency) 255,0,0 is color 2 is transparency
            brush = QBrush(brush_color)
            painter.setBrush(brush)

            # Draw the box around the window
            rect = self.rect().adjusted(pen_width, pen_width, -pen_width, -pen_width)
            painter.drawRect(rect)


    def update_temperature(self, cpu_temperature, gpu_temperature):
        # Update CPU label
        if cpu_temperature is None:
            self.cpu_label.setText("CPU Temperature: Not Available")
        else:
            self.cpu_label.setText(f"CPU: {cpu_temperature}°C")
        
        # Update GPU label
        self.gpu_label.setText(f"GPU: {gpu_temperature}°C")
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Set dark mode color palette
    dark_palette = app.palette()
    dark_palette.setColor(dark_palette.Window, Qt.black)
    dark_palette.setColor(dark_palette.WindowText, Qt.white)
    dark_palette.setColor(dark_palette.ToolTipBase, Qt.white)
    dark_palette.setColor(dark_palette.ToolTipText, Qt.white)
    dark_palette.setColor(dark_palette.Text, Qt.white)
    dark_palette.setColor(dark_palette.Button, Qt.darkGray)
    dark_palette.setColor(dark_palette.ButtonText, Qt.white)
    dark_palette.setColor(dark_palette.BrightText, Qt.red)
    dark_palette.setColor(dark_palette.Link, Qt.blue)
    dark_palette.setColor(dark_palette.Highlight, Qt.blue)
    dark_palette.setColor(dark_palette.HighlightedText, Qt.white)
    app.setPalette(dark_palette)
    
    # Set application font
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

