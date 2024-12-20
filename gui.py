import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QGridLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import time
from datetime import datetime

class CameraThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    save_completed_signal = pyqtSignal()  # 新增保存完成信号
    
    def __init__(self, device_path, resolution=(640, 480)):
        super().__init__()
        self.device_path = device_path
        self.resolution = resolution
        self.running = True
        self.save_flag = False
        self.cap = None
        
    def change_resolution(self, width, height):
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            # 丢弃几帧以确保分辨率已经改变
            for _ in range(5):
                self.cap.read()
    
    def run(self):
        self.cap = cv2.VideoCapture(self.device_path)
        self.change_resolution(self.resolution[0], self.resolution[1])
        
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_signal.emit(frame)
                if self.save_flag:
                    # 切换到高分辨率
                    self.change_resolution(1280, 720)
                    # 等待几帧以确保获得高分辨率图像
                    for _ in range(5):
                        ret, frame = self.cap.read()
                    
                    if ret:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"camera_{self.device_path.split('/')[-1]}_{timestamp}.jpg"
                        cv2.imwrite(filename, frame)
                    
                    # 切换回预览分辨率
                    self.change_resolution(640, 480)
                    self.save_flag = False
                    self.save_completed_signal.emit()
                    
        if self.cap is not None:
            self.cap.release()
        
    def stop(self):
        self.running = False
        
    def save_frame(self):
        self.save_flag = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Camera Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QGridLayout()
        main_widget.setLayout(layout)
        
        # Create camera displays
        self.displays = []
        self.camera_threads = []
        self.save_count = 0  # 用于跟踪保存完成的相机数量
        camera_devices = ['/dev/video0', '/dev/video2', '/dev/video4', 
                         '/dev/video6', '/dev/video8', '/dev/video10']
        
        for i in range(6):
            # Create display label
            display = QLabel()
            display.setMinimumSize(400, 300)
            display.setAlignment(Qt.AlignCenter)
            display.setStyleSheet("border: 1px solid black")
            self.displays.append(display)
            layout.addWidget(display, i // 3, i % 3)
            
            # Create and start camera thread
            thread = CameraThread(camera_devices[i])
            thread.frame_signal.connect(lambda frame, display=display: 
                                      self.update_frame(frame, display))
            thread.save_completed_signal.connect(self.on_save_completed)
            self.camera_threads.append(thread)
            thread.start()
        
        # Add save button
        self.save_button = QPushButton("Save All Frames")
        self.save_button.clicked.connect(self.save_all_frames)
        layout.addWidget(self.save_button, 2, 1)
        
    def update_frame(self, frame, display):
        # Scale frame for display while preserving aspect ratio
        h, w = frame.shape[:2]
        display_w = display.width()
        display_h = display.height()
        scaling = min(display_w/w, display_h/h)
        new_w = int(w * scaling)
        new_h = int(h * scaling)
        
        # Convert frame to QImage for display
        scaled_frame = cv2.resize(frame, (new_w, new_h))
        rgb_frame = cv2.cvtColor(scaled_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        display.setPixmap(QPixmap.fromImage(qt_image))
        
    def save_all_frames(self):
        self.save_button.setEnabled(False)  # 禁用保存按钮
        self.save_count = 0
        for thread in self.camera_threads:
            thread.save_flag = True
    
    def on_save_completed(self):
        self.save_count += 1
        if self.save_count >= len(self.camera_threads):
            self.save_button.setEnabled(True)  # 重新启用保存按钮
            
    def closeEvent(self, event):
        # Clean up resources
        for thread in self.camera_threads:
            thread.stop()
            thread.wait()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())