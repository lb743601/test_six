import cv2
import subprocess
import time
from datetime import datetime

def setup_camera(device_path, width=320, height=240):
    """初始化相机"""
    try:
        subprocess.run([
            'v4l2-ctl',
            '-d', device_path,
            '--set-fmt-video=width={},height={},pixelformat=YUYV'.format(width, height),
            '--set-parm=2',
            '-c', 'white_balance_temperature_auto=1',
            '-c', 'exposure_auto=3',
        ])
    except Exception as e:
        print(f"设置相机参数失败 {device_path}: {e}")

def capture_camera(device_path, save=False):
    """从指定相机捕获图像"""
    cap = cv2.VideoCapture(device_path)
    
    if save:
        # 设置高分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        # 等待几帧以确保画面稳定
        for _ in range(5):
            cap.read()
    else:
        # 预览分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    
    ret, frame = cap.read()
    cap.release()
    return ret, frame

def main():
    camera_paths = ['/dev/video0', '/dev/video2', '/dev/video4', 
                    '/dev/video6', '/dev/video8', '/dev/video10']
    
    # 初始化所有相机
    for path in camera_paths:
        setup_camera(path)
    
    print("按's'键开始拍摄所有相机")
    print("按'q'键退出程序")
    
    while True:
        # 从第一个相机获取预览画面
        ret, frame = capture_camera(camera_paths[0])
        if ret:
            cv2.imshow('Preview', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # 按's'开始拍摄
        if key == ord('s'):
            print("\n开始拍摄...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for i, path in enumerate(camera_paths):
                print(f"正在拍摄相机 {i+1}/6...")
                ret, frame = capture_camera(path, save=True)
                if ret:
                    filename = f"camera_{path.split('/')[-1]}_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"已保存: {filename}")
                else:
                    print(f"相机 {path} 拍摄失败")
                time.sleep(0.05)  # 等待USB带宽释放
            
            print("拍摄完成!")
        
        # 按'q'退出
        elif key == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()