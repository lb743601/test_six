import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QGridLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap
import time
from datetime import datetime
import subprocess

# 定义相机分组
CAMERA_GROUPS = [
    ['/dev/video0', '/dev/video2', '/dev/video4'],
    ['/dev/video6', '/dev/video8', '/dev/video10']
]

class CameraThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    save_completed_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, device_path, resolution=(1280, 720)):
        super().__init__()
        self.device_path = device_path
        self.resolution = resolution
        self.running = True
        self.paused = False
        self.save_flag = False
        self.cap = None
        
    def setup_camera_parameters(self):
        """设置相机参数"""
        if self.cap is not None:
            #设置手动曝光
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
            
            #尝试通过v4l2设置参数
            try:
                subprocess.run([
                    'v4l2-ctl',
                    '-d', self.device_path,
                    '-c', 'white_balance_temperature_auto=1',
                    '-c', 'exposure_auto=3',
                ])
            except Exception as e:
                self.error_signal.emit(f"v4l2-ctl error for {self.device_path}: {e}")
    
    def change_resolution(self, width, height):
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            # 丢弃几帧以确保分辨率已经改变
            for _ in range(5):
                self.cap.read()
    
    def pause(self):
        """暂停相机采集"""
        self.paused = True
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def resume(self):
        """恢复相机采集"""
        self.paused = False
    
    def run(self):
        while self.running:
            try:
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                # 如果相机未初始化，进行初始化
                if self.cap is None:
                    self.cap = cv2.VideoCapture(self.device_path)
                    if not self.cap.isOpened():
                        self.error_signal.emit(f"Failed to open camera {self.device_path}")
                        time.sleep(1)
                        continue
                    self.change_resolution(self.resolution[0], self.resolution[1])
                    self.setup_camera_parameters()
                
                ret, frame = self.cap.read()
                if not ret:
                    self.error_signal.emit(f"Failed to read frame from {self.device_path}")
                    if self.cap is not None:
                        self.cap.release()
                        self.cap = None
                    time.sleep(1)
                    continue
                
                self.frame_signal.emit(frame)
                
                if self.save_flag:
                    # 切换到高分辨率
                    self.change_resolution(1280, 720)
                    # 等待几帧以确保获得高分辨率图像
                    time.sleep(0.1)
                    ret, frame = self.cap.read()
                    
                    if ret:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"camera_{self.device_path.split('/')[-1]}_{timestamp}.jpg"
                        cv2.imwrite(filename, frame)
                    
                    self.save_flag = False
                    self.save_completed_signal.emit()
                
            except Exception as e:
                self.error_signal.emit(f"Camera {self.device_path} error: {str(e)}")
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                time.sleep(1)
    
    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            
    def save_frame(self):
        self.save_flag = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Camera Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QGridLayout()
        main_widget.setLayout(layout)
        
        self.displays = []
        self.camera_threads = []
        self.save_count = 0
        self.current_group = 0
        
        camera_devices = ['/dev/video0', '/dev/video2', '/dev/video4', 
                         '/dev/video6', '/dev/video8', '/dev/video10']
        
        # 在启动相机前，先用v4l2-ctl设置所有相机的参数
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
        
        # 创建相机显示和线程
        for i in range(6):
            display = QLabel()
            display.setMinimumSize(400, 300)
            display.setAlignment(Qt.AlignCenter)
            display.setStyleSheet("border: 1px solid black")
            self.displays.append(display)
            layout.addWidget(display, i // 3, i % 3)
            
            thread = CameraThread(camera_devices[i])
            thread.frame_signal.connect(lambda frame, display=display: 
                                      self.update_frame(frame, display))
            thread.save_completed_signal.connect(self.on_save_completed)
            thread.error_signal.connect(lambda msg: print(f"Error: {msg}"))
            self.camera_threads.append(thread)
            thread.start()
        
        # 添加控制按钮
        self.save_button = QPushButton("Save All Frames")
        self.save_button.clicked.connect(self.save_all_frames)
        layout.addWidget(self.save_button, 2, 1)
        
        # 设置相机组切换定时器
        self.switch_timer = QTimer()
        self.switch_timer.timeout.connect(self.switch_camera_group)
        self.switch_timer.start(5000)  # 每5秒切换一次组
        
        # 初始化第一组相机
        self.switch_camera_group()
        
    def update_frame(self, frame, display):
        h, w = frame.shape[:2]
        display_w = display.width()
        display_h = display.height()
        scaling = min(display_w/w, display_h/h)
        new_w = int(w * scaling)
        new_h = int(h * scaling)
        
        scaled_frame = cv2.resize(frame, (new_w, new_h))
        rgb_frame = cv2.cvtColor(scaled_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        display.setPixmap(QPixmap.fromImage(qt_image))
        
    def switch_camera_group(self):
        # 暂停当前组的相机
        current_devices = CAMERA_GROUPS[self.current_group]
        for i, device in enumerate(['/dev/video0', '/dev/video2', '/dev/video4', 
                                  '/dev/video6', '/dev/video8', '/dev/video10']):
            if device in current_devices:
                self.camera_threads[i].pause()
        
        # 切换到下一组
        self.current_group = (self.current_group + 1) % len(CAMERA_GROUPS)
        
        # 启动下一组的相机
        next_devices = CAMERA_GROUPS[self.current_group]
        for i, device in enumerate(['/dev/video0', '/dev/video2', '/dev/video4', 
                                  '/dev/video6', '/dev/video8', '/dev/video10']):
            if device in next_devices:
                self.camera_threads[i].resume()
        
    def save_all_frames(self):
        self.save_button.setEnabled(False)
        self.save_count = 0
        
        # 暂停自动切换
        self.switch_timer.stop()
        
        # 恢复所有相机
        for thread in self.camera_threads:
            thread.resume()
        
        # 等待相机初始化
        time.sleep(1)
        
        # 开始保存
        for thread in self.camera_threads:
            thread.save_flag = True
        
    def on_save_completed(self):
        self.save_count += 1
        if self.save_count >= len(self.camera_threads):
            self.save_button.setEnabled(True)
            self.save_count = 0
            # 重新开始自动切换
            self.switch_timer.start()
            
    def closeEvent(self, event):
        self.switch_timer.stop()
        for thread in self.camera_threads:
            thread.stop()
            thread.wait()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())