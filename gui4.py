import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap
import time
from datetime import datetime
import subprocess
from threading import Event, Thread

class CameraThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    save_completed_signal = pyqtSignal()
    ready_signal = pyqtSignal()
    
    def __init__(self, device_path, is_preview=False, resolution=(320, 240)):
        super().__init__()
        self.device_path = device_path
        self.resolution = resolution
        self.running = True
        self.save_flag = False
        self.cap = None
        self.is_preview = is_preview
        self.sync_event = Event()  # 用于同步拍照
        self.ready_event = Event()  # 用于指示相机就绪
        
    def setup_camera_parameters(self):
        """设置相机参数"""
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
            try:
                subprocess.run([
                    'v4l2-ctl',
                    '-d', self.device_path,
                    '-c', 'white_balance_temperature_auto=1',
                    '-c', 'exposure_auto=3',
                ])
            except Exception as e:
                print(f"v4l2-ctl error for {self.device_path}: {e}")
    
    def init_camera(self):
        """初始化相机"""
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.device_path)
            self.change_resolution(self.resolution[0], self.resolution[1])
            self.setup_camera_parameters()
    
    def release_camera(self):
        """释放相机"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def change_resolution(self, width, height):
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            for _ in range(5):
                self.cap.read()
    
    def prepare_for_capture(self):
        """准备拍照"""
        if not self.is_preview:
            self.init_camera()
        self.change_resolution(1280, 720)
        
        # 读取几帧以确保画面稳定
        for _ in range(5):
            ret, frame = self.cap.read()
            
        self.ready_event.set()
        self.ready_signal.emit()
        
        # 等待同步信号
        self.sync_event.wait()
        self.sync_event.clear()
    
    def capture_single_frame(self):
        """在单独线程中执行拍照"""
        def capture_thread():
            self.prepare_for_capture()
            
            ret, frame = self.cap.read()
            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"camera_{self.device_path.split('/')[-1]}_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
            
            if not self.is_preview:
                self.release_camera()
            else:
                self.change_resolution(320, 240)
                self.setup_camera_parameters()
            
            self.save_completed_signal.emit()
            
        Thread(target=capture_thread).start()
    
    def run(self):
        if self.is_preview:
            # 预览相机保持运行状态
            self.init_camera()
            while self.running:
                if self.save_flag:
                    self.capture_single_frame()
                    self.save_flag = False
                else:
                    ret, frame = self.cap.read()
                    if ret:
                        self.frame_signal.emit(frame)
            self.release_camera()
        else:
            # 非预览相机只在需要时初始化和运行
            while self.running:
                if self.save_flag:
                    self.capture_single_frame()
                    self.save_flag = False
                time.sleep(0.1)
            
    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # 单个预览显示
        self.display = QLabel()
        self.display.setMinimumSize(640, 480)
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setStyleSheet("border: 1px solid black")
        layout.addWidget(self.display)
        
        self.camera_threads = []
        self.save_count = 0
        self.ready_count = 0
        camera_devices = ['/dev/video0', '/dev/video2', '/dev/video4', 
                         '/dev/video6', '/dev/video8', '/dev/video10']
        
        # 设置所有相机的初始参数
        for device in camera_devices:
            try:
                subprocess.run([
                    'v4l2-ctl',
                    '-d', device,
                    '--set-fmt-video=width=320,height=240,pixelformat=YUYV',
                    '--set-parm=2'
                ])
            except Exception as e:
                print(f"Error setting up camera {device}: {e}")
        
        # 初始化所有相机线程
        for i, device in enumerate(camera_devices):
            is_preview = (i == 0)
            thread = CameraThread(device, is_preview=is_preview)
            
            if is_preview:
                thread.frame_signal.connect(self.update_frame)
            thread.save_completed_signal.connect(self.on_save_completed)
            thread.ready_signal.connect(self.on_camera_ready)
            
            self.camera_threads.append(thread)
            thread.start()
        
        self.save_button = QPushButton("Capture All Cameras")
        self.save_button.clicked.connect(self.save_all_frames)
        layout.addWidget(self.save_button)
        
    def update_frame(self, frame):
        h, w = frame.shape[:2]
        display_w = self.display.width()
        display_h = self.display.height()
        scaling = min(display_w/w, display_h/h)
        new_w = int(w * scaling)
        new_h = int(h * scaling)
        
        scaled_frame = cv2.resize(frame, (new_w, new_h))
        rgb_frame = cv2.cvtColor(scaled_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.display.setPixmap(QPixmap.fromImage(qt_image))
    
    def on_camera_ready(self):
        """当一个相机准备好拍照时调用"""
        self.ready_count += 1
        if self.ready_count >= len(self.camera_threads):
            # 所有相机都准备好了，发送同步信号
            for thread in self.camera_threads:
                thread.sync_event.set()
            self.ready_count = 0
        
    def save_all_frames(self):
        self.save_button.setEnabled(False)
        self.save_count = 0
        self.ready_count = 0
        for thread in self.camera_threads:
            thread.save_flag = True
            
    def on_save_completed(self):
        self.save_count += 1
        if self.save_count >= len(self.camera_threads):
            self.save_button.setEnabled(True)
            self.save_count = 0
            
    def closeEvent(self, event):
        for thread in self.camera_threads:
            thread.stop()
            thread.wait()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())